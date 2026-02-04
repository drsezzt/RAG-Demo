# 调用llm_service获取关键词
# 调用retriver获取文档
# 调用llm_client生成最终答案

import logging
import numpy as np
from rag_app.core import prompts
from rag_app.core import robust_json_parser

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
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class RAGService:
    def __init__(self, llm_client, vector_db):
        self.llm = llm_client
        self.vdb = vector_db
    def rewrite_query(self, user_input: str):
        logger.info("op=rewrite_query_start")

        """第一步：意图识别与关键词重写"""
        prompt = prompts.QUERY_REWRITE_TEMPLATE.format(user_input=user_input)
        response = self.llm.chat(
            prompt,
            temperature=0.01,
            top_p=0.1,
            max_tokens=8192
        )
        intent = robust_json_parser(response)

        logger.info("op=rewrite_query_done")

        return intent

    def retrieve(self, query):
        logger.info("op=retrieve_start")

        if self.vdb is None:
            return []

        store = self.vdb.store
        metadata = self.vdb.metadata
        embedder = self.vdb.embedder

        # 1. recall
        results = self.vdb.search(query)

        article_ids = set()

        for r in results:
            chunk = store.get(int(r["chunk_id"]))
            article_ids.update(chunk.article_ids)

        q_vec = embedder.embed_query(query)

        articles = []

        for aid in article_ids:
            embeds = self.vdb.load_embeddings()
            score = cosine_sim(q_vec, embeds[aid])
            articles.append((score, metadata.get_article(aid)))

        articles.sort(key=lambda x: x[0], reverse=True)

        logger.info("op=retrieve_done count=%d", len(articles))

        return articles[:2]

    def generate_answer(self, user_input, articles):
        logger.info(
            "op=generate_answer_start "
            f"user_input={user_input} "
            f"article_count={len(articles)}"
        )

        if not articles:
            return "未检索到相关知识文档。"

        # 获取最相关文档的分数
        best_score = articles[0][0]

        # 阈值控制：如果cosine分值小于0.65，说明结果质量较低
        if best_score < 0.65:
            return "抱歉，检索到的知识文档相关性较低，建议咨询人工。"

        """第三步：基于上下文生成答案"""
        content = "\n".join([art[1].text for art in articles])
        prompt = prompts.RAG_GENERATE_TEMPLATE.format(content=content, user_input=user_input)
        llm_raw_output = self.llm.chat(
            prompt,
            temperature=0.01,
            top_p=0.1,
            max_tokens=8192,
        )

        # 1. 预解析 LLM 输出的 JSON
        analysis = robust_json_parser(llm_raw_output)
        if analysis:
            title = " ".join([art[1].title for art in articles])
            tips_str = "\n".join([f"- {tip}" for tip in analysis.get("risk_tips", [])])
            print(f"{content}")
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

    def call_rag_flow(self, user_input):
        logger.info(
            "op=call_rag_flow_start "
            f"user_input={user_input}"
        )

        # 1. 重写
        try:
            intent = self.rewrite_query(user_input)
            search_words = intent.get('search_words', user_input)
        except Exception as e:
            logger.exception(
                "op=call_rag_flow_exception "
                f"intent={intent} "
                f"exception={type(e).__name__}"
            )
            search_words = user_input

        # 2. 检索
        articles = self.retrieve(search_words)

        # 3. 生成
        answer = self.generate_answer(user_input, articles)

        logger.info(
            "op=call_rag_flow_done "
            f"answer={answer}"
        )

        return answer