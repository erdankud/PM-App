# Architecture notes

How this MVP is put together, and why the pieces sit where they do. The product
specification is in [product-spec.md](product-spec.md); section references below point
at it.

---

## Topology

```
iPhone (SwiftUI)
   │  HTTPS, bearer access token
   ▼
FastAPI  ──────────────┐
   │                   │
   │ writes            │ enqueues
   ▼                   ▼
PostgreSQL ◄──── Evaluation worker ────► AI provider
                                          (key lives only here)
```

The worker runs inside the API process by default (`RUN_INLINE_WORKER=true`) so local
development is a single command. Setting it false and running `python -m app.worker`
splits it out with no code change; both read the same queue table.

---

## The one decision everything else follows from

**The client is a renderer.** It holds no scoring logic, no XP arithmetic, no level
thresholds, and no notion of what "today" is. Those all live in
`server/app/services/` and arrive over the wire already computed.

This is not only spec compliance (§12, §16). It is what makes the rest tractable:

- Changing the scoring model is a server deploy, not an App Store release.
- A tampered client cannot award itself XP, because XP comes from an append-only
  ledger with a unique constraint the client cannot reach.
- "What day is it" is answered once, from the timezone the client declares, so a user
  crossing a date line does not get two challenges or lose one (§18).
- The iOS tests can assert the absence of scoring logic, and they do.

The counterpart is that the app is useless offline beyond showing a cached Today and
saving a draft. That is the right trade for this product: the value is the evaluated
decision, and evaluation is inherently server-side.

---

## Trust boundaries in the payloads

`GET /challenges/{assignmentId}` deliberately ships less than the database holds:

| In the database | Sent to the client |
|---|---|
| Brief, evidence cards, decision prompt | Yes |
| Option label and description | Yes |
| Option `consequence` text | **No** — only in the submit response |
| Option `decisionPoints` weight | **No** |
| Authored `rubric` | **No** |
| `qaSubmissions` | **No** |

Consequences are withheld because reading them before deciding removes the exercise.
The rubric and weights are withheld because they are the answer key. A test asserts
each of these absences rather than trusting the serialiser to keep behaving.

The same logic applies to the prompt: `app/ai/prompt.py` assembles scenario content,
the rubric, and the user's submission — and no account identifier, email, device id,
analytics id, or unrelated history (§13).

---

## Idempotency, three ways

Duplicate submissions are the failure mode most likely to corrupt a practice record,
so it is defended at three levels rather than one:

1. **Client** — `LocalStore.idempotencyKey(forAttempt:)` persists a key until the
   submission resolves. A crash mid-submit reuses the same key.
2. **Application** — `submit_attempt` returns the original consequence unchanged when
   the attempt is no longer `draft`, instead of erroring or re-submitting.
3. **Database** — `XpLedgerEntry` has `UNIQUE (attempt_id, reason)`,
   `ChallengeAttempt` has `UNIQUE (assignment_id)`, `LearningPathAssignment` has
   `UNIQUE (user_id, local_date)`, and `EvidenceInteraction` has
   `UNIQUE (attempt_id, evidence_card_id)`.

The XP write catches `IntegrityError` and treats it as "already awarded" rather than
checking first and then inserting, because the check-then-act version has a race the
constraint does not.

---

## Evaluation: designed around the failure

The interesting part of the evaluation flow is not the happy path, it is what the user
sees when the model is slow, unavailable, or returns nonsense.

- The **authored consequence is snapshotted at submit time** and returned in the same
  response. The learning payoff never depends on the provider (§10.9, P0-08).
- Model output is **untrusted until validated**: JSON extracted (code fences and
  surrounding prose tolerated), scores range-checked, skill deltas bounded, text
  truncated, unknown skill keys rejected. Failing twice marks `feedback_failed` and
  preserves the attempt.
- **XP and skill deltas are not written until a validated evaluation exists.** A
  pending attempt shows pending XP rather than provisional numbers that might change.
- The client **polls a bounded number of times** and then leaves a state the user can
  act on, rather than spinning indefinitely (§16).
- The feedback screen **never synthesises coaching on device**. If there is no
  validated evaluation, it says so and offers a retry.

The one place this is deliberately strict: `evaluations_per_user_per_day` caps model
spend per user, which matters because the provider question is the spec's one blocking
open question (§6) and the answer may end up being a paid one.

---

## Path assignment

Deterministic by design (§12), which makes it auditable and testable:

1. Level comes from the assessment band.
2. Focus skills are the two lowest scores, ties broken by a fixed skill order.
3. Day N alternates between the two focus skills.
4. Within a level and focus skill, the first unseen scenario wins, sorted by id — so
   the same user state always produces the same path.
5. Fallbacks, in order: focus skill as a *secondary* skill at the same level → same
   level with the least-recently-seen tags → adjacent levels.
6. Only **future** assignments are recalculated after an evaluated attempt. Today's
   assignment and every past one are immutable.

Two users with identical assessment answers get identical paths. That is a feature for
debugging and a deliberate limit: it does not need AI planning, and it should not have
it until there is data suggesting the deterministic version is inadequate.

---

## Content as data

Scenarios are JSON validated against a schema plus editorial rules, seeded into the
database, and immutable per `(id, version)`. An attempt stores the version it was
evaluated against, so editing a scenario later cannot retroactively change what a
historical piece of feedback was responding to (§14).

The editorial rules encode product principles that a schema alone cannot:

- at least one non-reference option must earn meaningful partial credit — this is what
  stops the product becoming a single-right-answer quiz (§11)
- three QA fixtures per scenario, and they must fit the app's own 30–600 character
  limit, so calibration runs on answers a real user could type

`scripts/qa_evaluate.py` runs those fixtures through the configured provider and fails
on ordering violations. It is the closest thing to a regression test for feedback
quality, and it should run whenever the provider, model, or prompt changes.

---

## What was left out, and why

| Left out | Reason |
|---|---|
| Sign in with Apple as the only path | Implemented and verified server-side, but a dev path was needed to exercise the client before an Apple Developer account exists. It is `#if DEBUG` on the client and refused by the server outside development. |
| Push notifications | P1 in the spec, and the daily loop should be proven before it is nagged about. |
| Replaying a completed scenario | P1. Attempt immutability is simpler to get right first. |
| A custom admin UI | §24 — content is validated JSON, which is enough for 15 scenarios. |
| Multi-worker evaluation queue | One worker is sufficient at this scale; `claim_next` needs `FOR UPDATE SKIP LOCKED` before a second one is added, and that is noted in the server README. |
| Streaks beyond a compact count | §24 explicitly excludes streak gamification. The count is shown and nothing is built on top of it. |
