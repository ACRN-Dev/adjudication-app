#!/usr/bin/env bash
# POSIX/Git-Bash helper to activate a virtual environment.
# Usage: source scripts/activate_venv.sh
# Note: the script should be sourced (not executed) to affect the current shell:
#   source scripts/activate_venv.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
  # typical POSIX venv
  source "$PROJECT_ROOT/venv/bin/activate"
  echo "Activated virtual environment from venv/bin/activate"
elif [ -f "$PROJECT_ROOT/venv/Scripts/activate" ]; then
  # Git Bash on Windows
  source "$PROJECT_ROOT/venv/Scripts/activate"
  echo "Activated virtual environment from venv/Scripts/activate"
else
  echo "Virtual environment activate script not found. Expected venv/bin/activate or venv/Scripts/activate"
  return 1 2>/dev/null || exit 1
fi
