# PM Thinking Coach — Product Specification (MVP)

> Repository copy of the specification this build follows, included so that section
> references in the code and READMEs resolve. The canonical, editable version lives in
> the "PM App" Claude project. If the two diverge, the project copy wins.

**Status:** Implementation-ready draft
**Platform:** iOS (iPhone first)
**Audience:** Product, design, and AI coding agents
**Version:** 0.1
**Last updated:** 2026-08-22

## 1. Executive summary

PM Thinking Coach is an iOS app that helps aspiring Product Managers practise product judgment, rather than passively consume PM theory. Each day, the user works through a short, realistic product scenario: they inspect limited evidence, choose what to investigate, make and defend a decision, see plausible consequences, and receive coaching from AI. The app turns repeated deliberate practice into a visible skill progression.

The MVP is deliberately narrow: onboarding, goal selection, a lightweight skill assessment, a personalised learning path, one daily PM challenge, AI feedback, and a progress dashboard. It is **not** a full course, a free-form AI chat, or a complete interview-prep platform.

### Core loop

`Scenario → investigate → make decision → defend decision → consequences → AI feedback → learn → next scenario`

The first release should make this loop satisfying and trustworthy in 5–10 minutes, before adding breadth.

---

## 2. Product vision

**Vision:** Make learning product management feel like building real judgment through safe, repeated practice.

**Positioning:** "A daily PM decision gym." The value is not a library of lessons; it is practice with feedback on reasoning, trade-offs, and communication.

**Product principles**

1. **Judgment over recall.** Ask users to decide under ambiguity, not memorise frameworks.
2. **Evidence before solution.** Reward investigation and well-scoped hypotheses.
3. **Multiple defensible answers.** Avoid presenting product work as a single-answer quiz.
4. **Feedback explains reasoning.** AI should name strengths, gaps, risks, and a better next step.
5. **Small daily habit.** A useful session fits into 5–10 minutes.
6. **Visible progression.** Users should see which PM skills are improving and why.

---

## 3. Problem statement

Aspiring PMs can find abundant courses, templates, and framework content, but struggle to turn that knowledge into decisions in ambiguous, cross-functional situations. They rarely get fast, structured feedback on how they investigate a problem, prioritise options, articulate trade-offs, or communicate a recommendation.

Without practice, learners either consume more content without building confidence or prepare in an unrealistic way for interviews and real work. The app creates a low-stakes, repeatable place to practise the PM thinking process.

---

## 4. Target users / ICP

### Primary ICP — career switcher / aspiring PM

- Has 0–2 years of product experience; may come from design, engineering, marketing, operations, consulting, or a founder background.
- Wants a structured way to become interview- and job-ready.
- Has 5–15 minutes per day, often on a phone.
- Knows some PM terms but lacks confidence applying them.

### Secondary ICP — early-career PM

- Associate PM, junior PM, or a new founder building product instinct.
- Wants short practice and feedback outside their current company context.

### Excluded from MVP focus

- Senior PMs seeking organisation-specific strategy coaching.
- Teams needing collaboration, administration, or enterprise learning management.
- Users seeking formal certification or accredited education.

### Jobs to be done

| Situation | Motivation | Desired outcome |
|---|---|---|
| Preparing for a PM role or interview | "I know frameworks but freeze on open-ended cases." | Practise reasoning and explain decisions clearly. |
| Starting a first PM job | "I want to build product instincts faster." | Identify what to investigate and make safer trade-offs. |
| Maintaining a learning habit | "Courses are hard to sustain." | Complete one meaningful practice exercise daily. |

---

## 5. Goals and non-goals

### Goals (MVP)

1. Let a new user reach their first evaluated decision within 10 minutes of install.
2. Deliver a complete daily scenario session in 5–10 minutes.
3. Give feedback that is specific to the user's decision and rationale, not generic PM advice.
4. Surface a simple, credible view of progress across PM skills.
5. Learn enough from onboarding and completed work to select a sensible next challenge.

### Success metrics and initial targets

Targets are hypotheses for the first 30 days after a usable beta; revise after instrumentation data exists.

| Metric | Definition | Target |
|---|---|---|
| Activation | New users completing onboarding and their first challenge within 24h | ≥ 55% |
| First-session completion | Started challenges that reach feedback | ≥ 70% |
| Time to first value | Install to first feedback | median ≤ 10 min |
| D7 learning retention | Activated users completing ≥ 2 challenges between days 2–7 | ≥ 25% |
| Feedback usefulness | Post-feedback "Useful" rating | ≥ 70% of responses |
| Daily challenge completion | Users opening today's challenge who submit it | ≥ 60% |

### Non-goals (MVP)

1. **Four independent modes.** Learn, Simulate, Interview, and Portfolio are product directions, not separate MVP tabs.
2. **Open-ended conversational tutor.** AI is constrained to scenario feedback; no persistent general-purpose chat.
3. **Full PM curriculum or video course.** Brief learning takeaways only, linked to the completed exercise.
4. **Live interviewer or voice simulation.** Interview mode is a later phase.
5. **User-authored/public scenarios, social feed, leaderboards, or collaboration.** These require moderation and a larger content system.
6. **Automated job placement, certificates, or claims that scores predict hiring performance.** Scores support practice; they are not credentials.

---

## 6. Assumptions and open questions

### Assumptions (non-blocking; use for MVP)

