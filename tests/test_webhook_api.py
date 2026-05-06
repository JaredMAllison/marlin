import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import webhook


def test_api_state_returns_json():
    state = {"mode": "available", "last_surfaced_task": "test task", "last_surfaced_at": "2026-05-03T12:00:00"}
    with patch.object(webhook, "load_state", return_value=state):
        result = webhook.load_state()
    assert result["mode"] == "available"
    assert "last_surfaced_task" in result


def test_api_adls_returns_list():
    adls = [{"title": "Brush Teeth", "start_time": "08:00"}]
    with patch.object(webhook, "get_due_adls", return_value=adls):
        result = webhook.get_due_adls()
    assert isinstance(result, list)
    assert result[0]["title"] == "Brush Teeth"


def test_env_var_port_override(monkeypatch):
    monkeypatch.setenv("MARLIN_WEBHOOK_PORT", "7999")
    import importlib
    importlib.reload(webhook)
    assert webhook.PORT == 7999
    # restore
    monkeypatch.delenv("MARLIN_WEBHOOK_PORT")
    importlib.reload(webhook)
