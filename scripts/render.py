#!/usr/bin/env python3
"""Render markdown pages from data/tasks.json.

Outputs:
  README.md                       -- top-level overview (all tasks table, grouped)
  features/<feature_id>.md        -- one page per feature
  features/README.md              -- index of features
  daily/YYYY-MM-DD.md             -- today's summary (only if --daily is passed)
  daily/README.md                 -- index of daily reports
"""
from __future__ import annotations
import argparse, json, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "tasks.json"

STATUS_ORDER = ["in_progress", "todo", "blocked", "done", "cancelled"]
STATUS_LABEL = {
    "todo": "📋 待办",
    "in_progress": "🚧 进行中",
    "blocked": "⛔ 阻塞",
    "done": "✅ 已完成",
    "cancelled": "❌ 已取消",
}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _priority_key(p: str | None) -> int:
    return PRIORITY_ORDER.get((p or "P3").upper(), 9)


def _status_key(s: str | None) -> int:
    try:
        return STATUS_ORDER.index((s or "todo").lower())
    except ValueError:
        return len(STATUS_ORDER)


def sort_tasks(tasks: list[dict]) -> list[dict]:
    return sorted(tasks, key=lambda t: (_status_key(t.get("status")),
                                        _priority_key(t.get("priority")),
                                        t.get("id", "")))


