#!/usr/bin/env python3
"""Tiny CLI to mutate data/tasks.json without hand-editing.

Examples:
  python3 scripts/tb.py add-feature login "登录/注册" --priority P1 --description "手机号 + 邮箱"
  python3 scripts/tb.py add-task login "支持微信登录" --priority P1 --owner gcc-luo
  python3 scripts/tb.py set T-0007 status in_progress
  python3 scripts/tb.py done T-0007
  python3 scripts/tb.py list --status todo
"""
from __future__ import annotations
import argparse, json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "tasks.json"

VALID_STATUS = {"todo", "in_progress", "blocked", "done", "cancelled"}
VALID_PRIORITY = {"P0", "P1", "P2", "P3"}


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def next_task_id(data: dict) -> str:
    n = 0
    for t in data.get("tasks", []):
        tid = t.get("id", "")
        if tid.startswith("T-"):
            try:
                n = max(n, int(tid[2:]))
            except ValueError:
                pass
    return f"T-{n+1:04d}"


def find_task(data: dict, tid: str) -> dict:
    for t in data["tasks"]:
        if t["id"] == tid:
            return t
    sys.exit(f"task {tid} not found")


def find_feature(data: dict, fid: str) -> dict:
    for f in data["features"]:
        if f["id"] == fid:
            return f
    sys.exit(f"feature {fid} not found")


def cmd_add_feature(args):
    data = load()
    if any(f["id"] == args.id for f in data["features"]):
        sys.exit(f"feature {args.id} already exists")
    data["features"].append({
        "id": args.id,
        "name": args.name,
        "description": args.description or "",
        "status": args.status,
        "priority": (args.priority or "P2").upper(),
    })
    save(data)
    print(f"feature {args.id} added")


def cmd_add_task(args):
    data = load()
    find_feature(data, args.feature)  # validate
    tid = args.id or next_task_id(data)
    if any(t["id"] == tid for t in data["tasks"]):
        sys.exit(f"task {tid} already exists")
    task = {
        "id": tid,
        "feature_id": args.feature,
        "title": args.title,
        "description": args.description or "",
        "status": args.status,
        "priority": (args.priority or "P2").upper(),
        "owner": args.owner or "",
        "created_at": date.today().isoformat(),
        "due_date": args.due or None,
        "completed_at": None,
        "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()],
        "notes": args.notes or "",
    }
    if args.priority and task["priority"] not in VALID_PRIORITY:
        sys.exit("priority must be one of " + ",".join(sorted(VALID_PRIORITY)))
    if task["status"] not in VALID_STATUS:
        sys.exit("status must be one of " + ",".join(sorted(VALID_STATUS)))
    data["tasks"].append(task)
    save(data)
    print(tid)


def cmd_set(args):
    data = load()
    t = find_task(data, args.id)
    if args.field == "status":
        if args.value not in VALID_STATUS:
            sys.exit("status must be one of " + ",".join(sorted(VALID_STATUS)))
        t["status"] = args.value
        if args.value == "done" and not t.get("completed_at"):
            t["completed_at"] = date.today().isoformat()
        if args.value != "done":
            t["completed_at"] = None
    elif args.field == "priority":
        v = args.value.upper()
        if v not in VALID_PRIORITY:
            sys.exit("priority must be one of " + ",".join(sorted(VALID_PRIORITY)))
        t["priority"] = v
    elif args.field == "owner":
        t["owner"] = args.value
    elif args.field == "due":
        t["due_date"] = args.value or None
    elif args.field == "feature":
        find_feature(data, args.value)
        t["feature_id"] = args.value
    elif args.field == "title":
        t["title"] = args.value
    elif args.field == "notes":
        t["notes"] = args.value
    elif args.field == "tags":
        t["tags"] = [x.strip() for x in args.value.split(",") if x.strip()]
    else:
        sys.exit(f"unknown field: {args.field}")
    save(data)
    print(f"{t['id']} {args.field} => {args.value}")


def cmd_done(args):
    args_ns = argparse.Namespace(id=args.id, field="status", value="done")
    cmd_set(args_ns)


def cmd_remove(args):
    data = load()
    before = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] != args.id]
    if len(data["tasks"]) == before:
        sys.exit(f"task {args.id} not found")
    save(data)
    print(f"task {args.id} removed")


def cmd_list(args):
    data = load()
    ts = data["tasks"]
    if args.status:
        ts = [t for t in ts if t.get("status") == args.status]
    if args.feature:
        ts = [t for t in ts if t.get("feature_id") == args.feature]
    for t in ts:
        print(f"{t['id']}\t[{t.get('status','?'):11}]\t{t.get('priority',''):3}\t{t.get('feature_id',''):20}\t{t.get('title','')}")


def build_parser():
    p = argparse.ArgumentParser(prog="tb")
    sub = p.add_subparsers(dest="cmd", required=True)

    af = sub.add_parser("add-feature")
    af.add_argument("id"); af.add_argument("name")
    af.add_argument("--description"); af.add_argument("--priority", default="P2")
    af.add_argument("--status", default="active")
    af.set_defaults(func=cmd_add_feature)

    at = sub.add_parser("add-task")
    at.add_argument("feature")
    at.add_argument("title")
    at.add_argument("--id")
    at.add_argument("--description"); at.add_argument("--priority", default="P2")
    at.add_argument("--status", default="todo"); at.add_argument("--owner")
    at.add_argument("--due"); at.add_argument("--tags")
    at.add_argument("--notes")
    at.set_defaults(func=cmd_add_task)

    st = sub.add_parser("set")
    st.add_argument("id"); st.add_argument("field")
    st.add_argument("value")
    st.set_defaults(func=cmd_set)

    dn = sub.add_parser("done")
    dn.add_argument("id")
    dn.set_defaults(func=cmd_done)

    rm = sub.add_parser("remove")
    rm.add_argument("id")
    rm.set_defaults(func=cmd_remove)

    ls = sub.add_parser("list")
    ls.add_argument("--status"); ls.add_argument("--feature")
    ls.set_defaults(func=cmd_list)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
