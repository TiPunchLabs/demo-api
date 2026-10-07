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
curl localhost:8000/tasks/1
curl -X PUT localhost:8000/tasks/1 -H 'content-type: application/json' -d '{"title": "Example", "completed": true, "priority": "high"}'
curl -X PATCH localhost:8000/tasks/1 -H 'content-type: application/json' -d '{"priority": "low"}'
curl -X DELETE localhost:8000/tasks/1
```

Tasks have a `priority` (`"low"`, `"medium"` or `"high"`, default `"medium"`), accepted by
`POST` and `PUT`. `PATCH /tasks/{id}` updates only the fields present in the body
(`title`, `completed`, `priority`); an empty body, an unknown field or a `null` value answers 422.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pre-commit install           # once
uv run pre-commit run --all-files
```

See [CLAUDE.md](CLAUDE.md) for architecture, conventions and contribution rules.
