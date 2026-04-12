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
