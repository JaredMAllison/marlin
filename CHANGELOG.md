# Marlin Changelog

## [Unreleased]

### Planned
- Nextcloud shared key file distribution
- `sos` route handler (Twilio outbound + Nextcloud Talk)
- `ntfy` route handler (direct push to user's ntfy topic)

---

## [v1.2.0] — 2026-04-12

### Added
- `gv_gateway/users.py` — `User` dataclass and `load_users()` from `~/.config/marlin/users.json`
- `~/.config/marlin/users.json` — per-user config: key file path, email, broadcast_name, ntfy_topic, allowed routes
- `~/.keys/` — per-user key files with 0o700 directory and 0o600 file permissions
- Multi-user routing: router identifies sender by key file match, enforces per-user route restrictions
- Sender identity in inbox entries: `[Jared (SMS)]` prefix on all SMS-sourced inbox appends
- Sender label in desktop notifications: `payload (from Family)` for non-null broadcast_name
- Keyword directory email: keygen sends each user a per-route command reference showing only their allowed routes
- Route access control: users can only invoke routes explicitly listed in their profile (silent drop otherwise)
- 24 new tests (users, keygen, router multi-user, keys directory)

### Changed
- `email_key()` signature: now accepts `User` instead of `config` for recipient — sends to `user.email`, builds route-specific body
- `keygen.run()`: loops all users, generates per-user key, skips email for users with `email: null`
- Key files moved from `~/.config/marlin/gv_gateway.key` to `~/.keys/<user_id>.key`

---

## [v1.1.0] — 2026-04-12

### Added
- `gv_gateway` Python package — IMAP polling service for inbound SMS via Google Voice
- `gv_gateway.imap` — fetches unseen messages from `marlin.exobrain@gmail.com`, extracts plain-text body, marks as read
- `gv_gateway.router` — parses `key: keyword: payload` format (line-by-line scan), authenticates via daily key, routes to handler
- `gv_gateway.keys` — reads daily key from `~/.config/marlin/gv_gateway.key`
- `gv_gateway.keygen` — generates a new English-word key each morning, writes to key file, distributes via SMTP
- `gv_gateway.notify` — sends ntfy push notifications on successful route
- `gv_gateway.config` — loads config from `~/.config/marlin/gv_gateway.yml`
- `gv-gateway.service` — systemd user service; polls every 60s, restarts on failure
- `inbox` keyword handler — appends timestamped payload to `Inbox.md`
- Per-sender failed-attempt counter with ntfy alert on threshold breach (5 failures / 10 min)
- 26 passing tests across all modules

### Fixed
- Body parser now scans line-by-line — GV plain-text emails prepend `<https://voice.google.com>` before SMS text, which corrupted key extraction when parsing the full body as a single string

### Infrastructure
- Gmail filter: `jared.allison@gmail.com` forwards `@txt.voice.google.com` messages to `marlin.exobrain@gmail.com`
- GV forwarding confirmed live to personal Gmail

---

## [v1.0.0] — 2026-04-05

### Added
- `marlin.py` — surfacing engine; reads vault Tasks, filters by mode/context/date, sends one ntfy notification per run
- `webhook.py` — HTTP server on port 7832; handles Done/Defer/Snooze actions and mode switching
- `set-mode.sh` — CLI shortcut for mode updates
- `state.json` — runtime state (mode, snooze tracking)
- systemd user services for marlin timer and webhook server
- ntfy notification with Done/Defer/Snooze action buttons
- `available_from` field support — tasks surface on a separate schedule from their deadline
- Snooze enforcement via `snooze_until` in state.json
