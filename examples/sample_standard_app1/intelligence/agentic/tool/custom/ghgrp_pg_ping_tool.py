from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from agentuniverse.agent.action.tool.tool import Tool
from agentuniverse.base.config.component_configer.configers.tool_configer import ToolConfiger


class GhgrpPgPingTool(Tool):
    name: Optional[str] = None
    description: Optional[str] = None

    db_uri: Optional[str] = None
    default_schema: str = "core"
    statement_timeout_ms: int = 8000

    _engine: Optional[Engine] = None

    def initialize_by_component_configer(self, component_configer: ToolConfiger) -> "Tool":
        super().initialize_by_component_configer(component_configer)
        cfg = component_configer.configer.value

        self.db_uri = cfg.get("db_uri")
        self.default_schema = cfg.get("default_schema", "core")
        self.statement_timeout_ms = int(cfg.get("statement_timeout_ms", 8000))

        if not self.db_uri:
            raise ValueError("GhgrpPgPingTool: db_uri is required in yaml.")

        self._engine = create_engine(self.db_uri, pool_pre_ping=True, future=True)
        return self

    def execute(self, **kwargs) -> Dict[str, Any]:
        # ✅ 写死 SQL：优先做连通性 + schema + 表存在性验证
        sql = "SELECT current_database() AS db,current_user AS usr,version() AS pg_version,(SELECT COUNT(*) FROM core.facility) AS facility_cnt;"

        try:
            assert self._engine is not None
            with self._engine.connect() as conn:
                conn.execute(text(f"SET statement_timeout = {self.statement_timeout_ms}"))
                conn.execute(text(f"SET search_path TO {self.default_schema}"))
                row = conn.execute(text(sql)).mappings().first()

            return {"ok": True, "sql": sql, "result": dict(row) if row else None}

        except Exception as e:
            return {"ok": False, "sql": sql, "error": str(e)}
