#!/usr/bin/env python3
"""
Marlin webhook server.
Handles Done/Defer/Snooze actions from Ntfy and mode switching via web UI.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import yaml

VAULT = Path("/home/jared/Documents/Obsidian/Marlin/Tasks")
STATE_FILE = Path("/home/jared/marlin/state.json")
PORT = 7832
NTFY_TOPIC = os.environ.get("MARLIN_NTFY_TOPIC", "")
WEBHOOK_BASE = os.environ.get("MARLIN_WEBHOOK_BASE", "http://10.0.0.8:7832")

MODE_LABELS = {
    "available":  ("", "Available",  "#2d7a2d"),
    "deep-work":  ("", "Deep Work",  "#8b0000"),
    "transit":    ("", "Transit",    "#7a5c00"),
}

# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"mode": "available"}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Vault ─────────────────────────────────────────────────────────────────────

def find_task(title: str) -> Path | None:
    for path in VAULT.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            continue
        if isinstance(fm, dict) and fm.get("title") == title:
            return path
    return None

def update_frontmatter(path: Path, updates: dict) -> bool:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return False
    fm.update(updates)
    new_fm = yaml.dump(fm, default_flow_style=False, allow_unicode=True).strip()
    path.write_text(f"---\n{new_fm}\n---{parts[2]}", encoding="utf-8")
    return True

def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}

def next_occurrence(recurrence: str, from_date: date) -> date:
    """Return the next occurrence date given a recurrence value."""
    if recurrence == "daily":
        return from_date + timedelta(days=1)
    elif recurrence == "weekly":
        return from_date + timedelta(weeks=1)
    elif recurrence == "biweekly":
        return from_date + timedelta(weeks=2)
    elif recurrence.startswith("every-") and recurrence.replace("every-", "").replace("-", "").isdigit():
        n = int(recurrence.split("-")[1])
        return from_date + timedelta(days=n)
    elif recurrence.startswith("every-"):
        weekday_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                       "friday": 4, "saturday": 5, "sunday": 6}
        target = weekday_map.get(recurrence.removeprefix("every-"), 0)
        days_ahead = (target - from_date.weekday()) % 7 or 7
        return from_date + timedelta(days=days_ahead)
    else:
        return from_date + timedelta(days=1)

ADL_LOG = VAULT.parent / "ADL-log.md"

def append_adl_log(entry_date: str, slug: str, status: str):
    """Append a done/missed row to ADL-log.md."""
    row = f"| {entry_date} | {slug} | {status} |\n"
    text = ADL_LOG.read_text(encoding="utf-8")
    ADL_LOG.write_text(text + row, encoding="utf-8")

def get_due_adls() -> list[dict]:
    """Return recurring tasks with goal_date <= today, sorted by start_time."""
    today = date.today()
    adls = []
    for path in VAULT.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict) or not fm.get("recurrence"):
            continue
        if "Self-Care" not in str(fm.get("project", "")):
            continue
        goal_date = fm.get("goal_date")
        if goal_date is None:
            continue
        if isinstance(goal_date, str):
            try:
                goal_date = date.fromisoformat(goal_date)
            except ValueError:
                continue
        if goal_date <= today:
            adls.append({
                "title": fm.get("title", path.stem),
                "start_time": fm.get("start_time") or "",
            })
    adls.sort(key=lambda x: (x["start_time"] == "", str(x["start_time"])))
    return adls

# ── Ntfy ──────────────────────────────────────────────────────────────────────

def send_mode_notification(mode: str):
    if not NTFY_TOPIC:
        return
    emoji, label, _ = MODE_LABELS.get(mode, ("❓", mode, "#333"))
    actions = [
        {"action": "http", "label": f"{e} {l}", "url": f"{WEBHOOK_BASE}/mode?set={m}", "method": "GET"}
        for m, (e, l, _) in MODE_LABELS.items() if m != mode
    ]
    data = json.dumps({
        "topic": NTFY_TOPIC,
        "title": f"Marlin — {emoji} {label}",
        "message": "Tap to switch mode.",
        "priority": 1,
        "tags": ["brain"],
        "actions": actions,
    }).encode()
    req = urllib.request.Request(
        "https://ntfy.sh",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.URLError:
        pass

# ── HTML UI ───────────────────────────────────────────────────────────────────

def mode_page(current_mode: str, adls: list[dict]) -> str:
    emoji, label, color = MODE_LABELS.get(current_mode, ("❓", current_mode, "#333"))
    mode_buttons = ""
    for m, (e, l, c) in MODE_LABELS.items():
        active = ' style="opacity:0.4;pointer-events:none;"' if m == current_mode else ""
        mode_buttons += f'<a href="/mode?set={m}"{active}><button style="background:{c}">{e} {l}</button></a>\n'
    adl_section = ""
    if adls:
        adl_buttons = ""
        for adl in adls:
            encoded = quote(adl["title"])
            adl_buttons += f'<a href="/done?task={encoded}"><button style="background:#1a4a2e">✓ {adl["title"]}</button></a>\n'
        adl_section = f"""
