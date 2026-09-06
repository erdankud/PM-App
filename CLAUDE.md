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
  cannot open a gate early. **Staged unlocking is currently off**
  (`UNLOCK_ALL_BLOCKS=true`): every block is open from day one. That is a policy
  flag, not a move of ownership — the server still decides and still re-checks,
  and `tests/test_tree_flow.py` exercises both settings so the unlock graph stays
  working for when the route comes back.
- No AI provider key or call ever goes in the iOS client. Evaluation is
  server-side only (`server/app/ai/`).
- The authored consequence (shown right after submit) is separate from AI
  feedback and must never depend on model/provider availability.
- Exactly 3 root tabs: Map, Progress, Profile. No chat tab, no paywall, no
  leaderboards, no user-generated content (v0.1 §24, still in force).
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

## Lesson audio overview

- Each lesson can carry an **audio overview** — two hosts talking about the lesson,
  in the NotebookLM sense. It is deliberately not the lesson read aloud: reading
  written prose out loud always sounds like reading, which is the thing this replaces.
- Roles are fixed corpus-wide: `guide` asks the questions a listener would ask,
  `expert` answers as a practising PM. Two voices (Светлана / Дмитрий), because one
  voice for both speakers collapses the dialogue back into a monologue.
- The dialogue is **written once, at build time**, and stored as content in
  `content/<tree>/audio-scripts/<lessonId>.json`. The runtime never calls a provider;
  a script can be read, reviewed and hand-edited like any other content file.

      export EVALUATOR_API_KEY=...                      # Google AI Studio, free tier
      python -m scripts.generate_audio_scripts          # пишет диалоги
      python -m scripts.build_audio                     # синтез, ~27 с на урок
      python -m scripts.validate_content

- **The model is checked, not trusted.** `validate_script` rejects a draft whose
  numbers or Latin terms do not occur in the lesson, which is what stops the overview
  from teaching invented figures. It also rejects a monologue, a verbatim quote of the
  lesson, and radio-host openings. A rejected draft is retried with the complaints fed
  back into the prompt.
- `--mock` exists only to exercise the pipeline without a key. Its output is a stub
  that fails validation on purpose, and `validate_content` fails on any script with
  `provider: "mock"` so a stub can never ship.
- `sourceDigest` in each script is the digest of the lesson text. Edit the lesson and
  its overview stops counting as current: `load_script` returns None, the lesson has
  no audio until the script is regenerated. Silently voicing a previous edition is worse.
- The mp3 name and the URL carry a hash of the dialogue, so only changed overviews are
  rebuilt and a client cache can never serve a stale edition.
- Tables are not read aloud (a grid as a list of cells is unfollowable); diagrams are,
  through `describe_diagram`. `PRONUNCIATION` in `app/services/audio.py` spells Latin
  abbreviations out; it was written for Piper, whose espeak backend read `SLA` as «сла»,
  and is worth re-checking against the neural voices before adding to it.
- Synthesis is `edge-tts` — Microsoft's neural voices, the ones the Edge browser reads
  pages with. Free, no key, ~27 s per lesson (whole corpus ≈ 2 h). Piper was tried first
  and rejected: fully offline and twenty times faster, but its prosody is flat enough
  that the result sounds robotic, which defeats the point of an overview.
- **Know what this leans on.** `edge-tts` reaches an undocumented endpoint. Microsoft
  grants no right to use it outside the browser, access can be withdrawn, and stale
  clients are already rejected — 7.0.2 gets a 403 where 7.2.8 works, so expect to bump
  the pin. Because synthesis happens at build time, an outage stops new overviews from
  being built and never touches the ones already serving.
- `WORDS_PER_MINUTE` is measured, not looked up, and depends on the voices and
  `SPEECH_RATE` — re-measure it if either changes.
- Synthesis dependencies live in `requirements-audio.txt` and are **not** in the runtime
  image: the API serves prebuilt files and never synthesizes. `server/var/audio` is
  generated and gitignored.

## Signing in

- Four identity paths, and **the server says which of them exist**: `GET
  /v1/auth/methods` reports `password / google / apple / developer` plus the Google
  Client ID. A client never decides this for itself — a Google button with no Client
  ID behind it is a promise the server cannot keep.
