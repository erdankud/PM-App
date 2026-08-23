# PM Thinking Coach — server

FastAPI + SQLAlchemy. Owns everything the client must not: score, XP, level, the
user's local date, skill deltas, path assignment, and the AI evaluation call.

```
server/
├── app/
│   ├── config.py          Settings; the only place a provider key exists
│   ├── models.py          Relational model (spec §14)
│   ├── schemas.py         Wire contracts (camelCase out, snake_case in)
│   ├── security.py        JWT access tokens + hashed refresh tokens
│   ├── apple.py           Sign in with Apple identity-token verification
│   ├── content.py         Scenario loading + editorial validation
│   ├── worker.py          Evaluation worker loop
│   ├── ai/                Prompt assembly, output validation, provider adapters
│   ├── services/          scoring, skills, path assignment, evaluation
│   └── routers/           auth, me, assessment, today, attempts, progress, events
├── content/               Authored scenarios + assessment + JSON schema
├── scripts/               validate_content, seed, smoke, qa_evaluate
├── alembic/               Migrations
└── tests/                 pytest
```

---

## Running it

### Local, zero setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m scripts.validate_content && python -m scripts.seed
uvicorn app.main:app --reload
```

SQLite by default, tables created on startup, worker running in-process.

### Docker (Postgres, separate worker)

```bash
docker compose up --build
```

Runs migrations, seeds content, and starts the API on `:8000` with the worker as its
own service — closer to how you would deploy it.

---

## Choosing an evaluator

The provider is a configuration change, never a code change. Set two variables:

| Provider | Free tier | `EVALUATOR_PROVIDER` | Suggested `EVALUATOR_MODEL` | Key from |
|---|---|---|---|---|
| Google Gemini | yes | `gemini` | `gemini-2.0-flash` | aistudio.google.com/apikey |
| Groq | yes | `groq` | `llama-3.3-70b-versatile` | console.groq.com/keys |
| OpenRouter | yes, `:free` models | `openrouter` | `meta-llama/llama-3.3-70b-instruct:free` | openrouter.ai/keys |
| Anthropic | no | `anthropic` | `claude-sonnet-4-5` | console.anthropic.com |
| OpenAI | no | `openai` | `gpt-4o-mini` | platform.openai.com |
| Dev stub | n/a | `mock` | — | — |

```bash
EVALUATOR_PROVIDER=gemini
EVALUATOR_API_KEY=...
EVALUATOR_MODEL=gemini-2.0-flash
```

`mock` is a deterministic keyword heuristic for local development. It is not AI
feedback, must not be presented as such, and `get_settings()` raises on startup if it
is used with `ENVIRONMENT=production`.

Adding another provider means one class in `app/ai/providers.py` plus a line in
`app/ai/registry.py`. Everything upstream deals in `EvaluationRequest` and raw text.

### Calibrating before you ship

Every scenario carries three QA fixtures — a strong answer, a weak one, and a
well-argued alternative option. Run them through whichever provider you configured:

```bash
EVALUATOR_PROVIDER=gemini EVALUATOR_API_KEY=... python -m scripts.qa_evaluate
```

The harness reports each fixture's total against its expected band and fails on
**ordering** problems: strong must outscore the alternative, and the alternative must
outscore the weak answer. An alternative that scores like a weak answer is a content
bug, not a model bug — usually the option weights or the rubric need work.

---

## API

Base path `/v1`. Bearer access tokens; ownership is always derived from the token and
never from a client-supplied user id.

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/apple` | 503 unless `APPLE_CLIENT_ID` is set |
| POST | `/auth/dev` | 404 when `ALLOW_DEV_AUTH=false` or in production |
| POST | `/auth/refresh` | Rotates the refresh token |
| POST | `/auth/signout` | Revokes all refresh tokens |
| GET | `/me` | Profile, onboarding state, XP/level, skills |
| PATCH | `/me/profile` | Goal, timezone, complete onboarding |
| DELETE | `/me` | Anonymises the account, deletes rationales and feedback |
| GET | `/assessment` | Next diagnostic item |
| POST | `/assessment/responses` | Final answer computes baselines and the 7-day path |
| GET | `/assessment/result` | Path reveal payload |
| GET | `/today` | Resolves one assignment for the device-local date |
| GET | `/challenges/{assignmentId}` | Scenario content; creates the draft attempt |
| PUT | `/attempts/{id}/draft` | Autosave; 409 once submitted |
| POST | `/attempts/{id}/evidence` | Idempotent by unique constraint |
| POST | `/attempts/{id}/submit` | Accepts `Idempotency-Key`; returns the consequence |
| GET | `/attempts/{id}/feedback` | `pending` / `complete` / `failed` |
| POST | `/attempts/{id}/feedback/retry` | Subject to the daily evaluation limit |
| POST | `/attempts/{id}/feedback-rating` | `useful` / `not_useful` |
| GET | `/progress` | XP, level, streak, 7-day activity, six skills |
| GET | `/history` | Paginated completed attempts |
| POST | `/events` | Analytics sink; free-text properties are dropped |

