# Project Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone project visualization server (port 7833) that renders P1/P2 Marlin projects with completion percentages, current roadmap phase, and current task — read-only, one glance, cognitive prosthetic.

**Architecture:** Extract shared vault functions into `vault.py`; new `project_dashboard.py` HTTP server imports from it; webhook.py mechanically updated to import the same functions (no behavior change). Frontend HTML is a placeholder — the real UI comes from Claude Design and will replace it.

**Tech Stack:** Python 3.12, PyYAML, stdlib http.server, pytest — no new dependencies.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `vault.py` | Pure data functions: frontmatter read/write, task/project filtering, roadmap parsing, completion math |
| Modify | `webhook.py:45-81` | Import read_frontmatter, update_frontmatter from vault.py; remove local copies |
| Create | `tests/test_vault.py` | Tests for all vault.py functions |
| Create | `project_dashboard.py` | HTTP server on port 7833; assembles project data; serves JSON API + placeholder HTML |
| Create | `tests/test_project_dashboard.py` | Tests for data assembly functions |
| Create | `systemd/marlin-project-dashboard.service` | Systemd user service unit |
| Modify | `Projects/*.md` | Add `dashboard: true` to P1/P2 projects that should appear in the dashboard |
| Modify | `System/Vault/schemas.md` | Add `dashboard` field to project schema |

---

## Task 1: Create vault.py — frontmatter read/write

**Files:**
- Create: `vault.py`
- Create: `tests/test_vault.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_vault.py
import pytest
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd ~/marlin && pytest tests/test_vault.py -v
```

Expected: `ModuleNotFoundError: No module named 'vault'`

- [ ] **Step 3: Create vault.py with frontmatter functions**

```python
# vault.py
from datetime import date
from pathlib import Path

import yaml

DURATION_MINUTES = {"short": 15, "medium": 45, "long": 120}


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def update_frontmatter(path: Path, updates: dict) -> bool:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return False
    fm.update(updates)
    new_fm = yaml.dump(fm, default_flow_style=False, allow_unicode=True).strip()
    path.write_text(f"---\n{new_fm}\n---{parts[2]}", encoding="utf-8")
    return True
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd ~/marlin && pytest tests/test_vault.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/marlin && git add vault.py tests/test_vault.py
git commit -m "feat: add vault.py shared module with frontmatter read/write"
```

---

## Task 2: Add find_tasks and find_projects to vault.py

**Files:**
- Modify: `vault.py`
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_vault.py`:

```python
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
    import yaml
    _make_task(tmp_path, "Alpha")
    _make_task(tmp_path, "Beta")
    tasks = find_tasks(tmp_path)
    assert len(tasks) == 2
    titles = {t["title"] for t in tasks}
    assert titles == {"Alpha", "Beta"}


def test_find_tasks_filters_by_status(tmp_path):
    import yaml
    _make_task(tmp_path, "Done Task", status="done")
    _make_task(tmp_path, "Queued Task", status="queued")
    tasks = find_tasks(tmp_path, {"status": "done"})
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Done Task"


def test_find_tasks_filters_by_project_strips_wiki_links(tmp_path):
    import yaml
    _make_task(tmp_path, "Marlin Task", project="[[Marlin]]")
    _make_task(tmp_path, "Other Task", project="[[Other]]")
    tasks = find_tasks(tmp_path, {"project": "Marlin"})
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Marlin Task"


def test_find_tasks_excludes_dashboard_false(tmp_path):
    import yaml
    _make_task(tmp_path, "Visible Task")
    _make_task(tmp_path, "Hidden Task", dashboard=False)
    tasks = find_tasks(tmp_path, {"exclude_dashboard_false": True})
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Visible Task"


def test_find_projects_filters_by_dashboard(tmp_path):
    import yaml
    _make_project(tmp_path, "Shown", dashboard=True, priority=1)
    _make_project(tmp_path, "Hidden", priority=2)
    # Also create a roadmap file that should be skipped
    (tmp_path / "shown-roadmap.md").write_text("---\ntitle: roadmap\n---\n")
    projects = find_projects(tmp_path, {"dashboard": True})
    assert len(projects) == 1
    assert projects[0]["title"] == "Shown"


