#!/usr/bin/env python3
"""
HTTP客户端工具
"""

import json
import urllib.request
import urllib.error
import os

DEBUG = os.environ.get("DEBUG_HTTP") == "1"


def _short(x, n=300):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + f"...(truncated,len={len(s)})"


def http_json(method: str, url: str, payload=None, timeout=10):
    """
    发送HTTP JSON请求
    
    Args:
        method: HTTP方法 (GET, POST, DELETE等)
        url: 完整URL
        payload: 请求体 (dict)
        timeout: 超时时间(秒)
    
    Returns:
        (status_code, json_response, raw_body)
    """
    if DEBUG:
        print(f"[DEBUG] -> {method} {url} payload={_short(payload)}", flush=True)
    
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if DEBUG:
                print(f"[DEBUG] <- {resp.status} {resp.url}", flush=True)
            body = resp.read().decode("utf-8")
            try:
                j = json.loads(body) if body else None
            except Exception:
                j = None
            if DEBUG:
                print(f"[DEBUG] <- body={_short(body)}", flush=True)
            return resp.status, j, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return e.code, None, body


class HttpClient:
    """HTTP客户端类"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
    
    def get(self, path: str, timeout=10):
        return http_json("GET", f"{self.base_url}{path}", timeout=timeout)
    
    def post(self, path: str, payload=None, timeout=10):
        return http_json("POST", f"{self.base_url}{path}", payload, timeout)
    
    def delete(self, path: str, timeout=10):
        return http_json("DELETE", f"{self.base_url}{path}", timeout=timeout)
