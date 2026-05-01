# Project Dashboard — Backend Design

**Date:** 2026-04-24
**Status:** approved
**Project:** Marlin

---

## Context

The existing Marlin dashboard (webhook.py, port 7832) is a task-action interface: one surfaced task, today's list, mode switching, inbox capture. It is not a project-level view.

The operator needs a separate visualization surface: all P1/P2 projects at a glance, with completion percentage, current roadmap phase, and current task. Expanding a project reveals full roadmap detail and task list. Projects opt in via frontmatter.

This is a cognitive prosthetic — one glance should convey project health across the whole stack without navigation.

---

## Architecture

**New file:** `project_dashboard.py` — standalone HTTP server on port 7833. Same pattern as webhook.py. Serves frontend HTML at `/` and a JSON API.

**New shared module:** `vault.py` — pure data functions extracted from webhook.py (frontmatter read/write, task filtering, sort logic). No HTTP, no business logic. Both servers import from it.

webhook.py is refactored mechanically to import from vault.py — no behavior change. The full decomposition of webhook.py into focused modules (surfacing, ADL, HTML rendering) is tracked in the roadmap as Phase 4b and is out of scope here.

---

## Frontmatter Additions

Two new opt-in fields:

**Projects** (`Projects/*.md`):
```yaml
dashboard: true
```
Makes the project visible to the project dashboard. Absent or false = not shown.

**Tasks** (`Tasks/*.md`):
```yaml
dashboard: false
```
Opt-out toggle. Default is visible if the parent project is visible. Set to false to suppress internal/noise tasks from the project detail view.

Priority filter: `priority: 1` or `priority: 2` already exists on project files. Default view shows P1 and P2. API accepts `?priority=all` to override.

---

## vault.py — Shared Data Layer

Pure functions, no side effects beyond file writes. No HTTP dependencies.

```python
read_frontmatter(path: Path) -> dict
update_frontmatter(path: Path, updates: dict) -> bool
find_tasks(vault_path: Path, filters: dict) -> list[dict]
    # filters: status, project, priority, dashboard
find_projects(projects_path: Path, filters: dict) -> list[dict]
    # filters: dashboard, priority, status
resolve_roadmap_path(projects_path: Path, roadmap_link: str) -> Path | None
    # roadmap_link is "[[Title]]" — strips brackets, searches Projects/ by filename
parse_roadmap(path: Path) -> list[Phase]
    # Phase = { name: str, complete: bool, items: list[{text: str, done: bool}] }
    # Parses ## headers as phase names, - [x] / - [ ] as items
compute_completion(tasks: list[dict]) -> dict
    # Returns {done: int, total: int, pct: int}
    # done = status == "done"; total = dashboard != false; pct = done/total*100 rounded
current_phase(phases: list[Phase]) -> Phase | None
    # First phase with any item where done == false
top_task(tasks: list[dict]) -> dict | None
    # Queued tasks for project, sorted by goal_date ASC then duration ASC
    # duration sort: short=15, medium=45, long=120
```

webhook.py imports: `read_frontmatter`, `update_frontmatter`, `find_task` (renamed from its local copy).

---

## project_dashboard.py — Server

Port 7833. Thin HTTP server identical in pattern to webhook.py. Serves static HTML at `/` and two JSON endpoints.

### GET /api/projects

Query params:
- `?priority=all` — include P3+ projects (default: P1 and P2 only)

Response: array of project summary objects, sorted by priority ASC then title ASC.

```json
[
  {
    "slug": "marlin",
    "title": "Marlin",
    "priority": 2,
    "status": "evergreen",
    "brief": "Context-aware task surfacing engine...",
    "phase_current": "Phase 4 — Quickhack Menu",
    "phase_index": 3,
    "phase_total": 7,
    "task_current": "Dashboard — surface available_from tasks",
    "tasks_done": 5,
    "tasks_total": 12,
    "completion_pct": 42
  }
]
```

Field notes:
- `slug` — filename stem of the project file (e.g. `marlin` from `marlin.md`)
- `phase_index` — 1-based index of the current phase among all phases
- `phase_total` — total number of phases in the roadmap
- `phase_current` / `task_current` — null if roadmap absent or all tasks done
- `completion_pct` — 0 if no tasks; 100 if all done

### GET /api/projects/:slug

Response: full project detail object.

```json
{
  "slug": "marlin",
  "title": "Marlin",
  "priority": 2,
  "status": "evergreen",
  "brief": "...",
  "roadmap": [
    {
      "name": "Phase 1 — Core Engine",
      "complete": true,
      "items": [
        { "text": "Flat-file surfacing, Ntfy notifications...", "done": true }
      ]
    },
    {
      "name": "Phase 4 — Quickhack Menu",
      "complete": false,
      "items": [
        { "text": "Termux SSH link", "done": false },
        { "text": "/share endpoint", "done": false }
      ]
    }
  ],
  "tasks": [
    {
      "title": "Dashboard — surface available_from tasks",
      "status": "queued",
      "goal_date": "",
      "duration": "medium",
      "dashboard": true
    }
  ],
  "tasks_done": 5,
  "tasks_total": 12,
  "completion_pct": 42
}
```

Field notes:
- `roadmap` — empty array if no roadmap file found or linked
- `tasks` — all tasks for this project where `dashboard != false`, sorted by goal_date ASC
- Completed tasks (status: done) are included in the task list for full picture

### GET /

Serves the frontend HTML. Single-page app; JS fetches `/api/projects` on load and `/api/projects/:slug` on project expand. No server-side rendering of project detail.

---

## Roadmap Parsing

Roadmap files live in `Projects/` as `<slug>-roadmap.md`. Project frontmatter links them as `roadmap: "[[Title]]"`.

Resolution:
1. Strip `[[` and `]]` from the link value
2. Search `Projects/` for a file where the frontmatter `title` matches, or where the stem matches a slugified version of the title
3. Fallback: search for `<project-slug>-roadmap.md` directly

Parsing rules:
- `## ` lines → new phase, name = line content after `## `
- `- [x] ` lines → done item
- `- [ ] ` lines → open item
- Other lines → ignored
- Phase is `complete: true` if all its items are done AND it has at least one item

---

## Systemd Unit

New unit: `marlin-project-dashboard.service` — same structure as `marlin-webhook.service`. User service, `Restart=on-failure`, `WorkingDirectory=~/marlin`.

---

## Out of Scope

- Task actions (done/defer/snooze) — dashboard is read-only
- Inline task editing
- webhook.py internal decomposition (Phase 4b roadmap item)
- Real-time push updates (page load is fresh data; no websockets)
