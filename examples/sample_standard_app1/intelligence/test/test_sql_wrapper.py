# -*- coding: utf-8 -*-
"""
最小 SQL 工具联通测试
不经过 Agent，不经过 Planner，只验证：
SQLDBWrapper → SQLDatabase → ListSQLDatabaseTool
"""

from agentuniverse.database.sqldb_wrapper_manager import SQLDBWrapperManager
from langchain_community.tools.sql_database.tool import ListSQLDatabaseTool

# ❶ 填写你的 wrapper 实例 code
WRAPPER_CODE = "<你的appname>.sqldb_wrapper.ghgrp_pg"

print("==== Step 1: 获取 SQLDBWrapper 实例 ====")
wrapper = SQLDBWrapperManager().get_instance_obj(WRAPPER_CODE)
print("Wrapper instance:", wrapper)

print("\n==== Step 2: 获取 LangChain SQLDatabase 对象 ====")
db = wrapper.sql_database
print("SQLDatabase object:", db)

print("\n==== Step 3: 测试数据库是否能列出表 ====")
tables = db.get_usable_table_names()
print("Tables from SQLDatabase:", tables)

print("\n==== Step 4: 用 LangChain 的 ListSQLDatabaseTool 调用 ====")
tool = ListSQLDatabaseTool(db=db)

result = tool.invoke("")   # list 工具允许空输入
print("\n=== Tool Output ===")
print(result)

print("\n✅ 如果你看到表名列表，说明数据库已经成功联通！")
