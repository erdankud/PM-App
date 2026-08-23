import SwiftUI

// MARK: - Containers

struct CardContainer<Content: View>: View {
    var padding: CGFloat = Theme.Spacing.l
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.Palette.surface, in: RoundedRectangle(cornerRadius: Theme.Radius.card))
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

struct PrimaryButton: View {
    let title: String
    var systemImage: String?
    var isLoading = false
    var isEnabled = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: Theme.Spacing.s) {
                if isLoading {
                    ProgressView().tint(.white)
                } else if let systemImage {
                    Image(systemName: systemImage)
                }
                Text(title).fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity, minHeight: Theme.Spacing.xl + Theme.Spacing.m)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
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
        Button(action: action) {
            HStack(spacing: Theme.Spacing.s) {
                if let systemImage { Image(systemName: systemImage) }
                Text(title)
            }
            .frame(maxWidth: .infinity, minHeight: Theme.minimumTapTarget)
        }
        .buttonStyle(.bordered)
        .controlSize(.large)
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
        .foregroundStyle(tint)
        .accessibilityElement(children: .combine)
    }
}

struct StepProgressBar: View {
    let current: Int
    let total: Int

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule().fill(Theme.Palette.separator.opacity(0.4))
                    Capsule()
                        .fill(Theme.Palette.accent)
                        .frame(width: geometry.size.width * progress)
                }
            }
            .frame(height: 6)
        }
        .accessibilityElement()
        .accessibilityLabel("Step \(current) of \(total)")
        .accessibilityValue("\(Int(progress * 100)) percent")
    }

    private var progress: CGFloat {
        guard total > 0 else { return 0 }
        return min(1, CGFloat(current) / CGFloat(total))
    }
}

struct SkillRow: View {
    let skill: SkillView

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            HStack {
                Text(skill.label)
                    .font(.subheadline.weight(.medium))
                Spacer()
                HStack(spacing: Theme.Spacing.xs) {
                    Image(systemName: skill.trendSymbol)
                        .font(.caption2)
                        .foregroundStyle(Theme.trendColor(skill.trend))
                    Text("\(skill.score)")
                        .font(.subheadline.monospacedDigit())
                        .foregroundStyle(Theme.Palette.secondaryText)
                }
            }
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule().fill(Theme.Palette.separator.opacity(0.4))
                    Capsule()
                        .fill(Theme.Palette.accent)
                        .frame(width: geometry.size.width * CGFloat(skill.score) / 100)
                }
            }
            .frame(height: 6)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(skill.label)
        .accessibilityValue("\(skill.score) out of 100, \(skill.trendDescription)")
    }
}

struct ScoreHeadline: View {
    let score: Int
    let band: String

    var body: some View {
        VStack(spacing: Theme.Spacing.xs) {
            HStack(alignment: .firstTextBaseline, spacing: 2) {
                Text("\(score)")
                    .font(.system(size: 54, weight: .bold, design: .rounded))
                    .monospacedDigit()
                Text("/ 100")
                    .font(.title3.weight(.medium))
                    .foregroundStyle(Theme.Palette.secondaryText)
            }
            Text(band)
                .font(.headline)
                .foregroundStyle(Theme.Palette.accent)
        }
        .frame(maxWidth: .infinity)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Score \(score) out of 100. \(band).")
    }
}

// MARK: - States

struct LoadingState: View {
    var message: String = "Loading…"

    var body: some View {
        VStack(spacing: Theme.Spacing.m) {
            ProgressView()
            Text(message)
                .font(.subheadline)
                .foregroundStyle(Theme.Palette.secondaryText)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityElement(children: .combine)
    }
}

struct ErrorState: View {
    let title: String
    let message: String
    var retryTitle: String = "Try again"
    var onRetry: (() -> Void)?

    var body: some View {
        VStack(spacing: Theme.Spacing.m) {
            Image(systemName: "exclamationmark.triangle")
                .font(.largeTitle)
                .foregroundStyle(Theme.Palette.caution)
            Text(title).font(.headline)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(Theme.Palette.secondaryText)
                .multilineTextAlignment(.center)
            if let onRetry {
                Button(retryTitle, action: onRetry)
                    .buttonStyle(.borderedProminent)
                    .frame(minHeight: Theme.minimumTapTarget)
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
        .accessibilityElement(children: .combine)
    }
}
