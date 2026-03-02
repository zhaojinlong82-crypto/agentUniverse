# Agent Template

Agent template is designed to help users quickly build agents. Once the abstraction of the template layer is completed, users only need to fill in specific property configuration information in the agent template to execute the corresponding orchestration logic. For example, the RAG template, ReAct template, and PEER template are all built-in agent templates in the agentUniverse system.

## How to Define an Agent Template
### [Agent Template Base Class Definition](../../../../../../agentuniverse/agent/template/agent_template.py)

The `AgentTemplate` is based on the [Agent Base Class](../../../../../../agentuniverse/agent/agent.py) and includes the following configuration information:

- `llm_name`: The name of the LLM component. After the user configures `llm_model` in the agent YAML profile, the template class will automatically assemble it.

- `memory_name`: The name of the memory component. After the user configures `memory` in the agent YAML, the template class will automatically assemble it.

- `tool_names`: A list of names for the agent's tool components. After the user configures `tools` in the agent YAML, the template class will automatically assemble them.

- `knowledge_names`: A list of names for the agent's knowledge components. After the user configures `knowledge` in the agent YAML, the template class will automatically assemble them.

- `prompt_version`: The version number of the agent's prompt. After the user configures `prompt_version` in the agent YAML profile, the template class will automatically assemble it.

The class includes the following methods:

- execute(self, input_object: InputObject, agent_input: dict, **kwargs) -> dict:
  : The synchronous execution method of the agent template, which includes the processing logic for the agent's memory, LLM, and Prompt.

-  async_execute(self, input_object: InputObject, agent_input: dict, **kwargs) -> dict:
  : The asynchronous execution method of the agent template, which includes the processing logic for the agent's memory, LLM, and Prompt.

-  customized_execute(self, input_object: InputObject, agent_input: dict, memory: Memory, llm: LLM, prompt: Prompt, **kwargs) -> dict:
  : The custom synchronous execution method of the agent template. The base class of the agent template provides a default implementation. **It is recommended that you override this method when customizing your agent template.**

-  customized_async_execute(self, input_object: InputObject, agent_input: dict, memory: Memory, llm: LLM, prompt: Prompt, **kwargs) -> dict:
  : The custom asynchronous execution method of the agent template. The base class of the agent template provides a default implementation. **It is recommended that you override this method when customizing your agent template.**

- process_llm(self, **kwargs) -> LLM:
  : The default processing logic for the LLM in the agent template.

- process_memory(self, agent_input: dict, **kwargs) -> Memory | None:
  : The default processing logic for the memory in the agent template.

- process_prompt(self, agent_input: dict, **kwargs) -> Prompt:
  : The default processing logic for the Prompt in the agent template.

- invoke_tools(self, input_object: InputObject, **kwargs):
  : The default tool invocation logic in the agent template.

- invoke_knowledge(self, query_str: str, input_object: InputObject, **kwargs):
  : The default knowledge invocation logic in the agent template.

- invoke_chain(self, chain: RunnableSerializable[Any, str], agent_input: dict, input_object: InputObject, **kwargs):
  : The default synchronous chain invocation logic in the agent template.

-  async_invoke_chain(self, chain: RunnableSerializable[Any, str], agent_input: dict, input_object: InputObject, **kwargs):
  : The default asynchronous chain invocation logic in the agent template.


### Definition of Specific Agent Template Implementation Class

The implementation class of the template should inherit from the AgentTemplate base class and define the specific input and output parameters (`input_keys` and `output_keys`) for the current template, as well as the specific parsing methods for inputs and results (`parse_input` and `parse_result`).

If the custom execution methods in the AgentTemplate base class, such as `customized_execute`, do not meet your specific orchestration needs, we recommend overriding these methods to implement your own execution logic. 
Similarly, methods related to the processing logic of various agent-related domain components, such as `process_llm` and `invoke_tools`, can also be overridden to meet your custom requirements.

Note: The AgentTemplate base class is already highly abstract. **We recommend overriding specific methods based on your needs instead of copying the entire class, as this can lead to bloated code structures and high maintenance costs.**

## How to Use Agent Templates

Taking the built-in [PEER Agent Template](../../../../../../agentuniverse/agent/template/peer_agent_template.py) in agentUniverse as an example, the following configuration information can be filled in (all of which have default values):

- `planning_agent_name`: The name of the planning agent for task decomposition. After the user configures `planning` in the agent YAML profile, the template class will automatically assemble it.

- `executing_agent_name`: The name of the executing agent for task execution. After the user configures `executing` in the agent YAML profile, the template class will automatically assemble it.

- `expressing_agent_name`: The name of the expressing agent for task expression. After the user configures `expressing` in the agent YAML profile, the template class will automatically assemble it.

