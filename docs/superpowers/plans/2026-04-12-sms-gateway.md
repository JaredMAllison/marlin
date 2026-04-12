# SMS Gateway (gv-gateway) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python package that polls Gmail via IMAP for Google Voice SMS, validates a daily rotating dictionary-word key, routes `inbox` commands to Obsidian Inbox.md, and fires a desktop notification on Gretchen.

**Architecture:** A `gv_gateway/` package inside `~/marlin/` with five focused modules (config, keys, imap, router, notify) and two entry points (main.py for polling loop, keygen.py for daily key rotation). Two systemd units drive the services: a persistent polling service and a daily 07:00 timer for key rotation.

**Tech Stack:** Python 3.12, stdlib only (imaplib, smtplib, subprocess), PyYAML (already installed), pytest (needs install), notify-send (present at /usr/bin/notify-send)

---

## File Map

| File | Responsibility |
|---|---|
| `gv_gateway/__init__.py` | Package marker |
| `gv_gateway/config.py` | Load and parse `~/.config/marlin/gv_gateway.yml` |
| `gv_gateway/keys.py` | Generate daily key from dictionary, write to file, email it |
| `gv_gateway/imap.py` | Connect to Gmail IMAP, fetch unread GV emails, yield bodies |
| `gv_gateway/router.py` | Parse message, validate key, dispatch to handler |
| `gv_gateway/notify.py` | notify-send wrapper |
| `gv_gateway/keygen.py` | Entry point for daily key rotation (called by systemd timer) |
| `gv_gateway/main.py` | Entry point for polling loop (called by systemd service) |
| `tests/__init__.py` | Package marker |
| `tests/test_gv_gateway/__init__.py` | Package marker |
| `tests/test_gv_gateway/test_config.py` | Config loading tests |
| `tests/test_gv_gateway/test_keys.py` | Key generation, file write, email composition tests |
| `tests/test_gv_gateway/test_imap.py` | Email parsing and IMAP fetch tests |
| `tests/test_gv_gateway/test_router.py` | Parse, validate, dispatch, inbox append tests |
| `tests/test_gv_gateway/test_notify.py` | notify-send invocation tests |
| `systemd/gv-gateway.service` | Systemd service for polling loop |
| `systemd/gv-keygen.service` | Systemd oneshot for key rotation |
| `systemd/gv-keygen.timer` | Systemd timer — fires daily at 07:00 |
| `pytest.ini` | pytest config (test discovery) |

---

## Task 1: Install pytest and scaffold package structure

**Files:**
- Create: `gv_gateway/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_gv_gateway/__init__.py`
- Create: `pytest.ini`

- [ ] **Step 1: Install pytest**

```bash
pip3 install --user pytest
```

Expected: `Successfully installed pytest-...`

- [ ] **Step 2: Create package directories and empty init files**

```bash
mkdir -p gv_gateway tests/test_gv_gateway systemd
touch gv_gateway/__init__.py tests/__init__.py tests/test_gv_gateway/__init__.py
```

- [ ] **Step 3: Create pytest.ini**

Contents of `pytest.ini`:
```ini
[pytest]
testpaths = tests
```

- [ ] **Step 4: Verify pytest discovers the test directory**

```bash
cd /home/jared/marlin && python3 -m pytest --collect-only
```

Expected: `no tests ran` (no test files yet, but no errors)

- [ ] **Step 5: Commit**

```bash
git add gv_gateway/__init__.py tests/__init__.py tests/test_gv_gateway/__init__.py pytest.ini
git commit -m "feat: scaffold gv_gateway package and pytest config"
```

---

## Task 2: Config module

**Files:**
- Create: `gv_gateway/config.py`
- Create: `tests/test_gv_gateway/test_config.py`

- [ ] **Step 1: Write the failing tests**