- iPhone-only, portrait orientation, iOS 17+.
- ~~App language is English for v1, even if future localisation is expected.~~
  **Superseded 2026-08-23 at the product owner's request.** The app ships English and
  Russian. The switch is in Profile and on the welcome screen and covers everything a
  learner reads: app chrome, scenario briefs, evidence, decision options, authored
  consequences, and AI coaching. Both languages are authored and checked in; nothing is
  machine-translated at request time, so the authored consequence stays independent of
  provider availability (§10.9). Rubrics, skill weights and QA fixtures stay in the
  authoring language — they are internal and feed the evaluation prompt. A published
  scenario is not valid until it is complete in every offered language.
- Users authenticate with Sign in with Apple; anonymous/local preview is not required.
- Initial scenario library is editor-created and shipped/seeded by the product team; users do not create scenarios.
- A scenario has one recommended learning path, but several answers may be defensible.
- AI feedback is generated server-side through an approved model provider and never directly from the iOS client.
- Daily challenge means one assigned scenario per user per local calendar day; no push-notification requirement for v1.
- A numeric score is motivating only when paired with an explanation; skill scores are directional, not scientific assessment.

### Open questions

| Question | Owner | Blocking? | Default for MVP |
|---|---|---:|---|
| What brand/name and visual identity should ship? | Product/Design | No | "PM Thinking Coach" working name. |
| Which AI provider/model and cost limit per evaluation? | Engineering/Product | Yes before production | Server-managed model with strict JSON output and per-user daily limit. |
| Can a user replay a completed scenario? | Product | No | Not in MVP; history shows result only. |
| What counts as "daily" when a user travels? | Product/Engineering | No | Device local date recorded with timezone. |
| Is paid access available at MVP launch? | Product/Growth | No | Free beta; entitlement interface exists but no paywall. |
| What level of human review is required for generated feedback? | Product/Safety | No for closed scenario set | QA feedback against seeded test submissions before release. |

---

## 7. User stories

### Onboarding and personalisation (P0)

- As an aspiring PM, I want to choose why I am learning so that challenges fit my goal.
- As a learner, I want a short skill assessment so that I begin at an appropriate level.
- As a learner, I want to see the learning path the app chose so that the experience feels intentional, not random.

### Daily practice (P0)

- As a learner, I want to see a concise realistic scenario so that I can practise without needing a long study session.
- As a learner, I want to reveal or select evidence to investigate so that I can form a decision before jumping to a solution.
- As a learner, I want to select a recommendation and explain it in my own words so that I practise communicating PM judgment.
- As a learner, I want to see consequences and AI feedback after submitting so that I learn what was strong and what to improve.
- As a learner, I want to resume a partially completed daily challenge so that interruptions do not lose my work.

### Progress (P0)

- As a learner, I want to see completed challenges, XP, and skill trends so that I know whether I am progressing.
- As a learner, I want to rate feedback as useful or not useful so that the product can improve feedback quality.

### Reliability (P0)

- As a learner, I want clear recovery when the network or AI evaluation is unavailable so that I do not lose my response.

---

## 8. MVP scope and functional requirements

### P0 — required to launch

| ID | Requirement | Acceptance criteria |
|---|---|---|
| P0-01 | Sign in with Apple authentication | Given a signed-out user, when they choose Continue with Apple, then an account/session is created or restored and the app proceeds to onboarding or Home. |
| P0-02 | Onboarding and goal selection | User selects one goal: `Break into PM`, `Grow in my first PM role`, or `Practise product thinking`. User can finish onboarding without optional profile fields. |
| P0-03 | Skill assessment | User completes 3 short diagnostic items. Each item uses a fixed scenario and 2–4 options plus optional short rationale. Results initialise skill baselines. |
| P0-04 | Personalised learning path | After assessment, app assigns a starting level and a 7-day path of challenge metadata. Assignment is deterministic and stored server-side. |
| P0-05 | Daily PM challenge | Home displays one challenge for today, its estimated time, primary skill, completion state, and a CTA. Only one active daily challenge can exist. |
| P0-06 | Investigate flow | Scenario has 2–4 evidence cards. User must inspect at least one before a decision can be submitted. The app records cards opened. |
| P0-07 | Decision and defence | User chooses exactly one predefined decision option and provides 30–600 characters of rationale. Submit remains disabled until both are valid. |
| P0-08 | Consequences | Submission immediately returns authored consequence text based on the decision option; it does not depend on AI availability. |
| P0-09 | AI feedback | Server evaluates the selected choice, opened evidence, and rationale against an authored rubric; response includes score, skill deltas, strengths, gaps, and one suggested next step. |
| P0-10 | Progress dashboard | Shows total XP, current level, completed challenge count, 7-day activity, and the six skill scores. It must clearly label scores as practice signals. |
| P0-11 | History | User can view a reverse chronological list of completed daily challenges with score and feedback status; detail may reopen the result screen read-only. |
| P0-12 | Error/retry handling | Draft answers save locally and server-side. If AI feedback fails, user sees the consequence and a retry state; duplicate submissions must not double-award XP. |
| P0-13 | Basic product analytics | Events in Section 15 fire with anonymous user ID/account ID and no free-text rationale content. |

### P1 — fast follow after launch

- Push reminder opt-in and local "daily challenge ready" notification.
- A 2–3 minute "Learn" recap attached to feedback, based on one framework or concept.
- Ability to retry a completed scenario as a new attempt (without rewriting historical attempt).
- User profile editing and explicit difficulty preference.
- Feedback export/share card.

