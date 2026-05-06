# Marlin — Setup Guide

Fresh machine installation for the Marlin task surfacing engine.

---

## Prerequisites

- Linux (tested on Linux Mint)
- Python 3.12+
- `python3-yaml` (usually pre-installed; `sudo apt install python3-pip` if needed)
- systemd user services enabled
- Git + GitHub CLI (`gh`) configured
- Ntfy Android app installed, subscribed to your topic

---

## 1. Clone the repo

```bash
git clone git@github.com:JaredMAllison/marlin.git ~/marlin
cd ~/marlin
chmod +x marlin.py webhook.py set-mode.sh
```

---

## 2. Verify PyYAML

```bash
python3 -c "import yaml; print('ok')"
```

If it fails: `sudo apt install python3-pip && python3 -m pip install pyyaml --break-system-packages`

---

## 3. Create the Obsidian vault

Create the folder structure:

```bash
mkdir -p ~/Documents/Obsidian/Marlin/{Tasks,Projects,Daily}
```

Create the Inbox note:

```bash
echo "# Inbox" > ~/Documents/Obsidian/Marlin/Inbox.md
```

Open Obsidian → Open vault → select `~/Documents/Obsidian/Marlin`.

---

## 4. Create state.json

```bash
echo '{"mode": "available"}' > ~/marlin/state.json
```

This file is not tracked in git — create it manually on each machine.

---

## 5. Update config values

Edit `marlin.py` and `webhook.py` — update these at the top of each file:

| Variable | Description |
|---|---|
| `VAULT` | Path to your Tasks folder |
| `WEBHOOK_BASE` | `http://<your-machine-ip>:7832` |

Find your IP: `hostname -I | awk '{print $1}'`

---

## 6. Install systemd services

Create `~/.config/systemd/user/marlin.service`:

```ini
[Unit]
Description=Marlin task surfacing engine
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/YOUR_USER/marlin/marlin.py
Environment="MARLIN_NTFY_TOPIC=your-ntfy-topic"
Environment="MARLIN_WEBHOOK_BASE=http://YOUR_IP:7832"
StandardOutput=journal
StandardError=journal
```

Create `~/.config/systemd/user/marlin.timer`:

```ini
[Unit]
Description=Run Marlin every 15 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Unit=marlin.service

[Install]
WantedBy=timers.target
```

Create `~/.config/systemd/user/marlin-webhook.service`:

```ini
[Unit]
Description=Marlin webhook server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/YOUR_USER/marlin/webhook.py
Environment="MARLIN_NTFY_TOPIC=your-ntfy-topic"
Environment="MARLIN_WEBHOOK_BASE=http://YOUR_IP:7832"
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

---

## 7. Enable and start services

```bash
systemctl --user daemon-reload
systemctl --user enable --now marlin.timer
systemctl --user enable --now marlin-webhook.service
```

---

## 8. Verify

```bash
# Check timer
systemctl --user status marlin.timer

# Check webhook
systemctl --user status marlin-webhook.service

# Test surfacing manually
cd ~/marlin && MARLIN_NTFY_TOPIC=your-ntfy-topic python3 marlin.py

# Test webhook
curl http://localhost:7832/
```

---

## 9. Bookmark the mode UI

On your Android phone, open Chrome and navigate to `http://YOUR_IP:7832`. Tap the three-dot menu → Add to Home Screen.

---

## Ntfy topic

The Ntfy topic is set in both service files as `MARLIN_NTFY_TOPIC`. The current topic is `jared-surface-8n3p`. Subscribe to it in the Ntfy Android app.

When WireGuard is configured, update `MARLIN_WEBHOOK_BASE` to your WireGuard IP so actions work off home WiFi.

---

## Claude Code skills

Install the companion skills by copying the skill directories to `~/.claude/skills/`:

- `obsidian-enrich/` — structured enrichment sessions
- `marlin-capture/` — quick task capture

These are stored separately in `~/.claude/skills/` (not in this repo).
