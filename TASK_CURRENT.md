# HYDRA Current Task

## Goal
Fix the backend `/api/graph` crash during replay demo.

## Context
Backend log showed:
`GET /api/graph -> 500`
`AttributeError: 'NoneType' object has no attribute 'get'`
in `backend/api.py`, inside `_graph_from_db_kg_updates()`.

Likely cause:
Replay alerts have `kg_update: null`, and graph code assumes `kg_update` is always a dict.

## Files to inspect
- backend/api.py
- backend/db.py
- backend/neo4j_client.py

## Requirements
- Do not edit frontend.
- If Neo4j connection fails, `/api/graph` should return safe fallback/stored graph, not 500.
- Skip null or non-dict `kg_update` records.
- Keep replay demo working.
- Do not add dependencies.
- Do not touch secrets or .env files.

## Validation
Run:
`powershell -ExecutionPolicy Bypass -File scripts/check.ps1`

Also manually test:
`Invoke-RestMethod http://127.0.0.1:8000/api/graph`

## Commit message
fix: make graph endpoint tolerate null kg updates
