# Hide Done Projects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a toggle to the project dashboard that hides projects with `status: complete` by default, with a "Show done" button to include them.

**Architecture:** Add `exclude_complete` filter to `find_projects` in `vault.py`, wire a `hide_done` param through `get_projects_summary` and the HTTP handler, and add a frontend toggle alongside the existing priority toggle. Done projects are hidden by default — the toggle reveals them.

**Tech Stack:** Python 3 (vault.py, project_dashboard.py), vanilla JS (index.html), pytest

---

## File Map

| File | Change |
|---|---|
| `vault.py` | Add `exclude_complete: bool` filter key to `find_projects` |
| `project_dashboard.py` | Add `hide_done=True` to `get_projects_summary`; parse `?show_done=true` in HTTP handler |
| `index.html` | Add `state.hideDone`, update `apiList`, add status toggle row, filter mock fallback |
| `tests/test_vault.py` | Add test for `exclude_complete` filter |
| `tests/test_project_dashboard.py` | Add tests for `hide_done` default and `show_done` override |

---

## Task 1: vault.py — exclude_complete filter

**Files:**
- Modify: `vault.py` (the `find_projects` function, lines 66–99)
- Test: `tests/test_vault.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_vault.py`:

```python
def test_find_projects_excludes_complete(tmp_path):
    _make_project(tmp_path, "Active Project", status="active")
    _make_project(tmp_path, "Done Project", status="complete")
    results = find_projects(tmp_path, {"exclude_complete": True})
    titles = {r["title"] for r in results}
    assert "Active Project" in titles
    assert "Done Project" not in titles


def test_find_projects_includes_complete_when_flag_false(tmp_path):
    _make_project(tmp_path, "Active Project", status="active")
    _make_project(tmp_path, "Done Project", status="complete")
    results = find_projects(tmp_path, {"exclude_complete": False})
    titles = {r["title"] for r in results}
    assert "Active Project" in titles
    assert "Done Project" in titles
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
python3 -m pytest tests/test_vault.py::test_find_projects_excludes_complete tests/test_vault.py::test_find_projects_includes_complete_when_flag_false -v
```

Expected: FAIL — `exclude_complete` filter not implemented yet.

- [ ] **Step 3: Add `exclude_complete` to `find_projects` in vault.py**

In `find_projects`, after the existing `status` filter check (around line 94), add:

```python
        if filters.get("exclude_complete") and fm.get("status") == "complete":
            continue
```

The full filter block inside `find_projects` should now read:

```python
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
        if filters.get("exclude_complete") and fm.get("status") == "complete":
            continue
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
python3 -m pytest tests/test_vault.py::test_find_projects_excludes_complete tests/test_vault.py::test_find_projects_includes_complete_when_flag_false -v
```

Expected: both PASS.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
python3 -m pytest tests/ -q
```

Expected: all 41 tests pass plus the 2 new ones (43 total).

- [ ] **Step 6: Commit**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
git add vault.py tests/test_vault.py
git commit -m "feat: add exclude_complete filter to find_projects"
```

---

## Task 2: project_dashboard.py — hide_done param and HTTP wiring

**Files:**
- Modify: `project_dashboard.py` (the `get_projects_summary` function and `do_GET` handler)
- Test: `tests/test_project_dashboard.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_project_dashboard.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
python3 -m pytest tests/test_project_dashboard.py::test_get_projects_summary_hides_complete_by_default tests/test_project_dashboard.py::test_get_projects_summary_show_done_includes_complete -v
```

Expected: FAIL — `get_projects_summary` doesn't accept `hide_done` yet.

- [ ] **Step 3: Update `get_projects_summary` in project_dashboard.py**

Replace the current `get_projects_summary` signature and body:

```python
def get_projects_summary(
    projects_path: Path, tasks_path: Path, priority_all: bool = False, hide_done: bool = True
) -> list[dict]:
    filters: dict = {"dashboard": True}
    if not priority_all:
        filters["priority"] = [1, 2]
    if hide_done:
        filters["exclude_complete"] = True
    projects = find_projects(projects_path, filters)
    projects.sort(key=lambda fm: (fm.get("priority") or 99, fm.get("title", "")))
    return [build_project_summary(fm["_path"], tasks_path, projects_path) for fm in projects]
```

