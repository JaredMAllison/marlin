import pytest
from pathlib import Path
from unittest.mock import patch
from gv_gateway.router import route, _parse, _find_user
from gv_gateway.users import User
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


@pytest.fixture
def jared(tmp_path):
    key = tmp_path / "jared.key"
    key.write_text("maple")
    return User(
        user_id="jared",
        key_file=key,
        email="jared@gmail.com",
        broadcast_name="Jared (SMS)",
        ntfy_topic="jared-topic",
        routes=["inbox", "sos", "ntfy"],
    )


@pytest.fixture
def family(tmp_path):
    key = tmp_path / "family.key"
    key.write_text("forest")
    return User(
        user_id="family",
        key_file=key,
        email=None,
        broadcast_name="Family",
        ntfy_topic=None,
        routes=["sos"],
    )


# --- _parse ---

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


def test_parse_skips_preamble_lines():
    raw = "<https://voice.google.com>\nmaple: inbox: buy milk"
    assert _parse(raw) == ("maple", "inbox", "buy milk")


# --- _find_user ---

def test_find_user_matches_correct_user(jared, family):
    assert _find_user("maple", [jared, family]) is jared


def test_find_user_no_match_returns_none(jared, family):
    assert _find_user("wrong", [jared, family]) is None


def test_find_user_case_insensitive(jared):
    assert _find_user("Maple", [jared]) is jared
    assert _find_user("MAPLE", [jared]) is jared


def test_find_user_missing_key_file_skipped(tmp_path, family):
    ghost = User(
        user_id="ghost",
        key_file=tmp_path / "missing.key",
        email=None,
        broadcast_name=None,
        ntfy_topic=None,
        routes=[],
    )
    assert _find_user("forest", [ghost, family]) is family


# --- route: inbox ---

def test_route_inbox_appends_to_file(config, jared):
    with patch("gv_gateway.router.load_users", return_value=[jared]), \
         patch("gv_gateway.notify.send"):
        route("maple: inbox: buy milk", config)
    assert "buy milk" in config.inbox_path.read_text()


def test_route_inbox_stamps_sender_broadcast_name(config, jared):
    with patch("gv_gateway.router.load_users", return_value=[jared]), \
         patch("gv_gateway.notify.send"), \
         patch("gv_gateway.router.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-04-12 11:00"
        route("maple: inbox: buy milk", config)
    assert "- 2026-04-12 11:00 — [Jared (SMS)] buy milk\n" in config.inbox_path.read_text()


def test_route_inbox_no_label_when_no_broadcast_name(config, tmp_path):
    key = tmp_path / "anon.key"
    key.write_text("maple")
    anon = User("anon", key, "anon@x.com", None, None, ["inbox"])
    with patch("gv_gateway.router.load_users", return_value=[anon]), \
         patch("gv_gateway.notify.send"), \
         patch("gv_gateway.router.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2026-04-12 11:00"
        route("maple: inbox: buy milk", config)
    assert "- 2026-04-12 11:00 — buy milk\n" in config.inbox_path.read_text()


# --- route: notifications ---

def test_route_inbox_fires_notification_with_label(config, jared):
    with patch("gv_gateway.router.load_users", return_value=[jared]), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("maple: inbox: buy milk", config)
    mock_notify.assert_called_once_with("Marlin", "buy milk (from Jared (SMS))")


def test_route_sos_notifies_with_family_label(config, family):
    with patch("gv_gateway.router.load_users", return_value=[family]), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("forest: sos: emergency", config)
    mock_notify.assert_called_once_with("Marlin", "emergency (from Family)")


# --- route: access control ---

def test_route_family_cannot_use_inbox(config, family):
    with patch("gv_gateway.router.load_users", return_value=[family]), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("forest: inbox: sneak in", config)
    assert "sneak in" not in config.inbox_path.read_text()
    mock_notify.assert_not_called()


def test_route_invalid_key_drops_silently(config, jared):
    with patch("gv_gateway.router.load_users", return_value=[jared]), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("wrong: inbox: buy milk", config)
    assert "buy milk" not in config.inbox_path.read_text()
    mock_notify.assert_not_called()


def test_route_malformed_message_drops_silently(config, jared):
    with patch("gv_gateway.router.load_users", return_value=[jared]), \
         patch("gv_gateway.notify.send") as mock_notify:
        route("this is not valid", config)
    mock_notify.assert_not_called()
