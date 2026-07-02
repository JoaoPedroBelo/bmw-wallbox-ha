#!/bin/bash
# print-debug-warn.sh — Warn about leftover print()/breakpoint() in source files
# Home Assistant integrations must log via `_LOGGER`, never `print()`.

if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[ -z "$FILE_PATH" ] && exit 0

# Only Python files under the integration source (skip tests, scripts, debug server).
case "$FILE_PATH" in
  *custom_components/*.py) ;;
  *) exit 0 ;;
esac

[ ! -f "$FILE_PATH" ] && exit 0

MATCHES=$(grep -nE '(^|[^_.a-zA-Z])(print|breakpoint)\s*\(' "$FILE_PATH" 2>/dev/null | head -5)

if [ -n "$MATCHES" ]; then
  COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')
  echo "Warning: ${COUNT} print()/breakpoint() call(s) in $(basename "$FILE_PATH"):" >&2
  echo "$MATCHES" >&2
  echo "Use '_LOGGER.debug/info/warning/error(...)' instead. Remove before committing." >&2
fi

exit 0
