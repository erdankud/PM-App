import Foundation
import SwiftUI

/// The two languages the interface ships in.
///
/// Scenario content itself is authored server-side and is currently English only; the
/// language switch covers the app's own chrome plus every label the client derives from
/// a server enum (skills, levels, bands, states).
enum AppLanguage: String, CaseIterable, Identifiable, Sendable {
    case english = "en"
    case russian = "ru"

    var id: String { rawValue }

    /// Endonyms: a language picker should read in the language it offers.
    var displayName: String {
        switch self {
        case .english: return "English"
        case .russian: return "Русский"
        }
    }

    var shortName: String { rawValue.uppercased() }

    /// Drives date and number formatting so a switch changes more than just the words.
    var locale: Locale { Locale(identifier: rawValue) }

    static var deviceDefault: AppLanguage {
        let preferred = Locale.preferredLanguages.first ?? "en"
        return preferred.hasPrefix("ru") ? .russian : .english
    }
}

/// Holds the language for the plain-Swift string table in `Strings.swift`.
///
/// Deliberately not `Localizable.strings`: `Bundle` resolves its language once at launch,
/// and this app switches language in-place from Profile. A Swift table also keeps both
/// translations on the same line, which makes drift visible in review, and it is readable
/// from view models where there is no SwiftUI environment.
enum L10n {
    /// Written only from `LanguageStore` on the main actor; read from anywhere.
    nonisolated(unsafe) static var current: AppLanguage = .english
}

/// The single localisation call site. `t("Today", "Сегодня")`.
func t(_ english: String, _ russian: String) -> String {
    L10n.current == .russian ? russian : english
}

@MainActor
final class LanguageStore: ObservableObject {

    static let defaultsKey = "app.language"

    /// Views key off this so the whole tree rebuilds with the new strings.
    @Published private(set) var language: AppLanguage

    /// False until someone picks a language in this app on this device. Until then the
    /// value is a guess from the device locale, so a preference stored on the account
    /// is the better answer and should win.
    private(set) var hasExplicitChoice: Bool

    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        let stored = defaults.string(forKey: Self.defaultsKey).flatMap(AppLanguage.init(rawValue:))
        let resolved = stored ?? .deviceDefault
        self.hasExplicitChoice = stored != nil
        self.language = resolved
        L10n.current = resolved
    }

    /// A deliberate choice by the user.
    func select(_ language: AppLanguage) {
        hasExplicitChoice = true
        defaults.set(language.rawValue, forKey: Self.defaultsKey)
        guard language != self.language else { return }
        L10n.current = language
        self.language = language
    }

    /// The language stored on the account, applied only when this device has no
    /// choice of its own to defend.
    func adoptFromServer(_ language: AppLanguage) {
        guard !hasExplicitChoice, language != self.language else { return }
        L10n.current = language
        self.language = language
    }
}
