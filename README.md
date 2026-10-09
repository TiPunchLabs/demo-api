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
| GET | `/tasks` | 200 list of tasks (filtered, paginated: see below) | 422 invalid query parameter |
| POST | `/tasks` | 201 created task | 422 invalid payload |
| GET | `/tasks/stats` | 200 `{"total", "completed", "pending"}` | — |
| POST | `/tasks/bulk` | 201 list of created tasks (1–50, atomic) | 422 |
| DELETE | `/tasks?completed=true` | 200 `{"deleted": n}` | 422 if `completed` missing or not `true` |
| GET | `/tasks/{id}` | 200 task | 404 |
| PUT | `/tasks/{id}` | 200 replaced task | 404, 422 |
| PATCH | `/tasks/{id}` | 200 partially updated task | 404, 422 (empty body, unknown field, `null`, invalid value) |
| POST | `/tasks/{id}/toggle` | 200 task with `completed` inverted | 404 |
| POST | `/tasks/{id}/duplicate` | 201 copy of the task (same `title` and `priority`, `completed: false`, new `id`) | 404 |
| DELETE | `/tasks/{id}` | 204 empty body | 404 |

Task: `{"id": int, "title": str (1–200 chars), "completed": bool = false, "priority": "low"|"medium"|"high" = "medium"}`.

Examples:

```bash
curl localhost:8000/health
curl -X POST localhost:8000/tasks -H 'content-type: application/json' -d '{"title": "Example"}'
curl localhost:8000/tasks
curl 'localhost:8000/tasks?completed=true&limit=10&offset=0'
curl localhost:8000/tasks/1
curl -X PUT localhost:8000/tasks/1 -H 'content-type: application/json' -d '{"title": "Example", "completed": true, "priority": "high"}'
curl -X PATCH localhost:8000/tasks/1 -H 'content-type: application/json' -d '{"priority": "low"}'
curl -X POST localhost:8000/tasks/1/toggle
curl -X POST localhost:8000/tasks/1/duplicate
curl -X DELETE localhost:8000/tasks/1
curl localhost:8000/tasks/stats                     # {"total": 3, "completed": 1, "pending": 2}
curl -X POST localhost:8000/tasks/bulk -H 'content-type: application/json' -d '{"tasks": [{"title": "A"}, {"title": "B"}]}'
curl -X DELETE 'localhost:8000/tasks?completed=true'  # {"deleted": <n>}
```

Tasks have a `priority` (`"low"`, `"medium"` or `"high"`, default `"medium"`), accepted by
`POST` and `PUT`. `PATCH /tasks/{id}` updates only the fields present in the body
(`title`, `completed`, `priority`); an empty body, an unknown field or a `null` value answers 422.

`GET /tasks` returns tasks sorted by id and accepts optional query parameters:

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `completed` | bool | none (no filter) | `true` / `false` |
| `limit` | int | 20 | 1 to 100 inclusive |
| `offset` | int | 0 | >= 0 |

The `completed` filter is applied before pagination. An `offset` past the last task
returns `[]` (200); invalid values return 422.

`POST /tasks/bulk` takes `{"tasks": [<task>, ...]}` (1 to 50 tasks) and is atomic: if one
task is invalid, it answers 422 and creates nothing. Created tasks keep the request order
and get consecutive ids. `DELETE /tasks` only deletes completed tasks and requires
`completed=true`; without it, or with `completed=false`, it answers 422 and deletes nothing.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pre-commit install           # once
uv run pre-commit run --all-files
```

See [CLAUDE.md](CLAUDE.md) for architecture, conventions and contribution rules.
