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