- `reviewing_agent_name`: The name of the reviewing agent for task evaluation. After the user configures `reviewing` in the agent YAML profile, the template class will automatically assemble it.

- `expert_framework`: The expert framework for the PEER multi-agent system. After the user configures `expert_framework` in the agent YAML profile, the template class will automatically assemble it.

### Creating a Real Agent Instance Based on the PEER Agent Template

As described above, once the abstraction of the template layer is completed, users only need to fill in the specific property configuration information in the agent template to execute the corresponding orchestration logic. The configuration information is as follows:

```yaml
info:
  name: 'demo_peer_agent'
  description: 'demo peer agent'
profile:
  planning: 'demo_planning_agent'
  executing: 'demo_executing_agent'
  expressing: 'demo_expressing_agent'
  reviewing: 'demo_reviewing_agent'
  expert_framework:
    context:
      planning: # expert knowledge of the planning node
      executing: # expert knowledge of the executing node
      expressing: # expert knowledge of the expressing node
      reviewing: # expert knowledge of the reviewing node
    selector:
memory:
  name: 'demo_memory'
metadata:
  type: 'AGENT'
  module: 'agentuniverse.agent.template.peer_agent_template'
  class: 'PeerAgentTemplate'
```

## The agentUniverse currently includes the following built-in agent templates:

### [PeerAgentTemplate](../../../../../../agentuniverse/agent/template/peer_agent_template.py)
The introduction above has already covered this template, so it is omitted here.

The four node agent instances in the PeerAgentTemplate must be of the corresponding agent template class (PlanningAgentTemplate/ExecutingAgentTemplate/ExpressingAgentTemplate/ReviewingAgentTemplate) or their respective custom subclasses.

### [PlanningAgentTemplate](../../../../../../agentuniverse/agent/template/planning_agent_template.py)
The agent template for the Planning node in the Peer template.

### [ExecutingAgentTemplate](../../../../../../agentuniverse/agent/template/executing_agent_template.py)
The agent template for the Executing node in the Peer template.

### [ExpressingAgentTemplate](../../../../../../agentuniverse/agent/template/expressing_agent_template.py)
The agent template for the Expressing node in the Peer template.

### [ReviewingAgentTemplate](../../../../../../agentuniverse/agent/template/reviewing_agent_template.py)
The agent template for the Reviewing node in the Peer template.

### [RagAgentTemplate](../../../../../../agentuniverse/agent/template/rag_agent_template.py)
The RAG agent template, with a specific configuration example as follows:

```yaml
info:
  name: 'demo_rag_agent'
  description: 'demo rag agent'
profile:
  prompt_version: demo_rag_agent.cn
  llm_model:
    name: 'qwen_llm'
action:
  tool:
    - 'xxx_tool_1'
  knowledge:
    - 'xxx_knowledge_1'
memory:
  name: 'xxx_memory'
metadata:
  type: 'AGENT'
  module: 'agentuniverse.agent.template.rag_agent_template'
  class: 'RagAgentTemplate'
```

### [ReActAgentTemplate](../../../../../../agentuniverse/agent/template/react_agent_template.py)
The ReAct agent template, with a specific configuration example as follows:

```yaml
info:
  name: 'demo_react_agent'
  description: 'react agent'
profile:
  prompt_version: qwen_react_agent.cn
  llm_model:
    name: 'qwen_llm'
    model_name: 'qwen-max'
    stop: 'Observation'
    temperature: 0.1
action:
  tool:
    - 'xxx_tool_1'
    - 'xxx_tool_2'
  knowledge:
    - 'xxx_knowledge_1'
memory:
  name: 'xxx_memory'
metadata:
  type: 'AGENT'
  module: 'agentuniverse.agent.template.react_agent_template'
  class: 'ReActAgentTemplate'
```

### [Nl2ApiAgentTemplate](../../../../../../agentuniverse/agent/template/nl2api_agent_template.py)
The Nl2Api agent template, with a specific configuration example as follows:

```yaml
info:
  name: 'demo_nl2api_agent'
  description: 'demo nl2api agent'
profile:
  llm_model:
    name: 'qwen_llm'
action:
  tool:
    - 'xxx_tool_1'
    - 'xxx_tool_2'
    - 'xxx_tool_3'
    - 'xxx_tool_4'
    - 'xxx_tool_5'
metadata:
  type: 'AGENT'
  module: 'agentuniverse.agent.template.nl2api_agent_template'
  class: 'Nl2ApiAgentTemplate'
```

# Summary
You have now understood the purpose of agent templates, their specific definitions, and how to use them. Please read the work pattern documentation, where we will introduce the definition of work pattern, the differences between work pattern and agent template, as well as the planner related to agentUniverse.