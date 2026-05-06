# Ariel Naming + Infrastructure Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish correct Ariel naming throughout vault docs and prosper0 codebase, formalize Bazza as a live infrastructure node, and assess/clean up git state across both machines.

**Architecture:** Three phases — (1) vault document cleanup from Gretchen, (2) Bazza infrastructure formalization, (3) prosper0 codebase audit and git cleanup on Bazza. Phases 1–2 can be done from Gretchen; Phase 3 requires the user on Bazza WSL2.

**Tech Stack:** Obsidian vault (flat files), prosper0 orchestrator (WSL2/Bazza), marlin engine (Gretchen, Python), git, GitHub

---

## Naming Convention Reference

Before touching any file, internalize this:

| Term | Correct meaning |
|---|---|
| **Ariel** | The assistant persona — stable across vaults and models |
| **Prosper0** | A future work/job vault (does not exist yet) |
| **Ariel von Marlin** | Current deployment identity — Ariel serving the Marlin vault |
| **Ariel von Prosper0** | Future state — Ariel will serve Prosper0 vault when it's created |
| **prosper0** (lowercase) | The orchestrator codebase directory name — an artifact, not authoritative |
| **The orchestrator** | Ariel's infrastructure component — not "Prosper0's orchestrator" |

---

## Phase 1: Vault Document Cleanup (Gretchen)

### Task 1: Fix Naming in Daily Note

**Files:**
- Modify: `Daily/2026-04-20.md` (line ~53)

- [ ] **Step 1: Read the problematic section**

```bash
grep -n "prosper\|Prosper\|von Prosper" ~/Documents/Obsidian/Marlin/Daily/2026-04-20.md
```

- [ ] **Step 2: Fix the naming**

Find line containing `NAMED: AI assistant is **Ariel von Prosper0**` and correct it to:

```
NAMED: AI assistant is **Ariel** — persona stable across vaults and models.
Current deployment: **Ariel von Marlin**.
Future work deployment (when job + Prosper0 vault exists): **Ariel von Prosper0**.
```

Use the MCP `replace_lines` tool with the exact line numbers from Step 1.

- [ ] **Step 3: Verify**

```bash
grep -n "Prosper0\|von Marlin" ~/Documents/Obsidian/Marlin/Daily/2026-04-20.md
```

Expected: No remaining `Ariel von Prosper0` as current identity.

---

### Task 2: Fix Task Title and Rename Task File

**Files:**
- Modify: `Tasks/implement-desktop-gpu-setup-for-ariel-von-prosper0.md`

- [ ] **Step 1: Read the task file**

```bash
cat -n ~/Documents/Obsidian/Marlin/Tasks/implement-desktop-gpu-setup-for-ariel-von-prosper0.md | head -20
```

- [ ] **Step 2: Update the title frontmatter**

Change `title:` from `Implement desktop GPU setup for Ariel von Prosper0` to `Implement desktop GPU setup for Ariel von Marlin`.

- [ ] **Step 3: Check if status needs updating**

This task is about GPU setup for Bazza — which is now DONE (Ollama is running, Ariel is serving at 10.0.0.78:8742). Check:

```bash
grep -n "^status:\|^completed:" ~/Documents/Obsidian/Marlin/Tasks/implement-desktop-gpu-setup-for-ariel-von-prosper0.md
```

If `status: open` or `status: active`, update to `status: done` and add `completed: 2026-04-30`.

- [ ] **Step 4: Rename the file**

```bash
mv ~/Documents/Obsidian/Marlin/Tasks/implement-desktop-gpu-setup-for-ariel-von-prosper0.md \
   ~/Documents/Obsidian/Marlin/Tasks/implement-desktop-gpu-setup-for-ariel-von-marlin.md
```

- [ ] **Step 5: Scan for backlinks**

```bash
grep -r "implement-desktop-gpu-setup-for-ariel-von-prosper0" ~/Documents/Obsidian/Marlin/ 2>/dev/null
```

