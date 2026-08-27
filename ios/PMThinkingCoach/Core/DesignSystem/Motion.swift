import SwiftUI
import UIKit

/// Motion tokens and the handful of modifiers built on them.
///
/// Every one of these checks `accessibilityReduceMotion` and degrades to an instant,
/// non-moving state rather than a slower animation — a user who asked for less motion
/// wants none of it, not a gentler version (spec §16).
enum Motion {

    /// Taps, toggles, chevrons — anything that must feel immediate.
    static let quick = Animation.spring(response: 0.26, dampingFraction: 0.86)
    /// The default for content changing on screen.
    static let standard = Animation.spring(response: 0.42, dampingFraction: 0.82)
    /// Bars and meters filling, where overshoot would misrepresent a value.
    static let gentle = Animation.easeOut(duration: 0.55)
    /// Rewards only: score reveal, XP, streak. Overshoot is the point.
    static let celebratory = Animation.spring(response: 0.5, dampingFraction: 0.6)

    /// Gap between successive items in a staggered entrance.
    static let staggerStep: Double = 0.055
    /// Beyond this many items the stagger is capped so late rows are not left waiting.
    static let staggerCap = 8

    static func stagger(_ index: Int) -> Double {
        Double(min(index, staggerCap)) * staggerStep
    }
}

// MARK: - Entrance

/// Fades and lifts content into place once, offset by its position in the stack.
private struct AppearModifier: ViewModifier {
    let index: Int
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isVisible = false

    func body(content: Content) -> some View {
        content
            .opacity(isVisible ? 1 : 0)
            .offset(y: isVisible ? 0 : 16)
            .onAppear {
                guard !isVisible else { return }
                if reduceMotion {
                    isVisible = true
                } else {
                    withAnimation(Motion.standard.delay(Motion.stagger(index))) {
                        isVisible = true
                    }
                }
            }
    }
}

extension View {
    /// `appear(0)`, `appear(1)`, … down a stack gives a staggered entrance.
    func appear(_ index: Int = 0) -> some View {
        modifier(AppearModifier(index: index))
    }
}

// MARK: - Press feedback

/// Shrinks slightly while held. Used on card-shaped buttons, which otherwise give no
/// sign they are tappable until the action completes.
struct PressableButtonStyle: ButtonStyle {
    var scale: CGFloat = 0.975
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(reduceMotion ? 1 : (configuration.isPressed ? scale : 1))
            .opacity(configuration.isPressed ? 0.92 : 1)
            .animation(Motion.quick, value: configuration.isPressed)
    }
}

extension ButtonStyle where Self == PressableButtonStyle {
    static var pressable: PressableButtonStyle { PressableButtonStyle() }
}

// MARK: - Haptics

/// Thin wrapper so call sites read as intent rather than as UIKit generator plumbing.
@MainActor
enum Haptics {
    static func selection() { UISelectionFeedbackGenerator().selectionChanged() }

    static func tap(_ style: UIImpactFeedbackGenerator.FeedbackStyle = .light) {
        UIImpactFeedbackGenerator(style: style).impactOccurred()
    }

    static func success() { UINotificationFeedbackGenerator().notificationOccurred(.success) }
    static func warning() { UINotificationFeedbackGenerator().notificationOccurred(.warning) }
}

// MARK: - Numbers

/// A number that rolls up from zero the first time it appears.
///
/// Reduce Motion skips straight to the value; VoiceOver reads the final value either way
/// because the intermediate states are hidden from accessibility.
struct CountUpText: View {
    let value: Int
    var font: Font = .body
    var suffix: String = ""

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var shown = 0

    var body: some View {
        Text("\(shown)\(suffix)")
            .font(font)
            .monospacedDigit()
            .contentTransition(.numericText(value: Double(shown)))
            .onAppear {
                guard shown != value else { return }
                if reduceMotion {
                    shown = value
                } else {
                    withAnimation(.easeOut(duration: 0.8)) { shown = value }
                }
            }
            .onChange(of: value) { _, newValue in
                withAnimation(reduceMotion ? nil : Motion.standard) { shown = newValue }
            }
            .accessibilityHidden(true)
    }
}

// MARK: - Meters

/// A capsule meter that fills from empty on first appearance and animates on change.
struct ProgressTrack: View {
    let progress: Double
    var height: CGFloat = 6
    var tint: Color = Theme.Palette.accent
    var animatesOnAppear = true

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var shown: Double = 0

    private var clamped: Double { min(1, max(0, progress)) }

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Capsule().fill(Theme.Palette.separator.opacity(0.35))
                Capsule()
                    .fill(
                        LinearGradient(
                            colors: [tint.opacity(0.75), tint],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: max(0, geometry.size.width * shown))
            }
        }
        .frame(height: height)
        .onAppear {
            guard animatesOnAppear, !reduceMotion else {
                shown = clamped
                return
            }
            withAnimation(Motion.gentle.delay(0.1)) { shown = clamped }
        }
        .onChange(of: clamped) { _, newValue in
            withAnimation(reduceMotion ? nil : Motion.gentle) { shown = newValue }
        }
    }
}

// MARK: - Attention

/// A slow breathing scale. Reserved for a single element at a time — a call to action
/// waiting on the user, or a spinner-free "still working" state.
private struct PulseModifier: ViewModifier {
    var range: ClosedRange<CGFloat> = 1.0...1.06
    var duration: Double = 1.6

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isExpanded = false

    func body(content: Content) -> some View {
        content
            .scaleEffect(reduceMotion ? 1 : (isExpanded ? range.upperBound : range.lowerBound))
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: duration).repeatForever(autoreverses: true)) {
                    isExpanded = true
                }
            }
    }
}

extension View {
    func pulse(range: ClosedRange<CGFloat> = 1.0...1.06, duration: Double = 1.6) -> some View {
        modifier(PulseModifier(range: range, duration: duration))
    }
}

/// A one-shot burst of sparks behind a reward. Purely decorative, so it is hidden from
/// accessibility and skipped entirely under Reduce Motion.
struct SparkBurst: View {
    var count = 10
    var radius: CGFloat = 74
    var tint: Color = Theme.Palette.accent

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isBurst = false

    var body: some View {
        ZStack {
            ForEach(0..<count, id: \.self) { index in
                let angle = (Double(index) / Double(count)) * 2 * .pi
                Circle()
                    .fill(tint)
                    .frame(width: 6, height: 6)
                    .offset(
                        x: isBurst ? radius * CGFloat(cos(angle)) : 0,
                        y: isBurst ? radius * CGFloat(sin(angle)) : 0
                    )
                    .opacity(isBurst ? 0 : 0.9)
                    .scaleEffect(isBurst ? 0.4 : 1)
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(.easeOut(duration: 0.85).delay(0.25)) { isBurst = true }
        }
    }
}

// MARK: - Transitions

extension AnyTransition {
    /// Forward/back movement between challenge steps.
    static var stepForward: AnyTransition {
        .asymmetric(
            insertion: .move(edge: .trailing).combined(with: .opacity),
            removal: .move(edge: .leading).combined(with: .opacity)
        )
    }

    /// Content that expands in place, such as an evidence card body.
    static var expand: AnyTransition {
        .opacity.combined(with: .move(edge: .top))
    }
}
