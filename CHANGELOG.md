# Marlin Changelog

## [Unreleased]

### Added
- `vault.py` — shared vault I/O module: `read_frontmatter`, `update_frontmatter`, `find_tasks`, `find_projects`, `resolve_roadmap_path`, `parse_roadmap`, `compute_completion`, `current_phase`, `top_task` (ADR-023)
- `project_dashboard.py` — HTTP server on port 7833; `/api/projects`, `/api/projects/<slug>`, `/api/vault/tree`, `/api/vault/file` endpoints; CORS on all responses; `MARLIN_VAULT_ROOT` env var (falls back to `MARLIN_VAULT_PATH`, then hardcoded default) (ADR-026)
- `marlin-project-dashboard.service` — systemd user service; project dashboard auto-starts on login
- `dashboard` field added to project schema — P1/P2 projects `true`, P3+ `false`; 36 project files updated
- `setup_jason_instance.sh` — idempotent multi-user deployment script; creates Linux user, enables linger, seeds vault, writes `.env`, installs three systemd services (webhook :7842, project_dashboard :7843, cockpit :9101), copies cockpit repo, writes instance-specific `api.js`
- `seed_vault.sh` — seeds a fresh vault skeleton with the required folder structure and sentinel files for Ariel onboarding
- `webhook.py` — `/api/state` GET endpoint returns current mode/state JSON; `/api/adls` GET endpoint returns due ADL tasks; both with CORS headers; env var config via `MARLIN_WEBHOOK_PORT`
- 4 new tests: `tests/test_dashboard_api.py` (project + vault API), `tests/test_webhook_api.py` (state + adls + port env var)

### Changed
- `webhook.py` — refactored to import `read_frontmatter` and `update_frontmatter` from `vault.py`; duplicate implementations removed
- `webhook.py` — renamed UI from "Marlin" to **Quickhacks** (Cyberpunk 2077 reference); reflects expanded scope beyond mode switching
- `webhook.py` — `done` action now handles recurring tasks: advances `goal_date` via `next_occurrence()` instead of marking `status: done`; non-recurring tasks unchanged
- `webhook.py` — task actions now redirect to `/` on success (302) instead of returning plain text; better phone UX
- `webhook.py` — Self-Care section added to Quickhacks UI: surfaces due ADL tasks as tappable done buttons; powered by `get_due_adls()`
- `webhook.py` — `next_occurrence()`, `get_due_adls()`, `append_adl_log()` added for recurring task and ADL support
- `project_dashboard.py` — symlinks at vault root skipped in tree walk (prevents Claude skills/ and memory/ from being listed); `_text()` responses include CORS header; `parse_qs` moved to top-level import

---

### Added (prior unreleased)
- `webhook.py` — full dashboard page replacing the original mode-only UI
  - Surfaced task card — live on every page load; applies same mode/context/business-hours/available_from filters as marlin.py; decoupled from 15-min Ntfy timer
  - Today's task list grouped by project with dot-notation duration (•/••/•••)
  - Mode buttons (all 5 modes, current dimmed)
  - ADL buttons (Self-Care section)
  - Inbox capture bar fixed to bottom with flash confirmation; captures tagged `· dashboard`
- `webhook.py` — `get_today_tasks()` excludes Self-Care project (covered by ADL section)
- `webhook.py` — `append_inbox()` accepts optional `source` parameter; dashboard passes `"dashboard"`
- `gv-keygen.service` — `Restart=on-failure`, `RestartSec=60s`, 5-retry cap over 10 min; fixes silent miss when network not ready at session start (ADR-019)
- `CLAUDE.md` — naming convention: underscores for Python files/packages, hyphens for systemd unit names

### Planned
- Termux SSH link on dashboard
- Done/defer/snooze action buttons on surfaced task card
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