Contents of `tests/test_gv_gateway/test_config.py`:
```python
import pytest
import yaml
from pathlib import Path
from gv_gateway.config import load_config, Config


def test_load_config_all_fields(tmp_path):
    cfg_file = tmp_path / "gv_gateway.yml"
    cfg_file.write_text(yaml.dump({
        "gmail_address": "marlin@gmail.com",
        "gmail_app_password": "secret",
        "personal_email": "jared@gmail.com",
        "inbox_path": "/home/jared/Inbox.md",
        "poll_interval_seconds": 30,
    }))
    config = load_config(cfg_file)
    assert config.gmail_address == "marlin@gmail.com"
    assert config.gmail_app_password == "secret"
    assert config.personal_email == "jared@gmail.com"
    assert config.inbox_path == Path("/home/jared/Inbox.md")
    assert config.poll_interval_seconds == 30


def test_load_config_default_poll_interval(tmp_path):
    cfg_file = tmp_path / "gv_gateway.yml"
    cfg_file.write_text(yaml.dump({
        "gmail_address": "marlin@gmail.com",
        "gmail_app_password": "secret",
        "personal_email": "jared@gmail.com",
        "inbox_path": "/home/jared/Inbox.md",
    }))
    config = load_config(cfg_file)
    assert config.poll_interval_seconds == 60


def test_load_config_missing_required_field(tmp_path):
    cfg_file = tmp_path / "gv_gateway.yml"
    cfg_file.write_text(yaml.dump({
        "gmail_address": "marlin@gmail.com",
    }))
    with pytest.raises(KeyError):
        load_config(cfg_file)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_config.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'gv_gateway.config'`

- [ ] **Step 3: Implement config.py**

Contents of `gv_gateway/config.py`:
```python
import yaml
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "marlin" / "gv_gateway.yml"


@dataclass
class Config:
    gmail_address: str
    gmail_app_password: str
    personal_email: str
    inbox_path: Path
    poll_interval_seconds: int = 60


def load_config(path: Path = CONFIG_PATH) -> Config:
    with open(path) as f:
        data = yaml.safe_load(f)
    return Config(
        gmail_address=data["gmail_address"],
        gmail_app_password=data["gmail_app_password"],
        personal_email=data["personal_email"],
        inbox_path=Path(data["inbox_path"]),
        poll_interval_seconds=data.get("poll_interval_seconds", 60),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_config.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add gv_gateway/config.py tests/test_gv_gateway/test_config.py
git commit -m "feat: add config module with YAML loading"
```

---

## Task 3: Key generation and storage

**Files:**
- Create: `gv_gateway/keys.py`
- Create: `tests/test_gv_gateway/test_keys.py`

- [ ] **Step 1: Write the failing tests**

Contents of `tests/test_gv_gateway/test_keys.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import date
from gv_gateway.keys import generate_key, read_key, email_key
from gv_gateway.config import Config


@pytest.fixture
def dict_file(tmp_path):
    f = tmp_path / "words"
    # "Banana" excluded (capital), "cat's" excluded (apostrophe), "hi" excluded (too short)
    f.write_text("apple\nBanana\ncat's\nelephant\ntiger\nhi\nlongwordhere\n")
    return f


@pytest.fixture
def key_file(tmp_path):
    return tmp_path / "gv_gateway.key"


@pytest.fixture
def config(tmp_path):
    return Config(
        gmail_address="marlin@gmail.com",
        gmail_app_password="secret",
        personal_email="jared@gmail.com",
        inbox_path=tmp_path / "Inbox.md",
    )


def test_generate_key_only_selects_valid_words(dict_file, key_file):
    # Run many times to increase confidence; only apple, elephant, tiger are valid
    seen = set()
    for _ in range(50):
        word = generate_key(dict_path=dict_file, key_path=key_file)
        seen.add(word)
    assert seen.issubset({"apple", "elephant", "tiger"})


def test_generate_key_word_length_in_range(dict_file, key_file):
    for _ in range(20):
        word = generate_key(dict_path=dict_file, key_path=key_file)
        assert 5 <= len(word) <= 8


def test_generate_key_writes_to_file(dict_file, key_file):
    word = generate_key(dict_path=dict_file, key_path=key_file)
    assert key_file.read_text() == word


def test_read_key_returns_stored_word(tmp_path):
    key_file = tmp_path / "gv_gateway.key"
    key_file.write_text("maple")
    assert read_key(key_file) == "maple"


def test_read_key_strips_whitespace(tmp_path):
    key_file = tmp_path / "gv_gateway.key"
    key_file.write_text("maple\n")
    assert read_key(key_file) == "maple"


def test_email_key_sends_correct_subject_and_body(config):
    today = date.today().strftime("%Y-%m-%d")
    with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
        mock_smtp = mock_smtp_cls.return_value.__enter__.return_value
        email_key("maple", config)
        mock_smtp.login.assert_called_once_with("marlin@gmail.com", "secret")
        sent_msg = mock_smtp.send_message.call_args[0][0]
        assert f"Marlin Key — {today}" == sent_msg["Subject"]
        assert sent_msg["To"] == "jared@gmail.com"
        assert "maple" in sent_msg.get_payload()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_keys.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'gv_gateway.keys'`

