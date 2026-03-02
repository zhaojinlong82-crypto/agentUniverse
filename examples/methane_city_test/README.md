# Methane City Test

这个目录用于单独测试目标问题：
`2012 年全美国甲烷排放量最高的城市是什么？`

## 1) 前置条件

- 你已经能跑通：
  - `/Users/ayan/实验室数据/复现多Agent框架/agentUniverse-master/examples/sample_standard_app/intelligence/test/run_sql_qa_agent.py`
- `local_business_db.yaml` 已指向你的 PostgreSQL，并且 schema/table 配置正确。

## 2) 运行测试

```bash
/opt/anaconda3/envs/au311/bin/python /Users/ayan/实验室数据/复现多Agent框架/agentUniverse-master/examples/methane_city_test/run_methane_city_test.py
```

## 3) 你会看到什么

- Agent 会先检查 `emission_record/facility/facility_year` 的字段；
- 然后构造 SQL，按城市聚合 2012 年甲烷排放；
- 最后输出 Top 城市（并给出用于计算的 SQL 片段/解释）。

## 4) 建议追问（验证用）

第一轮结果出来后，再问：

- `请给出前10名城市及各自排放量。`
- `请只返回SQL，不要解释。`
- `请解释你如何识别“甲烷排放”对应字段。`

