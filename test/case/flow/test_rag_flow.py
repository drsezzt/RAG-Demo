#!/usr/bin/env python3
"""
RAG业务流程测试用例
测试文档上传→对话→删除完整流程
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.http_client import HttpClient
from common.assertions import assert_true, assert_status, assert_field_exists

RAG_BASE = os.environ.get("RAG_BASE", "http://127.0.0.1:8000")
TEST_DATA_PATH = os.environ.get("TEST_DATA_PATH", "test/config/test_data/test_data.txt")
DOC_NAME = os.environ.get("TEST_DATA_NAME", "test_data.txt")

client = HttpClient(RAG_BASE)

state = {"file_id": None}

CHAT_QUESTIONS = [
    "专利法所称的发明创造包括哪几种类型？",
    "职务发明创造申请专利的权利归属如何规定？",
]


def flow_upload_document():
    """流程步骤：上传文档"""
    print("[FLOW] Uploading document ...")
    
    if not os.path.isfile(TEST_DATA_PATH):
        raise AssertionError(f"TEST_DATA_PATH not found: {TEST_DATA_PATH}")
    
    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    payload = {"name": DOC_NAME, "content": content}
    code, j, body = client.post("/doc", payload, timeout=120)
    
    assert_status(code, 200, f"body={body}")
    assert_true(j.get("status") == "ok", f"expected status=ok, got {j}")
    
    code, j, body = client.get("/doc")
    assert_status(code, 200, f"body={body}")
    
    for d in j.get("docs", []):
        if isinstance(d, dict) and d.get("filename") == DOC_NAME:
            state["file_id"] = d.get("file_id")
            break
    
    print(f"[FLOW] Document uploaded: {DOC_NAME}, file_id={state['file_id']}")


def flow_chat_questions():
    """流程步骤：对话问答"""
    print("[FLOW] Asking questions ...")
    
    for i, question in enumerate(CHAT_QUESTIONS, 1):
        payload = {"text": question}
        code, j, body = client.post("/chat", payload, timeout=90)
        
        assert_status(code, 200, f"question {i} body={body}")
        assert_field_exists(j, "response", f"question {i} response={j}")
        assert_true(isinstance(j["response"], str), f"question {i} response should be string")
        
        response = j["response"]
        print(f"[FLOW] Q{i}: {question}")
        print(f"[FLOW] A{i}: {response[:100]}...")


def flow_delete_document():
    """流程步骤：删除文档"""
    print("[FLOW] Deleting document ...")
    
    file_id = state["file_id"]
    assert_true(file_id, "missing file_id before delete")
    
    code, j, body = client.delete(f"/doc/{file_id}", timeout=70)
    
    assert_status(code, 200, f"body={body}")
    assert_true(j.get("status") == "ok", f"expected status=ok, got {j}")
    print(f"[FLOW] Document deleted: file_id={file_id}")


if __name__ == "__main__":
    print("[TEST] RAG Flow Tests")
    
    try:
        flow_upload_document()
        flow_chat_questions()
        flow_delete_document()
        
        print("[TEST] ALL RAG FLOW TESTS PASSED")
    except Exception as e:
        print(f"[TEST] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
