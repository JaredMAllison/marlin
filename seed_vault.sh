#!/usr/bin/env bash
# seed_vault.sh — create a minimal vault skeleton for a new LMF user
# Called by setup_jason_instance.sh
# Usage: bash seed_vault.sh <username>
set -euo pipefail

USERNAME="${1:?username required}"
VAULT="/home/$USERNAME/marlin"

mkdir -p \
  "$VAULT/Tasks" \
  "$VAULT/Projects" \
  "$VAULT/Insights" \
  "$VAULT/Daily" \
  "$VAULT/Learning" \
  "$VAULT/Essays" \
  "$VAULT/People" \
  "$VAULT/System" \
  "$VAULT/Projects/Feature Requests"

# JASON.md stub — operator spec, intentionally empty
if [ ! -f "$VAULT/JASON.md" ]; then
  cat > "$VAULT/JASON.md" << 'EOF'
---
title: Operator Spec
type: operator-spec
created: CREATED_DATE
---

# Operator

*This file is filled in during the first conversation with your assistant.*

EOF
  sed -i "s/CREATED_DATE/$(date +%Y-%m-%d)/" "$VAULT/JASON.md"
fi

# Inbox.md
if [ ! -f "$VAULT/Inbox.md" ]; then
  cat > "$VAULT/Inbox.md" << 'EOF'
# Inbox

*Unprocessed thoughts and tasks. Your assistant will help you sort these.*

EOF
fi

# Starter task — the only pre-written content, intentionally inviting
if [ ! -f "$VAULT/Tasks/first-session.md" ]; then
  cat > "$VAULT/Tasks/first-session.md" << EOF
---
title: First session with your assistant
status: queued
created: $(date +%Y-%m-%d)
---

Tell your assistant what's been hard lately.
EOF
fi

# .vault_fresh sentinel — tells Ariel to run onboarding mode
echo "fresh_instance=true" > "$VAULT/.vault_fresh"

echo "--> Vault seeded at $VAULT"
