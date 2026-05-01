"""
orchestrator.py — Ariel conversation orchestrator.

HTTP server that sits between the user and Ollama.
Each turn: parses skill triggers, assembles context, calls Ollama, returns response.

Usage:
  python3 orchestrator.py [vault_path]

Endpoints:
  POST /chat   { "message": "..." }  → { "response": "..." }
  POST /reset                        → resets conversation history
  GET  /health                       → { "status": "ok" }
"""

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

from build_prompt import build_prompt

OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:7b"
HOST         = "0.0.0.0"
PORT         = 8742
SKILLS_DIR   = "System/Skills"


def load_skill(vault: Path, name: str) -> str | None:
    """Look up a skill file by name. Returns content or None."""
    candidates = [
        vault / SKILLS_DIR / f"{name}.md",
        vault / SKILLS_DIR / name / f"{name}.md",
        vault / SKILLS_DIR / name / "SKILL.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return None


def parse_skill_trigger(message: str) -> str | None:
    """Return skill name if message starts with /skill-name, else None."""
    match = re.match(r"^/([a-z0-9_-]+)", message.strip())
    return match.group(1) if match else None


class Orchestrator:
    def __init__(self, vault_path: str):
        self.vault = Path(vault_path)
        self.system_prompt = build_prompt(vault_path)
        self.history: list[dict] = []
        print(f"[orchestrator] Vault: {self.vault}")
        print(f"[orchestrator] System prompt: {len(self.system_prompt)} chars")
        print(f"[orchestrator] Listening on {HOST}:{PORT}")

    def reset(self):
        self.history = []

    def chat(self, user_message: str) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]

        # Inject skill if triggered
        skill_name = parse_skill_trigger(user_message)
        if skill_name:
            skill_content = load_skill(self.vault, skill_name)
            if skill_content:
                messages.append({
                    "role": "user",
                    "content": f"[Skill loaded: /{skill_name}]\n\n{skill_content}"
                })
                messages.append({
                    "role": "assistant",
                    "content": f"Skill /{skill_name} loaded. Following its instructions now."
                })

        messages += self.history
        messages.append({"role": "user", "content": user_message})

        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        })
        response.raise_for_status()
        reply = response.json()["message"]["content"]

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": reply})

        return reply


class Handler(BaseHTTPRequestHandler):
    orchestrator: Orchestrator = None

    def log_message(self, format, *args):
        pass  # quiet default logging

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/chat":
            message = body.get("message", "").strip()
            if not message:
                self._respond(400, {"error": "message required"})
                return
            try:
                reply = self.orchestrator.chat(message)
                self._respond(200, {"response": reply})
            except Exception as e:
                self._respond(500, {"error": str(e)})

        elif self.path == "/reset":
            self.orchestrator.reset()
            self._respond(200, {"status": "conversation reset"})

        else:
            self._respond(404, {"error": "not found"})


def run(vault_path: str):
    orch = Orchestrator(vault_path)
    Handler.orchestrator = orch
    server = HTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[orchestrator] Stopped.")


if __name__ == "__main__":
    vault = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Documents/Obsidian/Marlin")
    run(vault)
