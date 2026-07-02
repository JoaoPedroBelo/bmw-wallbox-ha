#!/bin/bash
# lint-on-edit.sh — Run `ruff check` after editing a Python file
# Reports only issues in the edited file to avoid noise. Non-blocking (advisory).

if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[ -z "$FILE_PATH" ] && exit 0

case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;
esac

RUFF=""
if [ -x "$CLAUDE_PROJECT_DIR/.venv/bin/ruff" ]; then
  RUFF="$CLAUDE_PROJECT_DIR/.venv/bin/ruff"
elif command -v ruff &>/dev/null; then
  RUFF="ruff"
else
  exit 0
fi

# --quiet suppresses the summary line; --output-format=concise keeps it terse.
OUTPUT=$("$RUFF" check "$FILE_PATH" --quiet --output-format=concise 2>/dev/null)

if [ -n "$OUTPUT" ]; then
  echo "Ruff issues in $(basename "$FILE_PATH") (run 'make fix' to auto-fix what's safe):" >&2
  echo "$OUTPUT" | head -15 >&2
fi

exit 0
