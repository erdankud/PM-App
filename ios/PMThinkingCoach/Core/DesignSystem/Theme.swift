import SwiftUI
import UIKit

/// Design tokens. Kept small on purpose: system colours and Dynamic Type do most of
/// the work, which is also what keeps accessibility correct by default (spec §16).
enum Theme {

    enum Spacing {
        static let xs: CGFloat = 4
        static let s: CGFloat = 8
        static let m: CGFloat = 12
        static let l: CGFloat = 16
        static let xl: CGFloat = 24
        static let xxl: CGFloat = 32
    }

    enum Radius {
        static let card: CGFloat = 16
        static let control: CGFloat = 12
        static let pill: CGFloat = 999
    }

    enum Palette {
        static let accent = Color.accentColor
        static let surface = Color(.secondarySystemGroupedBackground)
        static let background = Color(.systemGroupedBackground)
        static let separator = Color(.separator)
        static let primaryText = Color(.label)
        static let secondaryText = Color(.secondaryLabel)
        static let tertiaryText = Color(.tertiaryLabel)
        static let positive = Color(.systemGreen)
        static let caution = Color(.systemOrange)
        static let negative = Color(.systemRed)
        static let neutral = Color(.systemGray)
        /// Warm counterpart to the accent, matching the chosen node in the app icon.
        static let spark = Color(red: 1.0, green: 0.78, blue: 0.47)
    }

    enum Gradients {
        /// Behind the day's challenge, so the one card that matters reads as the hero.
        static let hero = LinearGradient(
            colors: [
                Palette.accent.opacity(0.16),
                Palette.accent.opacity(0.04)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )

        static let accentFill = LinearGradient(
            colors: [Palette.accent.opacity(0.8), Palette.accent],
            startPoint: .leading,
            endPoint: .trailing
        )
    }

    /// Minimum tap target (spec §16).
    static let minimumTapTarget: CGFloat = 44

    static func levelLabel(_ level: String) -> String {
        S.Labels.level(level)
    }

    /// Colour is never the only carrier of meaning; each of these pairs with a label
    /// or an SF Symbol at the call site.
    static func trendColor(_ trend: String) -> Color {
        switch trend {
        case "up": return Palette.positive
        case "down": return Palette.caution
        default: return Palette.neutral
        }
    }

    // MARK: - Dates
    //
    // Server dates are UTC calendar days, so parsing stays fixed to UTC. Only the
    // presentation follows the language the user picked.

    private static let isoParser: DateFormatter = {
        let parser = DateFormatter()
        parser.dateFormat = "yyyy-MM-dd"
        parser.locale = Locale(identifier: "en_US_POSIX")
        parser.timeZone = TimeZone(identifier: "UTC")
        return parser
    }()

    static func formattedDate(_ isoDate: String) -> String {
        guard let date = isoParser.date(from: isoDate) else { return isoDate }
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.locale = L10n.current.locale
        formatter.timeZone = TimeZone(identifier: "UTC")
        return formatter.string(from: date)
    }

    static func shortWeekday(_ isoDate: String) -> String {
        guard let date = isoParser.date(from: isoDate) else { return "" }
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEEE"
        formatter.locale = L10n.current.locale
        formatter.timeZone = TimeZone(identifier: "UTC")
        return formatter.string(from: date)
    }

}
