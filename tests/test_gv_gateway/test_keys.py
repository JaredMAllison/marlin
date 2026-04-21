import pytest
from pathlib import Path
from unittest.mock import patch
from datetime import date
from gv_gateway.keys import generate_key, read_key, email_key, _build_directory, ROUTE_DESCRIPTIONS
from gv_gateway.users import User
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


@pytest.fixture
def jared_user(tmp_path):
    return User(
        user_id="jared",
        key_file=tmp_path / "jared.key",
        email="jared@gmail.com",
        broadcast_name="Jared (SMS)",
        ntfy_topic="jared-topic",
        routes=["inbox", "sos", "ntfy"],
    )


@pytest.fixture
def family_user(tmp_path):
    return User(
        user_id="family",
        key_file=tmp_path / "family.key",
        email=None,
        broadcast_name="Family",
        ntfy_topic=None,
        routes=["sos"],
    )


# --- generate_key ---

def test_generate_key_only_selects_valid_words(dict_file, key_file):
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


# --- read_key ---

def test_read_key_returns_stored_word(tmp_path):
    key_file = tmp_path / "gv_gateway.key"
    key_file.write_text("maple")
    assert read_key(key_file) == "maple"


def test_read_key_strips_whitespace(tmp_path):
    key_file = tmp_path / "gv_gateway.key"
    key_file.write_text("maple\n")
    assert read_key(key_file) == "maple"


# --- _build_directory ---

def test_build_directory_includes_all_routes():
    result = _build_directory("maple", ["inbox", "sos"])
    assert "maple: inbox: your message" in result
    assert "maple: sos: your message" in result


def test_build_directory_excludes_ungranted_routes():
    result = _build_directory("maple", ["sos"])
    assert "inbox" not in result


def test_build_directory_includes_descriptions():
    result = _build_directory("maple", ["inbox"])
    assert ROUTE_DESCRIPTIONS["inbox"] in result


def test_build_directory_unknown_route_has_fallback():
    result = _build_directory("maple", ["teleport"])
    assert "teleport" in result
    assert "not configured" in result


# --- email_key ---

def test_email_key_sends_to_user_email(config, jared_user):
    today = date.today().strftime("%Y-%m-%d")
    with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
        mock_smtp = mock_smtp_cls.return_value.__enter__.return_value
        email_key("maple", jared_user, config)
        sent_msg = mock_smtp.send_message.call_args[0][0]
        assert sent_msg["To"] == "jared@gmail.com"
        assert f"Marlin Key — {today}" == sent_msg["Subject"]


def test_email_key_body_contains_key(config, jared_user):
    with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
        mock_smtp = mock_smtp_cls.return_value.__enter__.return_value
        email_key("maple", jared_user, config)
        sent_msg = mock_smtp.send_message.call_args[0][0]
        assert "maple" in sent_msg.get_payload()


def test_email_key_body_contains_granted_routes(config, jared_user):
    with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
        mock_smtp = mock_smtp_cls.return_value.__enter__.return_value
        email_key("maple", jared_user, config)
        body = mock_smtp.send_message.call_args[0][0].get_payload()
        assert "inbox" in body
        assert "sos" in body
        assert "ntfy" in body


def test_email_key_body_excludes_ungranted_routes(config, family_user):
    family_user.email = "family@gmail.com"
    with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
        mock_smtp = mock_smtp_cls.return_value.__enter__.return_value
        email_key("forest", family_user, config)
        body = mock_smtp.send_message.call_args[0][0].get_payload()
        assert "inbox" not in body
        assert "sos" in body


def test_email_key_authenticates_with_config_credentials(config, jared_user):
    with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
        mock_smtp = mock_smtp_cls.return_value.__enter__.return_value
        email_key("maple", jared_user, config)
        mock_smtp.login.assert_called_once_with("marlin@gmail.com", "secret")