### P2 — later modes

- **Learn:** structured micro-lessons and framework library.
- **Simulate:** longer multi-round simulation with stakeholder messages and richer branching.
- **Interview:** timed product-case practice, spoken answers, and interviewer-style follow-ups.
- **Portfolio:** guided case-study artefacts and shareable portfolio output.

---

## 9. Information architecture and navigation

### Root navigation

A native SwiftUI `TabView` with three tabs after onboarding:

1. **Today** — daily challenge and learning-path preview.
2. **Progress** — skills, XP, activity, history.
3. **Profile** — goal, account, privacy, sign-out.

Challenge screens are pushed modally/full-screen from Today and maintain their own step state. Do not expose future modes as empty tabs.

```text
Launch
 ├─ Signed out → Sign in with Apple → Onboarding → Assessment → Path Reveal → Today
 └─ Signed in → Today

Today → Challenge Brief → Investigate → Decide & Defend → Consequences → Feedback → Today
Progress → History → Read-only Result
Profile → Goal / Privacy / Sign out
```

### Navigation rules

- Back from any in-progress step saves a draft; user receives a non-blocking "Continue later" status on Today.
- User cannot jump to Feedback before valid submission.
- User can move backward among Brief, Investigate, and Decide before submitting; submitted attempts are immutable.
- On successful feedback completion, return button goes to Today, not an empty future mode.

---

## 10. Screen-by-screen UX specification

### 10.1 Welcome / sign-in

**Purpose:** Establish the practice promise and authenticate.

- Headline: "Practise thinking like a Product Manager."
- Supporting copy: "A short daily product scenario. Your decision. Clear feedback."
- Primary CTA: `Continue with Apple`.
- Secondary: Privacy link.
- Loading state disables duplicate Apple sign-in requests.
- If Apple auth is cancelled, remain on screen with a calm inline message only if necessary.

### 10.2 Goal selection

**Purpose:** Capture initial personalisation signal.

- Single-select cards: `Break into PM`, `Grow in my first PM role`, `Practise product thinking`.
- Each card has one-line description; no ranking or long form.
- CTA: `Continue`, disabled until selection.
- Persist choice immediately.

### 10.3 Skill assessment

**Purpose:** Calibrate path without feeling like an exam.

- Three fixed mini-cases, one per page, progress `1 of 3`.
- Each: brief context, 2–4 choices, "Why?" input optional, `Next`.
- Allow skipping optional rationale; require a choice.
- Final CTA: `See my starting point`.
- Assessment responses produce no AI call in MVP; score with author-defined option weights.

### 10.4 Path reveal

**Purpose:** Create commitment and explain personalisation.

- Show starting level: Foundation / Developing / Advanced (not a high-precision score).
- Show top two focus skills and next 7 days as compact cards: Day 1 active, Days 2–7 preview only.
- CTA: `Start today's challenge`.
- Do not claim this is a validated assessment.

### 10.5 Today (home)

**Purpose:** Make the next valuable action obvious.

- Header: greeting, current streak (if applicable), XP/level compactly.
- Hero card: today's scenario title, context label, primary skill, `5–10 min`, state-aware CTA: `Start`, `Continue`, or `Review`.
- "Your focus" shows top two skills and small trend indicators.
- If no assignment resolves, show retry button and an error event; do not fabricate a scenario locally.

### 10.6 Challenge brief

**Purpose:** Set decision context, stakes, and role.

- Show company type/name (fictional), user/problem, business context, goal, constraint, and task.
- Fixed "What good looks like" line: "Use the evidence, make a trade-off, and explain your choice."
- CTA: `Investigate`.
- No scoring hints or answer choices on this screen.

### 10.7 Investigate

**Purpose:** Model evidence gathering.

- Evidence cards are initially collapsed: e.g. `Funnel data`, `User interview`, `Engineering note`, `Business constraint`.
- Tapping reveals authored information; card becomes marked `Reviewed`.
- Show counter such as `2 of 4 signals reviewed`; require at least one reviewed to progress.
- CTA: `Make a decision`.
- Do not present a fake exhaustive research process; content makes evidence limits explicit.

### 10.8 Decide & defend

**Purpose:** Capture a concrete recommendation and reasoning.

- Show decision prompt and 2–4 mutually exclusive authored options.
- Each option: title + 1–2 sentence description; choice can be changed before submit.
- "Defend your decision" multiline input with placeholder: "What evidence, trade-off, and risk informed your choice?"
- Character count `0/600`; validation: 30–600 non-whitespace characters.
- CTA `Submit decision`; confirmation copy says feedback will assess reasoning, not only the option.
- On submit: create an idempotent `ChallengeAttempt`; disable CTA and show processing.

### 10.9 Consequences

**Purpose:** Provide immediate learning payoff even if AI is delayed.

- Show "What happens next" based on selected decision option.
- Include 1–2 outcomes and one trade-off; wording is authored, not model-generated.
- CTA `See coaching` requests/polls feedback status.
- If feedback is ready, move directly to Feedback; if pending, show progress with a `Try again` option. Do not lock the user indefinitely.

### 10.10 AI feedback

**Purpose:** Turn an attempt into a usable lesson.

