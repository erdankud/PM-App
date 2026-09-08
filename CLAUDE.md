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
- **4 root tabs: Learn, Skills Map, Progress, Profile.** This changed on the author's
  instruction and supersedes v0.1 §24's "exactly 3". The reason the rule existed still
  holds and still binds: no chat tab, no paywall, no leaderboards, no user-generated
  content. What split is the map — daily work («what do I read now») and the overview of
  the whole profession are different jobs, and making the overview the front door meant
  pushing through it to reach a lesson. Splitting further needs the same kind of reason.
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
  Skills Map behind a **Продукт / Системы** switcher — not a root of its own, because
  the two trees are the same thing for two audiences, and not a seventh sector, because
  18 more blocks would make one map unreadable.
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
- `titleEn` (domains), `termEn` (glossary) and `modelsEn` (node models) were written by
  the author. They are used as they are and applied **after** the overlay, so authored
  English always beats machine English. The five terms whose `termEn` is a dash get
  translated instead.
- `modelsEn` exists because most model names are international — «5 Whys», «HEART»,
  «RICE» — and were therefore excluded from translation altogether. Fourteen are not
  («Скрипт от гипотез»), and they showed up as Russian on the English screen. They carry
  industry names, not translations — «Матрица Ансоффа» *is* Ansoff Matrix — so a machine
  has nothing to invent here. `modelsEn` matches `models` position for position, and
  adding it does **not** stale the overlay: `digest()` covers only the translatable
  fields.
- **`tests/test_localization.py` sweeps every English response for Cyrillic.** A fully
  translated corpus does not mean a translated screen, and both ways of breaking that
  have already happened: `get_block` called `lessons_for_block` without a language, so
  every lesson title in a block came back in the authored language; and `TREE_TITLES`
  was hardcoded Russian in the router. Neither is visible in `validate_content`, which
  only checks the files. Check the response, not the corpus.
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

## Visual language — monochrome and glass

- **Black, white and translucent white.** No brand hue. The palette that used to be
  sand-and-green («Роща», in git history) was replaced wholesale: colour no longer
  encodes anything except the six domains on the map.
- The twelve-step scale survived the change because its job survived it — steps 1–2 are
  page grounds, 3–5 component surfaces, 6–8 borders, 9–10 solid fills, 11–12 text. Only
  the values changed, to Tailwind's neutral scales with pure black and white at the
  poles. Components still read **roles** (`--surface`, `--separator`, `--accent`), never
  steps.
- **Liquid Glass is a material of four layers**, and dropping any of them turns it back
  into a pale rectangle: blur *with* a saturation lift (colours behind stay alive rather
  than going muddy), a gradient across the plate itself, a **specular rim** — a 1 px
  gradient border cut out with `mask-composite: exclude` so light catches the edge and
  not the face — and a shadow that lifts it off the content. `.glass` / `.glass-strong`.
- **It only works over content.** There is nothing to refract on empty white, so it
  lives on the floating layer and nowhere else: the rail, the map's zoom controls and
  hint, the capsule switchers. This is why the sidebar was changed from a grid column to
  a fixed floating rail — as a column nothing passed behind it, and glass there would
  have been a grey box pretending.
- The rim is drawn by `::after`, so anything inside a glass surface needs its own
  stacking context (`position: relative; z-index: 2`) or the rim covers it.
- Dark theme is a clean inversion — black ground, white ink — so the monochrome logic
  holds in both. Nothing is defined only inside the media query.
- On the map the domain hue survives as a **very light fill and the card's border**;
  titles are black like everything else. Six sectors have to stay distinguishable, and
  position alone does not do it at overview scale — but the surfaces stay monochrome.
- Heavy weights, `clamp()` sizes, line-height below 1 on display type, negative
  tracking. Primary actions are black pills with a white circled arrow rotated −45°;
  secondary actions are white pills with a black rule that swap ground and ink on hover.

## Type

- **Open Sauce One** (SIL OFL, `marcologous/Open-Sauce-Fonts`) for Latin, **Onest** for
  Cyrillic, **Literata** for lesson body, **IBM Plex Mono** for designations. All four
  self-hosted in `web/fonts/`; nothing is fetched from a third-party host.
- Open Sauce One has **zero Cyrillic glyphs** — 371 characters, all Latin. The corpus is
  Russian, so as the only face it would fall back on every heading. It is therefore
  declared with a `unicode-range` covering Latin only, and the browser picks per
  character: `PM Thinking Coach` and the numerals come out in Open Sauce, «Услышать
  клиента» in Onest. Check coverage before adopting any display face here; this is the
  second one to fail on it (Outfit was the first).
- The licence file ships beside the fonts (`OpenSauceOne-OFL.txt`).

## Motion

- `web/src/motion.js`. Two things only: the splash counter and staggered reveal, both
  from the reference brief, both off in `prefers-reduced-motion`.
