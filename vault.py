# vault.py
from datetime import date
import re
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
    Each result dict has '_slug' and '_path' (Path object, not str) set.
    """
    filters = filters or {}
    results = []
    for path in sorted(projects_path.glob("*.md")):
        stem = path.stem
        if stem.endswith("-roadmap") or stem.endswith("-changelog") or stem.endswith("-brief") or stem.endswith("-open-questions"):
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
        .replace(" — ", "-")
        .replace("—", "-")
        .replace(" ", "-")
    )
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    candidate = projects_path / f"{slug}.md"
    if candidate.exists():
        return candidate

    for path in projects_path.glob("*.md"):
        fm = read_frontmatter(path)
        if fm.get("title") == title and fm.get("type") == "project-roadmap":
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