def test_find_projects_filters_by_priority(tmp_path):
    import yaml
    _make_project(tmp_path, "P1 Project", priority=1, dashboard=True)
    _make_project(tmp_path, "P2 Project", priority=2, dashboard=True)
    _make_project(tmp_path, "P3 Project", priority=3, dashboard=True)
    projects = find_projects(tmp_path, {"priority": [1, 2]})
    assert len(projects) == 2
    assert all(p["priority"] in (1, 2) for p in projects)
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd ~/marlin && pytest tests/test_vault.py -v -k "find"
```

Expected: `ImportError: cannot import name 'find_tasks'`

- [ ] **Step 3: Add find_tasks and find_projects to vault.py**

Append to `vault.py`:

```python
def find_tasks(vault_path: Path, filters: dict | None = None) -> list[dict]:
    """
    filters keys (all optional):
      status: str — exact match on status field
      project: str — matches after stripping [[...]] from task's project field
      exclude_dashboard_false: bool — if True, skip tasks where dashboard == False
    Each result dict has '_slug' set to the file stem.
    """
    filters = filters or {}
    results = []
    for path in sorted(vault_path.glob("*.md")):
        fm = read_frontmatter(path)
        if fm.get("type") != "task":
            continue
        if "status" in filters and fm.get("status") != filters["status"]:
            continue
        if "project" in filters:
            proj = str(fm.get("project", "") or "").strip()
            if proj.startswith("[[") and proj.endswith("]]"):
                proj = proj[2:-2]
            if proj != filters["project"]:
                continue
        if filters.get("exclude_dashboard_false") and fm.get("dashboard") is False:
            continue
        fm["_slug"] = path.stem
        results.append(fm)
    return results


def find_projects(projects_path: Path, filters: dict | None = None) -> list[dict]:
    """
    filters keys (all optional):
      dashboard: bool — if True, only return projects where dashboard == True
      priority: int | list[int] — match priority field
      status: str — exact match on status field
    Skips roadmap and changelog files automatically.
    Each result dict has '_slug' and '_path' set.
    """
    filters = filters or {}
    results = []
    for path in sorted(projects_path.glob("*.md")):
        stem = path.stem
        if stem.endswith("-roadmap") or stem.endswith("-changelog") or stem.endswith("-brief"):
            continue
        fm = read_frontmatter(path)
        if fm.get("type") != "project":
            continue
        if filters.get("dashboard") is True and not fm.get("dashboard"):
            continue
        if "priority" in filters:
            allowed = filters["priority"]
            if isinstance(allowed, list):
                if fm.get("priority") not in allowed:
                    continue
            else:
                if fm.get("priority") != allowed:
                    continue
        if "status" in filters and fm.get("status") != filters["status"]:
            continue
        fm["_slug"] = stem
        fm["_path"] = path
        results.append(fm)
    return results
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd ~/marlin && pytest tests/test_vault.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/marlin && git add vault.py tests/test_vault.py
git commit -m "feat: add find_tasks and find_projects to vault.py"
```

---

## Task 3: Add roadmap functions to vault.py

**Files:**
- Modify: `vault.py`
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_vault.py`:

```python
from vault import resolve_roadmap_path, parse_roadmap
import yaml


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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd ~/marlin && pytest tests/test_vault.py -v -k "roadmap or resolve"
```

Expected: `ImportError: cannot import name 'resolve_roadmap_path'`

- [ ] **Step 3: Add roadmap functions to vault.py**

Append to `vault.py`:

```python
def resolve_roadmap_path(projects_path: Path, roadmap_link: str) -> Path | None:
    """
    roadmap_link is "[[Title]]" format.
    Strategy 1: slugify the title and look for <slug>.md in projects_path.
    Strategy 2: scan *-roadmap.md files for matching frontmatter title.
    """
    title = roadmap_link.strip()
    if title.startswith("[[") and title.endswith("]]"):
        title = title[2:-2]

    slug = (
        title.lower()
        .replace(" — ", "-")   # em dash with spaces
        .replace("—", "-")      # em dash without spaces
        .replace(" ", "-")
    )
    candidate = projects_path / f"{slug}.md"
    if candidate.exists():
        return candidate

    for path in projects_path.glob("*-roadmap.md"):
        fm = read_frontmatter(path)
        if fm.get("title") == title:
            return path

    return None


def parse_roadmap(path: Path) -> list[dict]:
    """
    Returns list of Phase dicts:
      { name: str, complete: bool, items: list[{text: str, done: bool}] }
    Parses ## headings as phase names, - [x] / - [ ] as items.
    A phase is complete only if it has at least one item and all are done.
    """
    text = path.read_text(encoding="utf-8")
    phases: list[dict] = []
    current: dict | None = None

    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                phases.append(current)
            current = {"name": line[3:].strip(), "items": []}
        elif line.startswith("- [x] ") or line.startswith("- [X] "):
            if current is not None:
                current["items"].append({"text": line[6:].strip(), "done": True})
        elif line.startswith("- [ ] "):
            if current is not None:
                current["items"].append({"text": line[6:].strip(), "done": False})

    if current is not None:
        phases.append(current)

    for phase in phases:
        items = phase["items"]
        phase["complete"] = bool(items) and all(i["done"] for i in items)

    return phases
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd ~/marlin && pytest tests/test_vault.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/marlin && git add vault.py tests/test_vault.py
git commit -m "feat: add roadmap parsing to vault.py"
```