- The splash counts 0→100 in 2000 ms, bottom-left, then fades. It is driven by
  `performance.now()` and `requestAnimationFrame`, **not** by a 20 ms `setInterval` as
  the brief specifies: a background tab clamps timers to a second, which turned a
  two-second count into a ninety-second one. A hard timeout finishes it regardless,
  because a hidden tab gets no frames at all and the splash would otherwise never leave.
- `revealOnScroll` uses an IntersectionObserver at threshold 0.15, fires once, 24 px
  rise, 120 ms stagger. It carries a **1200 ms safety net**: an observer never fires in
  a hidden tab, and without the net the reader comes back to a page stuck at opacity 0.
  The animation is decoration; the content is not.
- Splash shows once per session (`sessionStorage`), not once per navigation.

## Learn — the home screen

- `/learn` is the root. It answers two questions and nothing else: **which direction am
  I on, and what do I read next.** It deliberately does not show level, XP or the eight
  competencies — the Progress tab owns those, and two of three tabs printing the same
  numbers is how a product stops being read.
- Three parts, in the order they are used: the **six directions** (which is current,
  what exists, how far each one is), the **black plate** with the single next lesson,
  and the **current block's lessons** as a list.
- The **gate is the last row of that list**, not a separate page. Before this, lessons
  were read on one screen and the gate sat on another, and the link between them lived
  in the reader's memory.
- The **Продукт / Системы** switcher lives on both Learn and the Skills Map, and the
  choice is shared through `web/src/tree-kind.js`. Two copies of that state would part
  ways on the first toggle and leave someone studying one tree while looking at the
  other. The chosen direction is remembered per tree (`pmcoach.learnDomain.<kind>`),
  because the two trees have different six directions.
- The chosen direction is remembered. Which block inside it is
  "current" uses the same order as the map's old recommendation: gate open → started →
  first available.
- Under the title sits **one paragraph** saying the six directions are the competencies
  a product manager is made of, with a deliberately quiet **Learn more** opening a
  dialog: the six directions with a line each, the three levels with who they are for,
  and the source. The copy paraphrases the Product Architecture Framework's own skill
  map and names it; the six System Design areas are written here, built around the
  `keyQuestion` each area already carries in content.
- The **blocks of the chosen direction** sit between the switcher and the black plate —
  three chips with progress. They are not decoration: clicking one changes which block
  the lesson list below shows, so the recommendation is a starting point, not rails.
- **The language switch lives only in Profile.** It had been in the rail and on the
  sign-in screen as well; three ways to do one thing, and the rail is for navigation.
  Nothing is lost on the way in — `initLanguage()` falls back to the browser's language,
  so the sign-in screen already arrives in the visitor's own.
- It costs two requests — `/tree` for directions and blocks, `/blocks/{id}` for the
  lesson list. If the block list fails the screen still renders: the switcher and the
  continue button do not depend on it.

## The map: the source diagram, made interactive

- Three shapes were tried and thrown away before this one — a **ring** (neighbouring
  sectors looked connected when the branches are independent), a **fan** (labels ran
  along slanted lines), and an orthogonal **skill tree** (legible, but a grid of block
  codes is not the map this product is about). What ships is the source diagram itself:
  «Skill Map of Product Management», Product Architecture Framework, Сергей Тихомиров.
- **Six sectors, three rings, one card per skill.** The card is exactly what the source
  legend defines: skill name, the key question that characterises it, and the set of
  models used in its context. Sectors run clockwise from the top in the source's own
  order (`SECTOR_ORDER` in `web/src/views/atlas.js`) — the content's `order` field is
  reading order, not a position on the wheel.
- **A card is a skill, and it opens a lesson.** The gate is not on the map at all; it
  lives on the block page. Clicking selects and fills the panel, the panel lists that
  skill's lessons and opens one. 56 of the 71 skills have exactly one lesson, so for
  most cards the card *is* the lesson.
- **The layout is computed, not hand-placed.** Each node is seeded inside its wedge
  (sector × ring) with alternating depth, then a relaxation pass pushes overlaps apart
  along whichever axis they overlap least, with a soft pull back into the wedge. A card
  may cross the dashed sector line, exactly as it does in the source. This is why the
  map survives a new node; the printed original does not.
- Ring radii are set by **density, not taste**: a band must hold up to 24 cards of
  176 × 92 with roughly twice their area, or relaxation squeezes them outward and the
  drawing sprawls. Change `CARD_W/H` or the node count and recompute.
- **Pan, zoom and level of detail.** Wheel zooms at the cursor, drag pans, two fingers
  pinch, and the buttons zoom about the canvas centre — never about the origin, because
  the middle of the map is a hole. Below k≈1.7 the question and the models are hidden
  and below k≈0.9 the titles go too: on an overview they are mush, and a card that is a
  coloured tile at a distance is what the printed sheet looks like from two steps away.
  The map opens at the overview, like any map.
