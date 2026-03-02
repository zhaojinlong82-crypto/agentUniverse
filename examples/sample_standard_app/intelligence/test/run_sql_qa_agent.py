# !/usr/bin/env python3
# -*- coding:utf-8 -*-

from pathlib import Path

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.base.agentuniverse import AgentUniverse

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.toml"
AgentUniverse().start(config_path=str(CONFIG_PATH), core_mode=True)


def chat(question: str, session_id: str = "sql-qa-session"):
    instance: Agent = AgentManager().get_instance_obj("sql_qa_agent")
    output_object = instance.run(input=question, session_id=session_id)
    print(output_object.get_data("output"))


if __name__ == "__main__":
    chat("请先列出当前数据库里的所有表。")
    chat("请统计每张表有多少行，并用中文总结。")