---

## Task 4: Add completion and phase helpers to vault.py

**Files:**
- Modify: `vault.py`
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_vault.py`:

```python
from vault import compute_completion, current_phase, top_task
from datetime import date


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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd ~/marlin && pytest tests/test_vault.py -v -k "completion or phase or top_task"
```

Expected: `ImportError: cannot import name 'compute_completion'`

- [ ] **Step 3: Add helpers to vault.py**

Append to `vault.py`:

```python
def compute_completion(tasks: list[dict]) -> dict:
    """
    Returns {done, total, pct}.
    Excludes tasks where dashboard == False from the count.
    """
    visible = [t for t in tasks if t.get("dashboard") is not False]
    total = len(visible)
    done = sum(1 for t in visible if t.get("status") == "done")
    pct = round(done / total * 100) if total else 0
    return {"done": done, "total": total, "pct": pct}


def current_phase(phases: list[dict]) -> dict | None:
    """Returns the first phase that has any open (done=False) item."""
    for phase in phases:
        if any(not i["done"] for i in phase["items"]):
            return phase
    return None


def top_task(tasks: list[dict]) -> dict | None:
    """
    Returns the highest-priority queued task.
    Sort: goal_date ASC (missing goal_date sorts last), then duration ASC.
    """
    queued = [t for t in tasks if t.get("status") == "queued"]
    if not queued:
        return None

    def _sort_key(fm: dict):
        goal = fm.get("goal_date")
        if goal and not isinstance(goal, date):
            try:
                goal = date.fromisoformat(str(goal))
            except (ValueError, TypeError):
                goal = None
        duration = DURATION_MINUTES.get(fm.get("duration", "medium"), 45)
        return (goal or date(9999, 1, 1), duration)

    queued.sort(key=_sort_key)
    return queued[0]
```

- [ ] **Step 4: Run all vault tests**

```bash
cd ~/marlin && pytest tests/test_vault.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/marlin && git add vault.py tests/test_vault.py
git commit -m "feat: add completion, phase, and top_task helpers to vault.py"
```

---

## Task 5: Refactor webhook.py to import from vault.py

**Files:**
- Modify: `webhook.py`

This is a mechanical refactor — no behavior change. The three functions defined locally in webhook.py (`read_frontmatter`, `update_frontmatter`, `find_task`) are replaced with imports from vault.py. `find_task` is kept as a local wrapper because it searches by title and returns a Path — different interface from `find_tasks`.

- [ ] **Step 1: Replace local definitions with imports**

In `webhook.py`, find and replace the block at lines 45–81:

```python
def find_task(title: str) -> Path | None:
    for path in VAULT.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            continue
        if isinstance(fm, dict) and fm.get("title") == title:
            return path
    return None

def update_frontmatter(path: Path, updates: dict) -> bool:
    ...

def read_frontmatter(path: Path) -> dict:
    ...
```

Replace with:

```python
from vault import read_frontmatter, update_frontmatter


def find_task(title: str) -> Path | None:
    for path in VAULT.glob("*.md"):
        fm = read_frontmatter(path)
        if isinstance(fm, dict) and fm.get("title") == title:
            return path
    return None