- Header score: `X / 100` with plain-language band (e.g. "Strong reasoning").
- Sections in this order: `What you did well`, `What to strengthen`, `A sharper approach`, `Skill impact`.
- "A sharper approach" is 2–4 sentences: it must not say the user was wrong solely because they selected a non-reference option.
- Skill impact lists only changed skills and ranges from -3 to +8 per completed challenge.
- Buttons: `Rate feedback` (Useful / Not useful) and `Finish`.
- If unavailable after server retry, show a transparent fallback: consequence, XP marked pending, and CTA `Retry coaching`. Never invent feedback on device.

### 10.11 Progress

**Purpose:** Reinforce a practice habit, not competition.

- Current level and total XP.
- 7-day activity strip (completed / missed / today).
- Six skill rows: score 0–100, label, simple trend (up/down/steady) based on last five completed attempts.
- Completed challenges count and history link.
- Footnote: "Skill scores are practice signals based on your in-app work, not an assessment of job readiness."

### 10.12 History and profile

- History: title, date, skill focus, score, `Feedback pending` or complete; tap opens read-only result.
- Profile: selected goal, delete-account request entry point, privacy notice, sign out. Goal change updates future-path assignment only, never overwrites historical scores.

---

## 11. Scenario content model

The MVP needs a small, curated bank rather than generative scenario creation. Seed **12–18 scenarios** across levels and skills so that the first weeks do not feel repetitive.

### Required scenario structure

| Field | Description |
|---|---|
| `id`, `version`, `status` | Stable ID, content version, draft/published/retired status. |
| `title`, `summary`, `estimatedMinutes` | User-facing metadata. |
| `level` | Foundation, Developing, or Advanced. |
| `primarySkill`, `secondarySkills` | One primary and 0–2 secondary skills. |
| `tags` | e.g. onboarding, retention, prioritisation, research, B2C. |
| `brief` | Role, fictional company, context, objective, constraints, task. |
| `evidenceCards` | 2–4 cards with title, type, display order, and content. |
| `decisionPrompt` | The question to answer. |
| `decisionOptions` | 2–4 options, each with ID, label, description, consequence text. |
| `rubric` | Reference reasoning, evidence signals, option notes, positive/negative signals by skill. |
| `learnTakeaway` | One short authored concept/reference for a later P1 recap. |

### Initial skills (six)

| Skill | What the app measures in MVP |
|---|---|
| Product Sense | Problem framing, user value, and solution fit. |
| Analytics | Use of available data, metrics, and causal caution. |
| User Research | Asking what must be learned and using qualitative evidence. |
| Prioritisation | Explicit trade-offs, impact/effort/risk reasoning. |
| Execution | Sequencing, constraints, validation, and delivery awareness. |
| Communication | Clear, concise recommendation and rationale. |

### Content quality rules

- Fictional companies only; do not imply access to real company data.
- Every option must be plausible; at least one non-reference answer should receive meaningful partial credit when defended with evidence.
- Evidence must contain both helpful and conflicting signals where appropriate.
- Rubric should reward identifying uncertainty and a next validation step.
- Avoid trivia, exact framework terminology as a requirement, and "gotcha" wording.
- Every published scenario needs at least three QA test submissions: strong, weak, and defensible alternative.

### Example scenario outline (not production copy)

`New-user retention drops after onboarding redesign` → evidence cards on funnel drop-off, qualitative interview, engineering limitation → decisions: rollback, investigate first, ship personalisation, acquisition campaign → rubric rewards isolating the segment and validating the onboarding hypothesis before committing to a large solution.

---

## 12. Scoring, XP, and skill system

### Principles

- Score **reasoning and evidence use**, not merely "correct" option selection.
- Author-defined logic provides a stable baseline; AI adds nuanced assessment of the rationale.
- Scores should be explainable and bounded.
- Avoid penalty-heavy design. A weak attempt should still teach and encourage return.

### Attempt score (0–100)

| Component | Points | Source |
|---|---:|---|
| Evidence engagement | 0–15 | Number/type of evidence cards viewed; capped at 15. |
| Decision quality | 0–25 | Authored option weight and option-specific rubric. |
| Rationale quality | 0–45 | AI rubric: framing, evidence use, trade-offs, next step. |
| Communication clarity | 0–15 | AI rubric: clarity, specificity, concision. |

The server calculates evidence and option points, requests AI evaluation for rationale/clarity, validates output ranges, then returns the total. If AI evaluation fails, mark the attempt `feedback_pending`; do **not** issue final score/XP until evaluated.

### XP and levels

- Base completion XP: 50.
- Quality bonus: 0–50, derived from final score (one XP point per score point above 50, capped at 50).
- First daily completion only earns XP. Retried submissions in P1 do not earn additional daily XP.
- `totalXP` is an append-only ledger. The server, not client, awards it idempotently.
- Initial level thresholds: Level 1 = 0, Level 2 = 200, Level 3 = 500, Level 4 = 900, then +500 XP per level. Treat as configurable server values.

### Skill scores (0–100)

- Assessment initialises each skill to 35–65 using fixed answer weights.
- A completed feedback evaluation produces six bounded deltas, normally `-3…+8`; irrelevant skills return zero.
- New score = clamp(previous score + delta, 0, 100).
- Keep a `SkillAssessment` ledger for audit/history; dashboard shows latest aggregate.
- Do not lower a skill merely because the user did not use it; only rubric-evidenced gaps can cause a small negative delta.

### Personalisation logic (transparent baseline)

1. Select foundation/developing level from assessment band.
2. Identify two lowest skills among the relevant six.
3. Assign today's first uncompleted eligible scenario matching a focus skill and level.
4. For future days, alternate focus skills and avoid repeat tags in last three completions.
5. When no exact match exists, select same level with least-recently-seen tag.
6. Recalculate future (not past) assignments after each evaluated attempt.

