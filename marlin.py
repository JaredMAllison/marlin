#!/usr/bin/env python3
"""
Marlin — context-aware task surfacing engine.
Reads the Obsidian vault, picks one task, sends a Ntfy notification.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

# ── Config ────────────────────────────────────────────────────────────────────

VAULT = Path("/home/jared/Documents/Obsidian/Marlin/Tasks")
STATE_FILE = Path("/home/jared/marlin/state.json")
NTFY_TOPIC = os.environ.get("MARLIN_NTFY_TOPIC", "")  # set in environment
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"
WEBHOOK_BASE = os.environ.get("MARLIN_WEBHOOK_BASE", "http://10.0.0.8:7832")

BUSINESS_HOURS_START = 8   # 8am Pacific
BUSINESS_HOURS_END = 17    # 5pm Pacific
BUSINESS_DAYS = {0, 1, 2, 3, 4}  # Mon–Fri

DURATION_MINUTES = {"short": 15, "medium": 45, "long": 120}

# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"mode": "available"}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Vault ─────────────────────────────────────────────────────────────────────

def parse_note(path: Path) -> dict | None:
    """Parse YAML frontmatter from a note. Returns None if not a valid task."""
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
    fm["_body"] = parts[2].strip()
    return fm

def load_tasks() -> list[dict]:
    tasks = []
    for path in VAULT.glob("*.md"):
        note = parse_note(path)
        if note and note.get("type") == "task" and note.get("status") == "queued":
            tasks.append(note)
    return tasks

# ── Filtering ─────────────────────────────────────────────────────────────────

def is_business_hours() -> bool:
    now = datetime.now()
    return now.weekday() in BUSINESS_DAYS and BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END

def is_available_today(task: dict) -> bool:
    available_from = task.get("available_from")
    if not available_from:
        return True
    if not isinstance(available_from, date):
        try:
            available_from = date.fromisoformat(str(available_from))
        except ValueError:
            return True
    return date.today() >= available_from

def context_compatible(task: dict, mode: str) -> bool:
    contexts = task.get("context", [])
    if isinstance(contexts, str):
        contexts = [contexts]

    if mode == "available":
        return True  # all tasks eligible

    if mode == "transit":
        # Only any-time + short duration
        duration = task.get("duration", "medium")
        return "any-time" in contexts and duration == "short"

    return False

def passes_business_hours(task: dict) -> bool:
    contexts = task.get("context", [])
    if isinstance(contexts, str):
        contexts = [contexts]
    if "business-hours" in contexts and not is_business_hours():
        return False
    return True

# ── Sorting ───────────────────────────────────────────────────────────────────

def sort_key(task: dict):
    goal = task.get("goal_date")
    if goal and not isinstance(goal, date):
        try:
            goal = date.fromisoformat(str(goal))
        except ValueError:
            goal = None
    duration = DURATION_MINUTES.get(task.get("duration", "medium"), 45)
    # Sort: soonest goal_date first, then shortest duration
    return (goal or date(9999, 1, 1), duration)

# ── Notification ──────────────────────────────────────────────────────────────

def send_notification(task: dict):
    title = task.get("title", "Task")
    project = task.get("project", "")
    goal = task.get("goal_date", "")
    duration = task.get("duration", "")
    duration_min = task.get("duration_minutes", "")

    lines = []
    if project:
        lines.append(f"Project: {project}")
    if goal:
        lines.append(f"Due: {goal}")
    if duration_min:
        lines.append(f"~{duration_min} min")
    elif duration:
        lines.append(f"Duration: {duration}")
    if task.get("_body"):
        lines.append(task["_body"][:120])

    message = "\n".join(lines) if lines else "Tap to review."

    from urllib.parse import quote
    t = quote(title)
    actions = [
        {"action": "http", "label": "✅ Done",   "url": f"{WEBHOOK_BASE}/done?task={t}",   "method": "GET"},
        {"action": "http", "label": "⏭ Defer",  "url": f"{WEBHOOK_BASE}/defer?task={t}",  "method": "GET"},
        {"action": "http", "label": "💤 Snooze", "url": f"{WEBHOOK_BASE}/snooze?task={t}", "method": "GET"},
    ]
    data = json.dumps({
        "topic": NTFY_TOPIC,
        "title": f"📌 {title}",
        "message": message,
        "priority": 3,
        "actions": actions,
    }).encode()

    req = urllib.request.Request(
        "https://ntfy.sh",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"Surfaced: {title}")
            else:
                print(f"Ntfy returned {resp.status}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Ntfy error: {e}", file=sys.stderr)
        sys.exit(1)

# ── Main ──────────────────────────────────────────────────────────────────────

def recently_surfaced(task: dict, state: dict, cooldown_hours: int = 2) -> bool:
    """Return True if this task was surfaced within the cooldown window."""
    last_title = state.get("last_surfaced_task")
    last_time = state.get("last_surfaced_at")
    if not last_title or not last_time:
        return False
    if task.get("title") != last_title:
        return False
    try:
        surfaced_at = datetime.fromisoformat(last_time)
    except ValueError:
        return False
    return datetime.now() - surfaced_at < timedelta(hours=cooldown_hours)


def main():
    if not NTFY_TOPIC:
        print("MARLIN_NTFY_TOPIC not set.", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    mode = state.get("mode", "available")

    if mode in ("deep-work", "relaxing", "sleeping"):
        print(f"{mode} — surfacing nothing.")
        sys.exit(0)

    # Check snooze
    snooze_until = state.get("snooze_until")
    if snooze_until:
        try:
            if datetime.now() < datetime.fromisoformat(snooze_until):
                print(f"Snoozed until {snooze_until} — surfacing nothing.")
                sys.exit(0)
        except ValueError:
            pass

    tasks = load_tasks()
    eligible = [
        t for t in tasks
        if context_compatible(t, mode)
        and passes_business_hours(t)
        and is_available_today(t)
        and not recently_surfaced(t, state)
    ]

    if not eligible:
        print("No eligible tasks (all recently surfaced or none queued).")
        sys.exit(0)

    eligible.sort(key=sort_key)
    chosen = eligible[0]

    # Record what we surfaced
    state["last_surfaced_task"] = chosen.get("title")
    state["last_surfaced_at"] = datetime.now().isoformat()
    save_state(state)

    send_notification(chosen)

if __name__ == "__main__":
    main()
