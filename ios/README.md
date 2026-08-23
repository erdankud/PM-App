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
│   │   └── DesignSystem/           Tokens and shared components
│   ├── Features/
│   │   ├── Auth/                   Welcome, privacy notice
│   │   ├── Onboarding/             Goal, assessment, path reveal
│   │   ├── Today/                  Daily challenge home
│   │   ├── Challenge/              Brief → Investigate → Decide → Consequence → Feedback
│   │   ├── Progress/               Dashboard, history, read-only result
│   │   └── Profile/                Goal, privacy, sign out, delete account
│   └── Resources/                  Assets.xcassets
└── PMThinkingCoachTests/
```

The Xcode project uses **file-system synchronised groups** (Xcode 16+), so adding a
Swift file to a folder is enough — there is no membership list to update.

---

## Building

```bash
open PMThinkingCoach.xcodeproj
```

Pick an iPhone simulator and run. If the checked-in project ever fails to open or
drifts from `project.yml`, regenerate it:

```bash
brew install xcodegen
cd ios && xcodegen generate
```

### Pointing at a server

`API_BASE_URL` is a build setting surfaced through `Info.plist`:

| Configuration | Value |
|---|---|
| Debug | `http://localhost:8000` |
| Release | `https://api.pmthinkingcoach.example` — change this |

The simulator reaches `localhost` directly. On a physical device, use Profile →
Developer to point at your Mac's LAN address (`http://192.168.x.x:8000`); the ATS
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

**The client computes nothing scoreable.** No score, XP, level, skill delta or "what
day is it" is derived on device. `ScoreBreakdown` renders what it receives;
`ChallengeState` maps a server string to a button label. If you find yourself adding
arithmetic over a score, the logic belongs on the server.

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

---

## Note on the first build

This code was written in an environment with no macOS or Swift toolchain, so it has
not been compiled. Expect a small number of build errors on first open — most likely
in SwiftUI generic inference or a concurrency annotation — rather than structural
problems. Fix those first, then run the tests; the shape of the app and its contract
with the server are the parts worth reviewing.
