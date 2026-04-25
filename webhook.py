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

from vault import read_frontmatter, update_frontmatter

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
        fm = read_frontmatter(path)
        if isinstance(fm, dict) and fm.get("title") == title:
            return path
    return None

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

def mode_page(current_mode: str) -> str:
    emoji, label, color = MODE_LABELS.get(current_mode, ("❓", current_mode, "#333"))
    buttons = ""
    for m, (e, l, c) in MODE_LABELS.items():
        active = ' style="opacity:0.4;pointer-events:none;"' if m == current_mode else ""
        buttons += f'<a href="/mode?set={m}"{active}><button style="background:{c}">{e} {l}</button></a>\n'
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
{buttons}
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
            html = mode_page(state.get("mode", "available"))
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

        self.respond(200 if ok else 500, msg)
        print(msg)

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
