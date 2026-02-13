#!/usr/bin/env python3
"""
LLM接口测试用例
测试 /chat 接口
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.http_client import HttpClient
from common.assertions import assert_true, assert_status, assert_response_type, assert_field_exists

LLM_BASE = os.environ.get("LLM_BASE", "http://127.0.0.1:8001")

client = HttpClient(LLM_BASE)


def test_chat():
    """测试LLM /chat 接口"""
    payload = {
        "text": "你好，请介绍一下自己",
        "history": []
    }
    code, j, body = client.post("/chat", payload, timeout=90)
    
    assert_status(code, 200, f"body={body}")
    assert_response_type(j, dict, f"response={j}")
    assert_field_exists(j, "response", f"response={j}")
    assert_true(isinstance(j["response"], str), f"response should be string, got {type(j['response'])}")


def test_chat_with_history():
    """测试带历史记录的对话"""
    payload = {
        "text": "继续介绍",
        "history": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！我是AI助手。"}
        ]
    }
    code, j, body = client.post("/chat", payload, timeout=90)
    
    assert_status(code, 200, f"body={body}")
    assert_field_exists(j, "response", f"response={j}")


if __name__ == "__main__":
    print("[TEST] LLM API Tests")
    
    try:
        print("[TEST] test_chat ...", flush=True)
        test_chat()
        print("[TEST] test_chat OK")
        
        print("[TEST] test_chat_with_history ...", flush=True)
        test_chat_with_history()
        print("[TEST] test_chat_with_history OK")
        
        print("[TEST] ALL LLM API TESTS PASSED")
    except Exception as e:
        print(f"[TEST] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
