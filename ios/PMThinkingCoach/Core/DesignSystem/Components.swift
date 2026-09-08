import SwiftUI

// MARK: - Containers

struct CardContainer<Content: View>: View {
    var padding: CGFloat = Theme.Spacing.l
    /// The one card on a screen that should read as the hero gets the accent wash.
    var isHighlighted = false
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background {
                RoundedRectangle(cornerRadius: Theme.Radius.card)
                    .fill(Theme.Palette.surface)
                    .overlay {
                        if isHighlighted {
                            RoundedRectangle(cornerRadius: Theme.Radius.card)
                                .fill(Theme.Gradients.hero)
                        }
                    }
                    .overlay {
                        RoundedRectangle(cornerRadius: Theme.Radius.card)
                            .strokeBorder(
                                Theme.Palette.accent.opacity(isHighlighted ? 0.22 : 0),
                                lineWidth: 1
                            )
                    }
                    .shadow(
                        color: Theme.Palette.panel.opacity(isHighlighted ? 0.16 : 0.08),
                        radius: isHighlighted ? 16 : 8,
                        y: isHighlighted ? 8 : 4
                    )
            }
    }
}

struct SectionHeader: View {
    let title: String
    var subtitle: String?

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            Text(title)
                .font(.headline)
                .foregroundStyle(Theme.Palette.primaryText)
            if let subtitle {
                Text(subtitle)
                    .font(.subheadline)
                    .foregroundStyle(Theme.Palette.secondaryText)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}

// MARK: - Buttons

private struct PrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.body.weight(.semibold))
            .foregroundStyle(Theme.Palette.accentInk)
            .frame(maxWidth: .infinity, minHeight: Theme.Spacing.xl + Theme.Spacing.m)
            .padding(.vertical, Theme.Spacing.xs)
            .background {
                Capsule()
                    .fill(Theme.Gradients.accentFill)
                    .opacity(isEnabled ? 1 : 0.4)
                    .shadow(
                        color: Theme.Palette.accent.opacity(isEnabled ? 0.32 : 0),
                        radius: configuration.isPressed ? 4 : 12,
                        y: configuration.isPressed ? 2 : 6
                    )
            }
            .scaleEffect(reduceMotion ? 1 : (configuration.isPressed ? 0.97 : 1))
            .animation(Motion.quick, value: configuration.isPressed)
    }
}

private struct SecondaryButtonStyle: ButtonStyle {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.body.weight(.medium))
            .foregroundStyle(Theme.Palette.accent)
            .frame(maxWidth: .infinity, minHeight: Theme.minimumTapTarget)
            .background {
                Capsule()
                    .fill(Theme.Palette.accentSoft)
                    .overlay { Capsule().strokeBorder(Theme.Palette.accentBorder, lineWidth: 1) }
                    .opacity(configuration.isPressed ? 0.72 : 1)
            }
            .scaleEffect(reduceMotion ? 1 : (configuration.isPressed ? 0.97 : 1))
            .animation(Motion.quick, value: configuration.isPressed)
    }
}

struct PrimaryButton: View {
    let title: String
    var systemImage: String?
    var isLoading = false
    var isEnabled = true
    let action: () -> Void

    var body: some View {
        Button {
            Haptics.tap()
            action()
        } label: {
            HStack(spacing: Theme.Spacing.s) {
                if isLoading {
                    ProgressView().tint(Theme.Palette.accentInk)
                } else if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title)
            }
            // The label swap between spinner and title should not jump the layout.
            .animation(Motion.quick, value: isLoading)
        }
        .buttonStyle(PrimaryButtonStyle())
        .disabled(!isEnabled || isLoading)
        .accessibilityLabel(Text(title))
        .accessibilityAddTraits(.isButton)
    }
}

struct SecondaryButton: View {
    let title: String
    var systemImage: String?
    let action: () -> Void

    var body: some View {
        Button {
            Haptics.tap()
            action()
        } label: {
            HStack(spacing: Theme.Spacing.s) {
                if let systemImage { Image(systemName: systemImage) }
                Text(title)
            }
        }
        .buttonStyle(SecondaryButtonStyle())
    }
}

// MARK: - Labels

struct Chip: View {
    let text: String
    var systemImage: String?
    var tint: Color = Theme.Palette.neutral

