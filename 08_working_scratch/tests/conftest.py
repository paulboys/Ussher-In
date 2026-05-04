import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "pipeline_scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Phase 3b helper scripts (annotation UI, A/B scoring, etc.) live under
# a sibling directory and are imported by some test modules.
PHASE3B_SCRIPTS_DIR = (
    Path(__file__).resolve().parents[1] / "phase3b" / "scripts"
)
if str(PHASE3B_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE3B_SCRIPTS_DIR))
