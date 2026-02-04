# 鲁棒性解析器
# 职责：存放处理模型输出数据

import json
import re
import logging

logger = logging.getLogger("RAG_APP")

def robust_json_parser(raw_text: str):
    """
    通用 LLM JSON 提取器：
    支持意图识别、法律生成、结构化抽取等所有场景。
    """
    if not raw_text:
        return {}

    # 1. 清理常见的 Markdown 标记
    # 有些模型会返回 ```json \n { ... } \n ```
    clean_text = raw_text.strip()
    clean_text = re.sub(r'^```json\s*|```$', '', clean_text, flags=re.MULTILINE)

    # 如果开头缺少大括号，手动补全
    if not clean_text.startswith("{"):
        clean_text = "{" + clean_text

    try:
        # 2. 尝试标准解析
        return json.loads(clean_text)
    except json.JSONDecodeError:
        try:
            # 3. 深度提取：正则寻找第一个 '{' 和最后一个 '}'
            match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if match:
                target_json = match.group()
                # 处理非法换行（可选，视模型表现而定）
                target_json = target_json.replace('\n', '\\n')
                return json.loads(target_json)
        except Exception:
            # 4. 终极回退：解析失败时不让程序挂掉
            return {}