def render_task_table(tasks: list[dict], show_feature: bool = False) -> str:
    if not tasks:
        return "_暂无任务_\n"
    headers = ["ID", "标题"]
    if show_feature:
        headers.append("功能")
    headers += ["状态", "优先级", "负责人", "截止", "标签"]
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for t in tasks:
        row = [t.get("id", ""), _escape(t.get("title", ""))]
        if show_feature:
            row.append(t.get("feature_id", ""))
        row += [
            STATUS_LABEL.get(t.get("status", "todo"), t.get("status", "")),
            (t.get("priority") or "").upper(),
            t.get("owner") or "",
            t.get("due_date") or "",
            ", ".join(t.get("tags") or []),
        ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def render_readme(data: dict) -> str:
    tasks = data.get("tasks", [])
    features = {f["id"]: f for f in data.get("features", [])}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    total = len(tasks)
    by_status = defaultdict(int)
    for t in tasks:
        by_status[t.get("status", "todo")] += 1

    parts = []
    parts.append("# 📌 产品任务清单\n")
    parts.append(f"_由 Hermes taskboard agent 维护 · 最近渲染：{now}_\n")
    parts.append("## 概览\n")
    parts.append(f"- 任务总数：**{total}**")
    for s in STATUS_ORDER:
        if by_status.get(s):
            parts.append(f"- {STATUS_LABEL[s]}：{by_status[s]}")
    parts.append("")
    parts.append("## 按产品功能分组\n")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        grouped[t.get("feature_id") or "_unassigned"].append(t)

    ordered_fids = sorted(grouped.keys(),
                          key=lambda fid: (fid == "_unassigned", fid))
    for fid in ordered_fids:
        f = features.get(fid, {"name": fid, "priority": "", "status": ""})
        display = f.get("name") or fid
        prio = (f.get("priority") or "").upper()
        parts.append(f"### {display}"
                     + (f" · {prio}" if prio else "")
                     + f"  ([详情](features/{fid}.md))\n")
        if f.get("description"):
            parts.append(f"> {f['description']}\n")
        parts.append(render_task_table(sort_tasks(grouped[fid])))
        parts.append("")

    parts.append("## 目录\n")
    parts.append("- [features/](features/README.md) — 按产品功能拆分的详细清单")
    parts.append("- [daily/](daily/README.md) — 每日工作总结")
    parts.append("- [data/tasks.json](data/tasks.json) — 原始数据（单一数据源）")
    parts.append("")
    return "\n".join(parts)


def render_feature_page(feature: dict, tasks: list[dict]) -> str:
    parts = [f"# {feature.get('name', feature['id'])}\n"]
    if feature.get("description"):
        parts.append(feature["description"] + "\n")
    meta = []
    if feature.get("status"):
        meta.append(f"状态：`{feature['status']}`")
    if feature.get("priority"):
        meta.append(f"优先级：`{feature['priority'].upper()}`")
    if meta:
        parts.append(" · ".join(meta) + "\n")
    parts.append("## 任务\n")
    parts.append(render_task_table(sort_tasks(tasks)))
    parts.append("\n[← 返回首页](../README.md)\n")
    return "\n".join(parts)


def render_features_index(data: dict) -> str:
    tasks_by_feature: dict[str, list[dict]] = defaultdict(list)
    for t in data.get("tasks", []):
        tasks_by_feature[t.get("feature_id") or "_unassigned"].append(t)

    parts = ["# 产品功能索引\n"]
    parts.append("| 功能 | 状态 | 优先级 | 任务总数 | 进行中 | 待办 | 已完成 |")
    parts.append("|---|---|---|---|---|---|---|")
    for f in data.get("features", []):
        ts = tasks_by_feature.get(f["id"], [])
        by = defaultdict(int)
        for t in ts:
            by[t.get("status", "todo")] += 1
        parts.append("| [{name}]({fid}.md) | {status} | {prio} | {tot} | {ip} | {td} | {dn} |".format(
            name=f.get("name") or f["id"],
            fid=f["id"],
            status=f.get("status") or "",
            prio=(f.get("priority") or "").upper(),
            tot=len(ts),
            ip=by.get("in_progress", 0),
            td=by.get("todo", 0),
            dn=by.get("done", 0),
        ))
    parts.append("\n[← 返回首页](../README.md)\n")
    return "\n".join(parts)


def render_daily(data: dict, target_date: date) -> str:
    """Summary for target_date: what was completed on that date, what's in-progress, top TODO."""
    tasks = data.get("tasks", [])
    features = {f["id"]: f for f in data.get("features", [])}
    ds = target_date.isoformat()

    completed_today = [t for t in tasks if t.get("completed_at") == ds]
    created_today = [t for t in tasks if t.get("created_at") == ds]
    in_progress = [t for t in tasks if t.get("status") == "in_progress"]
    blocked = [t for t in tasks if t.get("status") == "blocked"]
    todo_pending = sort_tasks([t for t in tasks if t.get("status") == "todo"])[:10]

    weekday = ["一","二","三","四","五","六","日"][target_date.weekday()]
    parts = [f"# 📅 {ds} 工作总结（周{weekday}）\n"]
    parts.append(f"_生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")

    parts.append("## ✅ 昨日完成\n")
    if completed_today:
        parts.append(render_task_table(completed_today, show_feature=True))
    else:
        parts.append("_昨日无完成任务_\n")

    parts.append("\n## 🚧 进行中\n")
    if in_progress:
        parts.append(render_task_table(sort_tasks(in_progress), show_feature=True))
    else:
        parts.append("_无进行中任务_\n")

    parts.append("\n## ⛔ 阻塞需关注\n")
    if blocked:
        parts.append(render_task_table(sort_tasks(blocked), show_feature=True))
    else:
        parts.append("_无阻塞任务_\n")

    parts.append("\n## 📋 今日重点（Top 10 待办）\n")
    if todo_pending:
        parts.append(render_task_table(todo_pending, show_feature=True))
    else:
        parts.append("_待办清单已清空 🎉_\n")

    if created_today:
        parts.append("\n## 🆕 昨日新建任务\n")
        parts.append(render_task_table(created_today, show_feature=True))

    parts.append("\n[← 返回首页](../README.md)\n")
    return "\n".join(parts)


def render_daily_index() -> str:
    daily_dir = ROOT / "daily"
    files = sorted([p for p in daily_dir.glob("*.md") if p.name != "README.md"],
                   reverse=True)
    parts = ["# 每日工作总结\n", "| 日期 | 链接 |", "|---|---|"]
    for p in files:
        parts.append(f"| {p.stem} | [{p.name}]({p.name}) |")
    parts.append("\n[← 返回首页](../README.md)\n")
    return "\n".join(parts)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily", action="store_true",
                    help="also produce daily/YYYY-MM-DD.md for --date (default: yesterday)")
    ap.add_argument("--date", default=None,
                    help="ISO date for --daily (default: yesterday)")
    args = ap.parse_args()

    data = load()
    write(ROOT / "README.md", render_readme(data))
    for f in data.get("features", []):
        ts = [t for t in data.get("tasks", []) if t.get("feature_id") == f["id"]]
        write(ROOT / "features" / f"{f['id']}.md", render_feature_page(f, ts))
    write(ROOT / "features" / "README.md", render_features_index(data))

    if args.daily:
        if args.date:
            target = date.fromisoformat(args.date)
        else:
            target = date.today() - timedelta(days=1)
        write(ROOT / "daily" / f"{target.isoformat()}.md", render_daily(data, target))
        write(ROOT / "daily" / "README.md", render_daily_index())

    return 0


if __name__ == "__main__":
    sys.exit(main())
