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
