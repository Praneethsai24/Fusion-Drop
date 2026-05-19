#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# FusionDrop Startup Script
# Usage:
#   bash scripts/start.sh              # Subsequent run (venv already exists)
#   bash scripts/start.sh --first-run  # First run (full setup from scratch)
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
ENV_FILE="$BACKEND_DIR/.env"
FIRST_RUN=false

# ── Parse arguments ───────────────────────────────────────────────────────────
for arg in "$@"; do
  [[ "$arg" == "--first-run" ]] && FIRST_RUN=true
done

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[FusionDrop]${NC} $*"; }
warning() { echo -e "${YELLOW}[FusionDrop]${NC} $*"; }
error()   { echo -e "${RED}[FusionDrop]${NC} $*"; exit 1; }

# ── First-run setup ───────────────────────────────────────────────────────────
if [[ "$FIRST_RUN" == "true" ]]; then
  info "=== First-Run Setup ==="

  # Check Python
  command -v python3 >/dev/null 2>&1 || error "Python 3.11+ required. Install from https://python.org"
  PY_VER=$(python3 -c "import sys; print(sys.version_info.minor)")
  [[ $PY_VER -ge 11 ]] || error "Python 3.11+ required (found 3.$PY_VER)"

  # Check Node
  command -v node >/dev/null 2>&1 || error "Node.js 20+ required. Install from https://nodejs.org"
  command -v npm  >/dev/null 2>&1 || error "npm not found. Install Node.js from https://nodejs.org"

  # Create venv
  info "Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"

  # Install backend deps
  info "Installing backend dependencies (this may take 2-3 minutes)..."
  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip --quiet
  pip install -r "$BACKEND_DIR/requirements.txt" --quiet
  info "Backend dependencies installed."

  # Create .env if missing
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
    warning ".env created from .env.example — review and update SECRET_KEY before production."
  fi

  # Install frontend deps
  info "Installing frontend dependencies..."
  cd "$FRONTEND_DIR" && npm install --silent
  info "Frontend dependencies installed."

  info "=== First-Run Setup Complete ==="
fi

# ── Activate venv ─────────────────────────────────────────────────────────────
[[ -d "$VENV_DIR" ]] || error "Virtual environment not found. Run: bash scripts/start.sh --first-run"
source "$VENV_DIR/bin/activate"

# ── Start backend ─────────────────────────────────────────────────────────────
info "Starting backend on http://localhost:8000 ..."
cd "$REPO_ROOT"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# ── Start frontend ────────────────────────────────────────────────────────────
info "Starting frontend on http://localhost:5173 ..."
cd "$FRONTEND_DIR" && npm run dev &
FRONTEND_PID=$!

info "Both services started."
info "  Backend API:  http://localhost:8000"
info "  API Docs:     http://localhost:8000/docs"
info "  Frontend:     http://localhost:5173"
info "Press Ctrl+C to stop both services."

# ── Graceful shutdown ─────────────────────────────────────────────────────────
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; info 'Services stopped.'" EXIT INT TERM
wait $BACKEND_PID $FRONTEND_PID