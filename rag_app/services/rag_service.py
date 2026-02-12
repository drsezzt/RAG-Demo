# 调用llm_service获取关键词
# 调用retriver获取文档
# 调用llm_client生成最终答案

import logging
import numpy as np
from typing import List, Tuple, Optional
from rag_app.core import prompts
from rag_app.core import robust_json_parser
from shared.config import get_rag_config
from rag_app.core.interface import ILLMClient, IVectorStoreService


logger = logging.getLogger("RAG_APP")

REPLY_REPORT_TEMPLATE = """
### ⚖️ 法律回复报告

**【核心法条】**：{doc_title}

**【法条原文】**：
> {doc_content}

---

**【律师分析】**：
* **场景判断**：{intent_analysis}
* **法律结论**：**{conclusion}**
* **逻辑推导**：{detailed_logic}

**【💡 避坑提示】**：
{risk_tips}

---
*免责声明：本回复由 AI 律师助手根据公开法条生成，不构成正式法律意见。*
"""

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """计算余弦相似度"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class RAGService:
    """RAG 服务，负责完整的 RAG 流程"""

    def __init__(
        self,
        llm_client: ILLMClient,
        vector_db: IVectorStoreService
    ):
        """
        初始化 RAG 服务

        Args:
            llm_client: LLM 客户端接口
            vector_db: 向量存储服务接口
        """
        self.llm = llm_client
        self.vdb = vector_db

        # 加载全局配置
        self.rag_config = get_rag_config()

        logger.info(
            "RAGService initialized with config: "
            f"similarity_threshold={self.rag_config.similarity_threshold}, "
            f"top_k={self.rag_config.top_k_retrieval}, "
            f"max_articles={self.rag_config.max_retrieved_articles}"
        )

    def rewrite_query(self, user_input: str) -> dict:
        """
        重写查询：意图识别与关键词提取

        Args:
            user_input: 用户输入

        Returns:
            dict: 包含意图和关键词的字典
        """
        logger.info("op=rewrite_query_start")

        # 使用配置中的 LLM 参数
        prompt = prompts.QUERY_REWRITE_TEMPLATE.format(user_input=user_input)
        response = self.llm.chat(
            prompt,
            temperature=self.rag_config.chat_temperature,
            top_p=self.rag_config.chat_top_p,
            max_tokens=self.rag_config.chat_max_tokens
        )
        intent = robust_json_parser(response)

        logger.info("op=rewrite_query_done")

        return intent

    def retrieve(self, query: str) -> List[Tuple[float, dict]]:
        """
        检索相关文档

        Args:
            query: 查询文本

        Returns:
            List[Tuple[float, dict]]: 检索结果列表，每个元素为(相似度分数, 文章元数据)
        """
        logger.info("op=retrieve_start")

        if self.vdb is None:
            return []

        # 使用配置中的检索参数
        results = self.vdb.search(query, self.rag_config.top_k_retrieval)

        article_ids = set()

        for r in results:
            # 注意：这里仍然存在耦合，需要后续重构
            # 理想情况下应该通过接口方法获取，而不是直接访问内部属性
            store = self.vdb.store  # 临时解决方案
            chunk = store.get(int(r["chunk_id"]))
            article_ids.update(chunk.article_ids)

        # 获取嵌入器
        embedder = self.vdb.embedder  # 临时解决方案
        q_vec = embedder.embed_query(query)

        articles = []

        for aid in article_ids:
            # 获取文章向量
            article_store = self.vdb.article_store  # 临时解决方案
            vec = article_store.get(aid)
            if vec is not None:
                score = cosine_sim(q_vec, vec)

                # 获取文章元数据
                metadata = self.vdb.metadata  # 临时解决方案
                article_meta = metadata.get_article(aid)
                if article_meta:
                    articles.append((score, article_meta))

        # 按相似度排序
        articles.sort(key=lambda x: x[0], reverse=True)

        # 使用配置中的最大文章数
        max_articles = self.rag_config.max_retrieved_articles
        result = articles[:max_articles]

        logger.info("op=retrieve_done count=%d", len(result))

        return result

    def generate_answer(
        self,
        user_input: str,
        articles: List[Tuple[float, dict]]
    ) -> str:
        """
        生成答案

        Args:
            user_input: 用户输入
            articles: 检索到的文章列表

        Returns:
            str: 生成的答案
        """
        logger.info(
            "op=generate_answer_start "
            f"user_input={user_input} "
            f"article_count={len(articles)}"
        )

        if not articles:
            return "未检索到相关知识文档。"

        # 获取最相关文档的分数
        best_score = articles[0][0]

        # 使用配置中的相似度阈值
        if best_score < self.rag_config.similarity_threshold:
            return "抱歉，检索到的知识文档相关性较低，建议咨询人工。"

        # 基于上下文生成答案
        content = "\n".join([art[1].text for art in articles])
        prompt = prompts.RAG_GENERATE_TEMPLATE.format(content=content, user_input=user_input)

        llm_raw_output = self.llm.chat(
            prompt,
            temperature=self.rag_config.chat_temperature,
            top_p=self.rag_config.chat_top_p,
            max_tokens=self.rag_config.chat_max_tokens,
        )

        # 解析 LLM 输出的 JSON
        analysis = robust_json_parser(llm_raw_output)
        if analysis:
            title = " ".join([art[1].title for art in articles])
            tips_str = "\n".join([f"- {tip}" for tip in analysis.get("risk_tips", [])])

            final_report = REPLY_REPORT_TEMPLATE.format(
                doc_title=title,
                doc_content=content,
                intent_analysis=analysis.get("intent_analysis", "未知场景"),
                conclusion=analysis.get("conclusion", "请咨询人工确认"),
                detailed_logic=analysis.get("detailed_logic", "分析过程缺失"),
                risk_tips=tips_str
            )
        else:
            final_report = llm_raw_output

        logger.info("op=generate_answer_done")

        return final_report

    def call_rag_flow(self, user_input: str) -> str:
        """
        执行完整的 RAG 流程

        Args:
            user_input: 用户输入

        Returns:
            str: RAG 生成的答案
        """
        logger.info(
            "op=call_rag_flow_start "
            f"user_input={user_input}"
        )

        # 1. 查询重写
        try:
            intent = self.rewrite_query(user_input)
            search_words = intent.get('search_words', user_input)
        except Exception as e:
            logger.exception(
                "op=call_rag_flow_exception "
                f"exception={type(e).__name__}"
            )
            search_words = user_input

        # 2. 文档检索
        articles = self.retrieve(search_words)

        # 3. 答案生成
        answer = self.generate_answer(user_input, articles)

        logger.info(
            "op=call_rag_flow_done "
            f"answer_length={len(answer)}"
        )

        return answer