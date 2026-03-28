# Marlin

A context-aware task surfacing engine for an Obsidian vault. Marlin reads your tasks, watches your state, and surfaces one thing at a time — at the right moment, through the least friction channel.

Named for the fish (GUPIE lineage) and Merlin the wizard.

---

## What it does

Marlin runs every 15 minutes. When you're available, it picks the highest-priority task that matches your current context and sends a notification to your phone. You tap Done, Defer, or Snooze — the vault updates automatically.

It does not surface anything during deep work. It does not batch notifications. It does not delete tasks. One thing at a time.

---

## Modes

Switch modes from the Marlin web UI at `http://10.0.0.8:7832` (bookmark it to your home screen).

| Mode | Behavior |
|---|---|
| **Available** | Surface any eligible task |
| **Deep Work** | Surface nothing |
| **Transit** | Surface only `any-time` + `short` tasks |

---

## Notification actions

When Marlin surfaces a task you get a notification with three buttons:

| Button | Effect |
|---|---|
| **Done** | Sets `status: done` + `completed: today` in the vault note |
| **Defer** | Sets `status: deferred` + `deferred_until: tomorrow` |
| **Snooze** | Holds the task for 2 hours, no vault write |

---

## Task schema

Tasks live in `/home/jared/Documents/Obsidian/Marlin/Tasks/` as `.md` files with YAML frontmatter.

```yaml
---
title: Task Title
type: task
status: queued
project: "[[Project Name]]"
goal_date: YYYY-MM-DD
available_from: YYYY-MM-DD
created: YYYY-MM-DD
context: [computer, business-hours]
duration: short
duration_minutes: 15
recurrence: every-friday
tags: [task, queued]
---

Optional body text.
```

### Status values
| Value | Meaning |
|---|---|
| `queued` | Ready to surface |
| `deferred` | Snoozed, re-queue later |
| `waiting` | Blocked on external party |
| `done` | Complete — never deleted |

### Context values
| Value | Meaning |
|---|---|
| `computer` | Requires desktop or laptop |
| `phone-call` | Requires a voice call |
| `business-hours` | Only Mon–Fri 8am–5pm Pacific |
| `any-time` | No constraint |

### Duration values
| Value | Time |
|---|---|
| `short` | Under 15 min |
| `medium` | 15–60 min |
| `long` | Over 1 hour |

### Optional fields
- `available_from` — earliest date to surface this task (use when a task shouldn't appear until a certain date even if goal_date is later)
- `duration_minutes` — exact estimate in minutes, for future scheduling
- `recurrence` — `daily`, `weekly`, `biweekly`, `monthly`, `every-friday`, `every-N-days`

---

## Adding tasks

Use the `/marlin-capture` Claude Code skill. It prompts for all required fields and validates frontmatter before writing.

```
/marlin-capture
```

For bulk enrichment sessions (processing notes, finding connections, creating atomic notes):

```
/obsidian-enrich
```

---

## Vault structure

```
/home/jared/Documents/Obsidian/Marlin/
├── Tasks/        ← one .md file per task
├── Projects/     ← one .md file per project
├── Daily/        ← YYYY-MM-DD.md daily notes
└── Inbox.md      ← unprocessed capture
```

---

## Surfacing rules

1. Mode must be `available` or `transit`
2. Task `status` must be `queued`
3. `available_from` must be today or earlier (if set)
4. `business-hours` context tasks only surface Mon–Fri 8am–5pm Pacific
5. Tasks surfaced within the last 2 hours are skipped — pick the next eligible one
6. Sort: soonest `goal_date` first, then shortest `duration`
7. Surface **one task only**

A task will re-surface after 2 hours if ignored. Tapping Snooze also holds it for 2 hours. Tapping Done or Defer removes it from the queue permanently (until status is reset).

---

## Files

| File | Purpose |
|---|---|
| `marlin.py` | Surfacing engine — run by systemd timer |
| `webhook.py` | Action server — handles Done/Defer/Snooze/mode |
| `set-mode.sh` | CLI mode switcher (alternative to web UI) |
| `state.json` | Runtime state — mode, snooze tracking (not in git) |

---

## Troubleshooting

**No notifications arriving:**
- Check mode: `cat ~/marlin/state.json`
- Run manually: `cd ~/marlin && MARLIN_NTFY_TOPIC=jared-surface-8n3p python3 marlin.py`
- Check timer: `systemctl --user status marlin.timer`

**Done/Defer not updating the vault:**
- Check webhook: `systemctl --user status marlin-webhook.service`
- Check logs: `journalctl --user -u marlin-webhook.service -n 20`

**Wrong task surfaced:**
- Check frontmatter on the task file — status, available_from, context
- Run marlin.py manually to see what it picks and why
