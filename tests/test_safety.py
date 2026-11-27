"""Tests for operation classification and SQL guards."""

import pytest

from ucm_mcp.safety import (
    assert_operation_allowed,
    assert_read_only_sql,
    classify_operation,
)


def test_classify_read_and_write():
    assert classify_operation("get_phone") == "read"
    assert classify_operation("list_process_nodes") == "read"
    assert classify_operation("run_sql_query") == "read"
    assert classify_operation("sql_query_inactive") == "read"
    assert classify_operation("add_phone") == "write"
    assert classify_operation("do_device_reset") == "write"
    assert classify_operation("sql_update") == "write"


def test_assert_operation_allowed_blocks_writes():
    assert_operation_allowed("get_user", allow_writes=False)
    with pytest.raises(PermissionError):
        assert_operation_allowed("add_user", allow_writes=False)
    assert_operation_allowed("add_user", allow_writes=True)


def test_read_only_sql_accepts_select():
    assert assert_read_only_sql("SELECT name FROM device") == "SELECT name FROM device"
    assert assert_read_only_sql("  with x as (select 1) select * from x; ").lower().startswith(
        "with"
    )


def test_read_only_sql_rejects_mutations():
    with pytest.raises(ValueError):
        assert_read_only_sql("DELETE FROM device")
    with pytest.raises(ValueError):
        assert_read_only_sql("SELECT 1; DROP TABLE device")
    with pytest.raises(ValueError):
        assert_read_only_sql("UPDATE device SET name='x'")
