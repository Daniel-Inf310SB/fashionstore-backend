"""Pruebas estructurales sin necesitar PostgreSQL ni enviar mensajes reales."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _parse(relative: str) -> ast.Module:
    return ast.parse((ROOT / relative).read_text(encoding="utf-8"))


def test_api_does_not_start_a_scheduler():
    tree = _parse("app/main.py")
    imports = [
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    ]
    assert not any(module.startswith("apscheduler") for module in imports)
    assert not any(
        isinstance(node, ast.FunctionDef)
        and node.name in {"start_background_scheduler", "stop_expiration_scheduler"}
        for node in ast.walk(tree)
    )


def test_worker_has_all_original_job_ids():
    tree = _parse("app/worker.py")
    job_ids = {
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "id" and isinstance(keyword.value, ast.Constant)
    }
    assert job_ids == {
        "fashionstore-expiration",
        "fashionstore-push-delivery",
        "fashionstore-marketing-notifications",
        "fashionstore-stripe-reconciliation",
    }


def test_worker_guards_against_multiple_instances():
    tree = _parse("app/worker.py")
    sql_literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    assert any("pg_try_advisory_lock" in value for value in sql_literals)
    assert any("pg_advisory_unlock" in value for value in sql_literals)
