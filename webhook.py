#!/usr/bin/env python3
"""
Marlin Quickhack Panel — webhook server.
Handles Done/Defer/Snooze actions from Ntfy and the Quickhacks UI:
mode switching, ADL completion, inbox capture, today's task list.
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

VAULT      = Path("/home/jared/Documents/Obsidian/Marlin/Tasks")
INBOX_FILE = VAULT.parent / "Inbox.md"
ADL_LOG    = VAULT.parent / "ADL-log.md"
STATE_FILE = Path("/home/jared/marlin/state.json")
PORT       = 7832
NTFY_TOPIC    = os.environ.get("MARLIN_NTFY_TOPIC", "")
WEBHOOK_BASE  = os.environ.get("MARLIN_WEBHOOK_BASE", "http://10.0.0.8:7832")

MODE_LABELS = {
    "available": ("", "Available", "#2d7a2d"),
    "deep-work": ("", "Deep Work", "#8b0000"),
    "transit":   ("", "Transit",   "#7a5c00"),
    "relaxing":  ("", "Relaxing",  "#2d5a7a"),
    "sleeping":  ("", "Sleeping",  "#1a1a3a"),
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

def next_occurrence(recurrence: str, from_date: date) -> date:
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

def append_adl_log(entry_date: str, slug: str, status: str):
    row = f"| {entry_date} | {slug} | {status} |\n"
    if ADL_LOG.exists():
        text = ADL_LOG.read_text(encoding="utf-8")
    else:
        text = "| Date | Task | Status |\n|---|---|---|\n"
    ADL_LOG.write_text(text + row, encoding="utf-8")

def get_due_adls() -> list[dict]:
    today = date.today()
    adls = []
    for path in VAULT.glob("*.md"):
        fm = read_frontmatter(path)
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

def get_today_tasks() -> list[dict]:
    """Return queued tasks with goal_date == today, grouped by project.

    Shape: [{"project": str, "tasks": [{"title": str, "duration": str}]}]
    """
    today = date.today()
    rows: list[tuple[str, dict]] = []
    for path in sorted(VAULT.glob("*.md")):
        fm = read_frontmatter(path)
        if not isinstance(fm, dict):
            continue
        if fm.get("type") != "task" or fm.get("status") != "queued":
            continue
        gd = fm.get("goal_date")
        if isinstance(gd, str):
            try:
                gd = date.fromisoformat(gd)
            except ValueError:
                continue
        if gd != today:
            continue
        proj = str(fm.get("project", "") or "").strip()
        if proj.startswith("[[") and proj.endswith("]]"):
            proj = proj[2:-2]
        rows.append((proj or "(no project)", {
            "title": fm.get("title", path.stem),
            "duration": fm.get("duration", ""),
        }))
    groups: dict[str, list[dict]] = {}
    for proj, task in rows:
        groups.setdefault(proj, []).append(task)
    return [{"project": p, "tasks": ts} for p, ts in groups.items()]

def append_inbox(text: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"- {ts} — {text}\n"
    if not INBOX_FILE.exists():
        INBOX_FILE.write_text("", encoding="utf-8")
    with INBOX_FILE.open("a", encoding="utf-8") as f:
        f.write(line)

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

# ── HTML helpers ──────────────────────────────────────────────────────────────

def _esc(s: str) -> str:
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

def _relative_time(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    secs = int((datetime.now() - dt).total_seconds())
    if secs < 60:    return "just now"
    if secs < 3600:  return f"{secs // 60} min ago"
    if secs < 86400: return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"

def _render_upcoming(groups: list[dict]) -> str:
    if not groups:
        return '<div class="upcoming-empty">clear day</div>'
    out = []
    for g in groups:
        rows = ""
        for t in g["tasks"]:
            dur = {"short": "•", "medium": "••", "long": "•••"}.get(t.get("duration"), "")
            rows += (
                f'<div class="task">'
                f'<div class="task-title">{_esc(t["title"])}</div>'
                f'<div class="duration">{dur}</div>'
                f'</div>'
            )
        out.append(
            f'<div class="project-group">'
            f'<div class="project-name">{_esc(g["project"])}</div>'
            f'{rows}</div>'
        )
    return "\n".join(out)

# ── Dashboard UI ──────────────────────────────────────────────────────────────

DASHBOARD_CSS = """
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0;
    font-family: sans-serif;
    color: #eee;
    min-height: 100vh;
    padding-bottom: 120px;
  }
  body.mode-available { background: radial-gradient(ellipse at top, rgba(45,122,45,0.18),  transparent 70%), #111; }
  body.mode-deep-work { background: radial-gradient(ellipse at top, rgba(139,0,0,0.18),    transparent 70%), #111; }
  body.mode-transit   { background: radial-gradient(ellipse at top, rgba(122,92,0,0.20),   transparent 70%), #111; }
  body.mode-relaxing  { background: radial-gradient(ellipse at top, rgba(45,90,122,0.18),  transparent 70%), #111; }
  body.mode-sleeping  { background: radial-gradient(ellipse at top, rgba(26,26,58,0.25),   transparent 70%), #111; }

  .wrap { max-width: 420px; margin: 0 auto; padding: 2rem 1.25rem 0; text-align: center; }
  h1 { font-size: 2rem; margin: 0 0 0.25rem; font-weight: 700; }
  .mode-label { font-size: 1.2rem; margin-bottom: 1.75rem; }

  .current {
    max-width: 320px; margin: 0 auto 1.5rem;
    padding: 20px 22px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; text-align: left;
  }
  .current .eyebrow { font-size: 10px; letter-spacing: 1.5px; color: #aaa; text-transform: uppercase; font-weight: 700; }
  .current .title   { font-size: 20px; font-weight: 700; margin-top: 6px; line-height: 1.2; }
  .current .meta    { font-size: 13px; color: #aaa; margin-top: 6px; }
  .current.empty    { background: transparent; border: 1px dashed #555; color: #aaa; font-size: 14px; text-align: center; padding: 18px 20px; }

  .section-head { font-size: 0.9rem; color: #aaa; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600; margin: 0 0 10px; }
  .upcoming { max-width: 320px; margin: 0 auto 1.5rem; text-align: left; }
  .upcoming .project-group { margin-bottom: 16px; }
  .upcoming .project-name  { font-size: 12px; color: #aaa; font-weight: 700; margin-bottom: 4px; padding-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.08); }
  .upcoming .task          { display: flex; align-items: center; padding: 8px 4px; }
  .upcoming .task-title    { flex: 1; font-size: 15px; color: #eee; line-height: 1.3; }
  .upcoming .duration      { font-size: 13px; color: #aaa; letter-spacing: 2px; margin-left: 10px; flex-shrink: 0; }
  .upcoming-empty          { color: #555; font-size: 14px; padding: 12px 0 24px; }

  a.btn-link { text-decoration: none; display: block; margin: 0.75rem auto; max-width: 280px; }
  a.btn-link button { width: 100%; padding: 1.2rem; font-size: 1.2rem; border: none; border-radius: 12px; color: white; cursor: pointer; font-weight: bold; font-family: inherit; }
  a.btn-link.dim { opacity: 0.4; pointer-events: none; }

  h2.adl-head { margin: 2rem 0 0.5rem; font-size: 0.9rem; color: #aaa; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600; }

  .inbox {
    position: fixed; bottom: 0; left: 0; right: 0;
    padding: 12px 16px 16px;
    background: rgba(17,17,17,0.92);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-top: 1px solid rgba(255,255,255,0.08);
    z-index: 20;
  }
  .inbox form   { display: flex; gap: 8px; max-width: 320px; margin: 0 auto; }
  .inbox input  { flex: 1; min-width: 0; padding: 12px 14px; font-size: 15px; background: rgba(255,255,255,0.06); color: #eee; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; outline: none; font-family: inherit; }
  .inbox button { width: 48px; padding: 0; font-size: 18px; font-weight: 700; background: rgba(255,255,255,0.08); color: #aaa; border: none; border-radius: 10px; cursor: pointer; transition: background .15s, color .15s; font-family: inherit; }
  .inbox.has-text button { background: #eee; color: #111; }
  .inbox .flash { font-size: 12px; color: #2d7a2d; text-align: center; margin-bottom: 6px; min-height: 16px; }
"""


def dashboard_page(current_mode: str, adls: list[dict]) -> str:
    emoji, label, color = MODE_LABELS.get(current_mode, ("❓", current_mode, "#333"))

    state = load_state()
    surfaced_title = state.get("last_surfaced_task")
    if surfaced_title:
        surfaced_project = ""
        task_path = find_task(surfaced_title)
        if task_path:
            fm = read_frontmatter(task_path)
            proj = str(fm.get("project", "") or "").strip()
            if proj.startswith("[[") and proj.endswith("]]"):
                proj = proj[2:-2]
            surfaced_project = proj
        surfaced_at = state.get("last_surfaced_at", "")
        meta_bits = [b for b in (surfaced_project, _relative_time(surfaced_at)) if b]
        meta = " · ".join(meta_bits)
        current_html = f"""
  <div class="current">
    <div class="eyebrow">Now surfacing</div>
    <div class="title">{_esc(surfaced_title)}</div>
    {f'<div class="meta">{_esc(meta)}</div>' if meta else ''}
  </div>"""
    else:
        current_html = '\n  <div class="current empty">nothing surfaced yet</div>'

    groups = get_today_tasks()
    total = sum(len(g["tasks"]) for g in groups)
    upcoming_html = _render_upcoming(groups)

    mode_buttons = ""
    for m, (e, l, c) in MODE_LABELS.items():
        dim = ' dim' if m == current_mode else ""
        mode_buttons += (
            f'<a class="btn-link{dim}" href="/mode?set={m}">'
            f'<button style="background:{c}">{l}</button></a>\n'
        )

    adl_html = ""
    if adls:
        adl_buttons = ""
        for adl in adls:
            encoded = quote(adl["title"])
            adl_buttons += (
                f'<a class="btn-link" href="/done?task={encoded}">'
                f'<button style="background:#1a4a2e">✓ {_esc(adl["title"])}</button></a>\n'
            )
        adl_html = f'<h2 class="adl-head">Self-Care</h2>\n{adl_buttons}'

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quickhacks</title>
<style>{DASHBOARD_CSS}</style>
</head>
<body class="mode-{current_mode}">
<div class="wrap">
  <h1>Quickhacks</h1>
  <div class="mode-label" style="color:{color}">{label}</div>
{current_html}

  <h2 class="section-head">Upcoming{f' · {total}' if total else ''}</h2>
  <div class="upcoming">{upcoming_html}</div>

  {mode_buttons}
  {adl_html}
</div>

<div class="inbox" id="inbox">
  <div class="flash" id="flash"></div>
  <form id="inbox-form" autocomplete="off">
    <input id="inbox-input" type="text" placeholder="capture..." />
    <button type="submit">↵</button>
  </form>
</div>

<script>
(function() {{
  var input  = document.getElementById('inbox-input');
  var form   = document.getElementById('inbox-form');
  var flash  = document.getElementById('flash');
  var wrap   = document.getElementById('inbox');

  input.addEventListener('input', function() {{
    wrap.classList.toggle('has-text', input.value.trim().length > 0);
  }});

  form.addEventListener('submit', function(e) {{
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    fetch('/inbox', {{
      method: 'POST',
      headers: {{'Content-Type': 'text/plain'}},
      body: text,
    }}).then(function(r) {{
      if (r.ok) {{
        input.value = '';
        wrap.classList.remove('has-text');
        flash.textContent = 'captured ✓';
        setTimeout(function() {{ flash.textContent = ''; }}, 1400);
      }} else {{
        flash.textContent = 'error — try again';
      }}
    }}).catch(function() {{ flash.textContent = 'error — try again'; }});
  }});
}})();
</script>
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
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return

        # ── Dashboard ──
        if action == "":
            state = load_state()
            html = dashboard_page(state.get("mode", "available"), get_due_adls())
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        # ── Today's tasks JSON ──
        if action == "tasks/today":
            body = json.dumps(get_today_tasks()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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

    def do_POST(self):
        if self.path.strip("/") != "inbox":
            self.respond(404, "Not found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", errors="replace").strip()
        if not body:
            self.respond(400, "Empty body")
            return
        try:
            append_inbox(body)
        except OSError as exc:
            print(f"Inbox write failed: {exc}")
            self.respond(500, "Write failed")
            return
        print(f"Inbox ← {body[:60]}")
        self.respond(200, "ok")

    def respond(self, code: int, message: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(message.encode())

    def log_message(self, format, *args):
        pass


def main():
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    print(f"Marlin Quickhack Panel listening on port {PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
