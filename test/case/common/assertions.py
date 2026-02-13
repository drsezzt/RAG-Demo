#!/usr/bin/env python3
"""
断言工具
"""

def assert_true(cond, msg):
    """断言条件为真"""
    if not cond:
        raise AssertionError(msg)


def assert_status(code, expected, msg=""):
    """断言HTTP状态码"""
    if code != expected:
        raise AssertionError(f"Expected status {expected}, got {code}. {msg}")


def assert_response_type(j, expected_type, msg=""):
    """断言响应类型"""
    if not isinstance(j, expected_type):
        raise AssertionError(f"Expected type {expected_type}, got {type(j)}. {msg}")


def assert_field_exists(j, field, msg=""):
    """断言字段存在"""
    if field not in j:
        raise AssertionError(f"Field '{field}' not found. {msg}")


def assert_field_value(j, field, expected, msg=""):
    """断言字段值"""
    if j.get(field) != expected:
        raise AssertionError(f"Expected '{field}'={expected}, got {j.get(field)}. {msg}")
