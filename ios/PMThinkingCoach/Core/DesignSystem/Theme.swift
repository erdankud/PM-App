import SwiftUI
import UIKit

/// Design tokens. Kept small on purpose: Dynamic Type still does most of the work,
/// which is what keeps accessibility correct by default (spec §16).
///
/// Colour is the one place where system defaults were given up. «Роща» is a sand
/// ground with a green accent, and `systemGroupedBackground` is a cool grey — mixing
/// the two reads as a bug, not as a theme. Every role below is a Color Set in the
/// asset catalogue with a light and a dark value, so the dark theme stays a property
/// of the asset instead of a branch in the code.
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
        static let card: CGFloat = 20
        static let control: CGFloat = 12
        static let pill: CGFloat = 999
    }

    enum Palette {
        /// Reads `AccentColor`, so the app-wide tint and this token can never diverge.
        static let accent = Color.accentColor
        /// Text and icons on top of a solid accent fill. A role of its own because the
        /// accent lightens in the dark theme and white stops being readable on it.
        static let accentInk = Color("AccentInk")
        static let accentSoft = Color("AccentSoft")
        static let accentBorder = Color("AccentBorder")
        static let surface = Color("Surface")
        /// An inset inside a card: it has to differ from the card, not from the page.
        static let surfaceTinted = Color("SurfaceTinted")
        static let background = Color("Sand")
        /// Dark green plate — the header and empty states. Dark in both themes.
        static let panel = Color("Panel")
        static let separator = Color("Hairline")
        static let primaryText = Color("Ink")
        static let bodyText = Color("BodyText")
        static let secondaryText = Color("Muted")
        static let tertiaryText = Color("Faint")
        /// Success is the accent: on a green palette a second green would only be
        /// noise. What separates «passed» from «tappable» is the mark and the fill
        /// density, never the hue alone.
        static let positive = Color.accentColor
        static let caution = Color("Caution")
        static let negative = Color("Negative")
        static let neutral = Color("Neutral")
        /// Warm counterpart to the accent, matching the chosen node in the app icon.
        /// Once per screen: two of these and neither reads as an accent.
        static let spark = Color("Spark")
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
