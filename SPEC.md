# demo-api — Specification

> **Status**: functional reference of the project, effective once merged by the owner.
> Each feature and rule states its status (FlowForge `docs/spec-contract.md` §2.3):
> `CONFIRMED` (documented or decided by the owner: a requirement), `OBSERVED` (current behaviour,
> not a requirement), `KNOWN GAP` (contract and implementation or tests disagree; the contract
> wins). Evidence, open observations and contradictions are tracked in
> [`docs/flowforge-spec-review.md`](docs/flowforge-spec-review.md); anything listed there but not
> here is not a requirement.
>
> Exact payloads and status codes per endpoint live in the `## API` section of `README.md`.
> This file states the behaviours and invariants a change must preserve.

## 1. Objective and scope

**Purpose.** `demo-api` is a minimal HTTP service for managing a list of tasks. It is the first
target repository of FlowForge: AI agents receive GitHub Issues and open Draft PRs here, so the
service must stay small, readable and fully tested.

**Consumers.** HTTP clients of the REST API (JSON over HTTP), and the FlowForge agents and humans
who evolve it.

**Responsibilities.**

- Expose liveness, readiness and identification endpoints.
- Create, read, list, update, duplicate and delete tasks.
- Provide task views: filtered/sorted/paginated listing, counters, overdue tasks.
- Log task changes, unknown-task requests and unhandled errors for debugging and audit.

**Out of scope (by design).**

- Persistence: tasks live in memory, are lost on restart and are not shared between processes.
- Authentication, authorization, multi-user ownership of tasks.
- Request tracing / access logging (left to uvicorn), structured logging, configurable log level.
- Real dependency checks behind readiness.
- Multi-worker or concurrent-safe operation (see R-005).

Any request that crosses these limits is a scope change and must be explicitly asked for in an Issue.

**Not guaranteed.** The current implementation shows these `OBSERVED` behaviours, but clients and
agents must not rely on them, and a change to them does not contradict this specification:

- Unknown fields in a `POST` / `PUT` body are currently ignored (`PATCH` rejects them: R-007).
- Ids of deleted tasks are currently not reused (R-002).
- Error response bodies (`detail` messages and shapes of 404, 422, 500): only status codes are
  contractual (R-015).
