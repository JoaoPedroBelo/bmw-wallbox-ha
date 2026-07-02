#!/bin/bash
# block-no-verify.sh — Block git commands that bypass the pre-commit / commit-msg hooks

if ! command -v jq &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

[ -z "$COMMAND" ] && exit 0

# Only inspect git commands.
echo "$COMMAND" | grep -q 'git ' || exit 0

if echo "$COMMAND" | grep -qE '\-\-no-verify'; then
  echo "Blocked: --no-verify bypasses the pre-commit and commit-msg hooks (ruff, bandit, hassfest). Remove the flag and fix the underlying issue instead." >&2
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git\s+commit\s.*\b-[a-zA-Z]*n'; then
  echo "Blocked: -n flag on git commit bypasses pre-commit hooks. Remove it and fix the underlying issue instead." >&2
  exit 2
fi

if echo "$COMMAND" | grep -qiE '\-c\s+core\.hookspath'; then
  echo "Blocked: core.hooksPath override bypasses pre-commit hooks. Remove it." >&2
  exit 2
fi

exit 0