- [ ] **Step 3: Implement keys.py**

Contents of `gv_gateway/keys.py`:
```python
import random
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
    word = random.choice(words)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(word)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_keys.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add gv_gateway/keys.py tests/test_gv_gateway/test_keys.py
git commit -m "feat: add key generation, storage, and email"
```

---

## Task 4: IMAP module

**Files:**
- Create: `gv_gateway/imap.py`
- Create: `tests/test_gv_gateway/test_imap.py`

- [ ] **Step 1: Write the failing tests**

Contents of `tests/test_gv_gateway/test_imap.py`:
```python
import pytest
import email
from email.message import EmailMessage
from unittest.mock import patch, MagicMock
from gv_gateway.imap import _extract_body, fetch_messages
from gv_gateway.config import Config


@pytest.fixture
def config(tmp_path):
    return Config(
        gmail_address="marlin@gmail.com",
        gmail_app_password="secret",
        personal_email="jared@gmail.com",
        inbox_path=tmp_path / "Inbox.md",
    )


def _make_raw_email(body: str) -> bytes:
    msg = EmailMessage()
    msg["From"] = "15031234567@txt.voice.google.com"
    msg["Subject"] = "SMS from +15031234567"
    msg.set_content(body)
    return msg.as_bytes()


def test_extract_body_strips_gv_footer():
    msg = EmailMessage()
    msg.set_content("maple: inbox: hello\n\n---\n(SMS from +15031234567)\n")
    result = _extract_body(msg)
    assert result == "maple: inbox: hello"


def test_extract_body_no_footer():
    msg = EmailMessage()
    msg.set_content("maple: inbox: hello")
    result = _extract_body(msg)
    assert result == "maple: inbox: hello"


def test_fetch_messages_yields_body(config):
    raw = _make_raw_email("maple: inbox: test payload\n\n---\nfooter\n")
    with patch("imaplib.IMAP4_SSL") as mock_cls:
        mock_imap = mock_cls.return_value.__enter__.return_value
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b"1"])
        mock_imap.fetch.return_value = ("OK", [(b"1 (RFC822 {123})", raw)])
        results = list(fetch_messages(config))
    assert results == ["maple: inbox: test payload"]


def test_fetch_messages_empty_inbox(config):
    with patch("imaplib.IMAP4_SSL") as mock_cls:
        mock_imap = mock_cls.return_value.__enter__.return_value
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b""])
        results = list(fetch_messages(config))
    assert results == []


def test_fetch_messages_marks_read(config):
    raw = _make_raw_email("maple: inbox: hello")
    with patch("imaplib.IMAP4_SSL") as mock_cls:
        mock_imap = mock_cls.return_value.__enter__.return_value
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b"1"])
        mock_imap.fetch.return_value = ("OK", [(b"1 (RFC822 {123})", raw)])
        list(fetch_messages(config))
        mock_imap.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_imap.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'gv_gateway.imap'`

- [ ] **Step 3: Implement imap.py**

Contents of `gv_gateway/imap.py`:
```python
import email
import imaplib
from typing import Generator

GV_SENDER_DOMAIN = "@txt.voice.google.com"


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode()
                break
        else:
            return ""
    else:
        body = msg.get_payload(decode=True).decode()
    if "---" in body:
        body = body[:body.index("---")]
    return body.strip()


def fetch_messages(config) -> Generator[str, None, None]:
    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(config.gmail_address, config.gmail_app_password)
        imap.select("INBOX")
        _, data = imap.search(None, f'(UNSEEN FROM "{GV_SENDER_DOMAIN}")')
        for num in data[0].split():
            _, msg_data = imap.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            body = _extract_body(msg)
            imap.store(num, "+FLAGS", "\\Seen")
            if body:
                yield body
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_imap.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add gv_gateway/imap.py tests/test_gv_gateway/test_imap.py
git commit -m "feat: add IMAP polling with GV email parsing"
```

---

## Task 5: Notify module

**Files:**
- Create: `gv_gateway/notify.py`
- Create: `tests/test_gv_gateway/test_notify.py`

- [ ] **Step 1: Write the failing tests**

Contents of `tests/test_gv_gateway/test_notify.py`:
```python
from unittest.mock import patch
from gv_gateway.notify import send


def test_send_calls_notify_send():
    with patch("subprocess.run") as mock_run:
        send("Marlin", "buy milk")
        mock_run.assert_called_once_with(
            ["notify-send", "Marlin", "buy milk"], check=True
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_notify.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'gv_gateway.notify'`

