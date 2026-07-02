---
description: Load the most recent session file and resume work with full context from where the last session ended.
---

# Resume Session

Load the last saved session and orient before doing any work.

## Process

### Step 1: Find the session file

If no argument: pick the most recently modified `*-session.md` in `~/.claude/session-data/`.
If $ARGUMENTS is a date (YYYY-MM-DD): find the matching file.
If $ARGUMENTS is a path: read it directly.
If none found: report and stop.

### Step 2: Read the entire file

### Step 3: Show structured briefing

```
SESSION LOADED: [path]

PROJECT: [name / topic]

WHAT WE'RE BUILDING:
[2-3 sentence summary]

CURRENT STATE:
  Working:     [count] confirmed
  In Progress: [list]
  Not Started: [list]

WHAT NOT TO RETRY:
  [failed approaches with reasons]

BLOCKERS:
  [blockers or open questions]

NEXT STEP:
  [exact next step from session file]

Ready to continue. What would you like to do?
```

### Step 4: Wait for the user

Do NOT start working. Do NOT touch files. Wait for direction.

## Edge Cases

- File references missing files: add WARNING.
- File older than 7 days: add WARNING.
- Empty/malformed: suggest `/save-session`.

## Arguments

$ARGUMENTS — optional date (YYYY-MM-DD) or file path.
