import email
import email.message
import imaplib
import logging
from typing import Generator

GV_SENDER_DOMAIN = "@txt.voice.google.com"

log = logging.getLogger(__name__)


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                break
        else:
            return ""
    else:
        body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
    if "---" in body:
        body = body[:body.index("---")]
    return body.strip()


def fetch_messages(config) -> Generator[str, None, None]:
    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(config.gmail_address, config.gmail_app_password)
        imap.select("INBOX")
        _, data = imap.search(None, f'(UNSEEN FROM "{GV_SENDER_DOMAIN}")')
        for num in data[0].split():
            try:
                _, msg_data = imap.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                body = _extract_body(msg)
                imap.store(num, "+FLAGS", "\\Seen")
                if body:
                    yield body
            except Exception as e:
                log.error("Failed to process message %s: %s", num, e)