- [ ] **Step 3: Implement notify.py**

Contents of `gv_gateway/notify.py`:
```python
import subprocess


def send(title: str, body: str) -> None:
    subprocess.run(["notify-send", title, body], check=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_notify.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add gv_gateway/notify.py tests/test_gv_gateway/test_notify.py
git commit -m "feat: add notify-send wrapper"
```

---

## Task 6: Router module

**Files:**
- Create: `gv_gateway/router.py`
- Create: `tests/test_gv_gateway/test_router.py`

- [ ] **Step 1: Write the failing tests**

Contents of `tests/test_gv_gateway/test_router.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import patch
from gv_gateway.router import route, _parse
from gv_gateway.config import Config


@pytest.fixture
def config(tmp_path):
    inbox = tmp_path / "Inbox.md"
    inbox.write_text("# Inbox\n\n")
    return Config(
        gmail_address="marlin@gmail.com",
        gmail_app_password="secret",
        personal_email="jared@gmail.com",
        inbox_path=inbox,
    )


def test_parse_valid_message():
    assert _parse("maple: inbox: buy milk") == ("maple", "inbox", "buy milk")


def test_parse_missing_separator_returns_none():
    assert _parse("maple inbox buy milk") is None


def test_parse_only_two_parts_returns_none():
    assert _parse("maple: inbox") is None


def test_parse_payload_can_contain_colons():
    assert _parse("maple: inbox: http://example.com") == (
        "maple", "inbox", "http://example.com"
    )


def test_route_inbox_appends_to_file(config):
    with patch("gv_gateway.keys.read_key", return_value="maple"), \
         patch("gv_gateway.notify.send"):
        route("maple: inbox: buy milk", config)
    content = Path(config.inbox_path).read_text()
    assert "buy milk" in content


def test_route_inbox_line_format(config):
    with patch("gv_gateway.keys.read_key", return_value="maple"), \
         patch("gv_gateway.notify.send"), \
         patch("gv_gateway.router.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-04-12 11:00"
        route("maple: inbox: buy milk", config)
    content = Path(config.inbox_path).read_text()
    assert "- 2026-04-12 11:00 — buy milk\n" in content


def test_route_inbox_fires_notification(config):
    with patch("gv_gateway.keys.read_key", return_value="maple"), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("maple: inbox: buy milk", config)
    mock_notify.assert_called_once_with("Marlin", "buy milk")


def test_route_unknown_keyword_notifies_only(config):
    with patch("gv_gateway.keys.read_key", return_value="maple"), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("maple: sos: emergency", config)
    content = Path(config.inbox_path).read_text()
    assert "emergency" not in content
    mock_notify.assert_called_once_with("Marlin", "emergency")


def test_route_invalid_key_drops_silently(config):
    with patch("gv_gateway.keys.read_key", return_value="maple"), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("wrong: inbox: buy milk", config)
    content = Path(config.inbox_path).read_text()
    assert "buy milk" not in content
    mock_notify.assert_not_called()


def test_route_malformed_message_drops_silently(config):
    with patch("gv_gateway.keys.read_key", return_value="maple"), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("this is not valid", config)
    mock_notify.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_router.py -v
```

Expected: `ERROR` — `ModuleNotFoundError: No module named 'gv_gateway.router'`

- [ ] **Step 3: Implement router.py**

Contents of `gv_gateway/router.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/jared/marlin && python3 -m pytest tests/test_gv_gateway/test_router.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Run the full test suite**

```bash
cd /home/jared/marlin && python3 -m pytest -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add gv_gateway/router.py tests/test_gv_gateway/test_router.py
git commit -m "feat: add router with key validation and inbox dispatch"
```

---

## Task 7: Entry points (keygen + main)

**Files:**
- Create: `gv_gateway/keygen.py`
- Create: `gv_gateway/main.py`

- [ ] **Step 1: Create keygen.py**

Contents of `gv_gateway/keygen.py`:
```python
import logging
from gv_gateway.config import load_config
from gv_gateway.keys import generate_key, email_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def run() -> None:
    config = load_config()
    word = generate_key()
    email_key(word, config)
    log.info("Key rotated and emailed to %s", config.personal_email)


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Create main.py**

Contents of `gv_gateway/main.py`:
```python
import time
import logging
from gv_gateway.config import load_config
from gv_gateway import imap, router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def run() -> None:
    config = load_config()
    log.info("gv-gateway started — polling every %ds", config.poll_interval_seconds)
    while True:
        try:
            for message in imap.fetch_messages(config):
                log.info("Received: %s", message[:60])
                router.route(message, config)
        except Exception as e:
            log.error("Poll error: %s", e)
        time.sleep(config.poll_interval_seconds)


if __name__ == "__main__":
    run()
```

