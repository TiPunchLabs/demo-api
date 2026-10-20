# demo-api — FlowForge spec review (working document)

> Working document supporting `SPEC.md`. It does **not** replace it.
> Produced on 2026-10-19 from `main` @ `92716a0`. Test suite at that commit: 108 passed.
> Owner decisions on the open questions were integrated the same day (see [Decisions](#decisions)).
> Revised on 2026-10-19 after the FlowForge Prompt 37.1 audit (C-6, statuses, per-scenario coverage).
>
> Statuses in `SPEC.md` (FlowForge `docs/spec-contract.md` §2.3): **CONFIRMED** (documented or
> decided by the owner), **OBSERVED** (seen in code or tests, not a requirement), **KNOWN GAP**
> (contract and implementation or tests disagree). In this document, **UNCERTAIN** marks an item
> insufficiently specified; contradictions are listed under [Contradictions](#contradictions).

## Sources analysed

| Source | What it provides |
|---|---|
| `README.md` § API | Endpoint table, task model, listing parameters, bulk/delete-completed rules, due date semantics |
| `CLAUDE.md` § What this repository is, Architecture, Constraints | Purpose, in-memory storage as intentional, scope discipline |
| `src/demo_api/schemas.py` | Field constraints, PATCH validation |
| `src/demo_api/storage.py` | Id assignment, atomic bulk create |
| `src/demo_api/routes/*.py`, `src/demo_api/main.py` | Endpoint behaviour, logging, 500 handler |
| `tests/test_tasks.py` | Task behaviours (CRUD, filters, sort, pagination, bulk, overdue, due date) |
| `tests/test_logging.py` | Logging levels, messages, title exclusion, 500 path |
| `tests/test_health.py`, `test_ready.py`, `test_info.py`, `test_version.py` | Probe and identification payloads |
| Issue #11 | `GET /info` intent and acceptance criteria |
| Issue #28 | `GET /ready` intent; no dependency check (explicitly out of scope) |
| Issue #29 | Logging requirements (levels, ids only, no titles, stdlib, fixed level) |
| Issue #49 (+ #5) | `/version` payload; version sourced from package metadata, never hardcoded |
| Issue #45 | Closed *not planned* (test issue) — `GET /tasks/due` is **not** a feature |
| Issue #22 (open) | Known documentation drift (README missing `/info`, CLAUDE.md structure outdated) |
| Issues #30, #31, #52 (open) | Pending demands: title search, complete-all, `HEAD /health` |
| `git log` | Feature-to-issue traceability (`Refs #n` in commit bodies) |

## Confirmed requirements

All went into `SPEC.md` as `CONFIRMED`. Each is documented (README, CLAUDE.md or issue acceptance
criteria) or stems from an owner decision. The "Tests" column lists the related tests; it does not
claim full coverage: per-scenario coverage is in [Coverage](#coverage).

| SPEC id | Requirement | Documentation | Tests |
|---|---|---|---|
| F-001 | `/health`, `/ready` static 200 | README, #28 | `test_health.py`, `test_ready.py` |
| F-002, R-014 | `/version` and `/info` return name + metadata version | README (`/version`), #11, #5, #49 | `test_version.py`, `test_info.py` |
| R-001 | Task model, constraints, defaults (server-assigned id) | README "Task:" line + due date paragraph | `test_create_*`, `test_invalid_*`, `test_past_due_date_is_accepted` |
| R-002 | Unique ids, consecutive in bulk, stable on update; reuse not guaranteed | README (bulk), decision 5 | `test_bulk_create_success`, `test_update_task` |
| R-003 | 404 on an unknown task | README table | `test_unknown_task_returns_404`, `test_duplicate_unknown_task_creates_nothing` |
| R-004 | 422 changes nothing | README (bulk, delete, PATCH) | `test_patch_rejects_invalid_payload`, `test_invalid_due_date_is_rejected`, `test_delete_completed_guard` |
| R-005 | In-memory, not persistent, not shared | CLAUDE.md Architecture + Constraints | `conftest.py` (fresh app = empty) |
| R-006 | Bulk 1–50, atomic | README | `test_bulk_create_*`, `test_store_create_many_is_atomic` |
| R-007 | PUT full replace / PATCH partial, PATCH rejections | README | `test_put_without_due_date_clears_it`, `test_create_and_replace_accept_priority`, `test_patch_*` |
| R-008 | Toggle / duplicate field preservation | README (table + due date paragraph) | `test_toggle_*`, `test_duplicate_*` |
| R-009 | Listing pipeline, sort, pagination, `X-Total-Count` | README | `test_list_*` |
| R-010 | Guarded delete-completed | README | `test_delete_completed*` |
| R-011 | Overdue definition (server local date) | README | `test_overdue_*` |
| R-012, R-013 | Logging events, no titles | #29 | `test_logging.py` |
| R-005 (single worker), R-015 | Single-worker assumption; error contract = status codes | Owner decisions 6 and 7 | — (statement of limits) |
| R-014 | Version from package metadata | #49, #5 | `test_version_matches_package_metadata`; **KNOWN GAP**: `test_info.py` and `test_version_returns_current_version` assert the literal `"0.1.0"` (C-2, #54) |

## Observed behaviours not confirmed

None of these is a requirement. The "Outcome" column records the owner decision, if any.

| # | Behaviour | Evidence | Level | Outcome |
|---|---|---|---|---|
| O-1 | Ids are never reused after a deletion (counter only grows). | `storage.py` `_next_id`; checked manually, no test | OBSERVED | Explicitly **not guaranteed** (decision 5, SPEC R-002) |
| O-2 | `POST` / `PUT` silently **ignore** unknown body fields, whereas `PATCH` rejects them (422). | `TaskIn` has no `extra="forbid"`; `TaskPatch` has it | OBSERVED | Kept as is, **outside the contract** (decision 3) |
| O-3 | Whitespace-only titles (`"   "`) are accepted; titles are not trimmed. | `Field(min_length=1)` counts spaces | OBSERVED | To be rejected: **#55** (decision 4) |
| O-4 | The 500 body is `{"detail": "Internal Server Error"}`. | `main._log_unhandled`; test checks status only | OBSERVED | Body not contractual (decision 7, R-015) |
| O-5 | The 422 from `DELETE /tasks` uses a custom detail `Query parameter completed=true is required`; other 422s use FastAPI's default error list. | `routes/tasks.py` | OBSERVED | Body not contractual (decision 7, R-015) |
| O-6 | `GET /tasks/overdue` and `GET /tasks/stats` are neither filtered nor paginated. | `routes/tasks.py` | OBSERVED | Open, no decision needed yet |
| O-7 | No concurrency guarantee inside one process: sync handlers run in a thread pool and `TaskStore` has no lock. | `storage.py`, FastAPI sync routes | UNCERTAIN | Documented as a limit (decision 6, R-005) |
| O-8 | Non-integer path ids (`/tasks/abc`) answer 422, not 404. | FastAPI path typing; untested | OBSERVED | Open, no decision needed yet |
| O-9 | The log format is `LEVEL logger message` on a handler attached to the `demo_api` logger. | `main._configure_logging` | OBSERVED (format detail, #29 only requires level + logger name) | Open, no decision needed yet |
| O-10 | In a fresh store the first task gets id 1; a rejected creation consumes no id. | `storage.py`; `test_create_task`, `test_bulk_create_is_atomic` | OBSERVED | Tagged `OBSERVED` in SPEC R-002; exact ids in S-003, S-005, S-006 illustrate it |
| O-11 | A request on an unknown task changes nothing. | `routes/tasks.py`; tested for duplicate only (`test_duplicate_unknown_task_creates_nothing`) | OBSERVED | Tagged `OBSERVED` in SPEC R-003 |
| O-12 | `duplicate` leaves the source task unchanged. | `test_duplicate_leaves_source_unchanged`; README silent | OBSERVED | Tagged `OBSERVED` in SPEC R-008 |
| O-13 | `pending = total - completed` in `GET /tasks/stats`. | `routes/tasks.py`, `test_stats_*`; README shows one example only | OBSERVED | Tagged `OBSERVED` in SPEC F-009 |
| O-14 | A client cannot set the id. | No source states it; a client `id` is an unknown field, ignored on `POST` (O-2) | OBSERVED | Removed from SPEC R-001 ("never by the client"); R-002 keeps "assigned by the server" |

> 💡 **Note**: some tests assert stricter details than the contract (e.g. the 404 body
> `{"detail": "Task 999 not found"}`). That is allowed: tests may pin the implementation, but a
> change to such a detail does not contradict `SPEC.md`.

## Contradictions

| # | Sources in conflict | Detail | Impact |
|---|---|---|---|
| C-1 | `README.md` § API vs code/tests/#11 | `GET /info` exists, is tested and was requested (#11), but is absent from the README API table. Tracked by open issue #22. | An agent reading only README misses an endpoint; a new "add `/info`" request would wrongly look new. `SPEC.md` F-002 now documents `/info`. Open in #22. |
| C-2 | Issue #11 vs issues #5/#49 vs tests | #11 required `version = "0.1.0"` literally; #5/#49 require the metadata version, never hardcoded. `test_info.py` and `test_version_returns_current_version` assert the literal `"0.1.0"`. | Any version bump breaks 3 tests although the code is right. `SPEC.md` follows #49 (most recent, explicit). Fix tracked in **#54** (decision 2). |
| C-3 | `CLAUDE.md` § Structure vs repository | Lists only `health.py` / `tasks.py` routes and 3 test files; misses `info.py`, `ready.py`, `version.py`, `test_info.py`, `test_ready.py`, `test_version.py`, `test_logging.py`. Also tracked by #22. | Agent orientation only; no behavioural impact. |
| C-4 | `README.md` table vs README prose | Table row for `duplicate` says "same `title` and `priority`"; the prose and tests add that `due_date` is copied too. | Minor: table is incomplete, not wrong. `SPEC.md` follows prose + tests. |
| C-5 | `README.md` intro / `CLAUDE.md` first line vs current scope | Both describe "`/health` + `/tasks` CRUD"; the service now also has `/ready`, `/version`, `/info`, stats, overdue, bulk, logging. | Minor understatement. |
| C-6 | `SPEC.md` R-002 (first version) vs owner decision 5 | R-002 said "each creation gets a higher id than the previous one", which guarantees that a deleted id is never reused, while the same rule and decision 5 say reuse is **not** guaranteed. | **Resolved** (Prompt 37.2): the ordering sentence is removed; R-002 keeps uniqueness, consecutive bulk ids and stable ids, and tags the observed id values `OBSERVED` (O-10). No new id rule. |

## Decisions

Owner decisions of 2026-10-19 on the questions raised by the first analysis.

| # | Question | Decision | Effect |
|---|---|---|---|
| 1 | `/info` vs `/version` (C-1) | Keep both; document their equivalence | SPEC F-002, S-002 |
| 2 | Version literal in tests (C-2) | Replace by the metadata version | Issue **#54** |
| 3 | Unknown body fields on `POST`/`PUT` (O-2) | No change; outside the guaranteed contract | SPEC § 1 "Not guaranteed" |
| 4 | Whitespace-only titles (O-3) | Reject them | Issue **#55**; SPEC § 1 "Not guaranteed" until done |
| 5 | Id reuse (O-1) | Not guaranteed | SPEC R-002, § 1 |
| 6 | Concurrency (O-7) | Document the single-worker assumption and its limits | SPEC R-005, § 1 |
| 7 | Error body contract (O-4, O-5) | Status codes and their triggering rules only | SPEC R-015; 404 body removed from R-003 / S-007 |
| 8 | `SPEC.md` discoverability | Reference it from `README.md` and `CLAUDE.md` | `README.md` § Specification, `CLAUDE.md` § Specification |

No question is left open. Remaining open items are documentation drift (#22) and the two issues above.

## Coverage

**In `SPEC.md`:** 11 features (F-001…F-011), 15 rules (R-001…R-015), 19 scenarios (S-001…S-019).
Every feature and every rule has at least one scenario.

**Scenario → test** (suite at `92716a0`, 108 passed). COVERED: every THEN is asserted by a test;
PARTIAL: some of it only; NOT_COVERED: no test.

| Scenario | Test(s) | Coverage | Not asserted |
|---|---|---|---|
| S-001 | `test_health_returns_ok`, `test_ready_returns_ready` | COVERED | — |
| S-002 | `test_version_matches_package_metadata`, `test_info_returns_name_and_version`, `test_info_schema_is_exact` | PARTIAL | `/info` against the metadata version (tests assert `"0.1.0"`, C-2, #54); `/info` = `/version` |
| S-003 | `test_create_task` | COVERED | — |
| S-004 | `test_create_rejects_invalid_payload`, `test_invalid_priority_rejected`, `test_invalid_due_date_is_rejected`, `test_patch_rejects_invalid_payload` | PARTIAL | title of 0 / 201 characters on `PUT`; "no task is created" after a rejected `POST` |
| S-005 | `test_bulk_create_is_atomic` | COVERED | — |
| S-006 | `test_bulk_create_success`, `test_bulk_create_rejects_empty_list`, `test_bulk_create_limits` | COVERED | — |
| S-007 | `test_unknown_task_returns_404`, `test_duplicate_unknown_task_creates_nothing` | PARTIAL | "no task is created" for read, replace, patch, toggle, delete |
| S-008 | `test_list_sort_applies_after_filters_and_before_pagination` | COVERED | — |
| S-009 | `test_list_sort_title_ties_by_id_ascending`, `test_list_sort_invalid_returns_422`, `test_list_rejects_invalid_query` | COVERED | — |
| S-010 | `test_list_defaults_to_twenty_sorted_by_id` | PARTIAL | `X-Total-Count: 25` with 25 tasks |
| S-011 | `test_patch_other_fields_keeps_due_date`, `test_put_without_due_date_clears_it`, `test_create_and_replace_accept_priority` | PARTIAL | `PATCH {"title": …}` keeping `priority: high` |
| S-012 | `test_patch_rejects_invalid_payload`, `test_patch_null_removes_due_date` | COVERED | — |
| S-013 | `test_toggle_task_keeps_priority`, `test_toggle_keeps_due_date`, `test_toggle_task_twice_restores_state`, `test_duplicate_task`, `test_duplicate_copies_due_date`, `test_duplicate_completed_task_is_pending`, `test_duplicate_leaves_source_unchanged` | COVERED | — (across several tests) |
| S-014 | `test_delete_completed_guard`, `test_delete_completed` | COVERED | — |
| S-015 | `test_stats_non_empty` | COVERED | — |
| S-016 | `test_overdue_mix`, `test_overdue_sorted_by_due_date_then_id` | COVERED | — (across two tests) |
| S-017 | `test_logs_task_changes`, `test_logs_not_found_as_warning`, `test_reads_and_validation_errors_log_no_change` | COVERED | — |
| S-018 | `test_logs_never_contain_titles` | COVERED | — |
| S-019 | `test_unhandled_exception_logs_error_with_traceback` | COVERED | — |

Totals: 14 COVERED, 5 PARTIAL (S-002, S-004, S-007, S-010, S-011), 0 NOT_COVERED. No test was
added: closing the PARTIAL gaps is left to the owner (tests are out of scope of this preparation).

**Deliberately not covered:**

- Exact per-endpoint payloads and the full status-code table → `README.md` § API remains the reference.
- Development process (branching, tests/lint before PR, Conventional Commits) → `CLAUDE.md`.
- Internal architecture (`create_app`, `TaskStore`, `get_store`) → evidence only, not requirements.
- OpenAPI `/docs` UI, uvicorn host/port, `uv run demo-api` entry point → tooling, not behaviour.
- Pending open issues (#30 search, #31 complete-all, #52 `HEAD /health`) → not implemented; none
  contradicts an existing rule. #31 must keep R-012 (one `INFO` per affected task).
- Closed-not-planned #45 (`GET /tasks/due`) → not a feature.

## Recommendation

`SPEC.md` can be submitted for review: every `CONFIRMED` statement is documented or stems from an
explicit owner decision, and behaviours seen only in code or tests are tagged `OBSERVED`. No open
contradiction affects a normative rule: C-2 is a `KNOWN GAP` resolved in favour of #49 (test fix in
#54), C-6 is resolved. Test coverage is partial for 5 scenarios (see [Coverage](#coverage)).

**Verdict: READY_FOR_REVIEW** — becomes the official reference once the owner merges it.
