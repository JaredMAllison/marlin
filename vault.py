# vault.py
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