- **Email and password** (`/auth/signup`, `/auth/signin`) is the path that works with
  no console setup. Hashing is `hashlib.scrypt` from the standard library, not bcrypt
  or argon2: it is a real KDF and it does not add a natively-built dependency for one
  operation. Cost parameters live inside the hash string, so they can be raised
  without invalidating stored passwords.
- **Google** (`/auth/google`) verifies the ID token against Google's JWKS exactly the
  way `app/apple.py` verifies Apple's, and links by `sub`, never by email — an address
  on a Google account can change. A verified address does link an account created by
  password to the same person rather than making a second one. Google OAuth is free;
  it needs a Client ID from Google Cloud Console and no billing.
- Sign-in errors never distinguish "no such account" from "wrong password": that
  difference is how you enumerate someone's registered addresses. Signing **up** on a
  taken address does say so, because there the person needs to be told to sign in.

## Languages

- The interface has always been bilingual; **content is now bilingual too**. Russian is
  the authored corpus and the only source of structure. English is an **overlay**:
  `content/i18n/en/<same relative path>.json` holds a flat map of `path -> English
  text` and is merged over the authored file when it is read.
- The overlay exists so that a translation run cannot damage the source — it writes to
  a different directory — and so that **the rubric, option weights and QA fixtures live
  in exactly one copy**. They are not in `SPECS` in `app/i18n_content.py`, so there is
  nothing to translate: "language never changes the score" is a property of the
  construction, not of discipline. The one exception is `rubric.remediation[].gap`,
  which the learner reads after a failed gate.
- `sourceDigest` works like the audio scripts': edit a lesson and its translation stops
  counting as current, so the reader gets today's Russian rather than last week's
  English. A half-translated file is an error in `validate_content`, not a warning —
  mixed language reads as a broken app, not as "not translated yet".
- `titleEn` (domains) and `termEn` (glossary) were written by the author. They are used
  as they are and applied **after** the overlay, so authored English always beats
  machine English. The five terms whose `termEn` is a dash get translated instead.
- Producing the English corpus:

      export EVALUATOR_API_KEY=...
      python -m scripts.translate_content            # весь корпус, возобновляемо
      python -m scripts.validate_content

  The run is resumable: a file whose overlay matches the source digest is skipped, so a
  run stopped by quota is continued by the same command. Files are batched **across**
  files into one request — free tiers meter requests, not volume — so the corpus is
  ~62 requests rather than ~450.
- **The translation is checked, not trusted** (`app/services/translation.py`): a missing
  field, a lost or invented number, broken `[[term]]` markup, leftover Cyrillic, or an
  exercise reference that no longer matches its own choices all reject the attempt and
  retry with the complaints fed back. Every overlay is marked `translationStatus:
  "machine"`; a human-reviewed file sets `"reviewed"` by hand.
- Audio is per language: `content/i18n/en/<tree>/audio-scripts/`, English voices, its
  own prompt (the overview is written in English, not translated from Russian — a
  translated conversation sounds translated), and its own measured `WORDS_PER_MINUTE`
  (172 for English, 110 for Russian). The mp3 name carries the language.

## Web client

- `web/` is the same product for the desktop, on **the same backend**: same account,
  same map, same lessons, same gates. Nothing about ownership changes — the server still
  decides score, XP and unlock status, and the client only renders them.
- It is served by the API process itself from `/app` (`server/app/main.py`), so there is
  one origin: no CORS, no second address to configure, and `Authorization` works on the
  audio files. There is **no build step** — plain ES modules, no npm, no bundler. Adding
  a toolchain for twenty screens would put a second build system into a repo that has
  none. The price is no version in the filenames, so outside production the files go out
  with `Cache-Control: no-cache`.
- `web/src/strings.js` is **generated** from the iOS string table and must never be
  hand-edited:

      python3 web/tools/port_strings.py

  Both translations live on one line in `ios/.../Strings.swift` precisely so drift is
  visible in review; a second hand-written copy would diverge on the first edit. Add UI
  copy there, then regenerate. The transpiler is not a toy — it already caught three
  places where a parameter name collided with a sibling key.
- The three root tabs are three sidebar items. A desktop bottom tab bar would be wrong,
  but the rule is about how many roots there are, not where they sit.
- Sign in with Apple is not wired up on the web: it needs a Services ID and a verified
  domain, which the free personal Apple account does not have. The dev path is used
  instead, and the button only appears when `/health` reports `devAuthEnabled` — the
  server decides, not the client.

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
