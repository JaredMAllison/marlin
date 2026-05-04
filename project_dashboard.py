# project_dashboard.py
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

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

VAULT_ROOT    = Path(os.environ.get("MARLIN_VAULT_ROOT",
                     os.environ.get("MARLIN_VAULT_PATH",
                     "/home/jared/Documents/Obsidian/Marlin")))
TASKS_PATH    = VAULT_ROOT / "Tasks"
PROJECTS_PATH = VAULT_ROOT / "Projects"
PORT          = int(os.environ.get("MARLIN_DASHBOARD_PORT", "7833"))


def _build_project_core(project_path: Path, tasks_path: Path, projects_path: Path) -> dict:
    """Shared data assembly used by both summary and detail views."""
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
        "_fm": fm,
        "_tasks": tasks,
        "_phases": phases,
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


def build_project_summary(project_path: Path, tasks_path: Path, projects_path: Path) -> dict:
    core = _build_project_core(project_path, tasks_path, projects_path)
    return {k: v for k, v in core.items() if not k.startswith("_")}


def build_project_detail(project_path: Path, tasks_path: Path, projects_path: Path) -> dict:
    core = _build_project_core(project_path, tasks_path, projects_path)
    task_list = []
    for t in sorted(
        core["_tasks"],
        key=lambda x: (str(x.get("goal_date") or "9999"), x.get("title", "")),
    ):
        task_list.append({
            "title": t.get("title", ""),
            "status": t.get("status", ""),
            "goal_date": str(t.get("goal_date") or ""),
            "duration": t.get("duration", ""),
            "dashboard": t.get("dashboard", True),
        })
    result = {k: v for k, v in core.items() if not k.startswith("_")}
    result["roadmap"] = core["_phases"]
    result["tasks"] = task_list
    return result


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


def get_project_detail(slug: str, projects_path: Path, tasks_path: Path) -> dict | None:
    path = projects_path / f"{slug}.md"
    if not path.exists():
        return None
    fm = read_frontmatter(path)
    if fm.get("type") != "project":
        return None
    return build_project_detail(path, tasks_path, projects_path)


def build_vault_tree(vault_root: Path) -> list[dict]:
    """Walk vault top-level dirs and their immediate children."""
    results = []
    for entry in sorted(vault_root.iterdir()):
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.is_dir():
            for child in sorted(entry.iterdir()):
                if child.name.startswith(".") or child.name.startswith("_"):
                    continue
                results.append({
                    "path": f"{entry.name}/{child.name}",
                    "name": child.name,
                    "folder": entry.name,
                })
        elif entry.suffix == ".md":
            results.append({
                "path": entry.name,
                "name": entry.name,
                "folder": "",
            })
    return results


def read_vault_file(vault_root: Path, rel_path: str) -> str:
    """Return raw content of a vault file. Raises ValueError on path traversal."""
    resolved = (vault_root / rel_path).resolve()
    if not resolved.is_relative_to(vault_root.resolve()):
        raise ValueError(f"Invalid path: {rel_path}")
    if not resolved.is_file():
        raise FileNotFoundError(rel_path)
    return resolved.read_text(encoding="utf-8")


INDEX_PATH = Path(__file__).parent / "index.html"


class ProjectDashboardHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            try:
                body = INDEX_PATH.read_bytes()
            except FileNotFoundError:
                self._text(500, "index.html not found next to project_dashboard.py")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

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

        if path.startswith("/api/projects/"):
            slug = path[len("/api/projects/"):]
            try:
                detail = get_project_detail(slug, PROJECTS_PATH, TASKS_PATH)
            except Exception as e:
                self._text(500, f"Internal error: {e}")
                return
            if detail is None:
                self._text(404, "Not found")
                return
            self._json(detail)
            return

        if path == "/api/vault/tree":
            try:
                data = build_vault_tree(VAULT_ROOT)
            except Exception as e:
                self._text(500, f"Internal error: {e}")
                return
            self._json(data)
            return

        if path == "/api/vault/file":
            from urllib.parse import parse_qs
            rel = parse_qs(parsed.query).get("path", [None])[0]
            if not rel:
                self._text(400, "Missing path parameter")
                return
            try:
                content = read_vault_file(VAULT_ROOT, rel)
            except ValueError as e:
                self._text(403, str(e))
                return
            except FileNotFoundError:
                self._text(404, "Not found")
                return
            except Exception as e:
                self._text(500, f"Internal error: {e}")
                return
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        self._text(404, "Not found")

    def _json(self, data):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _text(self, code: int, message: str):
        body = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        code = args[1] if len(args) > 1 else ""
        if code.startswith("4") or code.startswith("5"):
            print(f"[dashboard] {self.address_string()} {args}", file=sys.stderr)


def main():
    server = HTTPServer(("0.0.0.0", PORT), ProjectDashboardHandler)
    print(f"Marlin project dashboard on http://0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
