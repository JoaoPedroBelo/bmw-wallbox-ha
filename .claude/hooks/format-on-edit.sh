#!/bin/bash
# format-on-edit.sh — Auto-format Python files after Claude edits them
# Runs `ruff format` on the edited file to keep formatting consistent with CI.

if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[ -z "$FILE_PATH" ] && exit 0

# Only format Python files.
case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;
esac

# Resolve ruff: prefer the project venv, fall back to PATH.
RUFF=""
if [ -x "$CLAUDE_PROJECT_DIR/.venv/bin/ruff" ]; then
  RUFF="$CLAUDE_PROJECT_DIR/.venv/bin/ruff"
elif command -v ruff &>/dev/null; then
  RUFF="ruff"
else
  exit 0
fi

"$RUFF" format "$FILE_PATH" 2>/dev/null

exit 0