    var body: some View {
        HStack(spacing: Theme.Spacing.xs) {
            if let systemImage {
                Image(systemName: systemImage).font(.caption2)
            }
            Text(text).font(.caption).fontWeight(.medium)
        }
        .padding(.horizontal, Theme.Spacing.m)
        .padding(.vertical, Theme.Spacing.xs + 2)
        .background(tint.opacity(0.15), in: Capsule())
        .overlay(Capsule().strokeBorder(tint.opacity(0.22), lineWidth: 0.5))
        .foregroundStyle(tint)
        .accessibilityElement(children: .combine)
    }
}

struct StepProgressBar: View {
    let current: Int
    let total: Int

    var body: some View {
        ProgressTrack(progress: progress, animatesOnAppear: false)
            .accessibilityElement()
            .accessibilityLabel(S.Challenge.stepProgress(current, total))
            .accessibilityValue("\(Int(progress * 100))%")
    }

    private var progress: Double {
        guard total > 0 else { return 0 }
        return min(1, Double(current) / Double(total))
    }
}

struct SkillRow: View {
    let skill: SkillView

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            HStack {
                Text(skill.localizedLabel)
                    .font(.subheadline.weight(.medium))
                Spacer()
                HStack(spacing: Theme.Spacing.xs) {
                    Image(systemName: skill.trendSymbol)
                        .font(.caption2)
                        .foregroundStyle(Theme.trendColor(skill.trend))
                    CountUpText(value: skill.score, font: .subheadline)
                        .foregroundStyle(Theme.Palette.secondaryText)
                }
            }
            ProgressTrack(progress: Double(skill.score) / 100)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(skill.localizedLabel)
        .accessibilityValue(S.Labels.skillAccessibility(skill.score, skill.trend))
    }
}

struct ScoreHeadline: View {
    let score: Int
    let band: String

    var body: some View {
        VStack(spacing: Theme.Spacing.xs) {
            ZStack {
                // Only a strong result earns the burst; it would read as mockery otherwise.
                if score >= 70 { SparkBurst(tint: Theme.Palette.spark) }
                HStack(alignment: .firstTextBaseline, spacing: 2) {
                    CountUpText(
                        value: score,
                        font: .system(size: 54, weight: .bold, design: .rounded)
                    )
                    Text("/ 100")
                        .font(.title3.weight(.medium))
                        .foregroundStyle(Theme.Palette.secondaryText)
                }
            }
            Text(S.Labels.band(band))
                .font(.headline)
                .foregroundStyle(Theme.Palette.accent)
        }
        .frame(maxWidth: .infinity)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(S.Challenge.scoreAccessibility(score, band: S.Labels.band(band)))
    }
}

// MARK: - States

struct LoadingState: View {
    var message: String = S.Common.loading

    var body: some View {
        VStack(spacing: Theme.Spacing.m) {
            ProgressView()
                .controlSize(.large)
                .pulse(range: 0.94...1.06, duration: 1.4)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(Theme.Palette.secondaryText)
                .multilineTextAlignment(.center)
                .transition(.opacity)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityElement(children: .combine)
    }
}

struct ErrorState: View {
    let title: String
    let message: String
    var retryTitle: String = S.Common.tryAgain
    var onRetry: (() -> Void)?

    var body: some View {
        VStack(spacing: Theme.Spacing.m) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundStyle(Theme.Palette.caution)
                .appear(0)
            Text(title).font(.headline).appear(1)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(Theme.Palette.secondaryText)
                .multilineTextAlignment(.center)
                .appear(2)
            if let onRetry {
                Button(retryTitle) {
                    Haptics.tap()
                    onRetry()
                }
                .buttonStyle(.borderedProminent)
                .frame(minHeight: Theme.minimumTapTarget)
                .appear(3)
            }
        }
        .padding(Theme.Spacing.xl)
        .frame(maxWidth: .infinity)
    }
}

struct InlineNotice: View {
    let text: String
    var systemImage: String = "info.circle"
    var tint: Color = Theme.Palette.secondaryText

    var body: some View {
        HStack(alignment: .top, spacing: Theme.Spacing.s) {
            Image(systemName: systemImage).font(.footnote)
            Text(text).font(.footnote)
        }
        .foregroundStyle(tint)
        .frame(maxWidth: .infinity, alignment: .leading)
        .transition(.opacity.combined(with: .move(edge: .top)))
        .accessibilityElement(children: .combine)
    }
}