Interactive docs at `/docs` when the server is running.

### What the client is never sent

`GET /challenges/{id}` returns the brief, evidence, decision prompt and option
labels — and deliberately omits the authored rubric, each option's consequence text,
and its `decisionPoints` weight. The consequence appears only in the submit response,
from a server-side snapshot. A test asserts this
(`test_challenge_payload_withholds_rubric_and_consequences`).

---

## Scoring

| Component | Points | Computed by |
|---|---:|---|
| Evidence engagement | 0–15 | Server, from recorded `EvidenceInteraction` rows |
| Decision quality | 0–25 | Server, from the authored option weight |
| Rationale quality | 0–45 | Model, clamped and validated |
| Communication clarity | 0–15 | Model, clamped and validated |

XP is 50 for completion plus one point per score point above 50, capped at 50. The
`XpLedgerEntry` table has a unique constraint on `(attempt_id, reason)`, so a repeated
worker run or a duplicate submit cannot double-award — the code catches the
`IntegrityError` rather than relying on checking first.

Skill deltas are bounded to −3…+8 in three places: the prompt asks for it, the
validator rejects anything outside it, and `apply_deltas` clamps again before writing.

---

## Content authoring

Scenarios live in `content/scenarios/*.json` and are validated against
`content/scenario.schema.json` plus editorial rules in `app/content.py`:

- evidence card `order` must be 1..n with no gaps
- at least one option must be a strong choice (≥20 points)
- at least one **non-reference** option must earn meaningful partial credit (≥8)
- QA fixtures must include strong, weak, and defensible-alternative
- QA rationales must fit the product's own 30–600 character limit, so every fixture is
  something a real user could have typed

```bash
python -m scripts.validate_content   # gate this in CI
python -m scripts.seed               # inserts new (id, version) pairs only
```

Published content is immutable per `(id, version)`. Editing a live scenario requires a
version bump so historical attempts keep the content they were evaluated against.

---

## Evaluation flow

```
POST /submit ──► snapshot consequence, status=awaiting_feedback,
                 FeedbackEvaluation(status=queued)
                        │
                 worker claims it (status=running)
                        │
                 prompt assembled server-side  ──► provider
                        │                          (≤3 attempts, exponential backoff)
                 validate JSON, lengths, ranges
                        │
        ┌───────────────┴───────────────┐
   valid│                               │invalid twice
        ▼                               ▼
 one transaction:                 status=failed
 feedback + skill ledger          attempt=feedback_failed
 + aggregate skills + XP          consequence still shown
 + profile total                  retry available
 attempt=complete
        │
 recalculate FUTURE assignments only
```

`RUN_INLINE_WORKER=true` (the default) runs the worker inside the API process. Set it
false and run `python -m app.worker` to scale it separately.

The worker's claim is a simple read-then-update, which is safe for a single worker. If
you run more than one, add `SELECT ... FOR UPDATE SKIP LOCKED` on Postgres in
`claim_next`.

---

## Migrations

```bash
alembic upgrade head
alembic revision --autogenerate -m "what changed"
```

Local SQLite development also creates tables on startup as a convenience; deployments
should rely on Alembic only.

---

## Tests

```bash
python -m pytest tests -q
```

Covers score bounds and XP arithmetic, provider-output validation (out-of-range,
unknown skill keys, code fences, empty coaching), path determinism and the
one-assignment-per-day constraint, and over HTTP: onboarding gates, evidence and
rationale validation, draft immutability after submit, single XP award under repeated
submits, ownership rejection, analytics free-text stripping, and account deletion.
