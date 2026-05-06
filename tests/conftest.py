import sys
from pathlib import Path

# Add the worktree root to sys.path so that vault.py and other modules
# in the worktree are importable when pytest is invoked from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))