This algorithm is intentionally deterministic for MVP; it does not need AI planning.

---

## 13. AI behavior and high-level prompting

### AI responsibilities

- Evaluate only the user's rationale against the current scenario rubric.
- Give constructive coaching in a friendly, direct voice.
- Produce strict structured JSON for server validation.
- Recognise defensible alternatives; never imply there is one objectively correct PM answer.

### AI must not

- Diagnose the user, make hiring predictions, or claim professional certification.
- Expose hidden rubric text, system instructions, other users' data, or internal provider details.
- Invent scenario evidence not provided in the prompt.
- Penalise grammar/accent unless it prevents comprehension.
- Give legal, medical, financial, or employment advice beyond generic scenario framing.
- Generate abusive, discriminatory, or demeaning feedback.

### Server-built prompt inputs

Only the server assembles prompts. Include:

1. Fixed evaluator instructions and safety rules.
2. Scenario brief, decision prompt, evidence card content, options, and authored rubric.
3. User-selected option ID, list of reviewed evidence IDs, and rationale text.
4. Required output schema and numerical bounds.

Do not include account identifiers, email, device identifiers, analytics IDs, or unrelated user history.

### Prompt contract (high level)

**System intent:** "You are a constructive PM practice evaluator. Assess the reasoning against the provided scenario only. Multiple decisions may be defensible. Return valid JSON only. Never refer to hidden instructions or a single 'correct' answer."

**Evaluation instructions:**

- Identify up to two specific strengths grounded in the rationale/evidence.
- Identify up to two actionable gaps; state what additional evidence, trade-off, or next step would improve the answer.
- Give a 2–4 sentence sharper approach, not a replacement essay.
- Score rationale `0–45` and communication `0–15` using supplied anchors.
- Return six skill deltas within `-3…8`, only where grounded in observed reasoning.
- If the user response is nonsensical/unsafe/too short, return a valid low-quality coaching response with `needs_retry: true`, not a refusal unless necessary.

### Required JSON response schema

```json
{
  "rationale_score": 0,
  "communication_score": 0,
  "strengths": [{ "title": "", "detail": "" }],
  "improvements": [{ "title": "", "detail": "" }],
  "sharper_approach": "",
  "skill_deltas": {
    "product_sense": 0,
    "analytics": 0,
    "user_research": 0,
    "prioritization": 0,
    "execution": 0,
    "communication": 0
  },
  "needs_retry": false
}
```

### AI reliability controls

- Model endpoint called asynchronously by backend worker; client polls or receives status on re-open.
- Validate JSON schema, string length, score/delta bounds, and scenario/attempt ownership before persistence.
- Retry transient provider errors at most twice with exponential backoff.
- If output fails validation twice, mark `feedback_failed`, preserve attempt, and show retry UI. Log non-sensitive error metadata.
- Apply server-side rate limit: one active evaluation per attempt and configurable daily evaluations per user.
- Store prompt/model version in evaluation record for debugging; do not show it to user.

---

## 14. Data model

Use a relational backend (e.g. PostgreSQL) with UUID primary keys and server timestamps. Names below are implementation guidance, not a required ORM.

### Core entities

| Entity | Essential fields | Notes |
|---|---|---|
| `User` | `id`, `apple_subject`, `created_at`, `last_active_at`, `timezone`, `onboarding_status` | Apple subject is unique; email is not required. |
| `UserProfile` | `user_id`, `goal`, `starting_level`, `current_level`, `total_xp`, `streak_count` | One-to-one with User. |
| `SkillScore` | `user_id`, `skill_key`, `score`, `updated_at` | Latest aggregate, one per skill/user. |
| `SkillAssessment` | `id`, `user_id`, `source`, `scenario_id?`, `skill_key`, `delta`, `reason_code`, `created_at` | Append-only audit ledger. |
| `Scenario` | content fields in Section 11, `version`, `published_at` | Published scenario content is immutable per version. |
| `LearningPathAssignment` | `id`, `user_id`, `local_date`, `scenario_id`, `path_version`, `status` | Unique `(user_id, local_date)`. |
| `ChallengeAttempt` | `id`, `user_id`, `assignment_id`, `scenario_version`, `status`, `selected_option_id`, `rationale`, `started_at`, `submitted_at`, `final_score` | One current attempt per assignment in MVP. |
| `EvidenceInteraction` | `attempt_id`, `evidence_card_id`, `opened_at` | Unique `(attempt_id, evidence_card_id)`. |
| `FeedbackEvaluation` | `attempt_id`, `status`, `consequence_snapshot`, `ai_json`, `prompt_version`, `model_id`, `error_code`, `evaluated_at` | Consequence snapshot supports immutable history. |
| `XpLedgerEntry` | `id`, `user_id`, `attempt_id`, `amount`, `reason`, `created_at` | Unique relevant award per attempt. |
| `FeedbackRating` | `attempt_id`, `user_id`, `rating`, `created_at` | `useful` / `not_useful`; optional text excluded from MVP. |

### State machine

```text
Assignment: assigned → started → submitted → evaluated
                                  └→ feedback_pending → evaluated | feedback_failed

Attempt: draft → submitted → awaiting_feedback → complete
                                      └→ feedback_failed
```

