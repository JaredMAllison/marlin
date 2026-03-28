# Marlin — Claude Code Context

## What this is

Marlin is a context-aware task surfacing engine. It reads an Obsidian vault of markdown task notes, filters them by the operator's current state and context, and sends one notification to their Android phone via Ntfy. Notification actions (Done/Defer/Snooze) write back to the vault.

The operator has ADHD and Autism. Every decision should reduce cognitive load, not add to it. When in doubt: simpler, quieter, less.

---

## File map

| File | Purpose |
|---|---|
| `marlin.py` | Surfacing engine. Run by systemd timer every 15 min. Reads vault, filters, sorts, sends one Ntfy notification. |
| `webhook.py` | HTTP server on port 7832. Handles Done/Defer/Snooze task actions and mode switching. Serves the mode UI at `/`. |
| `set-mode.sh` | CLI shortcut to update state.json mode. |
| `state.json` | Runtime state. Not in git. Contains `mode` and optional snooze tracking. |

---

## Architecture

```
systemd timer (15 min)
    → marlin.py
        → reads Tasks/*.md (YAML frontmatter)
        → filters by mode, context, business-hours, available_from
        → sorts by goal_date ASC, duration ASC
        → POSTs one notification to ntfy.sh

Android Ntfy app
    → Done/Defer/Snooze buttons → GET http://10.0.0.8:7832/{action}?task=...
    → webhook.py updates vault frontmatter via yaml.dump

Mode UI
    → GET http://10.0.0.8:7832/ → HTML page with 3 buttons
    → GET http://10.0.0.8:7832/mode?set=X → updates state.json
```

---

## Key decisions and why

**Flat file query, no database**
The vault is the source of truth. No sync issues, no migration, no extra dependencies. Tasks are just `.md` files with YAML frontmatter.

**One notification at a time**
Alert fatigue is a real problem for the operator. Batching or lists are explicitly not wanted. Surface one thing; let the operator act on it.

**No AI in Phase 1**
The frontmatter is already structured. Filtering and sorting structured data doesn't need LLM reasoning. Keep it simple until simple stops working.

**Mode switching via web UI, not system schedule**
The operator's energy and availability is unpredictable. A rigid schedule doesn't work. Mode is always operator-declared, never inferred (yet).

**`available_from` separate from `goal_date`**
Goal date is the deadline. `available_from` is when Marlin should start surfacing it. Recurring weekly tasks with a Friday deadline should start appearing Monday, not Friday morning.

**Ntfy for notifications**
Self-hostable, Android native, supports HTTP action buttons that call back to the webhook. No app to build.

**systemd user services**
No root required. Services start on login, restart on failure, log to journald.

---

## Vault schema

Tasks at `/home/jared/Documents/Obsidian/Marlin/Tasks/*.md`:

```yaml
---
title: string          # required
type: task             # required, literal
status: queued         # queued | deferred | waiting | done
project: "[[Name]]"   # optional wiki link
goal_date: YYYY-MM-DD  # optional deadline
available_from: YYYY-MM-DD  # optional, earliest surface date
created: YYYY-MM-DD    # required, set at capture time
context: [computer]    # computer | phone-call | business-hours | any-time
duration: short        # short | medium | long
duration_minutes: 45   # optional, exact estimate
recurrence: weekly     # optional
tags: [task, queued]   # required, must include type and status
---
```

Status transitions:
- `queued` → `done` (Done action): adds `completed: YYYY-MM-DD`
- `queued` → `deferred` (Defer action): adds `deferred_until: tomorrow`
- Snooze: no vault write, state.json tracks snooze_until

---

## What not to break

- **Never delete or overwrite vault notes.** Status changes only. The vault is permanent.
- **Never surface more than one task per run.** One notification, always.
- **Never write to the vault without user confirmation** (from Claude Code skills — the surfacing engine only writes on explicit action button tap).
- **The webhook must stay on port 7832.** It's hardcoded in systemd service files and bookmarked on the operator's phone.
- **state.json is not in git.** It's runtime state, machine-specific. Don't add it.

---

## Environment variables

Both services require these environment variables (set in systemd service files):

| Variable | Value |
|---|---|
| `MARLIN_NTFY_TOPIC` | `jared-surface-8n3p` |
| `MARLIN_WEBHOOK_BASE` | `http://10.0.0.8:7832` (update when WireGuard is set up) |

---

## Planned / not built yet

- **Snooze enforcement** — state.json tracks snooze_until but marlin.py doesn't check it yet
- **Recurring task reset** — when a recurring task is marked done, nothing re-queues it yet
- **WireGuard** — webhook currently only works on home WiFi; update MARLIN_WEBHOOK_BASE to WG address when set up
- **Phase 2: Claude queries** — active natural language queries against the vault ("what can I do in 15 min?")
- **Deferred task re-queue** — deferred tasks need manual status reset; no automatic re-queue yet

---

## Companion skills (in ~/.claude/skills/)

- `/marlin-capture` — guided task/project note creation with frontmatter validation
- `/obsidian-enrich` — structured enrichment session (intake → scan → connections → approval → write)

Reference files for obsidian-enrich live in `~/.claude/skills/obsidian-enrich/references/`.
