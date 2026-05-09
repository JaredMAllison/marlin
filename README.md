# Marlin

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](requirements.txt)

A context-aware task surfacing engine for Obsidian vaults. Marlin reads your tasks, watches your state, and surfaces one thing at a time — at the right moment, through the least friction channel.

Built for people whose executive function needs external scaffolding. Named for the fish and Merlin the wizard.

---

## What it does

Marlin runs every 15 minutes. When you're available, it picks the highest-priority task matching your current context and sends a push notification to your phone. Tap Done, Defer, or Snooze — the vault updates automatically.

It does not surface anything during deep work. It does not batch notifications. It does not delete tasks. One thing at a time.

---

## Architecture

```
marlin.py          → Surfacing engine (systemd timer, every 15 min)
webhook.py         → HTTP action server (Done/Defer/Snooze, mode switching, mode UI)
vault.py           → Shared vault I/O — frontmatter read/write, task discovery
project_dashboard.py → Project/vault API server
state.json         → Runtime state (mode, snooze) — not in git
```

## Modes

| Mode | Behavior |
|---|---|
| **Available** | Surface any eligible task |
| **Deep Work** | Surface nothing |
| **Transit** | Surface only short, any-time tasks |

## Notification actions

| Action | Effect |
|---|---|
| **Done** | Sets `status: done` + `completed: today` |
| **Defer** | Sets `status: deferred` + `deferred_until: tomorrow` |
| **Snooze** | Holds the task for 2 hours, no vault write |

## Tech stack

- **Python** — surfacing engine, web server, vault I/O
- **Ntfy** — push notifications to mobile (self-hosted or ntfy.sh)
- **systemd** — timer and service units for automatic execution
- **Obsidian/Markdown** — flat-file vault as the data store

## Setup

```bash
git clone https://github.com/JaredMAllison/marlin.git
cd marlin
pip install -r requirements.txt
echo '{"mode": "available"}' > state.json
# Edit VAULT path and ntfy topic in marlin.py
python marlin.py
```

See [SETUP.md](SETUP.md) for systemd integration and full configuration.

## Related repos

- [lmf-ollama-obsidian](https://github.com/JaredMAllison/lmf-ollama-obsidian) — LLM orchestrator stack (used by Marlin as the AI conversation layer)
- [cockpit](https://github.com/JaredMAllison/cockpit) — unified HUD for the full stack
- [the-time-factory](https://github.com/JaredMAllison/the-time-factory) — ADHD-friendly visual calendar
- [prosper0](https://github.com/JaredMAllison/prosper0) — work-specific exobrain instance

---

*Part of the Local Mind Foundation architecture. Local-first, ND-designed, operator-sovereign.*
