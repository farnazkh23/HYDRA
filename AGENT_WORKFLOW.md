# HYDRA Agent Workflow

Standard process for agent-assisted changes in this repo. Follow these steps in order.

## Default model

Sonnet, unless a task explicitly calls for something else.

## Process

`/hydra` is a terminal-state runner: inspect, plan, get **one** approval, then run
the rest of the workflow to completion without stopping after every successful
step. It only stops early for a real blocker, a failure, or a safety rule.

1. **Inspect first**
   - Read `TASK_CURRENT.md` for the active task, or the task given as command
     arguments if provided instead.
   - Read every file listed under "Files to inspect" before writing any code.
   - Check `git status --short` and `git --no-pager diff` to see what's already
     in flight.

2. **Plan — one approval gate**
   - Present one short plan: the goal, the exact files that will change, and
     the exact validation that will run. Anything not listed is out of scope.
   - If the task would commit and push to `main`, say so explicitly in the plan.
   - Ask for one explicit approval. Do not edit anything before it is given.

3. **Run autonomously to a terminal state**
   Once approved, continue through the rest of the steps without pausing for
   confirmation between them:
   - **Edit** only the files named in the approved plan. Do not refactor,
     rename, or "clean up" unrelated code. Do not add dependencies unless the
     task explicitly asks for it.
   - **Validate**: run `scripts/check.ps1` if it exists. For tasks touching the
     frontend, also run `cd frontend; npm run build`.
   - **Targeted manual/API check**: for backend API tasks, run a targeted
     `Invoke-RestMethod` check against the running backend if one is reachable.
     If it isn't reachable, say explicitly that the check was skipped and why.
   - **Show diff**: run `git --no-pager diff --stat` and `git status --short`.
     Confirm the changed files match the approved scope exactly.
   - **Commit and push**: only if validation passed and the diff matches scope.
     Use `scripts/commit-push.ps1 -Message "..."` (see that script for
     behavior).
   - Stop immediately, without finishing the remaining steps, if any step
     fails or a safety rule would be violated — see Terminal states below.

## Terminal states

End every `/hydra` run by reporting exactly one of these, as the last line:

| State | Meaning |
|---|---|
| `DONE_PUSHED` | Edited, validated, committed, and pushed successfully. |
| `DONE_NOT_COMMITTED` | Validated successfully but not committed (e.g. push was out of the approved scope, or held back deliberately). |
| `BLOCKED_NEEDS_DECISION` | A real ambiguity came up that needs the user's judgment call. |
| `FAILED_WITH_ERROR` | Validation or a required check failed and couldn't be resolved within scope. |
| `UNSAFE_STOPPED` | Continuing would violate one of the safety rules below. |

## Hard rules

- Never read `.env`, `.env.*`, or any file that looks like it holds secrets/credentials.
- Never touch `data/`, `.venv/`, `node_modules/`, or `dist/`.
- Never commit `data/`, `.venv/`, `node_modules/`, `dist/`, `build/`, or any `.env*` file.
  These are already covered by `.gitignore` — do not force-add them.
- Never commit untracked files unless they are explicitly part of the approved scope.
- Never `git add -A` or `git add .`. Stage files explicitly by name.
- Never edit files outside the scope stated in the approved plan.
- Never add dependencies unless explicitly requested by the task.
- Use Windows PowerShell commands only, run from the repo root unless noted.
- Use `git --no-pager` for every diff.
- Don't add features, abstractions, or error handling beyond what the current task requires.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/check.ps1` | Compile-check backend, run layer1 pytest suite, build frontend, show git status |
| `scripts/demo-backend.ps1` | Run the backend dev server (uvicorn, port 8000) |
| `scripts/demo-frontend.ps1` | Run the frontend dev server against the local backend demo |
| `scripts/commit-push.ps1` | Stage tracked modified files, commit, push, show final status |
