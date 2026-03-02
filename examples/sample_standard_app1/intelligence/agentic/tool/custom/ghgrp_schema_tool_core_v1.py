# -*- coding: utf-8 -*-
"""
GhgrpSchemaTool
- 强制只读取指定 schema(默认 core) 的表/字段信息
- 返回稳定排序（多次运行不漂移）
- 返回 tool_file + DB fingerprint，用于定位“加载了哪个类/连到了哪个库”
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import inspect

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# agentUniverse Tool 基类（不同版本路径可能略有差异）
try:
    from agentuniverse.agent.action.tool.tool import Tool
except Exception:
    # 兼容兜底：有些版本在这里
    from agentuniverse.agent.action.tool.base_tool import Tool  # type: ignore

from agentuniverse.base.config.component_configer.component_configer import ComponentConfiger


class GhgrpSchemaTool(Tool):
    """
    输入参数（execute）：
      - table_name: 可选，指定表名（不带 schema），例如 "facility"
      - include_samples: 可选，是否返回样例行
      - sample_rows: 可选，样例行数（会被 max_sample_rows 限制）
    """

    # --- 由 YAML 注入 ---
    db_uri: Optional[str] = None
    schema: str = "core"

    default_include_samples: bool = False
    default_sample_rows: int = 3
    max_sample_rows: int = 5

    # --- runtime ---
    _engine: Optional[Engine] = None

    # ========== 生命周期：读取 YAML ==========
    def _initialize_by_component_configer(self, configer: ComponentConfiger) -> "GhgrpSchemaTool":
        super()._initialize_by_component_configer(configer)

        # YAML: db_uri / schema / default_include_samples / default_sample_rows / max_sample_rows
        if hasattr(configer, "db_uri"):
            self.db_uri = configer.db_uri
        if hasattr(configer, "schema") and configer.schema:
            self.schema = configer.schema

        if hasattr(configer, "default_include_samples"):
            self.default_include_samples = bool(configer.default_include_samples)
        if hasattr(configer, "default_sample_rows"):
            self.default_sample_rows = int(configer.default_sample_rows)
        if hasattr(configer, "max_sample_rows"):
            self.max_sample_rows = int(configer.max_sample_rows)

        # 延迟创建 engine：避免在扫描阶段就连接 DB
        self._engine = None
        return self

    # ========== 核心执行 ==========
    def execute(
        self,
        table_name: Optional[str] = None,
        include_samples: Optional[bool] = None,
        sample_rows: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # --- 1) 先输出“我到底加载的哪个文件” ---
        result: Dict[str, Any] = {
            "tool_file": inspect.getfile(self.__class__),
            "tool_class": self.__class__.__name__,
            "configured_schema": self.schema,
            "db_uri": self.db_uri,
        }

        if not self.db_uri:
            result["error"] = "db_uri is empty. Please configure db_uri in yaml."
            return result

        # --- 2) 参数默认值与边界 ---
        if include_samples is None:
            include_samples = self.default_include_samples
        if sample_rows is None:
            sample_rows = self.default_sample_rows

        try:
            k = int(sample_rows)
        except Exception:
            k = self.default_sample_rows
        k = max(1, min(k, int(self.max_sample_rows)))

        # --- 3) 建立 engine（只建一次） ---
        engine = self._get_engine()

        # --- 4) 连接并“固定 search_path”，并返回 DB 指纹 ---
        with engine.connect() as conn:
            # 强制 search_path：避免 current_schema / 未限定 schema 导致漂移
            conn.execute(text("SET search_path TO :schema, public"), {"schema": self.schema})

            fp = conn.execute(
                text(
                    """
                    SELECT
                      current_database() AS db,
                      current_user AS usr,
                      current_schema() AS cur_schema,
                      current_setting('search_path') AS search_path,
                      inet_server_addr() AS server_addr,
                      inet_server_port() AS server_port,
                      version() AS version
                    """
                )
            ).mappings().first()
            result["fingerprint"] = dict(fp) if fp else {}

            # --- 5) 读取 schema->tables（严格限定 table_schema = :schema） ---
            tables = self._list_tables(conn, schema=self.schema)

            # 稳定排序（确定性）
            tables = sorted(tables)
            result["tables"] = tables

            # 如果只要表清单，到这里就可以返回
            if not table_name:
                # 还可以把 schema 内表数量返回，便于 sanity check
                result["table_count"] = len(tables)
                return result

            # --- 6) 指定表：字段信息 + 可选样例 ---
            if table_name not in tables:
                result["error"] = f"table '{table_name}' not found in schema '{self.schema}'"
                result["available_tables"] = tables
                return result

            columns = self._get_columns(conn, schema=self.schema, table=table_name)
            # 稳定排序：按 ordinal_position
            result["table"] = f"{self.schema}.{table_name}"
            result["columns"] = columns

            if include_samples:
                sample_sql = f'SELECT * FROM "{self.schema}"."{table_name}" LIMIT {k}'
                rows = conn.execute(text(sample_sql)).mappings().all()
                result["samples"] = [dict(r) for r in rows]
                result["sample_rows"] = len(result["samples"])
            else:
                result["samples"] = []
                result["sample_rows"] = 0

            return result

    # ========== 内部工具函数 ==========
    def _get_engine(self) -> Engine:
        if self._engine is None:
            # pool_pre_ping 避免长连接断开导致奇怪行为
            self._engine = create_engine(self.db_uri, pool_pre_ping=True, future=True)
        return self._engine

    @staticmethod
    def _list_tables(conn, schema: str) -> List[str]:
        rows = conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema
                  AND table_type = 'BASE TABLE'
                """
            ),
            {"schema": schema},
        ).mappings().all()
        return [r["table_name"] for r in rows]

    @staticmethod
    def _get_columns(conn, schema: str, table: str) -> List[Dict[str, Any]]:
        rows = conn.execute(
            text(
                """
                SELECT
                  ordinal_position,
                  column_name,
                  data_type,
                  udt_name,
                  is_nullable
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table
                ORDER BY ordinal_position
                """
            ),
            {"schema": schema, "table": table},
        ).mappings().all()

        cols: List[Dict[str, Any]] = []
        for r in rows:
            cols.append(
                {
                    "ordinal_position": int(r["ordinal_position"]),
                    "column_name": r["column_name"],
                    "data_type": r["data_type"],
                    "udt_name": r["udt_name"],
                    "is_nullable": r["is_nullable"],
                }
            )
        return cols
