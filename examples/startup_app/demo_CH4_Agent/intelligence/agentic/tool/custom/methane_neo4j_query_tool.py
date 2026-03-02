# !/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import re
from typing import Optional, Dict, Any, Tuple

from pydantic import Field

from agentuniverse.agent.action.tool.tool import Tool
from agentuniverse.agent.action.knowledge.store.store_manager import StoreManager
from agentuniverse.agent.action.knowledge.store.query import Query


class MethaneNeo4jQueryTool(Tool):
    """
    甲烷排放设施知识图谱（Neo4j）直连查询工具（基于 Neo4jStore，不直接依赖 neo4j driver）。
    输入：自然语言 input
    输出：JSON（intent / cypher / params / rows）
    """

    store_name: str = Field(default="neo4j_store.yaml")

    def execute(self, input: str) -> str:
        question = (input or "").strip()
        if not question:
            return json.dumps({"error": "input 为空"}, ensure_ascii=False)

        intent, cypher, params = self._nlu_to_cypher(question)

        store = StoreManager().get_instance_obj(self.store_name)
        if store is None:
            return json.dumps(
                {"error": f"找不到 Store: {self.store_name}。请确认 neo4j_store.yaml.yaml 被扫描加载且 name 匹配。"},
                ensure_ascii=False
            )

        # Neo4jStore.query 必须带 ext_info.query_type
        q = Query(
            query_str=cypher,
            ext_info={
                "query_type": "direct_cypher",
                "query_params": params or {}
            }
        )

        docs = store.query(q)
        if not docs:
            return json.dumps({"intent": intent, "cypher": cypher, "params": params, "rows": []}, ensure_ascii=False)

        graph_doc = docs[0]
        df = getattr(graph_doc, "graph_data", None)

        # Neo4jStore 通常返回 GraphDocument(graph_data=df)
        if df is not None:
            rows = df.to_dict(orient="records")
            return json.dumps({"intent": intent, "cypher": cypher, "params": params, "rows": rows}, ensure_ascii=False)

        # 兜底：返回 text 字段（如果没有 graph_data）
        text = getattr(graph_doc, "text", "")
        return json.dumps({"intent": intent, "cypher": cypher, "params": params, "text": text}, ensure_ascii=False)

    # ----------------------------
    # 规则版 NL -> Cypher（先跑通 2–3 类问题）
    # ----------------------------
    def _nlu_to_cypher(self, question: str) -> Tuple[str, str, Dict[str, Any]]:
        year = self._extract_year(question) or 2023
        topk = self._extract_topk(question) or 10
        state = self._extract_state(question)
        fid = self._extract_facility_id(question)

        ql = question.lower()

        # 1) Top 排放设施：2023年CH4排放最高的10个设施
        if (("最高" in question) or ("top" in ql) or ("前" in question)) and ("排放" in question) and ("设施" in question):
            intent = "top_emitters_ch4"
            cypher = """
MATCH (f:Facility)-[:HAS_RECORD]->(r:EmissionRecord)
WHERE r.reporting_year = $year
  AND r.gas = 'CH4'
  AND r.data IS NOT NULL
RETURN
  f.facility_name AS facility,
  f.state AS state,
  SUM(r.data) AS total_ch4
ORDER BY total_ch4 DESC
LIMIT $topk
""".strip()
            return intent, cypher, {"year": year, "topk": topk}

        # 2) 按州列设施：Texas/德州有哪些设施
        if state and (("有哪些设施" in question) or ("哪些设施" in question) or ("设施有哪些" in question)):
            intent = "facilities_by_state"
            cypher = """
MATCH (f:Facility)
WHERE f.state = $state
RETURN
  f.facility_name AS facility,
  f.county AS county,
  f.primary_naics_code AS naics
ORDER BY facility
LIMIT 50
""".strip()
            return intent, cypher, {"state": state}

        # 3) 某设施 + 年份：排放构成（按 source/method）
        if fid and (("构成" in question) or ("来源" in question) or ("分解" in question)):
            intent = "facility_breakdown_ch4"
            cypher = """
MATCH (f:Facility)-[:HAS_RECORD]->(r:EmissionRecord)
WHERE f.ghgrp_facility_id = $fid
  AND r.reporting_year = $year
  AND r.gas = 'CH4'
RETURN
  r.source_name AS source,
  r.method_code AS method,
  SUM(r.data) AS ch4
ORDER BY ch4 DESC
""".strip()
            return intent, cypher, {"fid": fid, "year": year}

        # 兜底：方便调试
        intent = "unknown"
        cypher = "MATCH (f:Facility) RETURN f.facility_name AS facility, f.state AS state LIMIT 5"
        return intent, cypher, {}

    # ----------------------------
    # 参数抽取
    # ----------------------------
    def _extract_year(self, text: str) -> Optional[int]:
        m = re.search(r"(19|20)\d{2}", text)
        return int(m.group(0)) if m else None

    def _extract_topk(self, text: str) -> Optional[int]:
        m = re.search(r"(?:前|top)\s*(\d+)", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)\s*个", text)
        return int(m.group(1)) if m else None

    def _extract_state(self, text: str) -> Optional[str]:
        mapping = {
            "texas": "TX", "德州": "TX", "得州": "TX", "tx": "TX",
            "california": "CA", "加州": "CA", "ca": "CA",
        }
        tl = text.lower()
        for k, v in mapping.items():
            if k in tl or k in text:
                return v
        return None

    def _extract_facility_id(self, text: str) -> Optional[str]:
        m = re.search(r"\b(\d{4,})\b", text)
        return m.group(1) if m else None
