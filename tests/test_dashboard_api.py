# tests/test_dashboard_api.py
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import project_dashboard as pd


def test_vault_tree_returns_list(tmp_path):
    (tmp_path / "Tasks").mkdir()
    (tmp_path / "Tasks" / "my-task.md").write_text("---\ntitle: My Task\n---")
    (tmp_path / "Projects").mkdir()
    tree = pd.build_vault_tree(tmp_path)
    assert isinstance(tree, list)
    assert any(item["folder"] == "Tasks" for item in tree)


def test_vault_file_rejects_traversal(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="Invalid path"):
        pd.read_vault_file(tmp_path, "../etc/passwd")


def test_vault_file_reads_content(tmp_path):
    (tmp_path / "Tasks").mkdir()
    f = tmp_path / "Tasks" / "test.md"
    f.write_text("hello vault")
    content = pd.read_vault_file(tmp_path, "Tasks/test.md")
    assert content == "hello vault"


def test_env_var_port_override(monkeypatch):
    monkeypatch.setenv("MARLIN_DASHBOARD_PORT", "7999")
    import importlib
    importlib.reload(pd)
    assert pd.PORT == 7999
    monkeypatch.delenv("MARLIN_DASHBOARD_PORT")
    importlib.reload(pd)
