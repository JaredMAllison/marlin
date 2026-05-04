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

# ── 8. Reload systemd for the user ────────────────────────────────────
sudo -u "$USERNAME" XDG_RUNTIME_DIR="/run/user/$(id -u $USERNAME)" systemctl --user daemon-reload

echo ""
echo "==> Setup complete for $USERNAME"
echo "Next steps:"
echo "  1. Set up Jason's Cockpit: cp -r /home/jared/git/cockpit /home/$USERNAME/git/ && chown -R $USERNAME:$USERNAME /home/$USERNAME/git/cockpit"
echo "  2. Add WireGuard peer (see onboard_jason.sh)"
echo "  3. Run: sudo bash $MARLIN_SRC/onboard_jason.sh"