```

- [ ] **Step 2: Remove yaml from imports if no longer needed directly**

Check that `import yaml` is still needed in webhook.py (it is — used in `get_today_tasks` and `get_surfaced_task`). Leave it.

- [ ] **Step 3: Start the server and verify it starts without error**

```bash
cd ~/marlin && python3 -c "import webhook; print('import OK')"
```

Expected: `import OK`

- [ ] **Step 4: Run the full test suite**

```bash
cd ~/marlin && pytest -v
```

Expected: All existing tests PASS. No new failures.

- [ ] **Step 5: Commit**

```bash
cd ~/marlin && git add webhook.py
git commit -m "refactor: webhook.py imports read/update_frontmatter from vault.py"
```

---

## Task 6: Create project_dashboard.py — data assembly

**Files:**
- Create: `project_dashboard.py`
- Create: `tests/test_project_dashboard.py`

- [ ] **Step 1: Write failing tests**

```python
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


def test_project_summary_completion(tmp_path, monkeypatch):
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd ~/marlin && pytest tests/test_project_dashboard.py -v
```

Expected: `ModuleNotFoundError: No module named 'project_dashboard'`

- [ ] **Step 3: Create project_dashboard.py with data functions**

```python
# project_dashboard.py
from datetime import date
from pathlib import Path

from vault import (
    read_frontmatter,
    find_tasks,
    find_projects,
    resolve_roadmap_path,
    parse_roadmap,
    compute_completion,
    current_phase,
    top_task,
)

VAULT = Path("/home/jared/Documents/Obsidian/Marlin")
TASKS_PATH = VAULT / "Tasks"
PROJECTS_PATH = VAULT / "Projects"
PORT = 7833


def build_project_summary(project_path: Path, tasks_path: Path, projects_path: Path) -> dict:
    fm = read_frontmatter(project_path)
    slug = project_path.stem
    title = fm.get("title", slug)

    tasks = find_tasks(tasks_path, {"project": title})
    completion = compute_completion(tasks)

    phases = []
    roadmap_link = fm.get("roadmap", "")
    if roadmap_link:
        roadmap_path = resolve_roadmap_path(projects_path, str(roadmap_link))
        if roadmap_path:
            phases = parse_roadmap(roadmap_path)

    cp = current_phase(phases)
    phase_index = next((i + 1 for i, p in enumerate(phases) if p is cp), None)
    tt = top_task(tasks)

    return {
        "slug": slug,
        "title": title,
        "priority": fm.get("priority"),
        "status": fm.get("status", ""),
        "brief": fm.get("brief", ""),
        "phase_current": cp["name"] if cp else None,
        "phase_index": phase_index,
        "phase_total": len(phases),
        "task_current": tt.get("title") if tt else None,
        "tasks_done": completion["done"],
        "tasks_total": completion["total"],
        "completion_pct": completion["pct"],
    }


def build_project_detail(project_path: Path, tasks_path: Path, projects_path: Path) -> dict:
    fm = read_frontmatter(project_path)
    slug = project_path.stem
    title = fm.get("title", slug)

    tasks = find_tasks(tasks_path, {"project": title})
    completion = compute_completion(tasks)

    phases = []
    roadmap_link = fm.get("roadmap", "")
    if roadmap_link:
        roadmap_path = resolve_roadmap_path(projects_path, str(roadmap_link))
        if roadmap_path:
            phases = parse_roadmap(roadmap_path)

    task_list = []
    for t in sorted(tasks, key=lambda x: (str(x.get("goal_date") or "9999"), x.get("title", ""))):
        task_list.append({
            "title": t.get("title", ""),
            "status": t.get("status", ""),
            "goal_date": str(t.get("goal_date") or ""),
            "duration": t.get("duration", ""),
            "dashboard": t.get("dashboard", True),
        })

    return {
        "slug": slug,
        "title": title,
        "priority": fm.get("priority"),
        "status": fm.get("status", ""),
        "brief": fm.get("brief", ""),
        "roadmap": phases,
        "tasks": task_list,
        "tasks_done": completion["done"],
        "tasks_total": completion["total"],
        "completion_pct": completion["pct"],
    }


def get_projects_summary(
    projects_path: Path, tasks_path: Path, priority_all: bool = False
) -> list[dict]:
    filters: dict = {"dashboard": True}
    if not priority_all:
        filters["priority"] = [1, 2]
    projects = find_projects(projects_path, filters)
    projects.sort(key=lambda fm: (fm.get("priority") or 99, fm.get("title", "")))
    return [build_project_summary(fm["_path"], tasks_path, projects_path) for fm in projects]


