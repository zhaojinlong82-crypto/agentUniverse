# methane_expert_app (Initial)

这是一个初始版的设施级甲烷排放领域多智能体应用，使用 PEER 四角色：

- `methane_planning_agent`：问题分类与 SQL 子任务拆解
- `methane_executing_agent`：执行 SQL 子任务并产出中间结论
- `methane_expressing_agent`：整合输出为可汇报答案
- `methane_reviewing_agent`：质量审查（模板内置）

此外已加入“显式问题路由”：
- 在进入 PEER 前，主 Agent 会先把问题映射到 `question_type`
- 当前支持：`inventory_filtering / trend_analysis / threshold_ranking / spatial_filter / spatial_nearby / explanation_traceability / action_support / conflict_uncertainty`
- 路由结果会注入规划阶段，减少 SQL 字段幻觉
- 每次路由会写入结构化日志：`intelligence/test/.route_logs/route_audit.jsonl`

可用下面脚本统计路由分布：

```bash
/opt/anaconda3/envs/au311/bin/python /Users/ayan/实验室数据/复现多Agent框架/agentUniverse-master/examples/methane_expert_app/intelligence/test/analyze_route_logs.py
```

## 运行

```bash
/opt/anaconda3/envs/au311/bin/python /Users/ayan/实验室数据/复现多Agent框架/agentUniverse-master/examples/methane_expert_app/intelligence/test/run_methane_peer_agent.py
```

## 当前能力（初始版）

- 面向你当前数据库（`core.emission_record / facility / facility_year`）
- 优先覆盖：
  - 清单筛选与阈值排名
  - 趋势与对比（按年份、州/县）
  - 解释溯源（口径、限制、证据）

## 已知限制

- 当前数据库无 `city` 字段，空间粒度先用 `county` 近似
- 执行器当前已支持 `list/info/query` 三工具动态选择；后续新增表时，可通过环境变量 `METHANE_INFO_TABLES_DEFAULT` 扩展 `info` 默认表清单（逗号分隔）
