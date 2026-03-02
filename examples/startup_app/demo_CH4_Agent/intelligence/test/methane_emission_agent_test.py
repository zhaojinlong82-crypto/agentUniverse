# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/12/26 17:18
# @Author  : wangchongshi
# @Email   : wangchongshi.wcs@antgroup.com
# @FileName: methane_emission_agent_test.py
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager

AgentUniverse().start(config_path='../../config/config.toml', core_mode=True)


def chat(question: str):
    instance: Agent = AgentManager().get_instance_obj('methane_emission_agent')
    output_object: OutputObject = instance.run(input=question)
    print(output_object.get_data('output'))


if __name__ == '__main__':
    chat("2023年CH4排放最高的10个设施有哪些？")
