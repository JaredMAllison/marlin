from datetime import datetime
from pathlib import Path
from gv_gateway import keys, notify


def _parse(raw: str) -> tuple[str, str, str] | None:
    parts = raw.split(": ", 2)
    if len(parts) != 3:
        return None
    return (parts[0], parts[1], parts[2])


def route(raw: str, config) -> None:
    parsed = _parse(raw)
    if parsed is None:
        return
    key, keyword, payload = parsed
    if key != keys.read_key():
        return
    if keyword == "inbox":
        _handle_inbox(payload, config)
    notify.send("Marlin", payload)


def _handle_inbox(payload: str, config) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"- {timestamp} — {payload}\n"
    with open(config.inbox_path, "a") as f:
        f.write(line)