Update any backlinks found.

---

### Task 3: Update Hardware/jared-pc.md

**Files:**
- Modify: `Hardware/jared-pc.md`

The current state (confirmed today):
- IP: 10.0.0.78
- Ollama: running natively on Windows at 127.0.0.1:11434 (not Docker)
- Prosper0 orchestrator: running in WSL2 at port 8742
- Portproxy: 0.0.0.0:8742 → 127.0.0.1:8742 (exposes WSL2 service to LAN)
- Ariel von Marlin: live and responding (~17–20s avg response time)

- [ ] **Step 1: Fill in network section**

Set `ip: 10.0.0.78` in frontmatter and fill Network section:
```
- **LAN IP:** 10.0.0.78
- **Hostname:** JARED-PC
```

- [ ] **Step 2: Update Role table**

Add row: `| Ariel infrastructure node | Runs prosper0 orchestrator (WSL2) + Ollama (Windows native) — live Ariel von Marlin deployment |`

Change `role:` in frontmatter from `primary-workstation` to `primary-workstation, ariel-host`.

- [ ] **Step 3: Replace Infrastructure Blockers section**

The NVIDIA Container Toolkit blocker is no longer relevant — Ollama runs natively on Windows (not via Docker/Container Toolkit). Replace the section:

```markdown
## Infrastructure Status (as of 2026-04-30)

- **Ollama:** Running natively on Windows at `127.0.0.1:11434` — GPU acceleration via RTX 3070. Model: `qwen2.5:7b`.
- **Prosper0 orchestrator:** Running in WSL2, listening on port 8742 inside WSL2 network.
- **Windows portproxy:** `0.0.0.0:8742 → 127.0.0.1:8742` — exposes Ariel to LAN. Accessible at `http://10.0.0.78:8742` from any LAN device.
- **Ariel von Marlin:** Live and responding. Avg response time ~17–20s. 10 memory files, 9 skills indexed.

**Note:** NVIDIA Container Toolkit / Docker approach was planned but not used. Ollama runs natively on Windows with direct GPU access — simpler and effective.
```

- [ ] **Step 4: Verify**

```bash
grep -n "fill in\|FILL IN\|Container Toolkit.*not yet" ~/Documents/Obsidian/Marlin/Hardware/jared-pc.md -i
```

Expected: no matches.

---

### Task 4: Fill In bazza-context.md Stub

**Files:**
- Modify: `Hardware/bazza-context.md`

This is a stub with `[FILL IN]` placeholders. Fill based on what we know.

Known values:
- Hostname: `JARED-PC`
- LAN IP: `10.0.0.78`
- GPU: NVIDIA RTX 3070
- Vault path on WSL2: user confirms (likely `/home/jared/Documents/Obsidian/Marlin`)
- Ollama: native Windows, NOT Docker (correct the stub which says Docker)
- Ariel endpoint: `http://10.0.0.78:8742` (via portproxy)

- [ ] **Step 1: Read the full stub**

```bash
cat -n ~/Documents/Obsidian/Marlin/Hardware/bazza-context.md
```

- [ ] **Step 2: Fill in all known values and fix incorrect assumptions**

Replace all `[FILL IN ...]` placeholders. Set `updated: 2026-04-30`.

Fix the Ollama section — it currently says "Ollama runs in Docker". The actual setup:
```markdown
## Ollama / Ariel

- Ollama runs natively on Windows (not Docker) with GPU acceleration via RTX 3070
- Model: qwen2.5:7b
- API endpoint: http://localhost:11434 (loopback, Windows-only)
- Prosper0 orchestrator runs in WSL2, port 8742 (inside WSL2)
- Portproxy exposes Ariel on LAN: http://10.0.0.78:8742
- Start Ollama: it runs as a Windows service (check via Services or Task Manager)
```

