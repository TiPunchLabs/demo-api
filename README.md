# demo-api

Minimal FastAPI service (`/health` + `/tasks` CRUD, in-memory storage).
It is the first target repository used to validate FlowForge agent workflows.

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs Python 3.12 automatically)
- Optional: [direnv](https://direnv.net/), [pre-commit](https://pre-commit.com/) (installed as dev dependency)

## Quick start

```bash
uv sync
uv run demo-api            # http://127.0.0.1:8000, interactive docs at /docs
```

With direnv: `direnv allow` once, then the venv is synced and activated on `cd`.

## API

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | `/health` | 200 `{"status": "ok"}` | — |
| GET | `/version` | 200 `{"version": str}` | — |
| GET | `/tasks` | 200 list of tasks | — |
| POST | `/tasks` | 201 created task | 422 invalid payload |
| GET | `/tasks/{id}` | 200 task | 404 |
| PUT | `/tasks/{id}` | 200 replaced task | 404, 422 |
| POST | `/tasks/{id}/toggle` | 200 task with `completed` inverted | 404 |
| DELETE | `/tasks/{id}` | 204 empty body | 404 |

Task: `{"id": int, "title": str (1–200 chars), "completed": bool = false}`.

Examples:

```bash
curl localhost:8000/health
curl -X POST localhost:8000/tasks -H 'content-type: application/json' -d '{"title": "Example"}'
curl localhost:8000/tasks
curl localhost:8000/tasks/1
curl -X PUT localhost:8000/tasks/1 -H 'content-type: application/json' -d '{"title": "Example", "completed": true}'
curl -X POST localhost:8000/tasks/1/toggle
curl -X DELETE localhost:8000/tasks/1
```

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pre-commit install           # once
uv run pre-commit run --all-files
```

See [CLAUDE.md](CLAUDE.md) for architecture, conventions and contribution rules.
