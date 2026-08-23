# PM Thinking Coach

A daily PM decision gym. Each day you get one short, realistic product scenario:
inspect limited evidence, choose what to investigate, make a decision, defend it in
your own words, see plausible consequences, and get coaching on your reasoning.

This repository contains the first MVP build: an iOS app plus the server that owns
scoring, XP, dates, skill deltas, and AI evaluation.

```
pm-app/
├── ios/         SwiftUI app (iOS 17+, iPhone, portrait)
├── server/      FastAPI + SQLAlchemy + Postgres, evaluation worker, scenario content
└── docs/        Product spec and architecture notes
```

---

## What's built

| Spec area | Status |
|---|---|
| P0-01 Sign in with Apple | Server-side identity-token verification implemented; a dev sign-in path exists for local work before an Apple Developer account is configured |
| P0-02 Goal selection | Done |
| P0-03 Skill assessment (3 items) | Done — author-weighted, no AI call |
| P0-04 Personalised learning path | Done — deterministic, server-side, 7 days |
| P0-05 Daily challenge | Done — one per user per device-local date |
| P0-06 Investigate flow | Done — ≥1 evidence card required before deciding |
| P0-07 Decision + defence | Done — 30–600 char rationale, submit gated |
| P0-08 Consequences | Done — authored, returned with the submission, never model-generated |
| P0-09 AI feedback | Done — server-side worker, strict JSON validation, bounded retries |
| P0-10 Progress dashboard | Done |
| P0-11 History + read-only result | Done |
| P0-12 Error/retry handling | Done — local drafts, idempotency keys, pending/failed states |
| P0-13 Analytics | Done — event metadata only, rationale bucketed not stored |

15 published scenarios (5 foundation, 7 developing, 3 advanced) covering all six
skills, each with three QA fixtures.

**Not built, deliberately** (spec §24): chat tab, more than three root tabs,
user-generated scenarios, leaderboards, paywall, admin CMS.

---

## Non-negotiables this build enforces

These come from the spec and are wired into the code, not just documented:

- **The server owns score, XP, date and skill deltas.** The iOS client has no scoring
  logic at all — `PMThinkingCoachTests/AnalyticsPrivacyTests.swift` asserts it only
  renders what it receives. `GET /v1/today` computes the local date server-side from
  the declared timezone.
- **No AI key ever reaches the client.** Providers are configured only in
  `server/app/config.py` via environment variables. The client's `Info.plist` holds a
  base URL and nothing else.
- **Authored consequences are independent of the model.** They are snapshotted into
  `FeedbackEvaluation.consequence_snapshot` at submit time and returned immediately.
  If evaluation fails, the consequence still shows and XP stays pending.
- **Exactly three root tabs.** Today, Progress, Profile.
- **Reasoning is scored above option choice.** Rationale + communication = 60 of 100
  points; the decision itself is 25. Every scenario has at least one non-reference
  option worth meaningful partial credit, enforced by the content validator.

---

## Quick start

### 1. Server

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # defaults work as-is for local development
python -m scripts.validate_content
python -m scripts.seed
uvicorn app.main:app --reload
```

The API is now on `http://localhost:8000`, with the evaluation worker running
in-process. `python -m scripts.smoke` walks the entire P0 journey against it.

By default `EVALUATOR_PROVIDER=mock`, a deterministic offline stub so you can use the
app with no API key. It is **not** AI feedback and the server refuses to start with it
in production. See [server/README.md](server/README.md) for free-tier providers
(Gemini, Groq, OpenRouter).

### 2. iOS app

```bash
open ios/PMThinkingCoach.xcodeproj
```

Select an iPhone simulator and run. The Debug configuration points at
`http://localhost:8000`; Profile → Developer can override the host for a device build.

Sign in with Apple needs a real Apple Developer team, so on the simulator use
**Continue without Apple (development)**, which is compiled out of Release builds and
rejected by the server when `ALLOW_DEV_AUTH=false`.

---

## Tests

```bash
cd server && python -m pytest tests -q       # 76 tests
cd server && python -m scripts.validate_content
cd server && python -m scripts.smoke          # end-to-end, needs a running server
cd server && python -m scripts.qa_evaluate    # content QA against the live evaluator
```

iOS unit tests run from Xcode (⌘U) or:

```bash
cd ios && xcodebuild test -scheme PMThinkingCoach -destination 'platform=iOS Simulator,name=iPhone 16'
```

---

## Known gaps before beta

1. **The iOS app has not been compiled.** It was written in a Linux container with no
   Xcode or Swift toolchain available, so expect to fix a small number of build errors
   on first open. The backend, by contrast, is fully exercised by tests and a
   live end-to-end smoke run.
2. **Sign in with Apple needs configuration**: set `APPLE_CLIENT_ID` on the server to
   your bundle identifier, and enable the capability in your Apple Developer account.
3. **The evaluator is a stub until you set a provider key.** Run
   `scripts/qa_evaluate.py` with a real provider before showing feedback to anyone —
   the QA fixtures exist precisely to calibrate that.
4. **No app icon.** `Assets.xcassets/AppIcon.appiconset` is an empty placeholder.
5. **Retention policy is undocumented.** Deletion is implemented; the actual retention
   period needs a product decision before launch (spec §17).

---

## Documentation

- [docs/product-spec.md](docs/product-spec.md) — the product specification this build follows
- [docs/architecture.md](docs/architecture.md) — how the pieces fit and why
- [server/README.md](server/README.md) — API, providers, content authoring, deployment
- [ios/README.md](ios/README.md) — app structure, build settings, conventions