def get_project_detail(slug: str, projects_path: Path, tasks_path: Path) -> dict | None:
    path = projects_path / f"{slug}.md"
    if not path.exists():
        return None
    fm = read_frontmatter(path)
    if fm.get("type") != "project":
        return None
    return build_project_detail(path, tasks_path, projects_path)
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
cd ~/marlin && pytest tests/test_project_dashboard.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/marlin && git add project_dashboard.py tests/test_project_dashboard.py
git commit -m "feat: add project_dashboard.py data assembly functions"
```

---

## Task 7: Add HTTP server to project_dashboard.py

**Files:**
- Modify: `project_dashboard.py`

- [ ] **Step 1: Append HTTP server to project_dashboard.py**

```python
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


PLACEHOLDER_HTML = b"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marlin Projects</title></head>
<body style="font-family:sans-serif;color:#eee;background:#111;padding:2rem">
<h1>Marlin Projects</h1>
<p>Frontend coming soon — replace this file with the Claude Design output.</p>
</body>
</html>"""


class ProjectDashboardHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PLACEHOLDER_HTML)))
            self.end_headers()
            self.wfile.write(PLACEHOLDER_HTML)
            return

        if path == "/api/projects":
            priority_all = "priority=all" in (parsed.query or "")
            data = get_projects_summary(PROJECTS_PATH, TASKS_PATH, priority_all=priority_all)
            self._json(data)
            return

        if path.startswith("/api/projects/"):
            slug = path[len("/api/projects/"):]
            detail = get_project_detail(slug, PROJECTS_PATH, TASKS_PATH)
            if detail is None:
                self._text(404, "Not found")
                return
            self._json(detail)
            return

        self._text(404, "Not found")

    def _json(self, data):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, code: int, message: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(message.encode())

    def log_message(self, format, *args):
        pass


def main():
    server = HTTPServer(("0.0.0.0", PORT), ProjectDashboardHandler)
    print(f"Marlin project dashboard on http://0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test — start server and hit the API**

In one terminal:
```bash
cd ~/marlin && python3 project_dashboard.py
```

In a second terminal:
```bash
curl -s http://localhost:7833/api/projects | python3 -m json.tool | head -30
curl -s http://localhost:7833/ | head -5
```

Expected: JSON array (possibly empty if no projects have `dashboard: true` yet), and HTML from `/`.

Kill the server with Ctrl+C.

- [ ] **Step 3: Run full test suite**

```bash
cd ~/marlin && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
cd ~/marlin && git add project_dashboard.py
git commit -m "feat: add HTTP server to project_dashboard.py (port 7833)"
```

---

## Task 8: Add systemd unit

**Files:**
- Create: `systemd/marlin-project-dashboard.service`

- [ ] **Step 1: Create the service file**

```ini
# systemd/marlin-project-dashboard.service
[Unit]
Description=Marlin Project Dashboard — read-only project visualization
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/jared/marlin/project_dashboard.py
WorkingDirectory=/home/jared/marlin
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

- [ ] **Step 2: Install and start the service**

```bash
cp ~/marlin/systemd/marlin-project-dashboard.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable marlin-project-dashboard
systemctl --user start marlin-project-dashboard
systemctl --user status marlin-project-dashboard
```

Expected: `Active: active (running)`

- [ ] **Step 3: Verify it responds**

```bash
curl -s http://localhost:7833/ | head -3
```

Expected: HTML output.

- [ ] **Step 4: Commit**

```bash
cd ~/marlin && git add systemd/marlin-project-dashboard.service
git commit -m "feat: add systemd unit for project dashboard"
```

---

## Task 9: Complete frontmatter audit + add dashboard field to all projects

**Context:**
- `brief` was being added to all projects so Ariel can load context without reading full files. P1 and P2 are complete. P3 is almost done — only `packaged-exobrain-product.md` is missing `brief`. `brief` is not yet documented in `schemas.md`.
- `dashboard: true` is new — no projects have it yet. Add it to all P1/P2 projects and decide for each P3 project.

**Files:**
- Modify: `Projects/packaged-exobrain-product.md` — add `brief`
- Modify: `Projects/*.md` — add `dashboard: true` to selected P1/P2/P3 projects
- Modify: `System/Vault/schemas.md` — add `brief` and `dashboard` fields

- [ ] **Step 1: Add brief to packaged-exobrain-product.md**

Open `Projects/packaged-exobrain-product.md` and add this line after `priority: 3`:

```yaml
brief: "Consumer-packaged Marlin/Exobrain stack — LLM-guided setup for people who can't build it themselves; currently a seed concept, on-hold"
```

- [ ] **Step 2: Add dashboard field to P1 projects**

For each file, add `dashboard: true` after the `priority` line. All three P1 projects should appear on the dashboard.

- `Projects/job-hunt.md` → `dashboard: true`
- `Projects/id-replacement.md` → `dashboard: true`
- `Projects/interwest-inspection-preparation.md` → `dashboard: true`

- [ ] **Step 3: Add dashboard field to P2 projects**

Add `dashboard: true` to each of these (all are active P2 projects that belong on the dashboard):

```
adams-estate-inventory, ariel-von-marlin, ariel-von-marlin-identity,
ariel-von-marlin-orchestrator, ariel-von-marlin-runtime,
ariel-von-marlin-vault-sync, dental-fix, exobrain-context-awareness,
lmf-init, local-mind-foundation, marlin, personal-sms-gateway,
prosper0, prosper0-bridge, prosper0-deployment, prosper0-llm-stack,
prosper0-testing, prosper0-transparency, prosper0-vault,
the-time-factory, the-time-factory-1-0
```

Skip `ariel.md` (superseded by `ariel-von-marlin.md`) and `self-care.md` (ADL-only, not a development project).

Confirm with Jared before editing if any of these feel wrong.

- [ ] **Step 4: Add dashboard field to P3 projects**

P3 projects are maintenance/background — shown on the dashboard only if actively tracked:

- `Projects/diy-automation-keypad.md` → `dashboard: true` (active build)
- `Projects/hank.md` → `dashboard: true` (active loan tracking)
- `Projects/jiji.md` → `dashboard: true` (active vehicle)
- `Projects/lola.md` → `dashboard: true` (active vehicle)
- `Projects/packaged-exobrain-product.md` → `dashboard: false` (seed only, on-hold)

Confirm with Jared if any of these should flip before editing.

- [ ] **Step 5: Update schemas.md — add brief and dashboard fields**

In `System/Vault/schemas.md`, find the project frontmatter block and add both fields after `priority`:

```yaml
priority: 1             # 1 | 2 | 3 | R — see below
brief: "..."            # one-line summary for Ariel's always-loaded context
dashboard: true         # optional — if true, project appears in project visualization dashboard
```

- [ ] **Step 6: Verify dashboard returns data**

```bash
curl -s http://localhost:7833/api/projects | python3 -m json.tool | head -40
```

Expected: JSON array of projects with `dashboard: true`, with `brief`, completion percentages, and phase data populated.

- [ ] **Step 7: Commit**

```bash
cd ~/marlin && git add Projects/packaged-exobrain-product.md System/Vault/schemas.md
git add $(grep -rl "dashboard:" /home/jared/Documents/Obsidian/Marlin/Projects/*.md | tr '\n' ' ')
git commit -m "feat: add dashboard field to projects; complete brief audit; update schema"
```

---

## Self-Review

**Spec coverage:**
- ✓ Standalone server on port 7833 (Tasks 7–8)
- ✓ vault.py shared module (Tasks 1–4)
- ✓ webhook.py imports from vault.py (Task 5)
- ✓ `GET /api/projects` with priority filter (Task 7)
- ✓ `GET /api/projects/:slug` full detail (Task 7)
- ✓ `GET /` placeholder HTML (Task 7)
- ✓ completion_pct, current phase, current task in summary (Task 6)
- ✓ roadmap array with phases and items in detail (Task 6)
- ✓ `dashboard: true` frontmatter toggle on projects (Task 9)
- ✓ systemd unit (Task 8)
- ✓ `brief` audit completed and documented in schema (Task 9)

**Placeholder scan:** No TBDs. Task 9 Steps 3 and 4 include "confirm with Jared" gates — intentional, not placeholders. The default values are given; the gate is for edge cases.

**Type consistency:** `build_project_summary` and `build_project_detail` both call `find_tasks(tasks_path, {"project": title})` with the same filter key. `get_projects_summary` and `get_project_detail` both pass `PROJECTS_PATH` and `TASKS_PATH`. `compute_completion` returns `{done, total, pct}` — accessed as `completion["done"]` etc. throughout. Consistent.