- [ ] **Step 3: Verify keygen runs without a config file error message**

```bash
cd /home/jared/marlin && python3 -m gv_gateway.keygen 2>&1 | head -3
```

Expected: `FileNotFoundError` referencing `gv_gateway.yml` — that's correct, no config exists yet. If it says something else, investigate.

- [ ] **Step 4: Commit**

```bash
git add gv_gateway/keygen.py gv_gateway/main.py
git commit -m "feat: add keygen and main entry points"
```

---

## Task 8: Systemd units

**Files:**
- Create: `systemd/gv-gateway.service`
- Create: `systemd/gv-keygen.service`
- Create: `systemd/gv-keygen.timer`

- [ ] **Step 1: Create gv-gateway.service**

Contents of `systemd/gv-gateway.service`:
```ini
[Unit]
Description=Marlin GV Gateway — IMAP polling
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -m gv_gateway.main
WorkingDirectory=/home/jared/marlin
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

- [ ] **Step 2: Create gv-keygen.service**

Contents of `systemd/gv-keygen.service`:
```ini
[Unit]
Description=Marlin GV Key Rotation

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -m gv_gateway.keygen
WorkingDirectory=/home/jared/marlin
```

- [ ] **Step 3: Create gv-keygen.timer**

Contents of `systemd/gv-keygen.timer`:
```ini
[Unit]
Description=Marlin GV Key Rotation — daily at 07:00

[Timer]
OnCalendar=*-*-* 07:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 4: Commit**

```bash
git add systemd/
git commit -m "feat: add systemd service and timer units for gv-gateway"
```

---

## Task 9: Config file and manual smoke test

This task is manual setup — no code written. Gets the gateway running end-to-end.

- [ ] **Step 1: Create the config directory**

```bash
mkdir -p ~/.config/marlin
```

- [ ] **Step 2: Create the config file**

```bash
cat > ~/.config/marlin/gv_gateway.yml << 'EOF'
gmail_address: <marlin gmail address>
gmail_app_password: <app password from Google account settings>
personal_email: <your personal gmail>
inbox_path: /home/jared/Documents/Obsidian/Marlin/Inbox.md
poll_interval_seconds: 60
EOF
```

Fill in the actual values. The app password is generated at: Google Account → Security → 2-Step Verification → App passwords. Name it "Marlin Gateway".

- [ ] **Step 3: Generate first key manually and verify email arrives**

```bash
cd /home/jared/marlin && python3 -m gv_gateway.keygen
```

Expected: `Key rotated and emailed to <your personal email>` — check your Gmail inbox for `Marlin Key — 2026-04-12`.

- [ ] **Step 4: Install and start systemd units**

```bash
cp /home/jared/marlin/systemd/gv-gateway.service ~/.config/systemd/user/
cp /home/jared/marlin/systemd/gv-keygen.service ~/.config/systemd/user/
cp /home/jared/marlin/systemd/gv-keygen.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now gv-gateway.service
systemctl --user enable --now gv-keygen.timer
```

- [ ] **Step 5: Verify both units are running**

```bash
systemctl --user status gv-gateway.service
systemctl --user status gv-keygen.timer
```

Expected: `gv-gateway.service` — `active (running)`. `gv-keygen.timer` — `active (waiting)`.

- [ ] **Step 6: Send a test SMS and verify end-to-end**

From any phone, send an SMS to the GV number:
```
<today's key>: inbox: test message from SMS gateway
```

Wait up to 60 seconds. Verify:
1. Line appears in `/home/jared/Documents/Obsidian/Marlin/Inbox.md`
2. Desktop notification fired on Gretchen

- [ ] **Step 7: Check gateway logs**

```bash
journalctl --user -u gv-gateway.service -n 20
```

Expected: `Received: <key>: inbox: test message...`

---

## Verification Checklist

- [ ] `python3 -m pytest -v` — all tests pass
- [ ] `systemctl --user status gv-gateway.service` — active (running)
- [ ] `systemctl --user status gv-keygen.timer` — active (waiting), next trigger ~07:00
- [ ] Test SMS → line in Inbox.md within 60s
- [ ] Test SMS → desktop notification on Gretchen
- [ ] Wrong key → nothing happens
- [ ] `Marlin Key — YYYY-MM-DD` email in personal Gmail
