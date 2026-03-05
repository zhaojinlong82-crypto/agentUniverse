# !/usr/bin/env python3
# -*- coding:utf-8 -*-

from agentuniverse.agent.input_object import InputObject
from agentuniverse.agent.template.planning_agent_template import PlanningAgentTemplate


class MethanePlanningAgentTemplate(PlanningAgentTemplate):
    """Planning template that consumes explicit router metadata."""

    def parse_input(self, input_object: InputObject, agent_input: dict) -> dict:
        agent_input = super().parse_input(input_object, agent_input)
        agent_input["route_code"] = input_object.get_data("route_code", "Q1_REGION_TIME_FILTER")
        agent_input["question_type"] = input_object.get_data("question_type", "inventory_filtering")
        agent_input["route_reason"] = input_object.get_data("route_reason", "")
        agent_input["route_sql_hint"] = input_object.get_data("route_sql_hint", "")
        return agent_input
