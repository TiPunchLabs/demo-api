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
| GET | `/ready` | 200 `{"status": "ready"}` | — |
| GET | `/version` | 200 `{"name": "demo-api", "version": str}` | — |
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

Task: `{"id": int, "title": str (1–200 chars), "completed": bool = false, "priority": "low"|"medium"|"high" = "medium", "due_date": "YYYY-MM-DD"|null = null}`.

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
(`title`, `completed`, `priority`, `due_date`); an empty body, an unknown field or a `null` value
(except for `due_date`) answers 422.

Tasks also have an optional `due_date`, a calendar date in ISO 8601 `YYYY-MM-DD` format (`null` when
absent; past dates are accepted, an invalid date answers 422). Set it on `POST /tasks`, bulk create
or `PUT`; change it with `PATCH /tasks/{id}` and `{"due_date": "2030-05-17"}`; remove it with
`{"due_date": null}`. `PUT` is a full replace, so omitting `due_date` clears it. `toggle` and `PATCH` of
other fields keep it, and `duplicate` copies it.

`GET /tasks` returns tasks sorted by id and accepts optional query parameters:

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `completed` | bool | none (no filter) | `true` / `false` |
| `priority` | str | none (no filter) | `low` / `medium` / `high` (one value) |
| `sort` | str | `id` | `id`, `-id`, `title`, `-title`, `priority`, `-priority` |
| `limit` | int | 20 | 1 to 100 inclusive |
| `offset` | int | 0 | >= 0 |

The `completed` and `priority` filters can be combined and are applied before pagination. An `offset` past the last task
returns `[]` (200); invalid values return 422.

`sort` orders the results: `title` ignores case, `priority` ranks `low` < `medium` < `high`, and a `-`
prefix reverses the order (`-id` is id descending). Tasks equal on the sort key are always ordered by id
ascending, even in descending sorts. Any other value (including an empty one) returns 422. Sorting is
applied after the filters and before `limit` / `offset`, and does not change `X-Total-Count`.

The response carries an `X-Total-Count` header: the number of tasks matching the filters, before
`limit` / `offset` are applied (`0` when there are none). The JSON body stays a plain list.

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
