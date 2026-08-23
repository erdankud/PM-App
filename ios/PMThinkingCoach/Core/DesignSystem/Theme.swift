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
    }

    /// Minimum tap target (spec §16).
    static let minimumTapTarget: CGFloat = 44

    static func levelLabel(_ level: String) -> String {
        switch level {
        case "foundation": return "Foundation"
        case "developing": return "Developing"
        case "advanced": return "Advanced"
        default: return level.capitalized
        }
    }

    static func goalLabel(_ goal: String?) -> String {
        switch goal {
        case "break_into_pm": return "Break into PM"
        case "grow_in_first_role": return "Grow in my first PM role"
        case "practise_product_thinking": return "Practise product thinking"
        default: return "Not set"
        }
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

    static func formattedDate(_ isoDate: String) -> String {
        let parser = DateFormatter()
        parser.dateFormat = "yyyy-MM-dd"
        parser.timeZone = TimeZone(identifier: "UTC")
        guard let date = parser.date(from: isoDate) else { return isoDate }
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeZone = TimeZone(identifier: "UTC")
        return formatter.string(from: date)
    }

    static func shortWeekday(_ isoDate: String) -> String {
        let parser = DateFormatter()
        parser.dateFormat = "yyyy-MM-dd"
        parser.timeZone = TimeZone(identifier: "UTC")
        guard let date = parser.date(from: isoDate) else { return "" }
        let formatter = DateFormatter()
        formatter.dateFormat = "EEEEE"
        formatter.timeZone = TimeZone(identifier: "UTC")
        return formatter.string(from: date)
    }

    static func greeting(for date: Date = Date()) -> String {
        switch Calendar.current.component(.hour, from: date) {
        case 0..<12: return "Good morning"
        case 12..<18: return "Good afternoon"
        default: return "Good evening"
        }
    }
}
