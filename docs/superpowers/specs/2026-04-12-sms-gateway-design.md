# SMS Gateway (gv-gateway) — Design Spec
**Date:** 2026-04-12  
**Status:** Approved  
**Scope:** v1 — core loop (IMAP polling, key rotation, inbox routing, desktop notification)

---

## Context

The Personal SMS Gateway ("Jared's Exo-Brain Broadcast") allows sending structured commands from any phone in the world into Gretchen via SMS, requiring no app, no account, and no internet on the sending end — just a phone that can send an SMS.

v1 proves the pipe works end-to-end: an SMS sent to the Google Voice number arrives in Gmail, gets parsed, is authenticated by daily key, and routes to Inbox.md with a desktop notification on Gretchen.

---

## Architecture

A `gv_gateway/` Python package inside `~/marlin/`, alongside existing scripts. Two systemd units:

- `gv-gateway.service` — always-on polling loop (60s interval)
- `gv-keygen.timer` + `gv-keygen.service` — fires daily at 07:00 to rotate key and email it

```
~/marlin/
├── gv_gateway/
│   ├── __init__.py
│   ├── main.py        ← entry point, polling loop
│   ├── imap.py        ← connect, fetch new GV emails, mark read
│   ├── keys.py        ← generate daily key, email to personal Gmail
│   ├── router.py      ← parse message, validate key, dispatch route
│   └── notify.py      ← notify-send wrapper
├── tests/
│   └── test_gv_gateway/
│       ├── test_keys.py
│       ├── test_router.py
│       └── test_imap.py
```

---

## Google Account Bootstrap

1. Create GV number on personal Gmail → use that number to verify new Marlin Google account
2. Create GV number on Marlin Google account → this is the gateway number
3. Configure GV to forward SMS to Marlin Gmail
4. Generate Gmail app password for Marlin account → store in config

---

## Configuration

`~/.config/marlin/gv_gateway.yml` — not in repo:

```yaml
gmail_address: <marlin gmail>
gmail_app_password: <app password>
personal_email: <jared personal gmail>
inbox_path: /home/jared/Documents/Obsidian/Marlin/Inbox.md
poll_interval_seconds: 60
```

---

## Message Format

```
[word]: [keyword]: [payload]
```

Example: `maple: inbox: pick up heavy cream`

- **word** — today's dictionary key (validated against `~/.config/marlin/gv_gateway.key`)
- **keyword** — route selector (`inbox` in v1)
- **payload** — free text passed to the route handler

Invalid key or malformed message → silent drop. No response to sender.

---

## Daily Key Rotation (`keys.py`)

- Runs at 07:00 via systemd timer
- Selects a random word from `/usr/share/dict/words` filtered to: 5–8 characters, all alphabetic, lowercase first letter (excludes proper nouns)
- Writes word to `~/.config/marlin/gv_gateway.key` (replaces previous)
- Sends email from Marlin Gmail to personal Gmail:
  - Subject: `Marlin Key — YYYY-MM-DD`
  - Body: the word

---

## IMAP Polling (`imap.py`)

- Connects to `imap.gmail.com:993` via SSL using app password
- Searches for unread emails from `@txt.voice.google.com`
- Extracts SMS body: strips everything from `---` onward (GV footer); if no `---` present, uses full body
- Marks email read after processing
- Passes stripped text to `router.py`
- Polls every 60 seconds (configurable)

---

## Routing (`router.py`)

1. Split message on `: ` → `[key, keyword, payload]`
2. Validate key against `~/.config/marlin/gv_gateway.key`
3. Invalid or malformed → drop silently
4. Dispatch by keyword:

| Keyword | Handler |
|---|---|
| `inbox` | Append to Inbox.md + desktop notification |
| *(unknown valid keyword)* | Desktop notification only |

**Inbox handler:** appends `- YYYY-MM-DD HH:MM — [payload]` to Inbox.md at time of receipt.

v2 route stubs (not implemented): `sos`, `ntfy`, `all` (Nextcloud Talk broadcast).

---

## Desktop Notification (`notify.py`)

Thin wrapper around `notify-send`:

```
notify-send "Marlin" "[payload]"
```

Fires on every successfully routed message (including inbox).

---

## Testing

pytest, all external dependencies mocked. No live Gmail connection required.

**`test_imap.py`**
- Parses GV email format correctly
- Strips footer at `---`
- Handles empty inbox gracefully
- Handles malformed email body

**`test_keys.py`**
- Generated word comes from dictionary
- Word length is within 5–8 characters
- Key file is written correctly
- Email is composed with correct subject and body

**`test_router.py`**
- Valid key + `inbox` keyword → appends to Inbox.md + notification
- Valid key + unknown keyword → notification only, no file write
- Invalid key → silent drop
- Malformed message (missing separators) → silent drop

---

## v1 Success Criteria

1. SMS sent to GV number appears in Inbox.md within 60 seconds
2. Desktop notification fires on Gretchen on receipt
3. Daily key email arrives in personal Gmail at 07:00
4. Invalid key messages are silently dropped
5. All tests pass

---

## Out of Scope (v2)

- Twilio outbound SMS (`sos` route)
- Nextcloud Talk broadcast (`all` route)
- Multi-user support (`users.json`, per-user keys)
- Spam protection (failed-attempt counter)
- `ntfy` route
- CP10S as second Obsidian node
