# tests/test_project_dashboard.py
import yaml
import pytest
from pathlib import Path


def _write_project(path: Path, slug: str, **fields):
    fm = {
        "type": "project",
        "title": slug.replace("-", " ").title(),
        "status": "active",
        "priority": 2,
        "dashboard": True,
        **fields,
    }
    content = "---\n" + yaml.dump(fm, default_flow_style=False) + "---\n"
    (path / f"{slug}.md").write_text(content)
    return fm["title"]


def _write_task(path: Path, slug: str, **fields):
    fm = {"type": "task", "title": slug.replace("-", " ").title(), "status": "queued", **fields}
    content = "---\n" + yaml.dump(fm, default_flow_style=False) + "---\n"
    (path / f"{slug}.md").write_text(content)


def _write_roadmap(path: Path, slug: str, content: str, title: str):
    full = f"---\ntitle: {title}\ntype: project-roadmap\n---\n\n{content}"
    (path / f"{slug}-roadmap.md").write_text(full)


def test_project_summary_completion(tmp_path):
    from project_dashboard import build_project_summary
    projects_path = tmp_path / "Projects"
    tasks_path = tmp_path / "Tasks"
    projects_path.mkdir()
    tasks_path.mkdir()

    title = _write_project(projects_path, "marlin", priority=2)
    _write_task(tasks_path, "task-a", project=f"[[{title}]]", status="done")
    _write_task(tasks_path, "task-b", project=f"[[{title}]]", status="queued")

    summary = build_project_summary(
        projects_path / "marlin.md", tasks_path, projects_path
    )
    assert summary["slug"] == "marlin"
    assert summary["tasks_done"] == 1
    assert summary["tasks_total"] == 2
    assert summary["completion_pct"] == 50


def test_project_summary_current_phase(tmp_path):
    from project_dashboard import build_project_summary
    projects_path = tmp_path / "Projects"
    tasks_path = tmp_path / "Tasks"
    projects_path.mkdir()
    tasks_path.mkdir()

    _write_roadmap(
        projects_path, "marlin",
        "## Phase 1\n\n- [x] Done thing\n\n## Phase 2\n\n- [ ] Open thing\n",
        "Marlin — Roadmap",
    )
    _write_project(projects_path, "marlin", priority=2, roadmap="[[Marlin — Roadmap]]")

    summary = build_project_summary(
        projects_path / "marlin.md", tasks_path, projects_path
    )
    assert summary["phase_current"] == "Phase 2"
    assert summary["phase_index"] == 2
    assert summary["phase_total"] == 2


def test_project_detail_includes_roadmap_and_tasks(tmp_path):
    from project_dashboard import build_project_detail
    projects_path = tmp_path / "Projects"
    tasks_path = tmp_path / "Tasks"
    projects_path.mkdir()
    tasks_path.mkdir()

    _write_roadmap(
        projects_path, "marlin",
        "## Phase 1\n\n- [x] Done\n\n## Phase 2\n\n- [ ] Open\n",
        "Marlin — Roadmap",
    )
    title = _write_project(projects_path, "marlin", roadmap="[[Marlin — Roadmap]]")
    _write_task(tasks_path, "my-task", project=f"[[{title}]]", status="queued")

    detail = build_project_detail(
        projects_path / "marlin.md", tasks_path, projects_path
    )
    assert len(detail["roadmap"]) == 2
    assert detail["roadmap"][0]["complete"] is True
    assert len(detail["tasks"]) == 1
    assert detail["tasks"][0]["title"] == "My Task"
    assert detail["phase_current"] == "Phase 2"
    assert detail["phase_index"] == 2
    assert detail["phase_total"] == 2
    assert detail["task_current"] == "My Task"


def test_get_projects_summary_filters_priority(tmp_path):
    from project_dashboard import get_projects_summary
    projects_path = tmp_path / "Projects"
    tasks_path = tmp_path / "Tasks"
    projects_path.mkdir()
    tasks_path.mkdir()

    _write_project(projects_path, "p1-project", priority=1)
    _write_project(projects_path, "p2-project", priority=2)
    _write_project(projects_path, "p3-project", priority=3)

    results = get_projects_summary(projects_path, tasks_path, priority_all=False)
    assert len(results) == 2
    assert all(r["priority"] in (1, 2) for r in results)


def test_get_projects_summary_priority_all(tmp_path):
    from project_dashboard import get_projects_summary
    projects_path = tmp_path / "Projects"
    tasks_path = tmp_path / "Tasks"
    projects_path.mkdir()
    tasks_path.mkdir()

    _write_project(projects_path, "p1-project", priority=1)
    _write_project(projects_path, "p3-project", priority=3)

    results = get_projects_summary(projects_path, tasks_path, priority_all=True)
    assert len(results) == 2


def test_get_project_detail_missing_slug_returns_none(tmp_path):
    from project_dashboard import get_project_detail
    result = get_project_detail("nonexistent", tmp_path, tmp_path)
    assert result is None


def test_get_project_detail_wrong_type_returns_none(tmp_path):
    from project_dashboard import get_project_detail
    (tmp_path / "notes.md").write_text("---\ntype: note\ntitle: Notes\n---\n")
    result = get_project_detail("notes", tmp_path, tmp_path)
    assert result is None


def test_get_projects_summary_hides_complete_by_default(tmp_path):
    from project_dashboard import get_projects_summary
    projects_path = tmp_path / "Projects"
    tasks_path = tmp_path / "Tasks"
    projects_path.mkdir()
    tasks_path.mkdir()

    _write_project(projects_path, "active-project", status="active", priority=1)
    _write_project(projects_path, "done-project", status="complete", priority=1)

    results = get_projects_summary(projects_path, tasks_path)
    titles = {r["title"] for r in results}
    assert "Active Project" in titles
    assert "Done Project" not in titles


def test_get_projects_summary_show_done_includes_complete(tmp_path):
    from project_dashboard import get_projects_summary
    projects_path = tmp_path / "Projects"
    tasks_path = tmp_path / "Tasks"
    projects_path.mkdir()
    tasks_path.mkdir()

    _write_project(projects_path, "active-project", status="active", priority=1)
    _write_project(projects_path, "done-project", status="complete", priority=1)

    results = get_projects_summary(projects_path, tasks_path, hide_done=False)
    titles = {r["title"] for r in results}
    assert "Active Project" in titles
    assert "Done Project" in titles