- [ ] **Step 3: Update Setup State checkboxes**

Mark as done what is confirmed live:
- [x] WSL2 configured
- [x] Syncthing live
- [x] Claude Code installed (confirmed by current session)
- [x] Ollama running with GPU (RTX 3070)
- [x] Ariel orchestrator endpoint configured (10.0.0.78:8742)

Note: NVIDIA Container Toolkit is NOT installed and NOT needed — remove that checkbox.

- [ ] **Step 4: Delete the stub notice**

Remove the `> **Stub — complete this during Task 3...` block at the top.

- [ ] **Step 5: Verify no [FILL IN] remains**

```bash
grep "\[FILL IN" ~/Documents/Obsidian/Marlin/Hardware/bazza-context.md
```

Expected: no matches.

---

### Task 5: Update Ariel Project Statuses

**Files:**
- Modify: `Projects/ariel-von-marlin-runtime.md`
- Modify: `Projects/ariel-von-marlin-orchestrator.md`
- Modify: `Projects/ariel-von-marlin.md`
- Modify: `Hardware/bazza-setup-plan.md`

The bazza-setup-plan and runtime/orchestrator projects were for getting Bazza to this point. Ariel is now live.

- [ ] **Step 1: Check current status of each file**

```bash
grep -n "^status:\|^completed:\|blocker\|open question" \
  ~/Documents/Obsidian/Marlin/Projects/ariel-von-marlin-runtime.md \
  ~/Documents/Obsidian/Marlin/Projects/ariel-von-marlin-orchestrator.md \
  ~/Documents/Obsidian/Marlin/Projects/ariel-von-marlin.md \
  ~/Documents/Obsidian/Marlin/Hardware/bazza-setup-plan.md -i | head -40
```

- [ ] **Step 2: Update ariel-von-marlin-runtime.md**

If status is `open`: change to `complete` and add `completed: 2026-04-30`. Update any open questions that are now answered:
- GPU inference: resolved (RTX 3070, native Ollama, qwen2.5:7b, ~17–20s)
- Failover question: Gretchen has CPU Ollama fallback

- [ ] **Step 3: Update ariel-von-marlin-orchestrator.md**

If status is `open` and the orchestrator is confirmed running: change to `complete`, add `completed: 2026-04-30`.

- [ ] **Step 4: Update ariel-von-marlin.md**

Add a milestone entry noting Ariel is live on Bazza as of 2026-04-30. Update any in-progress checklist items.

- [ ] **Step 5: Update bazza-setup-plan.md**

The setup plan tasks are all unchecked. Most are now complete. Mark the completed tasks. Add a note at the top:

```markdown
> **Status as of 2026-04-30:** Setup complete. Ariel von Marlin is live on Bazza.
> The actual implementation differed from the plan — Ollama runs natively on Windows
> (not Docker/Container Toolkit). Tasks 4–5 are superseded by the native approach.
```

---

## Phase 2: ADR — Bazza as Infrastructure Node

### Task 6: Write ADR for Bazza Infrastructure Role

**Files:**
- Create: `Decisions/marlin-adr-025-bazza-as-infrastructure-node.md`
- Modify: `~/.claude/decisions/README.md`

Bazza going from "planned GPU host" to "live infrastructure node" is a significant architectural decision that needs an ADR.

- [ ] **Step 1: Read the ADR template**

```bash
cat ~/Documents/Obsidian/Marlin/Decisions/_template.md
```

- [ ] **Step 2: Check the last ADR number**

```bash
ls ~/Documents/Obsidian/Marlin/Decisions/ | grep "marlin-adr" | sort | tail -3
```

Confirm next number is 025 (or adjust).

- [ ] **Step 3: Write the ADR**

Create `Decisions/marlin-adr-025-bazza-as-infrastructure-node.md`:

