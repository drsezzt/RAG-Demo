#!/usr/bin/env python3
"""
VDB接口测试用例
测试 /doc 系列接口
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.http_client import HttpClient
from common.assertions import assert_true, assert_status, assert_response_type, assert_field_exists

RAG_BASE = os.environ.get("RAG_BASE", "http://127.0.0.1:8000")
TEST_DATA_PATH = os.environ.get("TEST_DATA_PATH", "test/config/test_data/test_data.txt")
DOC_NAME = os.environ.get("TEST_DATA_NAME", "test_data.txt")

client = HttpClient(RAG_BASE)

state = {"file_id": None}


def test_get_doc_empty():
    """测试获取空文档列表"""
    code, j, body = client.get("/doc")
    
    assert_status(code, 200, f"body={body}")
    assert_response_type(j, dict, f"response={j}")
    assert_field_exists(j, "docs", f"response={j}")
    assert_true(isinstance(j["docs"], list), f"docs should be list, got {type(j['docs'])}")


def test_add_doc():
    """测试添加文档"""
    if not os.path.isfile(TEST_DATA_PATH):
        raise AssertionError(f"TEST_DATA_PATH not found: {TEST_DATA_PATH}")
    
    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    payload = {"name": DOC_NAME, "content": content}
    code, j, body = client.post("/doc", payload, timeout=120)
    
    assert_status(code, 200, f"body={body}")
    assert_response_type(j, dict, f"response={j}")
    assert_true(j.get("status") == "ok", f"expected status=ok, got {j}")


def test_get_doc_after_add():
    """测试添加后获取文档列表"""
    code, j, body = client.get("/doc")
    
    assert_status(code, 200, f"body={body}")
    assert_field_exists(j, "docs", f"response={j}")
    
    docs = j["docs"]
    hit = None
    for d in docs:
        if isinstance(d, dict) and d.get("filename") == DOC_NAME:
            hit = d
            break
    
    assert_true(hit is not None, f"doc not found: filename={DOC_NAME}")
    
    file_id = hit.get("file_id")
    assert_true(isinstance(file_id, str) and file_id, f"invalid file_id: {hit}")
    state["file_id"] = file_id


def test_delete_doc():
    """测试删除文档"""
    file_id = state["file_id"]
    assert_true(file_id, "missing file_id before delete")
    
    code, j, body = client.delete(f"/doc/{file_id}", timeout=70)
    
    assert_status(code, 200, f"body={body}")
    assert_true(j.get("status") == "ok", f"expected status=ok, got {j}")


def test_get_doc_after_delete():
    """测试删除后获取文档列表"""
    code, j, body = client.get("/doc")
    
    assert_status(code, 200, f"body={body}")
    assert_field_exists(j, "docs", f"response={j}")
    
    for d in j["docs"]:
        if isinstance(d, dict) and d.get("file_id") == state["file_id"]:
            raise AssertionError(f"doc still exists after delete: {d}")


if __name__ == "__main__":
    print("[TEST] VDB API Tests")
    
    try:
        print("[TEST] test_get_doc_empty ...", flush=True)
        test_get_doc_empty()
        print("[TEST] test_get_doc_empty OK")
        
        print("[TEST] test_add_doc ...", flush=True)
        test_add_doc()
        print("[TEST] test_add_doc OK")
        
        print("[TEST] test_get_doc_after_add ...", flush=True)
        test_get_doc_after_add()
        print("[TEST] test_get_doc_after_add OK")
        
        print("[TEST] test_delete_doc ...", flush=True)
        test_delete_doc()
        print("[TEST] test_delete_doc OK")
        
        print("[TEST] test_get_doc_after_delete ...", flush=True)
        test_get_doc_after_delete()
        print("[TEST] test_get_doc_after_delete OK")
        
        print("[TEST] ALL VDB API TESTS PASSED")
    except Exception as e:
        print(f"[TEST] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
