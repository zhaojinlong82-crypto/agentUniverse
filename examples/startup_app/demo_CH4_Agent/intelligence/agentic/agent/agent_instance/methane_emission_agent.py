from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
from agentuniverse.agent.action.tool.tool_manager import ToolManager

from agentuniverse.llm.llm import LLM
from agentuniverse.prompt.prompt import Prompt
from agentuniverse.base.util.prompt_util import process_llm_token


class MethaneEmissionAgent(Agent):

    def input_keys(self):
        return ["input"]

    def output_keys(self):
        return ["output"]

    def parse_input(self, input_object: InputObject, agent_input: dict):
        agent_input["input"] = input_object.get_data("input")
        return agent_input

    def parse_result(self, agent_result: dict):
        return {"output": agent_result["output"]}

    def execute(self, input_object: InputObject, agent_input: dict, **kwargs):

        # ===== 1️⃣ 取 Neo4j Tool =====
        tool = ToolManager().get_instance_obj("methane_neo4j_query_tool.yaml")
        if tool is None:
            raise RuntimeError("❌ methane_neo4j_query_tool.yaml 未加载")

        # ===== 2️⃣ 调用 Tool（这是关键验证点）=====
        tool_result = tool.run(input=agent_input["input"])

        # 🔥 强烈建议你先打印 / 日志
        print("===== Neo4j Tool Result =====")
        print(tool_result)

        # ===== 3️⃣ 把 Tool 结果塞进 background =====
        agent_input["background"] = (
            "以下是从 Neo4j 甲烷排放知识图谱中查询得到的结构化结果：\n"
            f"{tool_result}"
        )

        # ===== 4️⃣ 正常走 LLM 总结 =====
        llm: LLM = self.process_llm(**kwargs)
        prompt: Prompt = self.process_prompt(agent_input, **kwargs)
        process_llm_token(llm, prompt.as_langchain(), self.agent_model.profile, agent_input)

        chain = prompt.as_langchain() | llm.as_langchain_runnable(
            self.agent_model.llm_params()
        )

        res = chain.invoke(agent_input)

        return {
            **agent_input,
            "output": res
        }
