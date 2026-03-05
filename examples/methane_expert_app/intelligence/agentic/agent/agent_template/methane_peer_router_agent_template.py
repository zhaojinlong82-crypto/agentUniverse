# !/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import re
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from agentuniverse.agent.input_object import InputObject
from agentuniverse.agent.memory.memory import Memory
from agentuniverse.agent.template.peer_agent_template import PeerAgentTemplate
from agentuniverse.agent.work_pattern.peer_work_pattern import PeerWorkPattern
from agentuniverse.base.util.logging.logging_util import LOGGER


@dataclass
class RouteResult:
    route_code: str
    question_type: str
    reason: str
    sql_hint: str


class MethanePeerRouterAgentTemplate(PeerAgentTemplate):
    """PEER entry agent with explicit question-type routing for methane domain."""

    def customized_execute(
        self,
        input_object: InputObject,
        agent_input: dict,
        memory: Memory,
        peer_work_pattern: PeerWorkPattern,
        **kwargs
    ) -> dict:
        self.build_expert_framework(input_object)
        route = self._classify_question(input_object.get_data("input", ""))
        self._emit_route_audit(input_object=input_object, route=route)
        input_object.add_data("route_code", route.route_code)
        input_object.add_data("question_type", route.question_type)
        input_object.add_data("route_reason", route.reason)
        input_object.add_data("route_sql_hint", route.sql_hint)
        return peer_work_pattern.invoke(input_object, agent_input)

    def _classify_question(self, question: str) -> RouteResult:
        q = question.lower().strip()

        def has(*patterns: str) -> bool:
            return any(re.search(p, q, re.IGNORECASE) for p in patterns)

        if has(r"冲突", r"不一致", r"遥感", r"核查", r"差异"):
            return RouteResult(
                route_code="Q12_CONFLICT_UNCERTAINTY",
                question_type="conflict_uncertainty",
                reason="检测到多源冲突/不确定性关键词",
                sql_hint=(
                    "先给出当前库内统计事实，再标注不确定性来源与待补充数据项。"
                ),
            )
        if has(r"监测", r"识别", r"实地", r"遥感核查", r"进一步核查"):
            return RouteResult(
                route_code="Q11_MONITORING_VALIDATION",
                question_type="monitoring_validation",
                reason="检测到监测与核查支持关键词",
                sql_hint=(
                    "先找高排放对象与位置，再输出建议核查对象清单与原因。"
                ),
            )
        if has(r"优先", r"排查", r"治理", r"投入", r"建议", r"行动"):
            return RouteResult(
                route_code="Q10_ACTION_PRIORITIZATION",
                question_type="action_support",
                reason="检测到行动建议关键词",
                sql_hint=(
                    "先统计高排放对象，再给出可执行优先级依据（排放量、波动、覆盖范围）。"
                ),
            )
        if has(r"缺失", r"异常", r"突然", r"升高", r"为何", r"为什么没有数据"):
            return RouteResult(
                route_code="Q9_MISSING_ANOMALY_EXPLANATION",
                question_type="missing_anomaly_explanation",
                reason="检测到缺失与异常解释关键词",
                sql_hint=(
                    "先查询时间序列与字段覆盖，再定位异常年份与缺失模式。"
                ),
            )
        if has(r"来源", r"口径", r"单位", r"筛选条件", r"应用了哪些条件"):
            return RouteResult(
                route_code="Q8_RESULT_TRACEABILITY",
                question_type="explanation_traceability",
                reason="检测到结果来源说明关键词",
                sql_hint=(
                    "先查询字段和样例，再查询目标值；最终输出过滤条件、单位、年份、可能缺失原因。"
                ),
            )
        if has(r"周边", r"\d+\s*公里", r"附近", r"半径", r"缓冲区"):
            return RouteResult(
                route_code="Q7_SPATIAL_NEARBY",
                question_type="spatial_nearby",
                reason="检测到空间邻近关键词",
                sql_hint=(
                    "若仅有 county/state 字段，先给出行政区近似；若后续接入 geom，使用 ST_DWithin。"
                ),
            )
        if has(r"位于", r"区域内", r"某县", r"某州", r"盆地", r"保护区", r"范围内"):
            return RouteResult(
                route_code="Q6_SPATIAL_LOCATION",
                question_type="spatial_filter",
                reason="检测到空间范围判断关键词",
                sql_hint=(
                    "优先使用 state/county 筛选；若问题包含年份和CH4，追加 reporting_year 与 gas 过滤。"
                ),
            )
        if has(r"对比", r"差异", r"哪一类", r"相比", r"之间"):
            return RouteResult(
                route_code="Q5_REGION_TYPE_COMPARISON",
                question_type="comparison_analysis",
                reason="检测到区域或类型对比关键词",
                sql_hint=(
                    "按对比维度分组（如盆地/类型/县州）并汇总 CH4 排放，输出差异。"
                ),
            )
        if has(r"趋势", r"变化", r"近\s*\d+\s*年", r"上升", r"下降", r"同比", r"环比"):
            return RouteResult(
                route_code="Q4_TIME_TREND",
                question_type="trend_analysis",
                reason="检测到时间变化/趋势关键词",
                sql_hint=(
                    "按 reporting_year 聚合 CH4 排放并排序，必要时按 state/county 分组；"
                    "输出多年的序列结果用于趋势判断。"
                ),
            )
        if has(r"前\s*\d+", r"top\s*\d+", r"超过", r"高于", r"阈值", r"最高", r"最低", r"排名"):
            return RouteResult(
                route_code="Q3_THRESHOLD_RANKING",
                question_type="threshold_ranking",
                reason="检测到阈值或排名关键词",
                sql_hint=(
                    "按对象(state/county/facility)聚合 SUM(value)，结合 LIMIT 或 HAVING。"
                ),
            )
        if has(r"压缩站", r"处理厂", r"集输站", r"油井", r"类型", r"分类"):
            return RouteResult(
                route_code="Q2_TYPE_FILTER",
                question_type="type_filtering",
                reason="检测到设施类型筛选关键词",
                sql_hint=(
                    "先识别设施类型字段（若存在），再按类型过滤并统计 CH4 排放。"
                ),
            )
        if has(r"\d{4}", r"德州", r"texas", r"permian", r"清单", r"有哪些", r"名单"):
            return RouteResult(
                route_code="Q1_REGION_TIME_FILTER",
                question_type="inventory_filtering",
                reason="检测到区域+时间筛选或清单关键词",
                sql_hint=(
                    "按年份、区域、类型过滤，并返回清单/聚合结果。"
                ),
            )
        return RouteResult(
            route_code="Q1_REGION_TIME_FILTER",
            question_type="inventory_filtering",
            reason="默认归入清单筛选类问题",
            sql_hint=(
                "按年份、区域、类型过滤，并返回清单/聚合结果。"
            ),
        )

    def _emit_route_audit(self, input_object: InputObject, route: RouteResult) -> None:
        payload = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "session_id": input_object.get_data("session_id", ""),
            "trace_id": input_object.get_data("trace_id", ""),
            "route_code": route.route_code,
            "question_type": route.question_type,
            "route_reason": route.reason,
            "route_sql_hint": route.sql_hint,
            "question": input_object.get_data("input", ""),
        }
        LOGGER.info(f"[ROUTE_AUDIT]{json.dumps(payload, ensure_ascii=False)}")
        log_dir = Path(__file__).resolve().parents[4] / "intelligence" / "test" / ".route_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "route_audit.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