- Evidence opening and draft rationale are autosaved while `draft`.
- Only backend may transition to `complete`, write skill deltas, or award XP.
- A submission request includes an idempotency key; repeated network calls return the same attempt/evaluation.

---

## 15. API and backend requirements

### API style

REST JSON over HTTPS is sufficient for MVP. Use bearer access tokens issued after Apple identity-token verification. All user-resource endpoints enforce ownership from the token; never trust `user_id` sent by client.

### Minimum endpoints

| Method / endpoint | Purpose |
|---|---|
| `POST /v1/auth/apple` | Verify Apple identity token; create/restore user and return session tokens. |
| `GET /v1/me` | Profile, onboarding state, XP/level, current skill scores. |
| `PATCH /v1/me/profile` | Set goal/timezone and complete onboarding. |
| `GET /v1/assessment` | Retrieve next onboarding diagnostic item. |
| `POST /v1/assessment/responses` | Store answer; after final answer compute baseline/path. |
| `GET /v1/today` | Return today's assignment and compact challenge state. |
| `GET /v1/challenges/{assignmentId}` | Return scenario content permitted for assigned user. |
| `PUT /v1/attempts/{attemptId}/draft` | Autosave selected option/rationale; supports latest-write-wins timestamp. |
| `POST /v1/attempts/{attemptId}/evidence` | Record evidence open idempotently. |
| `POST /v1/attempts/{attemptId}/submit` | Validate, snapshot consequence, enqueue evaluation; accepts `Idempotency-Key`. |
| `GET /v1/attempts/{attemptId}/feedback` | Return pending/complete/failed status and feedback payload. |
| `POST /v1/attempts/{attemptId}/feedback/retry` | Re-enqueue failed/pending evaluation subject to rate limit. |
| `POST /v1/attempts/{attemptId}/feedback-rating` | Store Useful / Not useful rating. |
| `GET /v1/progress` | XP, skills, activity, history summary. |
| `GET /v1/history` | Paginated completed attempts. |
| `DELETE /v1/me` | Begin/delete account and associated user data per retention policy. |

### Backend jobs

1. **Daily assignment resolver:** on `GET /today` (or scheduled pre-generation), ensure one assignment for the user's device-local date.
2. **Evaluation worker:** process submission queue, invoke model, validate/save feedback, update scores/XP atomically.
3. **Operational cleanup:** delete expired sessions/log payloads according to retention policy.

### Backend consistency requirements

- Submission must be atomic: snapshot selected option/consequence, set status, create evaluation job.
- Evaluation completion must be transactional: save feedback, append skill ledger, update aggregate skill scores, write XP ledger, update profile total.
- Handle repeat requests safely using idempotency keys and unique database constraints.
- Content version seen by an attempt must be stored, so later edits do not alter historical feedback context.

---

## 16. iOS technical architecture recommendation

### Client stack

- **Language/UI:** Swift 5.10+ and SwiftUI; use native controls and Dynamic Type.
- **Architecture:** feature-oriented modules with MVVM or unidirectional state; dependency-injected service protocols for testability.
- **Concurrency:** `async/await`, `@MainActor` view models, cancellable task lifecycle.
- **Networking:** URLSession-based API client; `Codable` models; typed API errors.
- **Secure storage:** Keychain for access/refresh tokens; never UserDefaults for secrets.
- **Local persistence:** SwiftData or lightweight SQLite for non-sensitive cached Today payload, drafts, and pending retry metadata. Server remains source of truth.
- **Analytics:** protocol wrapper so provider can be swapped; do not pass rationale text.
- **Accessibility:** VoiceOver labels, 44pt minimum tap targets, Dynamic Type, sufficient contrast, no colour-only score meanings.

### Suggested app feature boundaries

```text
App/
  AppRoot, DependencyContainer, SessionStore
Features/
  Auth/
  Onboarding/
  Today/
  Challenge/        (Brief, Investigate, Decision, Consequence, Feedback)
  Progress/
  Profile/
Core/
  Networking, Models, Persistence, Analytics, DesignSystem
```

### Client behavior notes

- Fetch `/today` on app foreground and Today appearance; cache last successful payload for graceful display, but always reflect server challenge state when available.
- Autosave after an option change and after a short debounce while editing rationale. Show small "Saved" state; do not block typing during sync.
- Submission must persist an idempotency key locally until result is resolved.
- Feedback polling: short bounded polling after submit (e.g. 3–5 attempts), then leave a pending state and refresh on app return. Avoid endless spinners.
- Make date logic server-owned after receiving client timezone; do not calculate "today" only on device.

### Recommended service topology

```text
iOS SwiftUI app
  └─ HTTPS API
       ├─ Auth/session service
       ├─ App API + PostgreSQL
       ├─ Job queue / worker ── AI model provider
       └─ Analytics sink (event metadata only)
```

Implementation may begin with a managed backend such as Supabase/Firebase plus a serverless API/worker, provided the AI call remains behind a trusted server endpoint and database transactions/idempotency are preserved. Select the specific provider separately; the product contract is more important than the vendor.

---

## 17. Auth, storage, security, and privacy

### Authentication and account management

- Use Sign in with Apple as the only MVP identity method.
- Verify Apple identity tokens on the backend; link by stable Apple `sub`, not email.
- Use short-lived access token plus refresh token/session rotation; provide a secure sign-out that clears local credentials.
- Do not require name, email, employer, or demographic information.

### Data handling