- [ ] **Step 4: Update the HTTP handler to parse `?show_done=true`**

In `do_GET`, replace the `/api/projects` branch:

```python
        if path == "/api/projects":
            priority_all = "priority=all" in (parsed.query or "")
            show_done = "show_done=true" in (parsed.query or "")
            try:
                data = get_projects_summary(
                    PROJECTS_PATH, TASKS_PATH,
                    priority_all=priority_all,
                    hide_done=not show_done,
                )
            except Exception as e:
                self._text(500, f"Internal error: {e}")
                return
            self._json(data)
            return
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
python3 -m pytest tests/test_project_dashboard.py::test_get_projects_summary_hides_complete_by_default tests/test_project_dashboard.py::test_get_projects_summary_show_done_includes_complete -v
```

Expected: both PASS.

- [ ] **Step 6: Run full test suite**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
python3 -m pytest tests/ -q
```

Expected: all 43 tests pass plus the 2 new ones (45 total).

- [ ] **Step 7: Commit**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
git add project_dashboard.py tests/test_project_dashboard.py
git commit -m "feat: hide complete projects by default; add show_done query param"
```

---

## Task 3: index.html — frontend hide-done toggle

**Files:**
- Modify: `index.html`

No new test file — the frontend is verified manually by loading the dashboard and toggling the button.

- [ ] **Step 1: Add `hideDone` to the router state object**

In the `state` object (around line 862), add `hideDone: true`:

```js
const state = {
  view: "list",
  slug: null,
  query: "",
  includeP3: false,
  hideDone: true,          // ← add this
  projects: null,
  detailCache: {},
  lastFetched: null,
};
```

- [ ] **Step 2: Update `apiList` to pass `show_done=true` when `hideDone` is false**

Replace the current `apiList` function:

```js
async function apiList(includeP3, hideDone) {
  const params = [];
  if (includeP3) params.push("priority=all");
  if (!hideDone) params.push("show_done=true");
  const url = "/api/projects" + (params.length ? "?" + params.join("&") : "");
  try {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (e) {
    let list = window.MOCK_PROJECTS.slice();
    if (!includeP3) list = list.filter(p => p.priority <= 2);
    if (hideDone) list = list.filter(p => p.status !== "complete");
    return list;
  }
}
```

- [ ] **Step 3: Update `loadList` to pass `state.hideDone` to `apiList`**

Replace the current `loadList` function:

```js
async function loadList(force) {
  if (force) state.projects = null;
  render();
  try {
    state.projects = await apiList(state.includeP3, state.hideDone);
    state.lastFetched = new Date();
  } catch (e) {
    state.projects = [];
  }
  render();
}
```

- [ ] **Step 4: Add the status toggle row to `viewList`**

In `viewList`, after the existing priority toggle block (around line 948), add a second toggle row for hide-done. Insert after `root.appendChild(toggle)`:

```js
  // Status toggle (hide done / show all)
  const statusToggle = el("div", {class:"toggle"},
    el("button", {
      type:"button",
      "aria-pressed": state.hideDone.toString(),
      onclick: () => { if (!state.hideDone) { state.hideDone = true; loadList(true); } }
    }, "Active"),
    el("button", {
      type:"button",
      "aria-pressed": (!state.hideDone).toString(),
      onclick: () => { if (state.hideDone) { state.hideDone = false; loadList(true); } }
    }, "Incl. done")
  );
  root.appendChild(statusToggle);
```

- [ ] **Step 5: Verify the dashboard in a browser**

Restart the dashboard service or run it directly:

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
python3 project_dashboard.py &
```

Open http://localhost:7833 in a browser and verify:
- "Active" button is pressed by default; complete projects are hidden
- Clicking "Incl. done" reloads and shows complete projects
- Clicking "Active" hides them again
- Both toggles (priority and status) work independently
- Filter input still works with both toggle states

Kill the test server when done: `kill %1`

- [ ] **Step 6: Run full test suite one final time**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
python3 -m pytest tests/ -q
```

Expected: 45 tests pass.

- [ ] **Step 7: Commit**

```bash
cd /home/jared/marlin/.worktrees/hide-done-projects
git add index.html
git commit -m "feat: add hide-done toggle to project dashboard frontend"
```
