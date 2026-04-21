import json
import pytest
from pathlib import Path
from unittest.mock import patch, call
from gv_gateway.keygen import run
from gv_gateway.users import User
from gv_gateway.config import Config


@pytest.fixture
def config(tmp_path):
    return Config(
        gmail_address="marlin@gmail.com",
        gmail_app_password="secret",
        personal_email="jared@gmail.com",
        inbox_path=tmp_path / "Inbox.md",
    )


@pytest.fixture
def jared(tmp_path):
    return User(
        user_id="jared",
        key_file=tmp_path / "jared.key",
        email="jared@gmail.com",
        broadcast_name="Jared (SMS)",
        ntfy_topic="jared-topic",
        routes=["inbox", "sos", "ntfy"],
    )


@pytest.fixture
def family(tmp_path):
    return User(
        user_id="family",
        key_file=tmp_path / "family.key",
        email=None,
        broadcast_name="Family",
        ntfy_topic=None,
        routes=["sos"],
    )


def test_keygen_generates_key_for_each_user(config, jared, family):
    with patch("gv_gateway.keygen.load_config", return_value=config), \
         patch("gv_gateway.keygen.load_users", return_value=[jared, family]), \
         patch("gv_gateway.keygen.email_key"), \
         patch("gv_gateway.keygen.generate_key", return_value="maple") as mock_gen:
        run()
    assert mock_gen.call_count == 2
    called_paths = {c.kwargs["key_path"] for c in mock_gen.call_args_list}
    assert jared.key_file in called_paths
    assert family.key_file in called_paths


def test_keygen_emails_users_with_email(config, jared, family):
    with patch("gv_gateway.keygen.load_config", return_value=config), \
         patch("gv_gateway.keygen.load_users", return_value=[jared, family]), \
         patch("gv_gateway.keygen.generate_key", return_value="maple"), \
         patch("gv_gateway.keygen.email_key") as mock_email:
        run()
    assert mock_email.call_count == 1
    args = mock_email.call_args
    assert args[0][1] is jared


def test_keygen_skips_email_for_users_without_email(config, jared, family):
    with patch("gv_gateway.keygen.load_config", return_value=config), \
         patch("gv_gateway.keygen.load_users", return_value=[jared, family]), \
         patch("gv_gateway.keygen.generate_key", return_value="maple"), \
         patch("gv_gateway.keygen.email_key") as mock_email:
        run()
    emailed_users = [c[0][1].user_id for c in mock_email.call_args_list]
    assert "family" not in emailed_users


def test_keygen_passes_word_and_config_to_email(config, jared):
    with patch("gv_gateway.keygen.load_config", return_value=config), \
         patch("gv_gateway.keygen.load_users", return_value=[jared]), \
         patch("gv_gateway.keygen.generate_key", return_value="cedar"), \
         patch("gv_gateway.keygen.email_key") as mock_email:
        run()
    word, user, cfg = mock_email.call_args[0]
    assert word == "cedar"
    assert user is jared
    assert cfg is config
