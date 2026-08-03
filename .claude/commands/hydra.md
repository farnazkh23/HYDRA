Read AGENT_WORKFLOW.md. Read TASK_CURRENT.md, or use the task described in
$ARGUMENTS instead of TASK_CURRENT.md if arguments were given.

`/hydra` is a terminal-state runner: inspect, plan, get one approval, then run
autonomously to completion. Follow the HYDRA workflow exactly:

1. Inspect first — read every file listed under "Files to inspect", check
   `git status --short` and `git --no-pager diff` to see what's already in flight.
2. Present one short plan: goal, exact files to change, exact validation to run.
   If the task would push to `main`, say so in the plan. Nothing else until approved.
3. Ask for one explicit approval before making any edit.
4. Once approved, continue autonomously without stopping after each successful
   step: edit -> validation -> targeted manual/API check -> git diff -> commit
   -> push. Do not pause for confirmation between these steps.
5. Stop only by reporting exactly one terminal state as the last line of your
   response:
   - `DONE_PUSHED`
   - `DONE_NOT_COMMITTED`
   - `BLOCKED_NEEDS_DECISION`
   - `FAILED_WITH_ERROR`
   - `UNSAFE_STOPPED`

Safety rules:
- Never read `.env` or secrets.
- Never touch `data/`, `.venv/`, `node_modules/`, `dist/`.
- Never add dependencies unless explicitly requested.
- Never edit files outside the approved scope.
- Never commit untracked files unless they are part of the approved scope.
- Use Windows PowerShell commands only.
- Use `git --no-pager` for diffs.
- Always run `scripts/check.ps1` if available.
- For frontend tasks, also run `cd frontend; npm run build`.
- For backend API tasks, run a targeted `Invoke-RestMethod` check if the
  backend is running, otherwise explain the manual check was skipped and why.
- Before committing, show `git --no-pager diff --stat` and `git status --short`.
- Commit/push only if validation passed and the changed files match the
  approved scope exactly.

Use Sonnet for normal HYDRA coding tasks.
