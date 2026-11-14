#!/bin/bash
# ───────────────────────────────────────────────────────────
#  Outreach tool installer (macOS). Double-click me.
#  If macOS blocks it: System Settings > Privacy & Security > "Open Anyway".
#  Safe to run again to update; it keeps your settings, history and Outlook sign-in.
# ───────────────────────────────────────────────────────────
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/OutreachTool"
PY="$DEST/.venv/bin/python"
clear
echo "Installing the outreach tool into $DEST"
echo

# 1. Python (comes with Apple's free developer tools)
if ! xcode-select -p >/dev/null 2>&1 && [ ! -x /opt/homebrew/bin/python3 ] && [ ! -x /usr/local/bin/python3 ]; then
  echo "Your Mac needs Apple's free developer tools first."
  echo "A window will pop up: click Install and wait until it finishes (5-10 min)."
  echo "Then double-click Setup again."
  xcode-select --install 2>/dev/null || true
  read -r -p "Press Enter to close this window." _
  exit 0
fi
PYTHON="$(command -v /opt/homebrew/bin/python3 || command -v /usr/local/bin/python3 || command -v python3)"
echo "[1/4] Python found: $("$PYTHON" --version)"

# 2. Copy the tool (never overwrites your config.yaml, history, or sign-in)
mkdir -p "$DEST/batches" "$DEST/review"
cp "$SRC/outreach.py" "$SRC/outlook_web.py" "$SRC/requirements.txt" "$SRC/config.example.yaml" "$DEST/"
echo "[2/4] Files copied"

# 3. Libraries
[ -x "$PY" ] || "$PYTHON" -m venv "$DEST/.venv"
"$PY" -m pip install -q --disable-pip-version-check --upgrade pip
"$PY" -m pip install -q --disable-pip-version-check -r "$DEST/requirements.txt"
if [ ! -d "/Applications/Google Chrome.app" ]; then
  echo "      (Google Chrome not found: downloading a private browser for Outlook, ~150 MB)"
  "$PY" -m playwright install chromium
fi
echo "[3/4] Libraries installed"

# 4. Teach Claude the /outreach command and pre-approve the tool's own actions
mkdir -p "$HOME/.claude/skills/outreach"
sed -e "s#{{TOOL_DIR}}#$DEST#g" -e "s#{{PY}}#$PY#g" "$SRC/skill/SKILL.md" > "$HOME/.claude/skills/outreach/SKILL.md"
"$PY" - "$DEST" "$PY" <<'EOF'
import json, sys, pathlib
dest, py = sys.argv[1], sys.argv[2]
path = pathlib.Path.home() / ".claude" / "settings.json"
try:
    settings = json.loads(path.read_text())
except (FileNotFoundError, ValueError):
    settings = {}
allow = settings.setdefault("permissions", {}).setdefault("allow", [])
for rule in [f"Bash({py} {dest}/outreach.py:*)", f"Bash({py} {dest}/outlook_web.py:*)", "WebSearch",
             "Read(~/OutreachTool/**)", "Write(~/OutreachTool/batches/**)", "Edit(~/OutreachTool/batches/**)",
             "Write(~/OutreachTool/config.yaml)", "Edit(~/OutreachTool/config.yaml)"]:
    if rule not in allow:
        allow.append(rule)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(settings, indent=2))
EOF
echo "[4/4] /outreach command added to Claude"

echo
echo "All set! Open the Claude app, go to the Code tab and type /outreach."
echo "The first time, Claude will ask you a few questions to set things up."
read -r -p "Press Enter to close this window." _