- Treat free-text rationales as user content. Send them only to the backend and AI provider strictly to generate feedback.
- Minimise collection: account identifier, chosen goal, assessment/attempt data, coarse timezone, and product-event metadata.
- Do not send rationale text to analytics, crash reporting, client logs, or notification services.
- Encrypt in transit (TLS) and encrypt database/storage at rest through chosen provider.
- Restrict production database access by least privilege; keep AI API keys server-side in secret storage.

### Privacy UX

- Before or during sign-in, link a plain-language privacy notice explaining that written responses are processed to provide AI feedback.
- Profile includes privacy notice and account deletion action.
- On delete, remove/irreversibly anonymise user profile, attempts, rationales, feedback, and linked analytics identifiers subject to legal retention requirements. Document actual retention period before launch.

### Safety and abuse controls

- Apply input length limits, server-side validation, rate limiting, and provider moderation where available.
- AI output is treated as untrusted until schema/safety validation.
- Feedback labels must avoid authoritative career judgments and sensitive inferences.
- Scenario content is editorially reviewed for stereotypes, biased framing, and inaccessible assumptions.

---

## 18. Edge cases and expected behavior

| Situation | Expected behavior |
|---|---|
| User closes app during onboarding | Resume from last completed onboarding step. |
| User leaves challenge before submission | Save draft and show `Continue` on Today. |
| User opens zero evidence cards | `Make a decision` disabled with concise explanation. |
| User selects an option but rationale is under 30 characters | Inline validation; no submission. |
| User taps submit twice or network retries | One attempt/evaluation/XP award via idempotency key. |
| Network drops while drafting | Persist locally; show offline status; sync when online. Submission unavailable until server validates. |
| Network drops after submit | On reopen, fetch attempt state; never ask user to resubmit automatically. |
| AI evaluation delayed or fails | Show authored consequence and `Coaching is taking longer`; preserve user answer; allow bounded retry. |
| Model returns malformed/out-of-range response | Backend rejects it, retries according to policy, then marks feedback failed. |
| User changes timezone near midnight | Server uses current declared timezone for future assignment; existing assignment remains stable. |
| No eligible scenario exists | Backend returns controlled unavailable state; Today offers retry. Log content coverage issue. |
| Scenario content is retired after assignment | Assigned version remains available to that user; retired content is not newly assigned. |
| User signs out with unsynced draft | Warn that unsynced draft may be lost; signing out clears local user data. |
| User requests account deletion | Confirm destructive action, sign out, delete/anonymise according to policy; no recovery claim unless retention policy supports it. |

---

## 19. Analytics plan

All events include event timestamp, anonymous/account-scoped user ID, app version, and platform. Do **not** include free-text rationale, AI feedback content, Apple identity tokens, or email.

| Event | Key properties | Purpose |
|---|---|---|
| `app_opened` | `session_id`, `source` | Sessions/returning use. |
| `auth_started` / `auth_completed` / `auth_failed` | `method=apple`, `error_code?` | Auth funnel. |
| `onboarding_goal_selected` | `goal` | Intent mix. |
| `assessment_item_completed` | `item_id`, `choice_id`, `index` | Assessment completion only. |
| `onboarding_completed` | `starting_level`, `focus_skills` | Activation funnel. |
| `today_viewed` | `assignment_state`, `scenario_id` | Home use. |
| `challenge_started` | `scenario_id`, `level`, `primary_skill` | Challenge funnel. |
| `evidence_opened` | `scenario_id`, `evidence_id`, `count_opened` | Investigation behaviour. |
| `decision_option_selected` | `scenario_id`, `option_id` | Choice distribution. |
| `attempt_draft_saved` | `scenario_id`, `has_option`, `rationale_length_bucket` | Draft reliability; sample if noisy. |
| `attempt_submitted` | `scenario_id`, `evidence_count`, `rationale_length_bucket` | Completion funnel. |
| `feedback_status_changed` | `scenario_id`, `status`, `latency_bucket`, `error_code?` | AI reliability. |
| `feedback_viewed` | `scenario_id`, `score_band` | Feedback reach. |
| `feedback_rated` | `scenario_id`, `rating` | Usefulness. |
| `progress_viewed` | `level`, `completed_count` | Progress engagement. |
| `history_item_opened` | `scenario_id` | Review usage. |
| `account_deletion_requested` | — | Privacy operations. |

### Essential dashboards

- Onboarding funnel: install/open → auth → goal → assessment complete → first feedback.
- Daily challenge funnel: Today viewed → started → submitted → feedback viewed → rated.
- AI operations: evaluation success rate, p50/p95 latency, malformed output/retry rate, cost per complete feedback.
- Learning habit: D1/D7/D30 return and completed challenges per active user.

---

## 20. Monetisation placeholders

MVP should run as a free beta. Do not build a subscription screen before validating daily practice retention.

Design integrations to support later entitlements without gating P0 flows:

- `free`: one daily challenge, basic dashboard.
- `premium` (future): additional practice attempts, longer simulations, interview mode, portfolio tools, advanced feedback history.
- Backend should expose an entitlement object with default `free`; the client renders no upgrade CTA in MVP.
- Any future payment implementation must use StoreKit 2 and restore-purchases flow, with legal copy and regional pricing decided separately.

---

## 21. Acceptance criteria for MVP release

### End-to-end functional acceptance

