#!/usr/bin/env python3
"""
RAG接口测试用例
测试 /chat 接口
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.http_client import HttpClient
from common.assertions import assert_true, assert_status, assert_response_type, assert_field_exists

RAG_BASE = os.environ.get("RAG_BASE", "http://127.0.0.1:8000")

client = HttpClient(RAG_BASE)

CHAT_CASES = [
    "专利法所称的发明创造包括哪几种类型？",
    "申请专利的发明创造涉及国家安全或重大利益需要保密的，应当如何处理？",
]


def test_chat():
    """测试RAG /chat 接口"""
    for i, text in enumerate(CHAT_CASES, 1):
        payload = {"text": text}
        code, j, body = client.post("/chat", payload, timeout=90)
        
        assert_status(code, 200, f"case {i} body={body}")
        assert_response_type(j, dict, f"case {i} response={j}")
        assert_field_exists(j, "response", f"case {i} response={j}")
        assert_true(isinstance(j["response"], str), f"case {i} response should be string")
        print(f"[TEST] chat case {i} OK")


if __name__ == "__main__":
    print("[TEST] RAG API Tests")
    
    try:
        print("[TEST] test_chat ...", flush=True)
        test_chat()
        print("[TEST] test_chat OK")
        
        print("[TEST] ALL RAG API TESTS PASSED")
    except Exception as e:
        print(f"[TEST] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
