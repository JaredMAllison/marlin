import pytest
import yaml
from datetime import date
from pathlib import Path
from vault import read_frontmatter, update_frontmatter, find_tasks, find_projects, resolve_roadmap_path, parse_roadmap, compute_completion, current_phase, top_task


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
    (tmp_path / "real-project-open-questions.md").write_text(content)
    projects = find_projects(tmp_path)
    assert len(projects) == 1
    assert projects[0]["title"] == "Real Project"


def test_parse_roadmap_phases_and_items(tmp_path):
    f = tmp_path / "marlin-roadmap.md"
    f.write_text(
        "## Phase 1 — Done\n\n- [x] Item A\n- [x] Item B\n\n"
        "## Phase 2 — Open\n\n- [x] Item C\n- [ ] Item D\n"
    )
    phases = parse_roadmap(f)
    assert len(phases) == 2
    assert phases[0]["name"] == "Phase 1 — Done"
    assert phases[0]["complete"] is True
    assert phases[0]["items"] == [
        {"text": "Item A", "done": True},
        {"text": "Item B", "done": True},
    ]
    assert phases[1]["name"] == "Phase 2 — Open"
    assert phases[1]["complete"] is False
    assert phases[1]["items"][1] == {"text": "Item D", "done": False}


def test_parse_roadmap_empty_phase_not_complete(tmp_path):
    f = tmp_path / "roadmap.md"
    f.write_text("## Phase 1 — No Items\n\n## Phase 2\n\n- [ ] Something\n")
    phases = parse_roadmap(f)
    assert phases[0]["complete"] is False  # no items → not complete
    assert phases[1]["complete"] is False


def test_parse_roadmap_ignores_non_phase_lines(tmp_path):
    f = tmp_path / "roadmap.md"
    f.write_text(
        "---\ntitle: Roadmap\n---\n\nSome intro text.\n\n"
        "## Phase 1\n\n- [x] Done thing\n\nSome notes here.\n"
    )
    phases = parse_roadmap(f)
    assert len(phases) == 1
    assert phases[0]["items"] == [{"text": "Done thing", "done": True}]


def test_resolve_roadmap_path_by_stem(tmp_path):
    roadmap = tmp_path / "marlin-roadmap.md"
    roadmap.write_text("---\ntitle: Marlin — Roadmap\ntype: project-roadmap\n---\n")
    result = resolve_roadmap_path(tmp_path, "[[Marlin — Roadmap]]")
    assert result == roadmap


def test_resolve_roadmap_path_by_frontmatter_title(tmp_path):
    roadmap = tmp_path / "custom-name.md"
    roadmap.write_text("---\ntitle: Marlin — Roadmap\ntype: project-roadmap\n---\n")
    result = resolve_roadmap_path(tmp_path, "[[Marlin — Roadmap]]")
    assert result == roadmap


def test_resolve_roadmap_path_not_found(tmp_path):
    result = resolve_roadmap_path(tmp_path, "[[Nonexistent Roadmap]]")
    assert result is None


def test_parse_roadmap_no_phases_returns_empty(tmp_path):
    f = tmp_path / "roadmap.md"
    f.write_text("---\ntitle: Roadmap\n---\nJust some prose, no phase headings.\n")
    assert parse_roadmap(f) == []


def test_compute_completion_mixed(tmp_path):
    tasks = [
        {"status": "done", "title": "A"},
        {"status": "done", "title": "B"},
        {"status": "queued", "title": "C"},
    ]
    result = compute_completion(tasks)
    assert result == {"done": 2, "total": 3, "pct": 67}


def test_compute_completion_excludes_dashboard_false():
    tasks = [
        {"status": "done", "title": "A"},
        {"status": "queued", "title": "B", "dashboard": False},
    ]
    result = compute_completion(tasks)
    assert result == {"done": 1, "total": 1, "pct": 100}


def test_compute_completion_empty():
    assert compute_completion([]) == {"done": 0, "total": 0, "pct": 0}


def test_compute_completion_all_done():
    tasks = [{"status": "done"}, {"status": "done"}]
    assert compute_completion(tasks)["pct"] == 100


def test_current_phase_returns_first_incomplete():
    phases = [
        {"name": "Phase 1", "complete": True, "items": [{"text": "A", "done": True}]},
        {"name": "Phase 2", "complete": False, "items": [{"text": "B", "done": False}]},
        {"name": "Phase 3", "complete": False, "items": [{"text": "C", "done": False}]},
    ]
    result = current_phase(phases)
    assert result["name"] == "Phase 2"


def test_current_phase_all_complete_returns_none():
    phases = [
        {"name": "Phase 1", "complete": True, "items": [{"text": "A", "done": True}]},
    ]
    assert current_phase(phases) is None


def test_current_phase_empty_returns_none():
    assert current_phase([]) is None


def test_top_task_returns_soonest_goal_date():
    tasks = [
        {"status": "queued", "title": "Later", "goal_date": "2026-05-01", "duration": "short"},
        {"status": "queued", "title": "Sooner", "goal_date": "2026-04-25", "duration": "short"},
    ]
    result = top_task(tasks)
    assert result["title"] == "Sooner"


def test_top_task_no_goal_date_sorts_last():
    tasks = [
        {"status": "queued", "title": "No Date", "goal_date": None, "duration": "short"},
        {"status": "queued", "title": "Has Date", "goal_date": "2026-05-01", "duration": "short"},
    ]
    assert top_task(tasks)["title"] == "Has Date"


def test_top_task_skips_non_queued():
    tasks = [
        {"status": "done", "title": "Done"},
        {"status": "queued", "title": "Active", "goal_date": None, "duration": "short"},
    ]
    assert top_task(tasks)["title"] == "Active"


def test_top_task_empty_returns_none():
    assert top_task([]) is None


def test_top_task_with_date_objects():
    tasks = [
        {"status": "queued", "title": "Later", "goal_date": date(2026, 5, 1), "duration": "short"},
        {"status": "queued", "title": "Sooner", "goal_date": date(2026, 4, 25), "duration": "short"},
    ]
    assert top_task(tasks)["title"] == "Sooner"


def test_top_task_duration_tiebreak():
    tasks = [
        {"status": "queued", "title": "Long", "goal_date": "2026-05-01", "duration": "long"},
        {"status": "queued", "title": "Short", "goal_date": "2026-05-01", "duration": "short"},
    ]
    assert top_task(tasks)["title"] == "Short"


def test_current_phase_skips_empty_items_phase():
    phases = [
        {"name": "Placeholder", "complete": False, "items": []},
        {"name": "Active", "complete": False, "items": [{"text": "X", "done": False}]},
    ]
    assert current_phase(phases)["name"] == "Active"
