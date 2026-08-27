import XCTest
@testable import PMThinkingCoach

/// The language switch is app state, not a bundle setting, so it needs its own coverage:
/// nothing else in the suite would notice a key that only resolves in one language.
final class LocalizationTests: XCTestCase {

    override func tearDown() {
        L10n.current = .english
        super.tearDown()
    }

    func testEveryStringDiffersBetweenLanguages() {
        // A sample across groups. Equal strings would mean a missed translation.
        let samples: [() -> String] = [
            { S.Tab.tree }, { S.Tab.progress }, { S.Tab.profile },
            { S.Tree.loading }, { S.Challenge.submitDecision },
            { S.Challenge.Step.decide }, { S.Progress.skillsTitle },
            { S.History.emptyTitle }, { S.Profile.deleteAccount },
            { S.Errors.offline }, { S.Tree.tierSubtitle(1) },
            { S.Labels.skill("discovery", fallback: "Discovery") },
            { S.Labels.band("Strong reasoning") }
        ]

        L10n.current = .english
        let english = samples.map { $0() }
        L10n.current = .russian
        let russian = samples.map { $0() }

        for (index, pair) in zip(english, russian).enumerated() {
            XCTAssertNotEqual(pair.0, pair.1, "sample \(index) is not translated")
        }
    }

    func testUnknownServerVocabularyFallsBackToTheServerString() {
        L10n.current = .russian
        XCTAssertEqual(S.Labels.skill("brand_new_skill", fallback: "Brand New"), "Brand New")
        XCTAssertEqual(S.Labels.band("Some new band"), "Some new band")
    }

    func testRussianPluralFormsFollowTheCount() {
        XCTAssertEqual(plural(1, "день", "дня", "дней"), "день")
        XCTAssertEqual(plural(2, "день", "дня", "дней"), "дня")
        XCTAssertEqual(plural(5, "день", "дня", "дней"), "дней")
        XCTAssertEqual(plural(11, "день", "дня", "дней"), "дней")
        XCTAssertEqual(plural(21, "день", "дня", "дней"), "день")
        XCTAssertEqual(plural(112, "день", "дня", "дней"), "дней")
    }

    @MainActor
    func testStoreRemembersTheSelectedLanguage() {
        let defaults = UserDefaults(suiteName: "LocalizationTests")!
        defaults.removePersistentDomain(forName: "LocalizationTests")

        let store = LanguageStore(defaults: defaults)
        store.select(.russian)
        XCTAssertEqual(L10n.current, .russian)

        let reopened = LanguageStore(defaults: defaults)
        XCTAssertEqual(reopened.language, .russian)
    }
}
