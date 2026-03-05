# !/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
from pathlib import Path

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.base.agentuniverse import AgentUniverse


APP_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = APP_ROOT.parents[1]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"

if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

CONFIG_PATH = APP_ROOT / "config" / "config.toml"
AgentUniverse().start(config_path=str(CONFIG_PATH), core_mode=True)


def chat(question: str, session_id: str = "methane-peer-demo"):
    instance: Agent = AgentManager().get_instance_obj("methane_peer_agent")
    output = instance.run(input=question, session_id=session_id)
    print("\n--- Final Answer ---")
    print(output.get_data("output"))


if __name__ == "__main__":
    demo_question = (
        "请分析2012年美国甲烷排放中，排放最高的县（以county近似城市）是谁，"
        "并说明口径、SQL证据与下一步补充数据建议。"
    )
    chat(demo_question)