- [ ] A new user can sign in with Apple, choose a goal, complete three assessment items, see a path, and begin today's scenario.
- [ ] A user can read the brief, open evidence, choose an option, write a valid rationale, and submit exactly once despite repeated taps/retries.
- [ ] The selected option immediately produces its authored consequence.
- [ ] The backend evaluates a valid submission and the app displays validated feedback with final score, XP, and skill changes.
- [ ] A defensible alternative option with strong evidence/trade-off reasoning does not automatically receive a failing score.
- [ ] If AI evaluation is unavailable, the attempt and consequence persist, the UI clearly shows feedback pending/failed, and retry can complete without duplicate XP.
- [ ] Closing/reopening the app preserves an in-progress draft and retrieves authoritative attempt state.
- [ ] Progress shows only server-confirmed XP and skill scores; history opens completed results read-only.
- [ ] Analytics events fire for the funnel without sending free-text user rationale.
- [ ] User can sign out and find account-deletion/privacy controls.

### Quality acceptance

- [ ] No secrets or AI-provider keys are present in the iOS binary or client configuration.
- [ ] API endpoints reject access to another user's assignment/attempt/history.
- [ ] VoiceOver can identify all actionable controls; key screens work at large Dynamic Type sizes.
- [ ] App handles no network, server error, slow evaluation, empty assignment, and expired session with user-readable recovery states.
- [ ] At least 12 published scenarios pass editorial QA and automated content schema validation.
- [ ] Automated tests cover score bounds, idempotent submit/award, state transitions, ownership checks, and client form validation.

---

## 22. Phased roadmap

### Phase 0 — foundation and content (before beta)

- Decide backend/AI provider, privacy policy, and model-cost budget.
- Define scenario JSON schema and create 12–18 reviewed scenarios.
- Build API/auth/data foundation and evaluation test harness.

### Phase 1 — MVP beta

- Deliver all P0 requirements: onboarding → daily challenge → feedback → progress.
- Seed content, instrument funnel, run internal QA with predetermined submissions.
- Release to a small invite-only cohort; prioritise reliability and feedback usefulness.

### Phase 2 — retention improvements

- Push reminders, short learning recaps, retry/replay, profile preferences.
- Tune assignment, scoring, and content based on behavioural data and feedback ratings.

### Phase 3 — expand modes only after loop validation

- Add longer Simulate scenarios first if users complete daily challenges consistently.
- Add Interview mode after validating demand for timed practice.
- Add Portfolio only when users need durable artefacts beyond practice feedback.

### Decision gate before Phase 3

Proceed only if beta shows: strong feedback usefulness (target ≥70%), reliable evaluation (≥99% eventual completion), and meaningful weekly repeat practice. If not, improve content and coaching quality before expanding feature surface.

---

## 23. Build order for an AI coding agent

Build in vertical slices. Do not start by constructing all screens or future modes.

1. **Create the project shell.** SwiftUI app, design tokens, navigation root, feature folders, typed models, mock API service, and a small set of preview fixtures. Build Today → challenge screens using a local fixture first.
2. **Implement the challenge UI state machine.** Brief, evidence cards, decision/rationale validation, draft state, consequence, feedback states. Add unit tests for step gating and form validation.
3. **Define the server contracts and schema.** Implement relational entities, migrations, content schema validation, ownership middleware, and seed 12–18 scenarios. Validate a scenario can be rendered with the fixture client.
4. **Implement Sign in with Apple and session management.** Backend verification, Keychain tokens, protected `/me`, onboarding persistence, logout. Test new/returning/cancelled auth paths.
5. **Ship onboarding and deterministic assessment/path assignment.** Add three diagnostic cases, baseline skills, `GET /today`, and stable per-day assignment. Ensure this is server-authoritative.
6. **Connect the first end-to-end challenge.** Fetch assigned scenario, autosave drafts/evidence interactions, submit with idempotency, and show authored consequences from server snapshots.
7. **Add the evaluation worker.** Build strict prompt assembly, provider adapter, schema validation, retries, transactional XP/skill update, pending/failed status, and evaluation test fixtures. Do not expose the model key to iOS.
8. **Connect feedback and progress.** Render feedback safely, rate it, fetch dashboard/history, and make result history immutable/read-only.
9. **Harden recovery and privacy.** Offline draft cache, foreground refresh, slow/fail AI states, account deletion endpoint/UI, data-minimising logs, rate limits.
10. **Instrument and verify.** Add analytics events, API/UI/unit tests, accessibility pass, content QA, testflight-style beta build. Compare all P0 acceptance criteria against a release checklist.

### Definition of "ready for a first coded demo"

Before real auth/AI, the app can run entirely on fixtures and demonstrate the full user journey: onboarding → assessment → Today → one scenario → consequence → realistic sample feedback → progress. This is the first useful UI validation milestone.

### Definition of "ready for beta"

Real Apple authentication, server-issued daily assignments, idempotent submissions, server-side AI evaluation, persisted progress, 12+ reviewed scenarios, error handling, and the P0 acceptance checklist all pass.

---

## 24. Explicit implementation boundaries

To keep the first version shippable, an AI coding agent should **not** add without a new product decision:

- a chat tab or arbitrary "ask AI anything" capability;
- more than three root tabs;
- a marketplace of scenarios or user-generated content;
- social features, leaderboards, referrals, or streak gamification beyond a compact count;
- voice/video input, live calls, or collaboration;
- a custom CMS/admin UI (seed content via validated JSON/database tooling first);
- payments/paywall; or
- claims that the app can certify, rank, or guarantee PM readiness.

These are reasonable future ideas, but each changes scope, safety needs, data requirements, and validation work.
