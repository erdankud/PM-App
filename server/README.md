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
├── scripts/               content pipeline, validate_content, smoke, qa_evaluate
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
python -m scripts.validate_content
uvicorn app.main:app --reload
```

SQLite by default, tables created on startup, worker running in-process.

### Docker (Postgres, separate worker)

```bash
docker compose up --build
```

Runs migrations and starts the API on `:8000` with the worker as its
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
| PATCH | `/me/profile` | Target role, timezone, language, complete onboarding |
| DELETE | `/me` | Anonymises the account, deletes rationales and feedback |
| GET | `/tree` | The whole map with this learner's status on every block |
| GET | `/blocks/{id}` | Nodes, lessons, progress, whether the gate is open |
| GET | `/lessons/{id}` | Lesson content |
| POST | `/lessons/{id}/complete` | Idempotent; awards lesson XP once |
| POST | `/gates/{id}/start` | **409 unless the block is `gate_ready`**; creates the attempt |
| PUT | `/attempts/{id}/draft` | Autosave; 409 once submitted |
| POST | `/attempts/{id}/evidence` | Idempotent by unique constraint |
| POST | `/attempts/{id}/submit` | Accepts `Idempotency-Key`; returns the consequence |
| GET | `/attempts/{id}/feedback` | `pending` / `complete` / `failed` |
| POST | `/attempts/{id}/feedback/retry` | Subject to the daily evaluation limit |
| POST | `/attempts/{id}/feedback-rating` | `useful` / `not_useful` |
| GET | `/progress` | XP, level, blocks passed, lessons read, seven competencies |
| GET | `/history` | Paginated gate sittings |
| POST | `/events` | Analytics sink; free-text properties are dropped |

Interactive docs at `/docs` when the server is running.

### What the client is never sent

`POST /gates/{id}/start` returns the brief, evidence, decision prompt and option
labels — and deliberately omits the authored rubric, each option's consequence text,
and its `decisionPoints` weight. The consequence appears only in the submit response.

Availability is the same kind of guarantee: the client is told the status of every
block, but it is the server that refuses `start` when the block is not `gate_ready`.
A test drives that path directly rather than through the UI.

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

## Lesson audio overview

A lesson can carry an **audio overview**: two hosts discussing it, the way NotebookLM
does. It is explicitly not the lesson read aloud — prose read out loud sounds like
prose read out loud, and that is what this replaced.

The dialogue is written once, at build time, by a model, and then stored as content in
`content/<tree>/audio-scripts/`. Nothing calls a provider at runtime, and a script is a
reviewable file like any other: read it, edit it, see it in a diff.

```bash
export EVALUATOR_API_KEY=...                 # Google AI Studio, free tier
python -m scripts.generate_audio_scripts     # write the dialogues
python -m scripts.build_audio --download     # two voices, 126 MB, once
python -m scripts.build_audio                # synthesize
```

**The model is checked, not trusted.** A draft is rejected when its numbers or Latin
terms do not appear in the lesson — the guard against an overview that teaches invented
figures — and also when it is a monologue, a verbatim quote, or opens like a radio show.
Rejections are retried with the complaints appended to the prompt. `--mock` produces a
deliberately invalid stub so the pipeline can be exercised without a key;
`validate_content` fails on any stub, so one cannot ship.

Each script records a `sourceDigest` of the lesson text. Edit the lesson and the
overview stops counting as current: the lesson simply has no audio until the script is
regenerated. Voicing a previous edition silently would be worse than no audio.

Synthesis is [Piper](https://github.com/OHF-Voice/piper1-gpl) locally on CPU, about 25×
faster than real time, with `lameenc` for MP3 so there is no ffmpeg dependency. Files
are built ahead of time; a lesson with no file reports `audio.available == false` and
the client hides the player. Tables become a pointer to the screen, diagrams are read
through `describe_diagram`, and Latin abbreviations go through `PRONUNCIATION` because
a Russian voice reads `SLA` as "сла".

---

## Content authoring

All authored content lives in `content/` as validated JSON. There is no seed
step and no content in the database: the tree, its lessons and its gate
scenarios are read from files and cached, so an edit takes effect on reload.

```
content/
├── tree.schema.json           map structure
├── lesson.schema.json         lesson blocks
├── gate-scenario.schema.json  gate exam (scenario + lesson links)
├── tree/
│   ├── tree.json              6 domains × 3 rings = 18 blocks, 71 nodes
│   ├── gates.json             which scenarios close which block
│   ├── lessons/*.json         one file per lesson
│   └── scenarios/*.json       gate scenarios
├── exercise.schema.json       formative exercise
├── glossary.schema.json       glossary of the System Design domain
├── diagram.schema.json        diagram as structure, not a picture
└── system-design/
    ├── tree.json              6 areas × 3 rings = 18 blocks, 96 nodes
    ├── gates.json             gates of the published blocks
    ├── glossary.json          489 terms, Russian and English
    ├── lessons/*.json         158 lessons, six sections each
    ├── exercises/*.json       96 formative exercises
    ├── diagrams/*.json        diagrams the client renders itself
    ├── scenarios/*.json       gate scenarios ready to publish
    └── scenarios-draft/*.json what the importer produces, before the authoring
```

The System Design tree is generated from the authored corpus, not edited by hand. The
importer is only the first of four steps: option weights, QA fixtures and exercise
acceptance cannot be derived from prose, so they are authored in scripts of their own
and applied on top. Run all four, in this order, after editing the corpus:

```bash
python -m scripts.import_system_design ../docs/system-design-course.md
python -m scripts.publish_system_design   # weights, fixtures, remediation
python -m scripts.type_exercises          # exercise inputs and acceptance
python -m scripts.validate_content        # gate this in CI
```

Importing without the rest silently loses the authoring: every gate falls back to a
draft and every exercise back to `open`.

The validator enforces the schemas plus the rules they cannot express:

- the unlock graph is acyclic and every block is reachable from `D1`;
- a `published` block has a lesson for every node and a gate;
- a gate has **at least two scenarios** — with one, a retake becomes memorising
  which option was right, which is the quiz this product must not be;
- every positive signal in a rubric names the `lessonId` whose concept it
  checks, and every covered lesson has a `remediation` entry to send a failed
  learner back to;
- the v0.1 editorial rules still apply: evidence `order` is 1..n with no gaps,
  one option scores ≥20, at least one non-reference option earns ≥8, and the QA
  fixtures cover strong / weak / defensible-alternative.

All 18 blocks are `published`: 90 lessons, 18 gates, 36 gate scenarios. The
`coming_soon` status is still supported and still enforced by the validator —
a block whose lessons are not written yet appears on the map with its nodes and
says so rather than pretending to be locked — but nothing uses it right now.

### Languages

Content is authored in Russian (v0.2 §16): the source map and the ICP are both
Russian-speaking. The app's own chrome is still bilingual, and the language a
request renders in is resolved in `app/deps.py`:

1. the `X-Content-Language` header, if the client sent one — this closes the gap
   between switching language in the app and the profile update landing;
2. otherwise `user_profiles.language`, the durable preference.

`Accept-Language` is deliberately ignored: HTTP clients set it from the device
locale, so honouring it would let the phone override a deliberate in-app choice.
The profile copy is also the only one the evaluation worker can read, since it
runs long after the request that queued it.

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
unknown skill keys, code fences, empty coaching), and over HTTP the whole v0.2 loop:

- a new account sees all 18 blocks with exactly one open, and a locked block still
  opens and explains what has to be passed to reach it;
- a gate cannot be started while lessons remain — asserted against the API, not the UI;
- passing writes `passed`, XP and the unlock in one transaction, and failing takes no
  XP, locks nothing, and returns `remediation` pointing at named lessons;
- a retake serves a different scenario, and re-passing a block awards nothing;
- picking an option without reasoning cannot reach 70, because evidence plus decision
  caps at 40;
- ownership rejection, analytics free-text stripping, account deletion;
- the unlock graph is acyclic and reachable, and every gate has two scenarios.
