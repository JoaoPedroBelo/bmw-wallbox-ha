#!/bin/bash
# protect-files.sh — Block edits to sensitive/generated files
# Prevents Claude from modifying files that should never be touched by an edit tool.

# Require jq for JSON parsing
if ! command -v jq &>/dev/null; then
  echo "Warning: jq not found, skipping file protection check." >&2
  exit 0
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Secrets, private keys, virtualenvs, caches and VCS internals.
PROTECTED_PATTERNS=(
  ".env"
  ".env.local"
  ".env.production"
  "privkey.pem"
  "id_rsa"
  ".git/"
  ".venv/"
  "venv/"
  "__pycache__/"
  ".mypy_cache/"
  ".ruff_cache/"
  ".pytest_cache/"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH matches protected pattern '$pattern'. This file should not be modified by Claude." >&2
    exit 2
  fi
done

# Any private-key-looking file (*.key), regardless of directory.
case "$FILE_PATH" in
  *.key)
    echo "Blocked: $FILE_PATH looks like a private key. Secrets must not be edited by Claude." >&2
    exit 2
    ;;
esac

exit 0