```markdown
---
title: "ADR-025: Bazza as Live Infrastructure Node"
date: 2026-04-30
status: accepted
project: marlin
---

## Context

Bazza (JARED-PC, RTX 3070) was planned as the GPU inference host for Ariel. As of 2026-04-30, the prosper0 orchestrator is running in WSL2 on Bazza, Ollama is running natively on Windows with GPU acceleration, and Ariel von Marlin is live and serving at 10.0.0.78:8742 via Windows portproxy.

This crossed Bazza from "planned" to "live infrastructure" without a formal decision point, which this ADR captures retroactively.

Key implementation details that differed from the plan:
- Ollama runs natively on Windows (not Docker + NVIDIA Container Toolkit)
- Portproxy (netsh interface portproxy) exposes WSL2 services to the LAN
- No SSH tunnel — LAN access is direct via portproxy

## Decision

Bazza is a live infrastructure node for the Marlin homestack. It must be treated with the same operational care as Gretchen:
- Changes to prosper0 on Bazza are production changes
- Bazza must be in scope for quarterly prosthetics audits
- The prosper0 codebase on Bazza needs version control

## Consequences

**Enables:**
- GPU-accelerated Ariel inference (~17–20s response time vs Gretchen CPU)
- Ariel accessible from any LAN device at 10.0.0.78:8742

**Forecloses:**
- Treating Bazza as a "scratch" dev machine — it now has live state that matters

**Requires:**
- Version control on prosper0 codebase (see Phase 3 of cleanup plan)
- Bazza included in quarterly prosthetics audit scope
- Failover behavior documented: Gretchen CPU Ollama is the fallback when Bazza is off
```

- [ ] **Step 4: Add to ADR index**

```bash
echo "- marlin-adr-025-bazza-as-infrastructure-node.md — Bazza formalized as live infrastructure node (Ariel von Marlin, portproxy, native Ollama)" >> ~/.claude/decisions/README.md
```

---

## Phase 3: Prosper0 Codebase Audit on Bazza

> **Note:** These tasks run on Bazza WSL2. The user must execute them there. They cannot be run remotely from Gretchen (SSH into Bazza WSL2 is not available).

### Task 7: Discover Prosper0 Codebase

- [ ] **Step 1: Find the prosper0 directory in WSL2**

In Bazza WSL2:
```bash
find ~ -maxdepth 4 -name "*.py" -path "*prosper*" 2>/dev/null | head -20
ls ~/prosper0 2>/dev/null || find ~ -maxdepth 3 -type d -name "prosper*" 2>/dev/null
```

- [ ] **Step 2: Check for git repo**

```bash
cd ~/prosper0 && git status 2>&1
# Or wherever the orchestrator lives:
git -C ~/prosper0 status 2>&1
```

Expected outcomes:
- **Has git, clean:** note remote URL (`git remote -v`)
- **Has git, dirty:** note what's uncommitted
- **No git:** proceed to Task 9 (initialize git)

- [ ] **Step 3: Map the codebase structure**

```bash
find ~/prosper0 -type f -name "*.py" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" -o -name "*.md" | grep -v __pycache__ | sort
```

Report the file list — this determines what naming issues to fix.

- [ ] **Step 4: Check for naming issues**

```bash
grep -rn "Ariel von Prosper0\|ariel-von-prosper0\|prosper0 orchestrator" ~/prosper0 --include="*.py" --include="*.yaml" --include="*.yml" --include="*.md" --include="*.json" -i
```

List every match — these are candidates for renaming.

---

### Task 8: Fix Naming in Prosper0 Codebase

**Context:** The correct naming is Ariel von Marlin (current). "Ariel von Prosper0" is only valid as a reference to the future work vault deployment.

- [ ] **Step 1: Fix system prompt / identity config**

Look for any config file or Python string that declares Ariel's identity. Common locations:
- `config.yaml`, `config.json`, or similar
- A `SYSTEM_PROMPT` constant in a Python file
- A `persona.md` or `identity.md` file

