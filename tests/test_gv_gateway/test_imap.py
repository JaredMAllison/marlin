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
