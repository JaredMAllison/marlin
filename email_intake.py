"""
email_intake.py — Marlin self-email capture pipeline.

Polls marlin.exobrain@gmail.com for unseen messages from personal_email.
For each message:
  - Saves body as plain text to ~/Documents/vault/emails/
  - Writes an email-stub note to Marlin/Emails/
  - Saves attachments to ~/Documents/vault/images/ with image-stub notes
  - Appends a capture entry to Marlin/Inbox.md
"""

import email
import email.header
import email.message
import email.utils
import imaplib
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from gv_gateway.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

VAULT_PATH = Path.home() / "Documents/Obsidian/Marlin"
EMAILS_STORE = Path.home() / "Documents/vault/emails"
IMAGES_STORE = Path.home() / "Documents/vault/images"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def decode_header_value(raw: str) -> str:
    parts = email.header.decode_header(raw)
    decoded = []
    for chunk, charset in parts:
        if isinstance(chunk, bytes):
            decoded.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(chunk)
    return "".join(decoded).strip()


def parse_date(msg: email.message.Message) -> str:
    raw = msg.get("Date", "")
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")


def extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="replace").strip()
        return ""
    return msg.get_payload(decode=True).decode("utf-8", errors="replace").strip()


def extract_attachments(msg: email.message.Message) -> list[tuple[str, bytes]]:
    """Return list of (filename, data) for non-text parts with a filename."""
    attachments = []
    if not msg.is_multipart():
        return attachments
    for part in msg.walk():
        content_disposition = part.get("Content-Disposition", "")
        filename = part.get_filename()
        if filename and ("attachment" in content_disposition or "inline" in content_disposition):
            data = part.get_payload(decode=True)
            if data:
                attachments.append((decode_header_value(filename), data))
    return attachments


def unique_path(base: Path) -> Path:
    """Return base if it doesn't exist, else base-2, base-3, ..."""
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    n = 2
    while True:
        candidate = base.with_name(f"{stem}-{n}{suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def write_email_stub(slug_date: str, subject: str, date: str, snippet: str) -> None:
    stub_path = VAULT_PATH / "Emails" / f"{slug_date}.md"
    file_path = f"~/Documents/vault/emails/{slug_date}.txt"
    content = f"""---
title: {subject}
type: email-stub
date: {date}
subject: {subject}
file_path: {file_path}
tags: [email]
---

{snippet}

File: `{file_path}`
"""
    stub_path.write_text(content, encoding="utf-8")
    log.info("Wrote email stub: %s", stub_path)


def write_image_stub(filename: str, date: str, subject: str, n: int) -> None:
    stub_name = Path(filename).stem
    stub_path = VAULT_PATH / "Images" / f"{stub_name}.md"
    stub_path = unique_path(stub_path)
    ext = Path(filename).suffix.lstrip(".")
    file_path = f"~/Documents/vault/images/{filename}"
    content = f"""---
title: {subject} — Attachment {n}
type: image-stub
date: {date}
file_path: {file_path}
tags: [image, email]
---

Attachment from email: {subject}

File: `{file_path}`
"""
    stub_path.write_text(content, encoding="utf-8")
    log.info("Wrote image stub: %s", stub_path)


def append_to_inbox(date: str, time: str, subject: str, slug_date: str, body: str) -> None:
    inbox_path = VAULT_PATH / "Inbox.md"
    snippet = body[:300].replace("\n", " ").strip()
    entry = (
        f"\n- {date} {time} email: {subject} → [[Emails/{slug_date}]]\n"
        f"  {snippet}\n"
    )
    with inbox_path.open("a", encoding="utf-8") as f:
        f.write(entry)
    log.info("Appended to Inbox.md")


def process_message(msg: email.message.Message) -> None:
    subject = decode_header_value(msg.get("Subject", "(no subject)"))
    date, time = parse_date(msg)
    body = extract_body(msg)
    attachments = extract_attachments(msg)

    slug = slugify(subject)
    slug_date = f"{slug}-{date}"

    # Save email body as plain text
    txt_path = unique_path(EMAILS_STORE / f"{slug_date}.txt")
    slug_date = txt_path.stem  # may have -2, -3 suffix after collision handling
    header = f"From: self\nDate: {date} {time}\nSubject: {subject}\n\n"
    txt_path.write_text(header + body, encoding="utf-8")
    log.info("Saved email body: %s", txt_path)

    # Write email stub
    snippet = body[:200].strip()
    write_email_stub(slug_date, subject, date, snippet)

    # Handle attachments
    for n, (filename, data) in enumerate(attachments, start=1):
        ext = Path(filename).suffix or ".bin"
        attach_name = f"{slug}-attach-{n}-{date}{ext}"
        attach_path = unique_path(IMAGES_STORE / attach_name)
        attach_path.write_bytes(data)
        log.info("Saved attachment: %s", attach_path)
        write_image_stub(attach_path.name, date, subject, n)

    # Append to Inbox.md
    append_to_inbox(date, time, subject, slug_date, body)


def run() -> None:
    config = load_config()
    EMAILS_STORE.mkdir(parents=True, exist_ok=True)

    log.info("Connecting to Gmail IMAP...")
    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(config.gmail_address, config.gmail_app_password)
        imap.select("INBOX")
        _, data = imap.search(None, f'(UNSEEN FROM "{config.personal_email}")')
        message_nums = data[0].split()

        if not message_nums:
            log.info("No new self-emails.")
            return

        log.info("Found %d new message(s).", len(message_nums))
        for num in message_nums:
            try:
                _, msg_data = imap.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                process_message(msg)
                imap.store(num, "+FLAGS", "\\Seen")
            except Exception as e:
                log.error("Failed to process message %s: %s", num, e)


if __name__ == "__main__":
    run()
