#!/usr/bin/env bash
# setup_jason_instance.sh — idempotent setup for a new LMF user on Gretchen
# Usage: sudo bash setup_jason_instance.sh [username]
# Default username: jason
set -euo pipefail

USERNAME="${1:-jason}"
MARLIN_SRC="/home/jared/marlin"
VAULT_ROOT="/home/$USERNAME/marlin"
GIT_DIR="/home/$USERNAME/git"

echo "==> Setting up LMF instance for: $USERNAME"

# ── 1. Create system user ──────────────────────────────────────────────
if ! id "$USERNAME" &>/dev/null; then
  echo "--> Creating user $USERNAME"
  sudo useradd -m -s /bin/bash "$USERNAME"
else
  echo "--> User $USERNAME already exists, skipping"
fi

# ── 2. Enable systemd user services (linger) ──────────────────────────
sudo loginctl enable-linger "$USERNAME"

# ── 3. Seed vault ─────────────────────────────────────────────────────
echo "--> Seeding vault at $VAULT_ROOT"
sudo -u "$USERNAME" bash "$MARLIN_SRC/seed_vault.sh" "$USERNAME"

# ── 4. Write .env ─────────────────────────────────────────────────────
echo "--> Writing /home/$USERNAME/.env"
sudo -u "$USERNAME" tee "/home/$USERNAME/.env" > /dev/null << EOF
# LMF instance env for $USERNAME
MARLIN_VAULT_PATH=$VAULT_ROOT/Tasks
MARLIN_VAULT_ROOT=$VAULT_ROOT
MARLIN_STATE_FILE=/home/$USERNAME/marlin-state/state.json
MARLIN_WEBHOOK_PORT=7842
MARLIN_DASHBOARD_PORT=7843
MARLIN_NTFY_TOPIC=
MARLIN_WEBHOOK_BASE=http://10.0.0.8:7842
EOF

# ── 5. Create state dir ────────────────────────────────────────────────
sudo -u "$USERNAME" mkdir -p "/home/$USERNAME/marlin-state"
sudo -u "$USERNAME" bash -c "echo '{\"mode\":\"available\",\"last_surfaced_task\":null,\"last_surfaced_at\":null}' > /home/$USERNAME/marlin-state/state.json"

# ── 6. Create git/cockpit dir ─────────────────────────────────────────
sudo -u "$USERNAME" mkdir -p "$GIT_DIR"

# ── 7. Install systemd user unit files ────────────────────────────────
UNIT_DIR="/home/$USERNAME/.config/systemd/user"
sudo -u "$USERNAME" mkdir -p "$UNIT_DIR"

echo "--> Installing systemd user units"

sudo -u "$USERNAME" tee "$UNIT_DIR/marlin-webhook.service" > /dev/null << EOF
[Unit]
Description=Marlin Webhook — $USERNAME instance
After=network.target

[Service]
Type=simple
EnvironmentFile=/home/$USERNAME/.env
ExecStart=/usr/bin/python3 $MARLIN_SRC/webhook.py
WorkingDirectory=$MARLIN_SRC
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

sudo -u "$USERNAME" tee "$UNIT_DIR/marlin-project-dashboard.service" > /dev/null << EOF
[Unit]
Description=Marlin Project Dashboard — $USERNAME instance
After=network.target

[Service]
Type=simple
EnvironmentFile=/home/$USERNAME/.env
ExecStart=/usr/bin/python3 $MARLIN_SRC/project_dashboard.py
WorkingDirectory=$MARLIN_SRC
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

sudo -u "$USERNAME" tee "$UNIT_DIR/marlin-cockpit.service" > /dev/null << EOF
[Unit]
Description=Marlin Cockpit — $USERNAME instance
After=network.target

[Service]
Type=simple
Environment=COCKPIT_PORT=9101
ExecStart=/usr/bin/python3 /home/$USERNAME/git/cockpit/cockpit.py
WorkingDirectory=/home/$USERNAME/git/cockpit
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

# ── 8. Copy cockpit + write instance-specific api.js ─────────────────
COCKPIT_SRC="/home/jared/git/cockpit"
COCKPIT_DEST="$GIT_DIR/cockpit"

if [ -d "$COCKPIT_SRC" ]; then
  echo "--> Copying cockpit to $COCKPIT_DEST"
  cp -r "$COCKPIT_SRC" "$COCKPIT_DEST"
  chown -R "$USERNAME:$USERNAME" "$COCKPIT_DEST"

  sudo -u "$USERNAME" tee "$COCKPIT_DEST/hooks/api.js" > /dev/null << 'APIEOF'
// hooks/api.js — fetch wrappers, one function per endpoint
// HOSTS is the only thing that changes between Jared's and Jason's deployments.

const HOSTS = {
  marlin:   'http://10.0.0.8:7842',
  projects: 'http://10.0.0.8:7843',
  ttf:      'http://10.0.0.8:3000',
  ariel:    'http://10.0.0.78:8742',
};

function _fetch(url) {
  return fetch(url).then(r => {
    if (!r.ok) throw new Error(`${r.status} ${r.statusText} — ${url}`);
    return r.json();
  });
}

function fetchState()         { return _fetch(`${HOSTS.marlin}/api/state`); }
function fetchTodayTasks()    { return _fetch(`${HOSTS.marlin}/tasks/today`); }
function fetchAdls()          { return _fetch(`${HOSTS.marlin}/api/adls`); }
function fetchProjects()      { return _fetch(`${HOSTS.projects}/api/projects`); }
function fetchVaultTree()     { return _fetch(`${HOSTS.projects}/api/vault/tree`); }
function fetchVaultFile(path) {
  const url = `${HOSTS.projects}/api/vault/file?path=${encodeURIComponent(path)}`;
  return fetch(url)
    .then(r => {
      if (!r.ok) throw new Error(`${r.status} ${r.statusText} — ${url}`);
      return r.text();
    });
}
function fetchTtfEvents() {
  const d     = new Date();
  const pad   = n => String(n).padStart(2, '0');
  const today = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  const end   = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 7);
  const week  = `${end.getFullYear()}-${pad(end.getMonth()+1)}-${pad(end.getDate())}`;
  return _fetch(`${HOSTS.ttf}/api/events?from=${today}&to=${week}`);
}
function fetchArielTurns() { return Promise.resolve([]); }  // stubbed until Ariel API confirmed
APIEOF
  echo "--> Wrote Jason's api.js (HOSTS → Gretchen :7842/:7843)"
else
  echo "WARNING: $COCKPIT_SRC not found — skipping cockpit copy"
fi

# ── 9. Reload systemd for the user ────────────────────────────────────
sudo -u "$USERNAME" XDG_RUNTIME_DIR="/run/user/$(id -u $USERNAME)" systemctl --user daemon-reload

echo ""
echo "==> Setup complete for $USERNAME"
echo "Next steps:"
echo "  1. Enable + start services:"
echo "     sudo -u $USERNAME XDG_RUNTIME_DIR=/run/user/\$(id -u $USERNAME) systemctl --user enable --now marlin-webhook.service marlin-project-dashboard.service marlin-cockpit.service"
echo "  2. Verify: curl http://localhost:7842/api/state && curl http://localhost:7843/api/projects | head -c 100"