- **Two traps live in `panZoom`, both already sprung once:**
  - Its render is scheduled with `requestAnimationFrame`, and a hidden tab gets no
    frames. Remembering "a frame is already queued" then deadlocks the map forever —
    zoom, buttons and drag all go silently dead. `schedule()` therefore draws
    synchronously while `document.hidden`, and flushes a stale frame on
    `visibilitychange`.
  - Pointer capture is taken **only once a drag really starts** (4 px of slop), never on
    `pointerdown`. Capturing on press retargets the compatibility `click` to the
    capturing element, so the card underneath never receives it and the map stops
    opening lessons. A click that follows a drag is swallowed in a capture-phase
    listener, because it is the tail of a gesture, not a choice.
  - Verifying either of these with `element.dispatchEvent(new MouseEvent('click'))` is
    worthless: dispatching straight at the node bypasses hit-testing and capture, which
    is exactly what breaks. Drive real input, at the coordinates the driver expects.
- `panZoom` is separate from drawing on purpose: selecting a card re-renders **only the
  panel**, because rebuilding the scene would throw away the position the reader just
  navigated to.
- The server side is `GET /v1/tree/{kind}/map` (`_map_response`), a purpose-built
  endpoint rather than an extension of `/tree`: both clients read the tree contract, and
  putting 71 nodes with their lessons into it would make everyone pay for one screen.
  **Edges are not invented** — inside a block they are the node order, between blocks
  they are the unlock graph. `tests/test_tree_flow.py` asserts both ends of every edge
  exist and that no third kind appears.
- One layout serves both trees: product is 6 × 3 with 71 nodes, System Design 6 × 3
  with 96.
- Three things mark **your own progress** on it, added on the author's instruction:
  - **Heavy solid dividers** between the six directions — they are territories, not
    dashed guides under the cards.
  - A **tally in the middle**: lessons completed out of the corpus.
  - Direction labels are sized by the **overview**, not by taste: at that zoom the map
    is squeezed to roughly 0.21 px per scene unit, so anything under ~55 units is a
    smear. They are 58, which is why `OUTER` had to grow to make room for them.
  - A **red frontier line** — the only colour on an otherwise monochrome map, and it is
    not decoration: red marks exactly what you have covered. Per direction it stands off
    the centre in proportion to the lessons done there, and the radius between sector
    axes is eased with a cosine, because progress drawn as a hexagon reads as a shape
    with corners rather than as ground gained. With nothing done it is a circle around
    the tally.
- **iOS still draws the ring** (`Features/Tree/SkillRing.swift`). Porting the atlas is
  the next piece of work.

## Type and chrome

- Two self-hosted families in `web/fonts/`, wired through `web/fonts.css`: **Onest** for
  interface and headings, **Literata** for lesson body only. Both carry full Cyrillic —
  the corpus is Russian, which rules out most geometric display faces (Outfit has no
  Cyrillic at all, which is why it was never actually adopted).
- Only the `cyrillic`, `cyrillic-ext`, `latin` and `latin-ext` subsets are stored, and
  `fonts.css` is generated from the Google Fonts CSS with the URLs rewritten to
  `/app/fonts/`. **Nothing is fetched from a third-party host** — the web client is
  served from one origin and that property is worth two files in the repo.
- The serif is the content, the sans is the chrome: a lesson reads in Literata at
  18/1.72, but headings inside the lesson stay Onest because they are navigation
  through the text, not the text.
- **The sidebar is collapsed by default** (`pmcoach.sidebarCollapsed`, default `"1"`).
  Three roots whose icons are learned on day one do not need permanent labels; the
  choice is remembered, and labels stay in `title`/`aria-label` so a collapsed button is
  never a guess. On narrow screens the sidebar is a top row and labels come back.

## One column for every screen

- Every screen sits in the same container: `--page-width` (1080 px), centred in the space
  the floating rail leaves. **One width and one alignment** — the two have to move
  together. Progress and Profile were 780 while Learn was 1080; both were centred, and
  because centring divides the *leftover*, different widths put the left edge in
  different places and the app read as two apps. Left-aligning fixes the edge but throws
  away the composition, so the answer is one width, still centred.
- The map and the block page used to be wider (1720 and 1240). They are in the shared
  column now. The atlas lost about 8% of its scale by it — it is bounded by
  `min(width, height)` and height was already the smaller side — and stayed readable.
  Give a screen its own width only when it genuinely cannot work in the column, and
  expect the left edge to jump when you do.
- **Reading measure is the text's job, not the page's.** `.lesson-body` carries its own
  `68ch` cap rather than relying on a narrow page. Anything else that grows into long
  prose needs the same.

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
