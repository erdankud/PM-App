# PM Thinking Coach — context for Claude Code

This file is read automatically by Claude Code at the start of every session in
this repo. It exists so a fresh session has the same ground rules a human
teammate would get on day one.

## What this is

An iOS course for people entering product management from zero. The skill map
of the profession (71 nodes, 6 domains, 3 rings) becomes a route: short
authored lessons explain a skill, then a practical gate — a real situation with
incomplete data — checks that the learner can apply it, not recite it. Passing
a gate opens the next block.

## Source of truth

`docs/product-spec-v0.2.md` is authoritative for the product tree.
`docs/system-design-spec.md` is authoritative for the seventh domain, System Design;
it extends v0.2 rather than replacing it, and `docs/system-design-course.md` is the
authored corpus that `scripts/import_system_design.py` turns into content files.
`docs/product-spec-v0.2.md` It supersedes v0.1
(`docs/product-spec.md`) for §1–5, §7–12, §14–15, §19, §21–23, and keeps v0.1's
§13 (AI behaviour), §16 (iOS architecture), §17 (auth/privacy), §20
(monetisation) and §24 (implementation boundaries). When the two disagree, v0.2
wins; when v0.2 is silent, v0.1 still applies. Architecture and the reasoning
behind key decisions: `docs/architecture.md` (written for v0.1; the trust
boundaries it explains are unchanged).

## Non-negotiables — enforce these in every change

- The server owns score, XP, skill deltas **and unlock status**. The client
  renders `locked / available / in_progress / gate_ready / passed` and never
  derives availability. `POST /gates/{id}/start` re-checks it, so a UI bug
  cannot open a gate early.
- No AI provider key or call ever goes in the iOS client. Evaluation is
  server-side only (`server/app/ai/`).
- The authored consequence (shown right after submit) is separate from AI
  feedback and must never depend on model/provider availability.
- Exactly 3 root tabs: Map, Progress, Profile. No chat tab, no paywall, no
  leaderboards, no user-generated content (v0.1 §24, still in force).
- Lessons are authored. The model never generates teaching content — it only
  evaluates a submission (v0.2 §1, invariant 6).
- A gate needs at least two scenarios. With one, a retake becomes memorising
  which option was right, which is the quiz this product must not be.
- Failure is information: never take XP away for a failed gate, never lock
  anything, and always return `remediation` pointing at specific lessons.
- Scoring rewards reasoning, not just which option was picked: rationale +
  communication = 60/100 pts vs. 25 for the decision itself
  (`server/app/services/scoring.py`). The pass threshold is 70 on the total, so
  option choice plus full evidence review (40) can never pass on its own. Flag
  anything that would turn this into a single-right-answer quiz.

## System Design — the seventh domain

- A second tree, same grammar: 6 areas × 3 rings = 18 blocks, 96 nodes. It lives in
  the Map tab behind a **Продукт / Системы** switcher — not a fourth tab, because the
  three-root-tab rule is not up for revision, and not a seventh sector, because 18
  more blocks would make the ring unreadable.
- **Open from day one**, independent of the product tree: people arrive with different
  backgrounds and someone from engineering may start here. The UI recommends `D1`
  first — a hint, not a lock.
- Content is authored in `docs/system-design-course.md` and imported, never hand-copied.
  The importer alone does not produce publishable content — two authoring layers sit on
  top of it, each in its own script, because neither can be derived from the prose:

      python -m scripts.import_system_design ../docs/system-design-course.md
      python -m scripts.publish_system_design   # веса опций, QA-фикстуры, remediation
      python -m scripts.type_exercises          # поля ввода и приёмка упражнений
      python -m scripts.validate_content

  Run all four after editing the source; the JSON under `content/system-design/` is
  generated, not the source of truth, and re-importing without the other three silently
  drops the authoring (gates go back to drafts, exercises go back to `open`).
- Lessons here are six fixed sections (вопрос, цена, суть, пример, границы, вывод) and
  run 12–15 minutes, not 3–5: `estimated_minutes` is a property of content, not a
  product constant.
- Exercises are **formative**: outside `final_score`, no XP, no effect on gate
  availability, and the reference reasoning is returned on every submit including an
  empty one. `ExerciseAttempt` is deliberately not linked to `BlockProgress`.
- 55 of the 96 exercises are typed in `scripts/sd_exercise_types.py` (227 checkable
  fields): `estimation` checks an interval, `classification` checks a choice against the
  reference. The other 41 stay `open` on purpose — their answer is a paragraph, and a
  field with an interval would not check it, only pretend to. Nothing here says
  "wrong": an estimate is «порядок верный / отличается», a choice is «как в разборе /
  иначе, чем в разборе». `tests/test_system_design.py` submits every reference answer
  back and requires it to pass, so an interval that excludes its own эталон fails CI.
- Diagrams are structure, not pictures: 8 primitives, 3 edge types, rendered by the
  client and described in words for VoiceOver automatically.
- `system_design` is the eighth competency. The prompt's `skill_deltas` key list is
  generated from `SKILL_KEYS` so it cannot drift again.