Find and update any incorrect `Ariel von Prosper0` → `Ariel von Marlin` references that describe the current running instance.

- [ ] **Step 2: Fix README / documentation files**

```bash
grep -n "prosper0\|Prosper0\|von Prosper" ~/prosper0/README.md 2>/dev/null
```

Update README to reflect:
- Ariel is the assistant persona
- This orchestrator serves the Marlin vault → "Ariel von Marlin"
- Prosper0 is a future vault concept, not the identity of this deployment

- [ ] **Step 3: Commit naming fixes**

```bash
git add -A
git commit -m "fix: correct Ariel naming convention — Ariel von Marlin for current deployment"
```

---

### Task 9: Initialize Git for Prosper0 (if missing)

> Skip this task if Task 7 Step 2 confirmed git already exists.

- [ ] **Step 1: Initialize**

```bash
cd ~/prosper0
git init
```

- [ ] **Step 2: Create .gitignore**

```bash
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.env
*.log
*.db
state.json
.venv/
venv/
node_modules/
EOF
```

- [ ] **Step 3: Initial commit**

```bash
git add -A
git status  # review what's being committed — exclude secrets, state files
git commit -m "feat: initial commit — Ariel von Marlin orchestrator"
```

- [ ] **Step 4: Create GitHub repo and push**

```bash
gh repo create JaredMAllison/ariel-orchestrator --private --source=. --remote=origin --push
```

Or use the GitHub web UI to create `JaredMAllison/ariel-orchestrator` (private), then:

```bash
git remote add origin git@github.com:JaredMAllison/ariel-orchestrator.git
git push -u origin main
```

---

## Phase 4: Marlin Engine Git Cleanup (Gretchen)

### Task 10: Review and Commit Unstaged Marlin Engine Work

**Files (from git status on 2026-04-30):**
- Unstaged: `state.json` (runtime state — do NOT commit)
- Untracked: `build_prompt.py`, `orchestrator.py`, `webhook.txt`, `docs/superpowers/plans/2026-04-24-project-dashboard.md`, `docs/superpowers/specs/`

- [ ] **Step 1: Review each untracked file**

```bash
cd ~/marlin
cat build_prompt.py
cat orchestrator.py
cat webhook.txt
```

Determine: is each file (a) finished and worth committing, (b) work in progress, or (c) scratch/noise?

- [ ] **Step 2: Add .gitignore entry for state.json if missing**

```bash
grep "state.json" ~/marlin/.gitignore 2>/dev/null || echo "state.json" >> ~/marlin/.gitignore
```

- [ ] **Step 3: Commit what's ready**

For each file determined to be complete in Step 1:

```bash
cd ~/marlin
git add <specific-file>
git commit -m "<type>: <description>"
```

Do NOT do `git add -A` — be selective. Do NOT commit `state.json`, secrets, or scratch files.

- [ ] **Step 4: Push**

```bash
git push origin main
```

- [ ] **Step 5: Update plan files**

The plan at `docs/superpowers/plans/2026-04-24-project-dashboard.md` is untracked. Commit it with the other docs:

```bash
git add docs/
git commit -m "docs: add project dashboard plan and specs"
git push origin main
```

---

## Self-Review

**Spec coverage check:**
- [x] Ariel naming fixed in vault docs (Tasks 1–2)
- [x] Bazza hardware docs updated to reflect live state (Tasks 3–4)
- [x] Ariel project statuses updated (Task 5)
- [x] ADR written for Bazza infrastructure decision (Task 6)
- [x] Prosper0 codebase audited and naming fixed (Tasks 7–8)
- [x] Git initialized on prosper0 if missing (Task 9)
- [x] Marlin engine git cleaned up (Task 10)
- [x] Bazza confirmed as infrastructure node in scope for audits

**Access note:** Tasks 7–9 require Bazza WSL2 access. The user must run these directly on Bazza — they cannot be executed from Gretchen via SSH.