- Whitespace-only titles are currently accepted; the owner decided to reject them (#55). `KNOWN GAP`

------

## 2. Features

### F-001 — Service probes

**Description:** `GET /health` reports that the process is alive; `GET /ready` reports that it is
ready to serve. Both always answer 200 with a fixed body and check no dependency.

**Rules:** —

**Status:** `CONFIRMED`

### F-002 — Service identification

**Description:** `GET /version` and `GET /info` return the service name (`demo-api`) and its
current version. Both endpoints are kept and are equivalent: they always return the same body.

**Rules:** R-014

**Status:** `CONFIRMED`

### F-003 — Task creation

**Description:** A client creates one task (`POST /tasks`) or 1 to 50 tasks in a single atomic
request (`POST /tasks/bulk`). The server assigns ids and returns the created task(s) with 201.

**Rules:** R-001, R-002, R-004, R-005, R-006

**Status:** `CONFIRMED`

### F-004 — Task reading

**Description:** A client reads one task by id (`GET /tasks/{id}`).

**Rules:** R-003

**Status:** `CONFIRMED`

### F-005 — Task listing

**Description:** `GET /tasks` returns tasks, optionally filtered by `completed` and `priority`,
sorted (`sort`), paginated (`limit`, `offset`), with the matching total in `X-Total-Count`.

**Rules:** R-004, R-009

**Status:** `CONFIRMED`

### F-006 — Task modification

**Description:** A client replaces a task (`PUT`), partially updates it (`PATCH`) or inverts its
completion state (`POST /tasks/{id}/toggle`).

**Rules:** R-001, R-003, R-004, R-007, R-008

**Status:** `CONFIRMED`

### F-007 — Task duplication

**Description:** `POST /tasks/{id}/duplicate` creates a new pending copy of an existing task.

**Rules:** R-002, R-003, R-008

**Status:** `CONFIRMED`

### F-008 — Task deletion

**Description:** A client deletes one task (`DELETE /tasks/{id}`, 204) or all completed tasks at
once (`DELETE /tasks?completed=true`, returns the number deleted).

**Rules:** R-003, R-010

**Status:** `CONFIRMED`

### F-009 — Task counters

**Description:** `GET /tasks/stats` returns `total`, `completed` and `pending` counts over all
tasks. `pending = total - completed` is `OBSERVED`.

**Rules:** —

**Status:** `CONFIRMED`

### F-010 — Overdue tasks

**Description:** `GET /tasks/overdue` lists the tasks that are late.

**Rules:** R-011

**Status:** `CONFIRMED`

### F-011 — Application logging

**Description:** The service logs successful task changes, requests on unknown tasks and
unhandled errors, in plain text, without ever exposing task content.

**Rules:** R-012, R-013

**Status:** `CONFIRMED`

### F-012 — Priority counters

**Description:** `GET /tasks/stats/by-priority` returns the number of tasks for each priority over
all tasks, completed or not, as `{"low": n, "medium": n, "high": n}`; the three keys are always
present, 0 for a priority with no task.

**Rules:** R-001

**Status:** `CONFIRMED` (owner decision, #58)

------

## 3. Rules and constraints

### R-001 — Task model

**Status:** `CONFIRMED`

**Requirement:** A task has exactly these fields:

| Field | Type | Constraint | Default |
|---|---|---|---|
| `id` | int | assigned by the server (R-002) | — |
| `title` | string | 1 to 200 characters, required | — |
| `completed` | bool | — | `false` |
| `priority` | string | one of `low`, `medium`, `high` | `medium` |
| `due_date` | date or `null` | ISO 8601 `YYYY-MM-DD`, must be a real calendar date; past dates are accepted | `null` |

Any value outside these constraints answers 422.

### R-002 — Id assignment

**Status:** `CONFIRMED`

**Requirement:** Ids are assigned by the server and unique among existing tasks. Tasks created by
one bulk request get consecutive ids in request order. A replace, patch or toggle never changes a
task's id. Whether the id of a deleted task can be reused is not guaranteed (owner decision 5).

`OBSERVED`, not guaranteed: in a fresh store the first task gets id 1, and a rejected creation
consumes no id. Scenarios that show exact id values (S-003, S-005, S-006) illustrate this current
behaviour.

### R-003 — Unknown task

**Status:** `CONFIRMED`

**Requirement:** Any operation on a task id that does not exist (read, replace, patch, toggle,
duplicate, delete) answers 404.

`OBSERVED`: the request changes nothing (tested for duplicate only).

### R-004 — Rejected input changes nothing

**Status:** `CONFIRMED`

**Requirement:** A request rejected with 422 (invalid body, invalid query parameter) leaves the
stored tasks unchanged.

### R-005 — In-memory storage

**Status:** `CONFIRMED`

**Requirement:** Tasks are kept in memory only: a fresh application starts with no task, and data is
neither persisted nor shared across processes. Persistence requires an explicit Issue.

The service assumes a **single worker process** (the `uv run demo-api` default). With several
workers, each holds its own independent store. Within one process, requests are not synchronised:
id uniqueness (R-002) and bulk atomicity (R-006) are only guaranteed for requests that do not run
concurrently.

### R-006 — Atomic bulk creation

**Status:** `CONFIRMED`

**Requirement:** `POST /tasks/bulk` accepts 1 to 50 tasks. If any task is invalid, or the count is
outside 1–50, the request answers 422 and creates no task.

### R-007 — Replace vs partial update

**Status:** `CONFIRMED`

**Requirement:**

- `PUT` is a full replace: every omitted field takes its default (`completed: false`,
  `priority: medium`, `due_date: null`).
- `PATCH` changes only the fields present in the body. An empty body, an unknown field, or a `null`
  value for any field other than `due_date` answers 422. `{"due_date": null}` removes the due date.

### R-008 — Field preservation on derived operations

**Status:** `CONFIRMED`

**Requirement:**

- `toggle` inverts `completed` and keeps every other field.
- `duplicate` creates a new task with a new id, the same `title`, `priority` and `due_date`,
  `completed: false`, and answers 201. It leaves the source task unchanged (`OBSERVED`).

### R-009 — Listing pipeline

**Status:** `CONFIRMED`

**Requirement:** `GET /tasks` processes in this order: filters → sort → pagination.

- `completed` and `priority` filters are optional and combinable.
- `sort` accepts only `id`, `-id`, `title`, `-title`, `priority`, `-priority` (default `id`).
  `title` ignores case; `priority` ranks `low < medium < high`; `-` reverses. Tasks equal on the
  sort key are ordered by id ascending, in both directions.
- `limit` is 1–100 (default 20); `offset` ≥ 0 (default 0). An offset past the end returns `[]` (200).
- `X-Total-Count` is the number of tasks matching the filters, before pagination (`0` if none);
  sorting does not change it. The body stays a plain JSON list.
- Any invalid parameter value answers 422.

### R-010 — Guarded bulk deletion

**Status:** `CONFIRMED`

**Requirement:** `DELETE /tasks` deletes only completed tasks and only when `completed=true` is
given. Without it, or with `completed=false`, it answers 422 and deletes nothing.

### R-011 — Overdue definition

**Status:** `CONFIRMED`

**Requirement:** A task is overdue when it is not completed, has a `due_date`, and that date is
strictly before today's date on the server (local date). A task due today is not overdue.
`GET /tasks/overdue` returns overdue tasks sorted by `due_date` ascending, then id ascending.

### R-012 — Logged events

**Status:** `CONFIRMED`

**Requirement:**

- Each successful task change (create, bulk create, replace, patch, toggle, duplicate, delete,
  delete completed) logs one `INFO` record per affected task, with the action and the task id
  (e.g. `task created id=3`).
- A 404 on an unknown task logs a `WARNING` with the id.
- An unhandled exception logs an `ERROR` with the traceback and answers 500.
- Reads (`GET`) and 422 responses log no task record.
- Standard library `logging`, plain text, fixed `INFO` level, no new dependency.

### R-013 — No task content in logs

**Status:** `CONFIRMED`

**Requirement:** Task titles never appear in log messages. Logs identify tasks by id only.

### R-014 — Version source

**Status:** `CONFIRMED`

**Requirement:** The version reported by the API equals the installed package version (from
`pyproject.toml` metadata) and is never hardcoded in the application code.

`KNOWN GAP`: `test_info.py` and `test_version_returns_current_version` still assert the literal
`"0.1.0"` (fix tracked in #54).

### R-015 — Error contract

**Status:** `CONFIRMED`

**Requirement:** The error contract is limited to HTTP status codes and the rules that trigger
them: 404 for an unknown task (R-003), 422 for invalid input with no state change (R-004, R-006,
R-007, R-010), 500 for an unhandled error (R-012). Error response bodies are not contractual.

------

## 4. Validation scenarios

### S-001 — Probes answer

**Covers:** F-001

GIVEN a running service
WHEN a client calls `GET /health` then `GET /ready`
THEN both answer 200, with `{"status": "ok"}` and `{"status": "ready"}` respectively

### S-002 — Identification follows package version

**Covers:** F-002, R-014

GIVEN the installed package version `V`
WHEN a client calls `GET /version` and `GET /info`
THEN both answer 200 with the same body `{"name": "demo-api", "version": V}`, and the OpenAPI
`info.version` is `V`

### S-003 — Create with defaults

**Covers:** F-003, R-001, R-002, R-005

GIVEN a fresh application (empty store)
WHEN a client posts `{"title": "Example"}` to `/tasks`
THEN the answer is 201 `{"id": 1, "title": "Example", "completed": false, "priority": "medium", "due_date": null}`

### S-004 — Invalid task is rejected

**Covers:** R-001, R-004

GIVEN an existing task
WHEN a client sends a title of 0 or 201 characters, priority `urgent`, or due date `2026-02-30`
on create, replace or patch
THEN the answer is 422, the existing task is unchanged and no task is created

### S-005 — Bulk creation is atomic

**Covers:** F-003, R-002, R-006

GIVEN an empty store
WHEN a client posts three tasks to `/tasks/bulk` with the second title empty
THEN the answer is 422, `GET /tasks` returns `[]`, and the next created task gets id 1

### S-006 — Bulk creation keeps order and limits

**Covers:** F-003, R-002, R-006

GIVEN a store holding one task
WHEN a client bulk-creates `a`, `b`, `c`
THEN the answer is 201 with ids 2, 3, 4 in that order;
AND a bulk request of 0 or 51 tasks answers 422, while 50 tasks answers 201

### S-007 — Unknown task

**Covers:** F-004, F-006, F-007, F-008, R-003, R-015

GIVEN no task with id 999
WHEN a client reads, replaces, patches, toggles, duplicates or deletes task 999
THEN each answer is 404 and no task is created

### S-008 — Listing pipeline and total count

**Covers:** F-005, R-009

GIVEN tasks `apple/medium`, `Banana/high`, `cherry/low`, `Apple/high`, `banana/low` (ids 1–5)
WHEN a client calls `GET /tasks?priority=high&sort=-title&limit=1&offset=1`
THEN the body is `[task 4]` and `X-Total-Count` is `2`

### S-009 — Sort ties and invalid parameters

**Covers:** F-005, R-009

GIVEN the five tasks of S-008
WHEN a client sorts by `title` then by `-title`
THEN ids are `[1, 4, 2, 5, 3]` then `[3, 2, 5, 1, 4]`;
AND `sort` in `foo`, `""`, `Title`, `+id`, `limit` in `0`, `101`, or `offset=-1` answers 422

### S-010 — Default pagination

**Covers:** F-005, R-009

GIVEN 25 tasks
WHEN a client calls `GET /tasks` with no parameter
THEN the body holds ids 1 to 20 and `X-Total-Count` is `25`

### S-011 — PUT clears, PATCH keeps

**Covers:** F-006, R-007

GIVEN a task with `priority: high` and `due_date: 2030-05-17`
WHEN a client sends `PATCH {"title": "New"}`
THEN only the title changes;
AND a following `PUT {"title": "x"}` yields `priority: medium` and `due_date: null`

### S-012 — PATCH rejects ambiguous bodies

**Covers:** F-006, R-004, R-007

GIVEN an existing task
WHEN a client sends `PATCH` with `{}`, `{"foo": 1}` or `{"title": null}`
THEN the answer is 422 and the task is unchanged;
AND `PATCH {"due_date": null}` answers 200 and removes only the due date

### S-013 — Toggle and duplicate preserve fields

**Covers:** F-006, F-007, R-008

GIVEN a completed task with `priority: high` and `due_date: 2030-05-17`
WHEN a client toggles it, and separately duplicates it
THEN the toggled task differs only by `completed`;
AND the duplicate answers 201 with a new id, same title, priority and due date, `completed: false`,
and the source task is unchanged

### S-014 — Guarded deletion of completed tasks

**Covers:** F-008, R-010

GIVEN tasks 1 and 3 completed, task 2 pending
WHEN a client calls `DELETE /tasks` without parameter, then with `completed=false`
THEN both answer 422 and nothing is deleted;
AND `DELETE /tasks?completed=true` answers 200 `{"deleted": 2}` and only task 2 remains

### S-015 — Counters

**Covers:** F-009

GIVEN three tasks, one completed
WHEN a client calls `GET /tasks/stats`
THEN the answer is 200 `{"total": 3, "completed": 1, "pending": 2}`

### S-016 — Overdue selection and order

**Covers:** F-010, R-011

GIVEN pending tasks due yesterday, 10 days ago (two tasks), today, tomorrow, one without due date,
and a completed task due 5 days ago
WHEN a client calls `GET /tasks/overdue`
THEN only the pending tasks due yesterday and 10 days ago are returned: the two 10-day-old tasks
first (by id), then the one due yesterday

### S-017 — Change and error logging

**Covers:** F-011, R-012

GIVEN the service logging at `INFO`
WHEN a client creates task 1, deletes unknown task 42, lists tasks, and posts an invalid body
THEN the log holds `INFO task created id=1` and `WARNING task not found id=42`, and nothing for
the list or the 422

### S-018 — Titles never logged

**Covers:** F-011, R-013

GIVEN a distinctive title `SECRET-distinctive-title`
WHEN a client creates, replaces and duplicates a task with that title
THEN no log message contains that title

### S-019 — Unhandled error

**Covers:** F-011, R-012

GIVEN a request whose handler raises an unexpected exception
WHEN the request is processed
THEN the answer is 500 and an `ERROR` record with the traceback is logged

### S-020 — Counts per priority

**Covers:** F-012, R-001

GIVEN tasks with priorities `high` (pending), `high` (completed) and `low`, and none `medium`
WHEN a client calls `GET /tasks/stats/by-priority`
THEN the answer is 200 `{"low": 1, "medium": 0, "high": 2}`
