# HYDRA Agent Workflow

Standard process for agent-assisted changes in this repo. Follow these steps in order.

## Default model

Sonnet, unless a task explicitly calls for something else.

## Process

1. **Inspect first**
   - Read `TASK_CURRENT.md` for the active task.
   - Read every file listed under "Files to inspect" before writing any code.
   - Check `git status --short` and `git diff` to see what's already in flight.

2. **Plan**
   - State the approach in a few sentences before editing.
   - Identify exactly which files will change. Anything not listed is out of scope.

3. **Edit only approved files**
   - Only touch files listed in `TASK_CURRENT.md` under "Requirements" / the agreed file list.
   - Do not refactor, rename, or "clean up" unrelated code while in there.
   - Do not add dependencies unless the task explicitly asks for it.

4. **Run checks**
   - Run `scripts/check.ps1` from the repo root.
   - All steps (py_compile, pytest, frontend build) must pass before moving on.

5. **Show diff**
   - Run `git diff` and `git status --short` and show the result before committing.
   - Confirm the diff only touches the files that were supposed to change.

6. **Commit and push only after validation**
   - Only commit once checks pass and the diff has been reviewed.
   - Use `scripts/commit-push.ps1 -Message "..."` (see that script for behavior).
   - Never push directly to `main` without checking with the user first.

## Hard rules

- Never read `.env`, `.env.*`, or any file that looks like it holds secrets/credentials.
- Never commit `data/`, `.venv/`, `node_modules/`, `dist/`, `build/`, or any `.env*` file.
  These are already covered by `.gitignore` — do not force-add them.
- Never `git add -A` or `git add .`. Stage files explicitly by name.
- Use PowerShell (`.ps1`) for all local automation scripts, run from the repo root unless noted.
- Don't add features, abstractions, or error handling beyond what the current task requires.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/check.ps1` | Compile-check backend, run layer1 pytest suite, build frontend, show git status |
| `scripts/demo-backend.ps1` | Run the backend dev server (uvicorn, port 8000) |
| `scripts/demo-frontend.ps1` | Run the frontend dev server against the local backend demo |
| `scripts/commit-push.ps1` | Stage tracked modified files, commit, push, show final status |
