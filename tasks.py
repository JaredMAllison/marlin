#!/usr/bin/env python3
"""
tasks.py — Marlin task viewer.
Prints a grouped, sorted table of vault tasks.

Usage:
  python3 tasks.py                      # queued tasks, grouped by project
  python3 tasks.py --status all         # all statuses
  python3 tasks.py --status done        # only done tasks
  python3 tasks.py --project "Job Hunt" # filter by project (partial match)
"""

import argparse
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import yaml

VAULT = Path("/home/jared/Documents/Obsidian/Marlin/Tasks")
STATE_FILE = Path("/home/jared/marlin/state.json")
DURATION_ORDER = {"short": 0, "medium": 1, "long": 2}
VALID_STATUSES = {"queued", "done", "deferred", "waiting"}


def parse_note(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    fm["_path"] = path
    return fm


def load_all_tasks() -> list[dict]:
    tasks = []
    for path in VAULT.glob("*.md"):
        note = parse_note(path)
        if note and note.get("type") == "task":
            tasks.append(note)
    return tasks


def strip_wikilink(value) -> str:
    if not value:
        return ""
    s = str(value)
    return s.strip("[]")


def sort_key(task: dict):
    goal = task.get("goal_date")
    if goal and not isinstance(goal, date):
        try:
            goal = date.fromisoformat(str(goal))
        except ValueError:
            goal = None
    duration_rank = DURATION_ORDER.get(task.get("duration", "medium"), 1)
    return (goal or date(9999, 1, 1), duration_rank)


def format_context(ctx) -> str:
    if not ctx:
        return ""
    if isinstance(ctx, str):
        ctx = [ctx]
    return "[" + ", ".join(ctx) + "]"


def print_table(tasks: list[dict]):
    # Group by project
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        project = strip_wikilink(t.get("project")) or "(no project)"
        groups[project].append(t)

    # Sort groups: named projects first (alphabetical), (no project) last
    def group_sort(name):
        return ("z" + name) if name == "(no project)" else ("a" + name.lower())

    col_title = 32
    col_status = 9
    col_date = 12
    col_dur = 8

    for group_name in sorted(groups, key=group_sort):
        group_tasks = sorted(groups[group_name], key=sort_key)
        bar = "─" * (col_title + col_status + col_date + col_dur + 20)
        print(f"\n── {group_name} {bar}"[:72])
        for t in group_tasks:
            title = t.get("title", "Untitled")[:col_title]
            status = (t.get("status") or "")[:col_status]
            goal = str(t.get("goal_date") or "—")[:col_date]
            dur = (t.get("duration") or "")[:col_dur]
            ctx = format_context(t.get("context"))

            hints = []
            avail = t.get("available_from")
            if avail:
                hints.append(f"avail: {avail}")
            dur_min = t.get("duration_minutes")
            if dur_min:
                hints.append(f"~{dur_min} min")
            recur = t.get("recurrence")
            if recur:
                hints.append(recur)
            hint_str = ("  (" + ", ".join(hints) + ")") if hints else ""

            print(f"  {title:<{col_title}}  {status:<{col_status}}  {goal:<{col_date}}  {dur:<{col_dur}}  {ctx}{hint_str}")


def main():
    parser = argparse.ArgumentParser(description="View Marlin tasks")
    parser.add_argument("--status", default="queued",
                        help="Filter by status: queued (default), done, deferred, waiting, all")
    parser.add_argument("--project", default=None,
                        help="Filter by project name (partial match, case-insensitive)")
    args = parser.parse_args()

    # Header: state
    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    mode = state.get("mode", "available")
    snooze = state.get("snooze_until")
    snooze_str = "none"
    if snooze:
        try:
            snooze_dt = datetime.fromisoformat(snooze)
            if datetime.now() < snooze_dt:
                snooze_str = snooze_dt.strftime("%H:%M")
            # else snooze has expired
        except ValueError:
            pass

    print(f"Mode: {mode}  |  Snooze: {snooze_str}")

    all_tasks = load_all_tasks()

    # Count by status for summary line
    counts: dict[str, int] = defaultdict(int)
    for t in all_tasks:
        counts[t.get("status", "unknown")] += 1

    # Filter
    status_filter = args.status.lower()
    if status_filter == "all":
        filtered = all_tasks
    else:
        filtered = [t for t in all_tasks if t.get("status") == status_filter]

    if args.project:
        proj_lower = args.project.lower()
        filtered = [
            t for t in filtered
            if proj_lower in strip_wikilink(t.get("project")).lower()
        ]

    if not filtered:
        print("\n(no tasks match)")
    else:
        print_table(filtered)

    # Summary counts
    queued = counts.get("queued", 0)
    done = counts.get("done", 0)
    deferred = counts.get("deferred", 0)
    waiting = counts.get("waiting", 0)
    parts = [f"{queued} queued", f"{done} done", f"{deferred} deferred"]
    if waiting:
        parts.append(f"{waiting} waiting")
    print(f"\n{' | '.join(parts)}")


if __name__ == "__main__":
    main()
