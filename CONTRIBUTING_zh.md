**🎈🎈🎈 欢迎来到agentUniverse！🎉🎉🎉**  
感谢您对agentUniverse的关注并有意愿为项目做出贡献，欢迎您加入agentUniverse的社区大家庭。作为一个人工智能领域的开源项目，您的贡献对我们项目的发展和改进至关重要。我们欢迎各种类型的贡献参与，如新功能引入、代码修复、文档改进、issue提交、案例添加等。

### 与我们沟通
如果您有任何贡献相关的想法与疑问可以提前与我们进行沟通，您可以在agentUniverse的项目的[issue](https://github.com/antgroup/agentUniverse/issues) 、发送邮件、或加入我们的社群进行沟通，更详细的沟通方式可见[联系方式](docs/guidebook/zh/联系我们.md)。

### 贡献指南
#### 项目代码与文档贡献
本项目的代码与文档贡献流程完全遵循github社区的标准流程，详细的操作步骤您可以参考github官方发布的[Fork-and-Pull-Request文档](https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project) 。

在提交commit的过程中，本项目参考沿用了部分git-commit Angular规范，在commit提交中需要您标记对应的类型。

commit类型列表：
* feat: 新功能 (如,feat:新增Agent Template功能)
* fix: bug修复 (如,fix:框架内核内存泄漏修复)
* docs: 文档更新 (如,docs: 智能体使用指导文档更新)
* refactor: 代码重构,不涉及功能改动的代码重构 (如, refactor: 知识加工模块代码重构)
* test: 测试类或工具提交 (如, test: 添加智能体加载模块单元测试)
* chore: 其他杂项 (如, chore: 项目icon图片替换)

##### Pull Request规范
在PR的提交过程中，我们沿用了上述commit类型，您可在PR提交中根据主要内容选择对应类型作为PR标签。

请您确保在提交PR时满足如下要求：
- 阅读并理解[贡献者指南](https://github.com/antgroup/agentUniverse/blob/master/CONTRIBUTING_zh.md) 的要求。
- 检查没有与此PR请求重复的功能并与项目维护者进行了沟通。
- 接受PR配合维护人员的建议进行修改或关闭。
- 提交测试文件并提供测试结果截图(功能修改、BUG修复类PR必须提供，其他按需)
- 添加或修改本次pr对应的文档说明(非必要，根据实际PR内容按需添加)
- 添加使用案例代码与文档说明(非必要，根据实际PR内容按需添加)
- 认真填写PR请求，包括指定维护人员、详细描述PR内容、提供必要的说明与截图等

#### 研发规范参考
在代码与注释规范方面，本项目推荐采用[python PEP8](https://peps.python.org/pep-0008/) 与 [Google Python Style](https://google.github.io/styleguide/pyguide.html) 规范。

若您对于python语言不是特别熟悉，不必对于这些规范感到压力，重点关注如下基本规范即可：
##### 命名规范
参考PEP8中的 [Naming Styles](https://peps.python.org/pep-0008/#naming-conventions) 部分。

##### 注释规范
按如下样例格式提供注释，如功能、Args参数、Returns返回、Raises报错信息等。
```python
def connect_to_next_port(self, minimum: int) -> int:
    """Connects to the next available port.

    Args:
      minimum: A port value greater or equal to 1024.

    Returns:
      The new minimum port.

    Raises:
      ConnectionError: If no available port is found.
    """
    if minimum < 1024:
      # Note that this raising of ValueError is not mentioned in the doc
      # string's "Raises:" section because it is not appropriate to
      # guarantee this specific behavioral reaction to API misuse.
      raise ValueError(f'Min. port must be at least 1024, not {minimum}.')
    port = self._find_next_open_port(minimum)
    if port is None:
      raise ConnectionError(
          f'Could not connect to service on port {minimum} or higher.')
    # The code does not depend on the result of this assert.
    assert port >= minimum, (
        f'Unexpected port {port} when minimum was {minimum}.')
    return port
```

#### 文章与案例贡献
如果您使用agentUniverse项目并感到满意，欢迎您在项目社区或者任何您熟悉的媒体平台中分享您的案例，我们会不定期举行社区交流活动，赞扬、鼓励与传播那些优秀案例与开发者。
