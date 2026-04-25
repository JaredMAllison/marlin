# project_dashboard.py
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

    cp = current_phase(phases)
    phase_index = next((i + 1 for i, p in enumerate(phases) if p is cp), None)
    tt = top_task(tasks)

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
        "phase_current": cp["name"] if cp else None,
        "phase_index": phase_index,
        "phase_total": len(phases),
        "task_current": tt.get("title") if tt else None,
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
