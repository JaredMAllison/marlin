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


from vault import find_tasks, find_projects


def _make_task(tmp_path, name, **fields):
    """Helper: write a task file with given frontmatter fields."""
    fm = {"type": "task", "title": name, "status": "queued", **fields}
    content = "---\n" + yaml.dump(fm, default_flow_style=False) + "---\n"
    (tmp_path / f"{name.lower().replace(' ', '-')}.md").write_text(content)


def _make_project(tmp_path, name, **fields):
    fm = {"type": "project", "title": name, "status": "active", **fields}
    content = "---\n" + yaml.dump(fm, default_flow_style=False) + "---\n"
    (tmp_path / f"{name.lower().replace(' ', '-')}.md").write_text(content)


def test_find_tasks_returns_all_tasks(tmp_path):
    _make_task(tmp_path, "Alpha")
    _make_task(tmp_path, "Beta")
    tasks = find_tasks(tmp_path)
    assert len(tasks) == 2
    titles = {t["title"] for t in tasks}
    assert titles == {"Alpha", "Beta"}


def test_find_tasks_filters_by_status(tmp_path):
    _make_task(tmp_path, "Done Task", status="done")
    _make_task(tmp_path, "Queued Task", status="queued")
    tasks = find_tasks(tmp_path, {"status": "done"})
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Done Task"


def test_find_tasks_filters_by_project_strips_wiki_links(tmp_path):
    _make_task(tmp_path, "Marlin Task", project="[[Marlin]]")
    _make_task(tmp_path, "Other Task", project="[[Other]]")
    tasks = find_tasks(tmp_path, {"project": "Marlin"})
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Marlin Task"


def test_find_tasks_excludes_dashboard_false(tmp_path):
    _make_task(tmp_path, "Visible Task")
    _make_task(tmp_path, "Hidden Task", dashboard=False)
    tasks = find_tasks(tmp_path, {"exclude_dashboard_false": True})
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Visible Task"


def test_find_projects_filters_by_dashboard(tmp_path):
    _make_project(tmp_path, "Shown", dashboard=True, priority=1)
    _make_project(tmp_path, "Hidden", priority=2)
    projects = find_projects(tmp_path, {"dashboard": True})
    assert len(projects) == 1
    assert projects[0]["title"] == "Shown"


def test_find_projects_filters_by_priority(tmp_path):
    _make_project(tmp_path, "P1 Project", priority=1, dashboard=True)
    _make_project(tmp_path, "P2 Project", priority=2, dashboard=True)
    _make_project(tmp_path, "P3 Project", priority=3, dashboard=True)
    projects = find_projects(tmp_path, {"priority": [1, 2]})
    assert len(projects) == 2
    assert all(p["priority"] in (1, 2) for p in projects)


def test_find_projects_skips_companion_files(tmp_path):
    _make_project(tmp_path, "Real Project", priority=1)
    # Companion files with -roadmap, -changelog, -brief stems — even if they have type: project — must be skipped
    fm = {"type": "project", "title": "Should Not Appear", "status": "active", "priority": 1}
    content = "---\n" + yaml.dump(fm, default_flow_style=False) + "---\n"
    (tmp_path / "real-project-roadmap.md").write_text(content)
    (tmp_path / "real-project-changelog.md").write_text(content)
    projects = find_projects(tmp_path)
    assert len(projects) == 1
    assert projects[0]["title"] == "Real Project"
