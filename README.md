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

```bash
curl localhost:8000/health
curl -X POST localhost:8000/tasks -H 'content-type: application/json' -d '{"title": "Example"}'
curl localhost:8000/tasks
curl 'localhost:8000/tasks?completed=true&limit=10&offset=0'
curl localhost:8000/tasks/1
curl -X PUT localhost:8000/tasks/1 -H 'content-type: application/json' -d '{"title": "Example", "completed": true}'
curl -X DELETE localhost:8000/tasks/1
```

`GET /tasks` returns tasks sorted by id and accepts optional query parameters:

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `completed` | bool | none (no filter) | `true` / `false` |
| `limit` | int | 20 | 1 to 100 inclusive |
| `offset` | int | 0 | >= 0 |

The `completed` filter is applied before pagination. An `offset` past the last task
returns `[]` (200); invalid values return 422.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pre-commit install           # once
uv run pre-commit run --all-files
```

See [CLAUDE.md](CLAUDE.md) for architecture, conventions and contribution rules.
