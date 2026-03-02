from __future__ import annotations

import re
from typing import Optional, List, Any, Dict

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from agentuniverse.agent.action.tool.tool import Tool


class GhgRpSqlTool(Tool):
    """
    Lightweight, read-only SQL tool for GHGRP Postgres.
    """

    # these fields can be injected from YAML (custom keys are allowed)
    db_uri: Optional[str] = None
    default_schema: str = "core"
    allowed_schemas: List[str] = ["core"]
    default_limit: int = 50
    max_limit: int = 200
    query_timeout_seconds: int = 30

    _engine: Optional[Engine] = None

    def _get_engine(self) -> Engine:
        if not self.db_uri:
            raise ValueError("db_uri is empty. Please set db_uri in ghgrp_sql_tool.yaml")
        if self._engine is None:
            # pool_pre_ping avoids stale connections on long-running sessions
            self._engine = create_engine(self.db_uri, pool_pre_ping=True)
        return self._engine

    @staticmethod
    def _is_read_only(sql: str) -> bool:
        s = sql.strip().lower()
        return s.startswith("select") or s.startswith("with")

    @staticmethod
    def _has_limit(sql: str) -> bool:
        # naive but practical; ignores subqueries
        return bool(re.search(r"\blimit\b\s+\d+", sql, flags=re.IGNORECASE))

    @staticmethod
    def _extract_limit(sql: str) -> Optional[int]:
        m = re.search(r"\blimit\b\s+(\d+)", sql, flags=re.IGNORECASE)
        return int(m.group(1)) if m else None

    def _apply_limit_policy(self, sql: str) -> str:
        if not self._has_limit(sql):
            return f"{sql.rstrip(';')} LIMIT {int(self.default_limit)};"
        lim = self._extract_limit(sql)
        if lim is not None and lim > int(self.max_limit):
            # clamp the limit
            sql_no_semicolon = sql.rstrip(";")
            sql_no_semicolon = re.sub(r"\blimit\b\s+\d+", f"LIMIT {int(self.max_limit)}",
                                      sql_no_semicolon, flags=re.IGNORECASE)
            return sql_no_semicolon + ";"
        return sql

    def execute(self, input: str) -> str:
        if not input or not input.strip():
            return "SQL 为空。请提供 SELECT 或 WITH 开头的查询语句。"

        sql = input.strip()

        # read-only guard
        if not self._is_read_only(sql):
            return (
                "出于安全原因，本工具仅允许只读查询（SELECT/WITH）。\n"
                "请将需求改写为 SELECT（例如用查询验证，而不是写入/删除）。"
            )

        # enforce limit policy
        sql = self._apply_limit_policy(sql)

        engine = self._get_engine()

        # run query with schema search_path and timeout
        # Note: statement_timeout is per-connection; requires Postgres.
        with engine.connect() as conn:
            # schema control (optional)
            if self.default_schema:
                conn.execute(text(f"SET search_path TO {self.default_schema}"))
            if self.query_timeout_seconds:
                conn.execute(text(f"SET statement_timeout TO {int(self.query_timeout_seconds) * 1000}"))

            df = pd.read_sql(text(sql), conn)

        if df.empty:
            return f"查询已执行，但结果为空。\nSQL（已应用限制策略）:\n{sql}"

        # readable output (truncate wide columns)
        preview = df.head(int(self.max_limit))
        return f"SQL（已应用限制策略）:\n{sql}\n\n返回行数: {len(df)}\n\n结果预览:\n{preview.to_string(index=False)}"
