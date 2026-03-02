# !/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
from pathlib import Path

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.base.agentuniverse import AgentUniverse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "examples" / "sample_standard_app" / "config" / "config.toml"

# Ensure sibling example package `sample_standard_app` is importable.
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
if str(EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_ROOT))

# Standard app components are loaded from sample_standard_app config.
AgentUniverse().start(config_path=str(CONFIG_PATH), core_mode=True)


def main():
    question = """
请在 core schema 下完成以下任务：
1) 先检查 emission_record、facility、facility_year 三张表的字段定义；
2) 找到“甲烷排放量”字段与“城市”字段；
3) 基于 2012 年数据，按城市聚合甲烷排放总量并降序排序；
4) 返回全美国甲烷排放量最高的城市（Top1），并附上你最终执行的 SQL。

要求：
- 只使用数据库工具，不要臆测字段名；
- 如果一次 SQL 报错，先修正再重试；
- 最终答案用中文。
""".strip()

    instance: Agent = AgentManager().get_instance_obj("sql_qa_agent")
    output = instance.run(input=question, session_id="methane-city-2012-test")
    print(output.get_data("output"))


if __name__ == "__main__":
    main()
