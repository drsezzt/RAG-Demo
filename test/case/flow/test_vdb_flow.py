#!/usr/bin/env python3
"""
VDB业务流程测试用例
测试文档上传→列表→删除完整流程
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
    print(f"[FLOW] Document uploaded: {DOC_NAME}")


def flow_list_documents():
    """流程步骤：列出文档"""
    print("[FLOW] Listing documents ...")
    
    code, j, body = client.get("/doc")
    
    assert_status(code, 200, f"body={body}")
    assert_field_exists(j, "docs", f"response={j}")
    
    docs = j["docs"]
    assert_true(len(docs) > 0, "expected at least one document")
    
    hit = None
    for d in docs:
        if isinstance(d, dict) and d.get("filename") == DOC_NAME:
            hit = d
            break
    
    assert_true(hit is not None, f"doc not found: filename={DOC_NAME}")
    state["file_id"] = hit.get("file_id")
    print(f"[FLOW] Found document: file_id={state['file_id']}")


def flow_delete_document():
    """流程步骤：删除文档"""
    print("[FLOW] Deleting document ...")
    
    file_id = state["file_id"]
    assert_true(file_id, "missing file_id before delete")
    
    code, j, body = client.delete(f"/doc/{file_id}", timeout=70)
    
    assert_status(code, 200, f"body={body}")
    assert_true(j.get("status") == "ok", f"expected status=ok, got {j}")
    print(f"[FLOW] Document deleted: file_id={file_id}")


def flow_verify_deleted():
    """流程步骤：验证文档已删除"""
    print("[FLOW] Verifying document deleted ...")
    
    code, j, body = client.get("/doc")
    
    assert_status(code, 200, f"body={body}")
    
    for d in j.get("docs", []):
        if isinstance(d, dict) and d.get("file_id") == state["file_id"]:
            raise AssertionError(f"doc still exists after delete: {d}")
    
    print("[FLOW] Document verified as deleted")


if __name__ == "__main__":
    print("[TEST] VDB Flow Tests")
    
    try:
        flow_upload_document()
        flow_list_documents()
        flow_delete_document()
        flow_verify_deleted()
        
        print("[TEST] ALL VDB FLOW TESTS PASSED")
    except Exception as e:
        print(f"[TEST] FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
