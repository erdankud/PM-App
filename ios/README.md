# PM Thinking Coach — iOS

SwiftUI, iOS 17+, iPhone only, portrait. MVVM with dependency-injected service
protocols, `async/await`, `@MainActor` view models.

```
ios/
├── PMThinkingCoach.xcodeproj
├── project.yml                     XcodeGen spec (source of truth for settings)
├── Supporting/
│   ├── Info.plist                  API base URL + ATS local-networking exception
│   └── PMThinkingCoach.entitlements  Sign in with Apple
├── PMThinkingCoach/
│   ├── App/                        Entry point, DI container, SessionStore, tabs
│   ├── Core/
│   │   ├── Networking/             APIClient, typed APIError, AppConfig
│   │   ├── Models/                 Codable wire models
│   │   ├── Persistence/            Keychain, local draft/idempotency store
│   │   ├── Analytics/              Event types and buckets
│   │   ├── Localization/           Language store + the EN/RU string table
│   │   └── DesignSystem/           Tokens, motion, shared components
│   ├── Features/
│   │   ├── Auth/                   Welcome, privacy notice
│   │   ├── Onboarding/             How the route works, optional target role
│   │   ├── Tree/                   The map: rings, block detail
│   │   ├── Lesson/                 Lesson reader and content renderer
│   │   ├── Challenge/              Gate: Brief → Investigate → Decide → Consequence → Feedback
│   │   ├── Progress/               Blocks, lessons, competencies, gate history
│   │   └── Profile/                Role, language, privacy, sign out, delete
│   └── Resources/                  Assets.xcassets (app icon, accent colour)
├── Tools/
│   └── MakeAppIcon.swift           Draws the 1024pt app icon; not in any target
└── PMThinkingCoachTests/
```

The checked-in project lists every source file explicitly. A new Swift file has to be
added to the target — through Xcode, or by regenerating from `project.yml`, which
globs the folder:

```bash
brew install xcodegen && cd ios && xcodegen generate
```

---

## Building

```bash
open PMThinkingCoach.xcodeproj
```

Pick an iPhone simulator and run.

### Pointing at a server

`API_BASE_URL` is a build setting surfaced through `Info.plist`:

| Configuration | Value |
|---|---|
| Debug | `http://192.168.1.252:8000` — your Mac's LAN address |
| Release | `https://api.pmthinkingcoach.example` — change this |

A physical device cannot reach the Mac's `localhost`, which is why Debug points at a
LAN address; the simulator reaches either. To change it without rebuilding, use
Profile → Developer and restart the app; the ATS
exception allows plain HTTP on the local network only, and the field is compiled out
of Release builds.

There is no AI provider key here, and there is nowhere to put one. The app talks only
to this API.

### Sign in with Apple

Requires an Apple Developer team and `APPLE_CLIENT_ID` set on the server to your
bundle identifier. Until then use **Continue without Apple (development)**, which is
`#if DEBUG` only and which the server refuses when `ALLOW_DEV_AUTH=false`.

---

## Conventions worth knowing

**The client computes nothing scoreable, and nothing about access.** No score, XP,
level or skill delta is derived on device, and neither is whether a block is open.
`BlockStatus` is rendered as received; `POST /gates/{id}/start` re-checks availability,
so a UI bug cannot let anyone into a gate early. If you find yourself deciding on
device whether something is unlocked, the logic belongs on the server.

**The map is one request.** `GET /v1/tree` returns all 18 blocks with the learner's
status on each. It is cached in `LocalStore`, so a cold offline launch still shows the
route as it was last seen.

**Step gating lives in `ChallengeFormState`,** a plain struct with no dependencies, so
the rules (≥1 evidence card before deciding, 30–600 characters before submitting,
no editing after submission, no route back into a submitted attempt) are unit-tested
directly rather than through the UI.

**Drafts survive everything.** `LocalStore` writes to Application Support with
complete file protection. It also holds the submit idempotency key until the
submission resolves, so a crash or a network drop mid-submit still produces exactly
one attempt on the server.

**Analytics cannot carry free text by construction.** `AnalyticsValue` only encodes
scalars, and rationale length is reported as a bucket. `AnalyticsPrivacyTests` asserts
that a real sentence cannot appear in an encoded payload.

**Language is app state, not a bundle setting.** `Core/Localization/` holds an
`AppLanguage` (English or Russian), a `LanguageStore` that persists the choice, and a
`S` string table where both translations sit on the same line. The switch is in
Profile and on the welcome screen, and it applies immediately: the root view is keyed
on the language, so the whole tree rebuilds. This is a plain Swift table rather than
`Localizable.strings` because `Bundle` resolves its language once at launch and this
app switches in place — and because view models need the strings too.

Scenario content is localised too, on the server. `APIClient` sends the current choice
as `X-Content-Language` on every request, so the response after a switch already speaks
the new language — there is no window where the chrome is Russian and the brief is
still English. `AppContainer.setLanguage` also pushes the choice to the profile, which
is what the evaluation worker reads when it writes coaching later. `SessionStore`
reconciles the two on every profile load: a deliberate choice on this device wins and
is pushed up; otherwise the account's preference is adopted, so a language picked on
another device carries over. Client-side vocabularies (skills, levels, states, bands)
are still translated from the server *key*, with the server string as the fallback —
that keeps cached, offline payloads readable.

**Motion has a token layer.** `Core/DesignSystem/Motion.swift` holds the springs,
the staggered `appear(_:)` entrance, `ProgressTrack`, `CountUpText`, press feedback
and haptics. Every one of them checks `accessibilityReduceMotion` and degrades to an
instant, non-moving state rather than to a slower animation. Prefer these over
ad-hoc `withAnimation` so timing stays consistent across screens.

**Accessibility is part of the component, not a later pass.** Shared components carry
their own labels and values; trends are stated in words as well as colour; tap targets
are at least 44pt; Dynamic Type is used throughout.

---

## Tests

⌘U in Xcode, or:

```bash
xcodebuild test -scheme PMThinkingCoach \
  -destination 'platform=iOS Simulator,name=iPhone 16'
```

- `ChallengeFormStateTests` — step gating, rationale validation, immutability
- `ChallengeViewModelTests` — load/submit/feedback lifecycle against `StubAPIClient`
- `AnalyticsPrivacyTests` — no free text in events; no scoring logic on device
- `LocalizationTests` — both languages resolve, plural forms, unknown server
  vocabulary falls back, the choice survives a relaunch

---

## App icon

The icon is generated, not hand-exported, so it can be changed in a diff:

```bash
swift Tools/MakeAppIcon.swift \
  PMThinkingCoach/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
```

Only the 1024pt master is committed; Xcode derives the rest. The mark is a decision
fork — one path in, two ways out, one of them taken.
