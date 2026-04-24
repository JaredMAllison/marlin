import pytest
import yaml
from pathlib import Path
from vault import read_frontmatter, update_frontmatter


def test_read_frontmatter_returns_dict(tmp_path):
    f = tmp_path / "task.md"
    f.write_text("---\ntitle: My Task\ntype: task\nstatus: queued\n---\nBody text")
    fm = read_frontmatter(f)
    assert fm["title"] == "My Task"
    assert fm["type"] == "task"
    assert fm["status"] == "queued"


def test_read_frontmatter_no_frontmatter(tmp_path):
    f = tmp_path / "plain.md"
    f.write_text("Just plain text, no frontmatter at all")
    assert read_frontmatter(f) == {}


def test_read_frontmatter_malformed_yaml(tmp_path):
    f = tmp_path / "bad.md"
    f.write_text("---\n: : : bad yaml\n---\nBody")
    assert read_frontmatter(f) == {}


def test_update_frontmatter_updates_key(tmp_path):
    f = tmp_path / "task.md"
    f.write_text("---\ntitle: Task\nstatus: queued\n---\nBody")
    result = update_frontmatter(f, {"status": "done"})
    assert result is True
    fm = read_frontmatter(f)
    assert fm["status"] == "done"
    assert fm["title"] == "Task"


def test_update_frontmatter_preserves_body(tmp_path):
    f = tmp_path / "task.md"
    f.write_text("---\ntitle: Task\n---\nThis is the body.\n\nSecond paragraph.")
    update_frontmatter(f, {"status": "done"})
    text = f.read_text()
    assert "This is the body." in text
    assert "Second paragraph." in text


def test_update_frontmatter_no_frontmatter_returns_false(tmp_path):
    f = tmp_path / "plain.md"
    f.write_text("No frontmatter here")
    assert update_frontmatter(f, {"status": "done"}) is False
