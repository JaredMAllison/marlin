from datetime import datetime
from gv_gateway import notify
from gv_gateway.users import load_users


def _parse(raw: str) -> tuple[str, str, str] | None:
    for line in raw.splitlines():
        parts = line.strip().split(": ", 2)
        if len(parts) == 3:
            return (parts[0], parts[1], parts[2])
    return None


def _find_user(key: str, users):
    for user in users:
        try:
            if key.lower() == user.key_file.read_text().strip().lower():
                return user
        except FileNotFoundError:
            continue
    return None


def route(raw: str, config) -> None:
    parsed = _parse(raw)
    if parsed is None:
        return
    key, keyword, payload = parsed
    user = _find_user(key, load_users())
    if user is None:
        return
    if keyword not in user.routes:
        return
    if keyword == "inbox":
        _handle_inbox(payload, user, config)
    label = f" (from {user.broadcast_name})" if user.broadcast_name else ""
    notify.send("Marlin", f"{payload}{label}")


def _handle_inbox(payload: str, user, config) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    sender = f"[{user.broadcast_name}] " if user.broadcast_name else ""
    line = f"- {timestamp} — {sender}{payload}\n"
    with open(config.inbox_path, "a") as f:
        f.write(line)
