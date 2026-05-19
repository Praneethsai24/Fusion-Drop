#!/usr/bin/env python3
"""
FusionDrop startup script (Python version of start.sh).
Usage:
    python scripts/start.py              # Subsequent run
    python scripts/start.py --first-run  # Full setup from scratch
"""
import sys
import os
import subprocess
import signal
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontgnal
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "front