# -*- coding: utf-8 -*-
"""
DbSchemaIntrospectTool (V3)
- 目标：只做“数据库结构浏览/诊断”，为后续 SQL 生成提供表名、字段、主键等基础信息
- 解耦原则：
  1) Agent 不包含任何 db_uri / schema / 连接细节
  2) Tool 通过 YAML 注入 db_uri / schema
- 默认仅枚举指定 schema 下的 BASE TABLE，并返回稳定排序
- 解析下沉：Tool 直接接收自然语言 input，自行解析 table_name / include_samples / sample_rows / include_pk / include_indexes 等
- 安全：table_name 必须在当前 schema 的表清单中命中后才会执行进一步查询；样例查询使用双引号引用 schema/table
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import inspect
import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# agentUniverse Tool 基类（不同版本路径可能略有差异）
try:
    from agentuniverse.agent.action.tool.tool import Tool
except Exception:
    from agentuniverse.agent.action.tool.base_tool import Tool  # type: ignore

from agentuniverse.base.config.component_configer.component_configer import ComponentConfiger


class DbSchemaIntrospectTool(Tool):
    """
    推荐用法（Agent 侧只传 input，让 Tool 自己解析意图）：
      tool.execute(input="列出 core 下的表")
      tool.execute(input="facility 表有哪些字段")
      tool.execute(input="core.facility 的字段 + 主键 + 2 行样例")
      tool.execute(input="给我 facility 的索引信息")
      tool.execute(input="只要字段，不要样例")

    兼容用法（显式参数覆盖解析结果，便于调试）：
      tool.execute(table_name="facility", include_samples=True, sample_rows=3, include_pk=True)
    """

    # ---------- YAML 注入 ----------
    db_uri: Optional[str] = None

    # 注意：为避免与父类/框架潜在属性冲突，不直接用 schema 字段名
    db_schema: str = "core"

    default_include_samples: bool = False
    default_sample_rows: int = 3
    max_sample_rows: int = 5

    default_include_pk: bool = True
    default_include_indexes: bool = False

    # ---------- runtime ----------
    _engine: Optional[Engine] = None

    def _initialize_by_component_configer(self, configer: ComponentConfiger) -> "DbSchemaIntrospectTool":
        super()._initialize_by_component_configer(configer)

        if hasattr(configer, "db_uri") and getattr(configer, "db_uri"):
            self.db_uri = str(configer.db_uri).strip()

        # 兼容 YAML 里仍然写 schema: core
        if hasattr(configer, "schema") and getattr(configer, "schema"):
            self.db_schema = str(configer.schema).strip() or self.db_schema
        if hasattr(configer, "db_schema") and getattr(configer, "db_schema"):
            self.db_schema = str(configer.db_schema).strip() or self.db_schema

        if hasattr(configer, "default_include_samples"):
            self.default_include_samples = bool(configer.default_include_samples)
        if hasattr(configer, "default_sample_rows"):
            self.default_sample_rows = int(configer.default_sample_rows)
        if hasattr(configer, "max_sample_rows"):
            self.max_sample_rows = int(configer.max_sample_rows)

        if hasattr(configer, "default_include_pk"):
            self.default_include_pk = bool(configer.default_include_pk)
        if hasattr(configer, "default_include_indexes"):
            self.default_include_indexes = bool(configer.default_include_indexes)
        self.db_schema = self.schema

        # 延迟创建 engine：避免在扫描阶段就连接 DB
        self._engine = None
        return self

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        兼容 AU 调用形态：execute(input=...), 或 execute(table_name=..., include_samples=..., sample_rows=...)
        """
        result: Dict[str, Any] = {
            "tool_file": inspect.getfile(self.__class__),
            "tool_class": self.__class__.__name__,
            "configured_schema": self.db_schema,
            "db_uri": self.db_uri,
            "capabilities": {
                "list_tables": True,
                "describe_table_columns": True,
                "describe_primary_key": True,
                "describe_indexes": True,
                "sample_rows": True,
            },
        }

        if not self.db_uri:
            result["error"] = "db_uri is empty. Please configure db_uri in yaml."
            return result

        user_text = (kwargs.get("input") or kwargs.get("query") or kwargs.get("text") or "").strip()

        explicit_table_name = kwargs.get("table_name", None)
        explicit_include_samples = kwargs.get("include_samples", None)
        explicit_sample_rows = kwargs.get("sample_rows", None)
        explicit_include_pk = kwargs.get("include_pk", None)
        explicit_include_indexes = kwargs.get("include_indexes", None)

        include_samples = self.default_include_samples
        sample_rows = self.default_sample_rows
        include_pk = self.default_include_pk
        include_indexes = self.default_include_indexes
        table_name: Optional[str] = None

        if user_text:
            parsed = self._parse_nl(user_text)
            table_name, p_samples, p_k, p_pk, p_idx = parsed
            if p_samples is not None:
                include_samples = p_samples
            if p_k is not None:
                sample_rows = p_k
            if p_pk is not None:
                include_pk = p_pk
            if p_idx is not None:
                include_indexes = p_idx

        # 显式参数覆盖
        if explicit_table_name:
            table_name = str(explicit_table_name).strip()
        if explicit_include_samples is not None:
            include_samples = bool(explicit_include_samples)
        if explicit_sample_rows is not None:
            try:
                sample_rows = int(explicit_sample_rows)
            except Exception:
                sample_rows = self.default_sample_rows
        if explicit_include_pk is not None:
            include_pk = bool(explicit_include_pk)
        if explicit_include_indexes is not None:
            include_indexes = bool(explicit_include_indexes)

        k = max(1, min(int(sample_rows), int(self.max_sample_rows)))

        engine = self._get_engine()
        with engine.connect() as conn:
            # 强制 search_path，避免漂移
            conn.execute(text("SET search_path TO :schema, public"), {"schema": self.db_schema})

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

            tables = sorted(self._list_tables(conn, schema=self.db_schema))
            result["tables"] = tables
            result["table_count"] = len(tables)

            if not table_name:
                result["resolved"] = {
                    "intent": "list_tables",
                    "schema": self.db_schema,
                    "table_name": None,
                    "include_samples": False,
                    "sample_rows": 0,
                    "include_pk": False,
                    "include_indexes": False,
                    "raw_input": user_text,
                }
                return result

            table_name_norm = self._normalize_table_name(table_name)
            if table_name_norm not in tables:
                result["error"] = f"table '{table_name_norm}' not found in schema '{self.db_schema}'"
                result["resolved"] = {
                    "intent": "describe_table",
                    "schema": self.db_schema,
                    "table_name": table_name_norm,
                    "include_samples": bool(include_samples),
                    "sample_rows": int(k) if include_samples else 0,
                    "include_pk": bool(include_pk),
                    "include_indexes": bool(include_indexes),
                    "raw_input": user_text,
                }
                return result

            result["table"] = f"{self.db_schema}.{table_name_norm}"
            result["columns"] = self._get_columns(conn, schema=self.db_schema, table=table_name_norm)

            if include_pk:
                result["primary_key"] = self._get_primary_key(conn, schema=self.db_schema, table=table_name_norm)
            else:
                result["primary_key"] = []

            if include_indexes:
                result["indexes"] = self._get_indexes(conn, schema=self.db_schema, table=table_name_norm)
            else:
                result["indexes"] = []

            if include_samples:
                sample_sql = f'SELECT * FROM "{self.db_schema}"."{table_name_norm}" LIMIT {k}'
                rows = conn.execute(text(sample_sql)).mappings().all()
                result["samples"] = [dict(r) for r in rows]
                result["sample_rows"] = len(result["samples"])
            else:
                result["samples"] = []
                result["sample_rows"] = 0

            result["resolved"] = {
                "intent": "describe_table",
                "schema": self.db_schema,
                "table_name": table_name_norm,
                "include_samples": bool(include_samples),
                "sample_rows": int(k) if include_samples else 0,
                "include_pk": bool(include_pk),
                "include_indexes": bool(include_indexes),
                "raw_input": user_text,
            }
            return result

    # ---------------- NL 解析 ----------------
    def _parse_nl(
            self, text_in: str
    ) -> Tuple[Optional[str], Optional[bool], Optional[int], Optional[bool], Optional[bool]]:
        """
        返回：table_name, include_samples, sample_rows, include_pk, include_indexes
        """
        t_raw = text_in.strip()
        t = t_raw.lower()

        include_samples: Optional[bool] = None
        if re.search(r"(样例|示例|例子|前\s*\d+\s*行|给我\s*\d+\s*行|看看\s*数据|几行|top\s*\d+|limit\s*\d+)", t):
            include_samples = True
        if re.search(r"(只要字段|不要样例|不需要样例|不看数据)", t):
            include_samples = False

        k: Optional[int] = None
        m = re.search(r"(?:前|top|limit)\s*(\d+)\s*行?", t)
        if not m:
            m = re.search(r"(\d+)\s*行\s*(?:样例|示例|数据)", t)
        if m:
            try:
                k = int(m.group(1))
            except Exception:
                k = None

        include_pk: Optional[bool] = None
        if re.search(r"(主键|primary\s*key|pk)", t):
            include_pk = True
        if re.search(r"(不要主键|不需要主键)", t):
            include_pk = False

        include_indexes: Optional[bool] = None
        if re.search(r"(索引|index|indexes)", t):
            include_indexes = True
        if re.search(r"(不要索引|不需要索引)", t):
            include_indexes = False

        # ---------------- 关键修复：表名提取（去掉 \b） ----------------
        table: Optional[str] = None

        # 1) “facility表” / “facility 表”
        m = re.search(r"([a-z_][a-z0-9_]*)\s*表", t)
        if m:
            table = m.group(1)

        # 2) “表名: facility” / “表名：facility”
        if not table:
            m = re.search(r"表名\s*[:：]?\s*([a-z_][a-z0-9_]*)", t)
            if m:
                table = m.group(1)

        # 3) “core.facility” / “staging.emission_record” ——只取 table 部分
        if not table:
            m = re.search(r"([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)", t)
            if m:
                table = m.group(2)

        # 4) 英文表达：describe facility / schema of facility / columns of facility
        if not table:
            m = re.search(r"(?:columns?\s+of|schema\s+of|describe)\s+([a-z_][a-z0-9_]*)", t)
            if m:
                table = m.group(1)

        return table, include_samples, k, include_pk, include_indexes

    @staticmethod
    def _normalize_table_name(name: str) -> str:
        n = name.strip().strip('"').strip("'")
        if "." in n:
            n = n.split(".", 1)[1]
        return n.strip()

    # ---------------- DB helpers ----------------
    def _get_engine(self) -> Engine:
        if self._engine is None:
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
                ORDER BY table_name
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

    @staticmethod
    def _get_primary_key(conn, schema: str, table: str) -> List[Dict[str, Any]]:
        """
        information_schema: table_constraints + key_column_usage
        返回形如：[{"column_name": "...", "ordinal_position": 1}, ...]
        """
        rows = conn.execute(
            text(
                """
                SELECT
                  kcu.column_name,
                  kcu.ordinal_position
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                 AND tc.table_name = kcu.table_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = :schema
                  AND tc.table_name = :table
                ORDER BY kcu.ordinal_position
                """
            ),
            {"schema": schema, "table": table},
        ).mappings().all()
        return [{"column_name": r["column_name"], "ordinal_position": int(r["ordinal_position"])} for r in rows]

    @staticmethod
    def _get_indexes(conn, schema: str, table: str) -> List[Dict[str, Any]]:
        """
        Postgres: pg_indexes 视图（如果不是 Postgres，该查询可能不可用）
        """
        try:
            rows = conn.execute(
                text(
                    """
                    SELECT schemaname, tablename, indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = :schema
                      AND tablename = :table
                    ORDER BY indexname
                    """
                ),
                {"schema": schema, "table": table},
            ).mappings().all()
            return [dict(r) for r in rows]
        except Exception:
            return []
