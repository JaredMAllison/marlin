import os
import secrets
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

DICT_PATH = Path("/usr/share/dict/words")
KEY_PATH = Path.home() / ".config" / "marlin" / "gv_gateway.key"


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


def email_key(word: str, config) -> None:
    today = date.today().strftime("%Y-%m-%d")
    msg = EmailMessage()
    msg["Subject"] = f"Marlin Key — {today}"
    msg["From"] = config.gmail_address
    msg["To"] = config.personal_email
    msg.set_content(word)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(config.gmail_address, config.gmail_app_password)
        smtp.send_message(msg)
