"""
build_prompt.py — Ariel system prompt compiler.

Assembles a complete system prompt from:
  1. Identity doc (System/Memory/ARIEL.md)
  2. All memory files listed in System/Memory/MEMORY.md

Stack-level: parameterized by vault path. Works for any LMF vault instance.
Each vault supplies its own ARIEL.md + System/Memory/ + System/Skills/.

Usage:
  python3 build_prompt.py [vault_path]     # prints compiled prompt to stdout
  from build_prompt import build_prompt    # returns string
"""

import re
import sys
from pathlib import Path

IDENTITY_PATH = "System/Memory/ARIEL.md"
MEMORY_INDEX  = "System/Memory/MEMORY.md"
MEMORY_DIR    = "System/Memory"


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _parse_memory_files(index_path: Path) -> list[Path]:
    """Parse MEMORY.md and return ordered list of linked file paths."""
    if not index_path.exists():
        return []
    files = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        match = re.search(r"\(([^)]+\.md)\)", line)
        if match:
            files.append(index_path.parent / match.group(1))
    return files


def build_prompt(vault_path: str | Path) -> str:
    vault = Path(vault_path)
    sections = []

    # 1 — Identity
    identity = _read(vault / IDENTITY_PATH)
    if identity:
        sections.append("# Identity\n\n" + identity)
    else:
        sections.append(
            "# Identity\n\n"
            f"[{IDENTITY_PATH} not found in vault at {vault}. "
            "Operating without identity context until ARIEL.md is created.]"
        )

    # 2 — Memory
    memory_files = _parse_memory_files(vault / MEMORY_INDEX)
    blocks = []
    for path in memory_files:
        # Skip ARIEL.md if it appears in the index — already loaded as identity
        if path.name == "ARIEL.md":
            continue
        content = _read(path)
        if content:
            blocks.append(f"### {path.stem}\n\n{content}")

    if blocks:
        sections.append("# Memory\n\n" + "\n\n---\n\n".join(blocks))

    return "\n\n---\n\n".join(sections)


if __name__ == "__main__":
    vault = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / "Documents/Obsidian/Marlin")
    print(build_prompt(vault))
