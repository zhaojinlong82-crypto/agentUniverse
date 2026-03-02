# -*- coding: utf-8 -*-
"""
GhgrpSchemaTool (Core V2)
- 只读取指定 schema(默认 core) 的表/字段信息（严格限定 information_schema.table_schema）
- 返回稳定排序（多次运行不漂移）
- 解析下沉：Tool 直接接收自然语言 input，自行解析 table_name / include_samples / sample_rows
- 返回 tool_file + DB fingerprint，方便定位“加载了哪个类/连到了哪个库”
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


class GhgrpSchemaTool(Tool):
    """
    推荐用法（Agent 侧只传 input）：
      tool.execute(input="列出 core 下的表")
      tool.execute(input="facility 表有哪些字段")
      tool.execute(input="给我 facility 表前 3 行样例数据")
      tool.execute(input="core.facility 的字段 + 2 行样例")

    兼容用法（显式参数覆盖解析结果）：
      tool.execute(table_name="facility", include_samples=True, sample_rows=3)
    """

    # ---------- YAML 注入 ----------
    db_uri: Optional[str] = None

    # 注意：为避免与父类/框架潜在属性冲突，不直接用 schema 字段名
    db_schema: str = "core"

    default_include_samples: bool = False
    default_sample_rows: int = 3
    max_sample_rows: int = 5

    # ---------- runtime ----------
    _engine: Optional[Engine] = None

    # ========== 生命周期：读取 YAML ==========
    def _initialize_by_component_configer(self, configer: ComponentConfiger) -> "GhgrpSchemaTool":
        super()._initialize_by_component_configer(configer)

        # db_uri
        if hasattr(configer, "db_uri") and getattr(configer, "db_uri"):
            self.db_uri = configer.db_uri

        # schema：兼容 YAML 里仍然写 schema: core
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

        # 延迟创建 engine：避免在扫描阶段就连接 DB
        self._engine = None
        return self

    # ========== 核心执行 ==========
    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        兼容 AU 调用形态：execute(input=...), 或 execute(table_name=..., include_samples=..., sample_rows=...)
        """
        # 0) 基础输出：定位加载与连接
        result: Dict[str, Any] = {
            "tool_file": inspect.getfile(self.__class__),
            "tool_class": self.__class__.__name__,
            "configured_schema": self.db_schema,
            "db_uri": self.db_uri,
        }
        if not self.db_uri:
            result["error"] = "db_uri is empty. Please configure db_uri in yaml."
            return result

        # 1) 取入参（优先显式参数；否则走 input 解析）
        user_text = (kwargs.get("input") or kwargs.get("query") or kwargs.get("text") or "").strip()

        explicit_table_name = kwargs.get("table_name", None)
        explicit_include_samples = kwargs.get("include_samples", None)
        explicit_sample_rows = kwargs.get("sample_rows", None)

        # 2) 先给默认值
        include_samples = self.default_include_samples
        sample_rows = self.default_sample_rows
        table_name: Optional[str] = None

        # 3) 如果用户传了自然语言 input，则解析
        if user_text:
            parsed_table, parsed_include, parsed_k = self._parse_nl(user_text)
            if parsed_table:
                table_name = parsed_table
            if parsed_include is not None:
                include_samples = parsed_include
            if parsed_k is not None:
                sample_rows = parsed_k

        # 4) 显式参数覆盖解析结果（用于你调试/强制）
        if explicit_table_name:
            table_name = str(explicit_table_name).strip()
        if explicit_include_samples is not None:
            include_samples = bool(explicit_include_samples)
        if explicit_sample_rows is not None:
            try:
                sample_rows = int(explicit_sample_rows)
            except Exception:
                sample_rows = self.default_sample_rows

        # 5) sample_rows 边界
        k = max(1, min(int(sample_rows), int(self.max_sample_rows)))

        # 6) 建立 engine（只建一次）
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

            # 严格限定 schema 表清单
            tables = sorted(self._list_tables(conn, schema=self.db_schema))
            result["tables"] = tables
            result["table_count"] = len(tables)

            # 如果没有识别到 table_name：只返回表列表（这是“列出 core 下的表”的标准行为）
            if not table_name:
                result["resolved"] = {
                    "intent": "list_tables",
                    "table_name": None,
                    "include_samples": False,
                    "sample_rows": 0,
                    "raw_input": user_text,
                }
                return result

            # 规范化表名（去掉可能的 core. 前缀/引号）
            table_name_norm = self._normalize_table_name(table_name)

            # 验证表是否存在
            if table_name_norm not in tables:
                result["error"] = f"table '{table_name_norm}' not found in schema '{self.db_schema}'"
                result["resolved"] = {
                    "intent": "describe_table",
                    "table_name": table_name_norm,
                    "include_samples": bool(include_samples),
                    "sample_rows": int(k) if include_samples else 0,
                    "raw_input": user_text,
                }
                return result

            # 字段信息
            cols = self._get_columns(conn, schema=self.db_schema, table=table_name_norm)
            result["table"] = f"{self.db_schema}.{table_name_norm}"
            result["columns"] = cols

            # 可选样例
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
                "table_name": table_name_norm,
                "include_samples": bool(include_samples),
                "sample_rows": int(k) if include_samples else 0,
                "raw_input": user_text,
            }
            return result

    # ========== NL 解析（方案 A：下沉到 Tool） ==========
    def _parse_nl(self, text_in: str) -> Tuple[Optional[str], Optional[bool], Optional[int]]:
        """
        返回：table_name, include_samples, sample_rows
        - table_name：识别 “facility 表 / core.facility / 表 facility / 表名 facility”
        - include_samples：识别 “样例/示例/前N行/看看数据/给我几行”
        - sample_rows：从 “前3行/3行样例/limit 3/top 3” 抽取 N
        """
        t = text_in.strip().lower()

        # 1) include_samples 意图
        include_samples = None
        if re.search(r"(样例|示例|例子|前\s*\d+\s*行|给我\s*\d+\s*行|看看\s*数据|几行|top\s*\d+|limit\s*\d+)", t):
            include_samples = True
        if re.search(r"(只要字段|不要样例|不需要样例|不看数据)", t):
            include_samples = False

        # 2) 行数
        k = None
        m = re.search(r"(?:前|top|limit)\s*(\d+)\s*行?", t)
        if not m:
            m = re.search(r"(\d+)\s*行\s*(?:样例|示例|数据)", t)
        if m:
            try:
                k = int(m.group(1))
            except Exception:
                k = None

        # 3) 表名：尽量保守，只在“像表名”的位置提取
        #    支持：core.facility / "facility" / facility 表 / 表 facility / 表名 facility
        table = None

        m = re.search(r"\b([a-z_][a-z0-9_]*)\s*表\b", t)
        if m:
            table = m.group(1)

        if not table:
            m = re.search(r"\b表名[:：]?\s*([a-z_][a-z0-9_]*)\b", t)
            if m:
                table = m.group(1)

        if not table:
            m = re.search(r"\bcore\.([a-z_][a-z0-9_]*)\b", t)
            if m:
                table = m.group(1)

        if not table:
            # “describe facility / columns of facility” 这类英文提示也兼容一下
            m = re.search(r"(?:columns?\s+of|schema\s+of|describe)\s+([a-z_][a-z0-9_]*)", t)
            if m:
                table = m.group(1)

        return table, include_samples, k

    @staticmethod
    def _normalize_table_name(name: str) -> str:
        n = name.strip().strip('"').strip("'")
        if "." in n:
            # core.facility -> facility
            n = n.split(".", 1)[1]
        return n.strip()

    # ========== 内部 DB 方法 ==========
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
