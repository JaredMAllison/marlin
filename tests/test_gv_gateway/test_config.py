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
