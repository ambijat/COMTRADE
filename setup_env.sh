#!/usr/bin/env bash
# UN Comtrade R7 Reconstruction — environment bootstrap
# Run this once per machine or after the venv is lost.
# Usage:
#   chmod +x setup_env.sh
#   ./setup_env.sh
#
# NOTE: uses --copies because this project lives on a mounted
# filesystem (/media/...) that does not allow symlinks.
# Do NOT use plain  python3 -m venv .venv  here.

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "Project: $PROJECT_DIR"

if [ -d "$VENV_DIR" ] && [ -x "$VENV_DIR/bin/python" ]; then
    echo "venv already exists and is executable — skipping creation."
else
    echo "Creating venv with --copies (required on mounted filesystems)..."
    rm -rf "$VENV_DIR"
    python3 -m venv --copies "$VENV_DIR"
    echo "venv created."
fi

echo "Installing dependencies from requirements.txt..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

echo ""
echo "Environment ready. To activate:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run the builder:  python comtrade_panel_builder.py"
echo "To open the GUI:     python comtrade_panel_gui.py"
echo ""
echo "Remember: place your subscription key in:"
echo "  secrets/comtrade_primary_key.txt"
