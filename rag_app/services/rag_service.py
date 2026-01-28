# 调用llm_service获取关键词
# 调用retriver获取文档
# 调用llm_client生成最终答案

import json
import logging
from rag_app.core import prompts
from rag_app.core import legal_search
from rag_app.core import robust_json_parser

logger = logging.getLogger("RAG_APP")

REPLY_REPORT_TEMPLATE = """
### ⚖️ 法律回复报告

**【核心法条】**：{law_title}

**【法条原文】**：
> {law_content}

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

class RAGService:
    def __init__(self, llm_client, vector_db):
        self.llm = llm_client
        self.vdb = vector_db
    def rewrite_query(self, user_input: str):
        """第一步：意图识别与关键词重写"""
        prompt = prompts.QUERY_REWRITE_TEMPLATE.format(user_input=user_input)
        response = self.llm.chat(
            prompt,
            temperature=0.01,
            top_p=0.1,
            max_tokens=8192
        )
        return robust_json_parser(response)

    def retrieve_docs(self, query, law_name, user_input):
        if self.vdb is None:
            return []

        """第二步：向量库检索"""
        if not law_name.startswith("中华人民共和国"):
            law_name = "中华人民共和国" + law_name

        return legal_search(self.vdb, query, law_name, user_input)

    def generate_answer(self, user_input, docs):
        if not docs:
            return "未检索到相关法律条文。"

        # 获取最相关文档的分数
        best_score = docs[0].metadata.get('score', 1.0)

        # 阈值控制：如果分值（距离）大于 0.6，说明语义上已经不相关了
        if best_score > 0.6:
            return "抱歉，检索到的法律条文相关性较低，建议咨询人工律师。"

        """第三步：基于上下文生成答案"""
        content = "\n".join([d.page_content for d in docs])
        prompt = prompts.RAG_GENERATE_TEMPLATE.format(content=content, user_input=user_input)
        llm_raw_output = self.llm.chat(
            prompt,
            temperature=0.01,
            top_p=0.1,
            max_tokens=8192,
        )
        # 1. 预解析 LLM 输出的 JSON
        analysis = robust_json_parser(llm_raw_output)
        # 2. 从检索到的 docs 中提取真实法条信息（保证绝对准确）
        law_title = docs[0].metadata.get("article_name", "相关法律条款")
        law_content = docs[0].page_content
        # 3. 使用Markdown美化排版
        tips_str = "\n".join([f"- {tip}" for tip in analysis.get("risk_tips", [])])
        final_report = REPLY_REPORT_TEMPLATE.format(
            law_title=law_title,
            law_content=law_content,
            intent_analysis=analysis.get("intent_analysis", "未知场景"),
            conclusion=analysis.get("conclusion", "请咨询人工确认"),
            detailed_logic=analysis.get("detailed_logic", "分析过程缺失"),
            risk_tips=tips_str
        )

        return final_report

    def call_rag_flow(self, user_input):
        # 1. 重写
        try:
            intent = self.rewrite_query(user_input)
            search_words = intent.get('search_words', user_input)
            law_name = intent.get('law_name', '')
        except Exception as e:
            search_words, law_name = user_input, ""

        # 2. 检索
        docs = self.retrieve_docs(search_words, law_name, user_input)

        # 3. 生成
        return self.generate_answer(user_input, docs)