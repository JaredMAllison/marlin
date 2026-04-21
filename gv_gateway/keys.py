import os
import secrets
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

DICT_PATH = Path("/usr/share/dict/words")
KEY_PATH = Path.home() / ".config" / "marlin" / "gv_gateway.key"

ROUTE_DESCRIPTIONS = {
    "inbox": "→ Jared's Exo-Brain: appends your message to the inbox",
    "sos":   "→ Emergency broadcast: SMS to family + Nextcloud Talk alert",
    "ntfy":  "→ Push notification directly to Jared's phone",
}


def _load_words(dict_path: Path = DICT_PATH) -> list[str]:
    with open(dict_path) as f:
        return [
            w.strip() for w in f
            if w.strip().isalpha()
            and w.strip()[0].islower()
            and 5 <= len(w.strip()) <= 8
        ]


def generate_key(dict_path: Path = DICT_PATH, key_path: Path = KEY_PATH) -> str:
    words = _load_words(dict_path)
    word = secrets.choice(words)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(word)
    return word


def read_key(key_path: Path = KEY_PATH) -> str:
    return key_path.read_text().strip()


def _build_directory(word: str, routes: list[str]) -> str:
    lines = []
    for r in routes:
        desc = ROUTE_DESCRIPTIONS.get(r, "→ (route description not configured)")
        lines.append(f"  {word}: {r}: your message\n      {desc}")
    return "\n\n".join(lines)


def email_key(word: str, user, config) -> None:
    today = date.today().strftime("%Y-%m-%d")
    directory = _build_directory(word, user.routes)
    body = (
        f"Marlin key for {today}: {word}\n\n"
        f"Send a command by SMS to (971) 246-7642:\n\n"
        f"{directory}\n\n"
        f"Format: [key]: [command]: [your message]\n"
        f"Example: {word}: {user.routes[0]}: your message here\n"
    )
    msg = EmailMessage()
    msg["Subject"] = f"Marlin Key — {today}"
    msg["From"] = config.gmail_address
    msg["To"] = user.email
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(config.gmail_address, config.gmail_app_password)
        smtp.send_message(msg)