<h2 style="margin-top:2rem;font-size:0.9rem;color:#aaa;letter-spacing:0.08em;text-transform:uppercase;">Self-Care</h2>
{adl_buttons}"""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marlin</title>
<style>
  body {{ font-family: sans-serif; text-align: center; padding: 2rem; background: #111; color: #eee; }}
  h1 {{ font-size: 2rem; margin-bottom: 0.25rem; }}
  .mode {{ font-size: 1.2rem; color: {color}; margin-bottom: 2rem; }}
  a {{ text-decoration: none; display: block; margin: 0.75rem auto; max-width: 280px; }}
  button {{ width: 100%; padding: 1.2rem; font-size: 1.2rem; border: none; border-radius: 12px;
            color: white; cursor: pointer; font-weight: bold; }}
</style>
</head>
<body>
<h1>Marlin</h1>
<div class="mode">{emoji} {label}</div>
{mode_buttons}{adl_section}
</body>
</html>"""

# ── Handler ───────────────────────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        action = parsed.path.strip("/")

        # ── Mode switch ──
        if action == "mode":
            new_mode = params.get("set", [None])[0]
            if new_mode not in MODE_LABELS:
                self.respond(400, "Invalid mode")
                return
            state = load_state()
            state["mode"] = new_mode
            save_state(state)
            send_mode_notification(new_mode)
            print(f"Mode → {new_mode}")
            # Redirect back to the status page
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return

        # ── Status page ──
        if action == "":
            state = load_state()
            html = mode_page(state.get("mode", "available"), get_due_adls())
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())
            return

        # ── Task actions ──
        title = params.get("task", [None])[0]
        if not title:
            self.respond(400, "Missing task parameter")
            return

        path = find_task(title)
        if not path:
            self.respond(404, f"Task not found: {title}")
            return

        today = date.today().isoformat()

        if action == "done":
            fm = read_frontmatter(path)
            recurrence = fm.get("recurrence")
            if recurrence:
                # Recurring task — advance goal_date, keep status: queued
                next_date = next_occurrence(recurrence, date.today())
                ok = update_frontmatter(path, {"goal_date": next_date})
                if ok:
                    append_adl_log(today, path.stem, "done")
                msg = f"Done (recurring → {next_date}): {title}" if ok else "Update failed"
            else:
                ok = update_frontmatter(path, {"status": "done", "completed": today})
                msg = f"Done: {title}" if ok else "Update failed"

        elif action == "defer":
            defer_until = (date.today() + timedelta(days=1)).isoformat()
            ok = update_frontmatter(path, {"status": "deferred", "deferred_until": defer_until})
            msg = f"Deferred: {title}" if ok else "Update failed"

        elif action == "snooze":
            state = load_state()
            state["snoozed_task"] = title
            state["snooze_until"] = (datetime.now() + timedelta(hours=2)).isoformat()
            save_state(state)
            msg = f"Snoozed 2h: {title}"
            ok = True

        else:
            self.respond(400, f"Unknown action: {action}")
            return

        print(msg)
        if ok:
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.respond(500, msg)

    def respond(self, code: int, message: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(message.encode())

    def log_message(self, format, *args):
        pass


def main():
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    print(f"Marlin webhook listening on port {PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