- **All 18 blocks are published**: 96 nodes, 158 lessons, 36 gate scenarios (2 per gate),
  108 QA fixtures, 489 glossary terms. The source carries neither option weights nor QA
  fixtures — a scenario cannot be published without them — so those live in
  `scripts/sd_supplements.py` and `scripts/publish_system_design.py` turns each draft in
  `content/system-design/scenarios-draft/` into a publishable scenario. The drafts stay:
  they are what the importer produces, and the diff between draft and published is
  exactly the authoring.

## Current state (as of the last working session)

- Backend: FastAPI + SQLAlchemy + Alembic, SQLite for dev, Postgres in
  production via docker-compose. 97 tests passing at last check.
- Evaluator: `EVALUATOR_PROVIDER=mock` (deterministic keyword heuristic) — no
  real AI provider key has been chosen yet. Good enough to exercise the flow;
  coaching text reads as a stub, and gate calibration against the QA fixtures
  is not meaningful until a real provider is wired up.
- Content: **all 18 blocks are written and published** — 71 nodes, 90 lessons,
  18 gates, 36 gate scenarios (2 per gate), 108 QA fixtures. No block is
  `coming_soon` any more. Each domain has one fictional company running through
  all three of its blocks (D — «Смена», V — «Диспетчер»/«Сурма», R — «Полка»,
  M — «Реестр», G — «Ветка», S — «Кедр»), and each gate's second scenario uses a
  different company so a retake cannot be passed from memory. Inner-ring gates
  are `foundation`/`developing`, outer-ring (`D3 V3 R3 M3 G3 S3`) are
  `advanced`. A full traversal D1 → … → S3 was verified end to end through the
  API: 18/18 blocks reachable and passable.
- `content/tree/roles.json` now carries all ten role overlays, read off the
  source diagram: `product_manager` spans all 71 nodes, the nine specialised
  roles hold 13–29 each. The rule for a node on a contour's edge is written into
  the file's `sourceAttribution`: it belongs to the role when more than half of
  its card lies inside. `validate_roles()` in `app/tree_content.py` checks the
  overlays still name real nodes, and `tests/test_roles.py` asserts it — a
  renamed node must not silently drop out of a role.
- Per-node `aiImpact` is still `null` everywhere: the source map does not carry
  it and it must not be invented.
- Both trees are complete: the product tree (18 blocks, 71 nodes) and System Design
  (18 blocks, 96 nodes) are fully published. The corpus totals 254 lessons, 36 gates,
  72 gate scenarios.
- The «Полка» running example is numerically consistent across the System Design
  corpus: 180 тыс. активных × 1.4 сессии ≈ 250 тыс. сессий и ~20 тыс. заказов в сутки
  при 8 млн заказов накопленным итогом. Add a new number about «Полка» only after
  checking it against those; the sweep is a grep for `Полк` over
  `content/system-design/{lessons,exercises}`.
- The 15 v0.1 scenarios have been rewritten into blocks (v0.2 §15 step 8) and the
  old library is gone: each case now sits in the gate of the block whose lessons it
  examines, in Russian, with a company of its own. Fifteen gates therefore have
  three scenarios instead of two (`R1`, `M1`, `S1` still have two). The originals
  live in git history; `scripts/qa_evaluate.py` now runs the fixtures of the gate
  scenarios and reports both band misses and ordering problems.
- Language: content is authored in Russian (v0.2 §16). The app's own chrome is
  still English/Russian with a switch, and the language the AI writes coaching
  in follows the profile.
- iOS: SwiftUI, MVVM, personal (free) Apple ID team, so Sign In with Apple is
  removed from the target and the `#if DEBUG` dev-auth path is used instead.
- Local run: `server/README.md`. Python 3.11 venv, SQLite,
  `alembic upgrade head`, `uvicorn app.main:app --reload --host 0.0.0.0
  --port 8000`. There is no seed step any more — tree, lessons and gate
  scenarios are validated content files. iOS `API_BASE_URL` points at the
  Mac's LAN IP, not localhost, because a physical device cannot reach it.

## Before making changes

- Read `docs/architecture.md` — it explains *why* things are split the way
  they are (trust boundaries, idempotency, evaluation failure handling), not
  just what the code does.
- Check `server/tests/` for the behavior a change might affect; this project
  treats "server owns X" as something tests assert, not just document.
- Content lives in `server/content/tree/` (map, lessons, gates, gate scenarios)
  and must pass `python -m scripts.validate_content`, which also proves the
  unlock graph is acyclic and fully reachable from `D1`. A block marked
  `published` must have a lesson for every node and a gate with 2+ scenarios.
- Every positive signal in a gate rubric names the `lessonId` whose concept it
  checks, and every covered lesson needs a `remediation` entry. That link is
  what makes a failed gate actionable instead of discouraging.
- Nothing about the language a learner reads in may change what they score.
  `tests/test_localization.py` asserts this directly (identical submission, two
  languages, identical score).
