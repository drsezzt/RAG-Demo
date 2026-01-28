# 向量检索器
# 职责：封装FAISS的加载和查询逻辑，后续可支持其他向量数据库

import re
import os
import logging

logger = logging.getLogger("RAG_APP")

BGE_PATH = "rag_app/bge-small-zh-v1.5"          # BGE模型路径

os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'

def legal_search(vector_db, query, law_name, user_input):
    # 1. 强制提取条目（用正则，不要 LLM 提取的）
    regex_article = re.search(r'第[一二三四五六七八九十百0-9]+条', user_input)

    docs_with_score = []

    # 如果用户真的提到了某一条（比如问：二十九条是什么）
    if regex_article:
        target = regex_article.group(0)
        # 遍历查找精准匹配的条目
        for _, doc in vector_db.docstore._dict.items():
            if doc.metadata.get('article_name') == target:
                # 给精准匹配的条目赋予一个极高的分值（假设距离越小越相关，则设为 0.0）
                # 注意：如果你的向量库分数是余弦相似度（越大越相关），则设为 1.0
                doc.metadata['score'] = 0.0
                docs_with_score.append((doc, 0.0))
                break

    # 3. 语义搜索：改用 similarity_search_with_score
    # 返回格式为 List[Tuple[Document, float]]
    semantic_results = vector_db.similarity_search_with_score(
        query,
        k=4,
        filter={"law_name": law_name}
    )

    # 将语义搜索结果合并
    docs_with_score.extend(semantic_results)

    # 4. 去重且保留分值
    seen_content = set()
    unique_results = []
    for doc, score in docs_with_score:
        if doc.page_content not in seen_content:
            # 将分数记录在 metadata 中，方便 Service 层读取
            doc.metadata["score"] = round(float(score), 4)
            unique_results.append(doc)
            seen_content.add(doc.page_content)

    # 5. 按分数重新排序（如果是距离，升序；如果是相似度，降序）
    # 假设使用 FAISS 或 Chroma 的默认 L2 距离，升序排列
    unique_results.sort(key=lambda x: x.metadata["score"])

    return unique_results[:3] # 返回前3条最靠谱的
