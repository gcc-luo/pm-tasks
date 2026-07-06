# pm-tasks

个人产品任务清单，由 [Hermes](https://hermes-agent.nousresearch.com/) 的 `taskboard` agent 自动维护。

- 数据源：[`data/tasks.json`](data/tasks.json)（**唯一真相**，所有 md 页由脚本渲染）
- 首页任务全景：[`README.md`](README.md)（自动生成）
- 按功能拆分：[`features/`](features/)
- 每日总结：[`daily/`](daily/)（每天早上 9:00 由 cron 自动生成）

## 本地使用

```bash
# 修改数据
python3 scripts/tb.py add-feature login "登录/注册" --priority P1
python3 scripts/tb.py add-task login "支持微信登录" --priority P0 --owner me
python3 scripts/tb.py set T-0002 status in_progress
python3 scripts/tb.py done T-0002

# 重新渲染 md
python3 scripts/render.py           # 只更新首页/features
python3 scripts/render.py --daily   # 顺带生成昨天的日报
```

## agent 使用

直接和 `taskboard` profile 对话：

```bash
hermes -p taskboard chat
# 或
taskboard chat
```

对它说自然语言即可：

- "新增功能：搜索"
- "在搜索下加个任务：支持拼音首字母匹配，P1，我负责"
- "T-0007 完成了"
- "帮我总结一下今天的工作"
