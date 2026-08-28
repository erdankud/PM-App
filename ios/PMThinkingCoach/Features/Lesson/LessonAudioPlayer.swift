import SwiftUI

/// Плеер аудиоверсии урока: одна строка над текстом, а не отдельный экран.
///
/// Урок можно читать и слушать одновременно, поэтому плеер не забирает экран и не
/// перекрывает текст. До первого нажатия он занимает одну строку — пока человек не
/// попросил звук, качать полтора мегабайта незачем.
struct LessonAudioPlayer: View {
    @ObservedObject var viewModel: LessonAudioViewModel
    /// Перечитывает урок, пока идёт сборка. Владелец урока знает, как это сделать.
    var reloadAudio: (() async -> LessonAudioView?)?

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            HStack(spacing: Theme.Spacing.m) {
                playButton
                VStack(alignment: .leading, spacing: 2) {
                    Text(needsBuild ? S.Lesson.audioBuild : S.Lesson.audioTitle)
                        .font(.subheadline.weight(.semibold))
                    Text(caption)
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.secondaryText)
                }
                Spacer(minLength: 0)
                if viewModel.state == .ready { speedMenu }
            }
            if viewModel.state == .ready { transport }
        }
        .padding(Theme.Spacing.m)
        .background(Theme.Palette.surface, in: RoundedRectangle(cornerRadius: Theme.Radius.card))
    }

    private var caption: String {
        switch viewModel.state {
        case .buildable: return S.Lesson.audioSubtitle
        case .building: return S.Lesson.audioBuilding
        case .buildFailed: return S.Lesson.audioBuildFailed
        case .loading: return S.Lesson.audioLoading
        case .failed: return S.Lesson.audioFailed
        case .ready: return "\(time(viewModel.position)) / \(time(viewModel.duration))"
        default:
            // До загрузки полезнее сказать, что это вообще такое, и сколько идёт.
            return viewModel.duration > 0
                ? "\(S.Lesson.audioSubtitle) · \(time(viewModel.duration))"
                : S.Lesson.audioSubtitle
        }
    }

    private var isBuilding: Bool { viewModel.state == .building }

    private var needsBuild: Bool {
        viewModel.state == .buildable || viewModel.state == .buildFailed
    }

    private var playButton: some View {
        Button {
            Task {
                if needsBuild {
                    await viewModel.build(reload: reloadAudio ?? { nil })
                } else {
                    await viewModel.toggle()
                }
            }
        } label: {
            ZStack {
                Circle().fill(Theme.Palette.accent).frame(width: 44, height: 44)
                if viewModel.state == .loading || isBuilding {
                    ProgressView().tint(.white)
                } else {
                    Image(systemName: symbol)
                        .font(.system(size: 17, weight: .bold))
                        .foregroundStyle(.white)
                }
            }
        }
        .buttonStyle(.plain)
        .disabled(viewModel.state == .loading || isBuilding)
        .accessibilityLabel(buttonLabel)
    }

    private var symbol: String {
        if viewModel.state == .buildFailed { return "arrow.clockwise" }
        if needsBuild { return "wand.and.stars" }
        return viewModel.isPlaying ? "pause.fill" : "play.fill"
    }

    private var buttonLabel: String {
        if needsBuild { return S.Lesson.audioBuild }
        return viewModel.isPlaying ? S.Lesson.audioPause : S.Lesson.audioPlay
    }

    private var speedMenu: some View {
        Menu {
            Picker(S.Lesson.audioSpeed, selection: $viewModel.rate) {
                ForEach(LessonAudioViewModel.rates, id: \.self) { rate in
                    Text(speedLabel(rate)).tag(rate)
                }
            }
        } label: {
            Text(speedLabel(viewModel.rate))
                .font(.footnote.weight(.semibold).monospacedDigit())
                .padding(.horizontal, Theme.Spacing.s)
                .padding(.vertical, 6)
                .background(
                    Capsule().strokeBorder(Theme.Palette.separator)
                )
        }
        .accessibilityLabel(S.Lesson.audioSpeed)
        .accessibilityValue(speedLabel(viewModel.rate))
    }

    private var transport: some View {
        HStack(spacing: Theme.Spacing.m) {
            Button { viewModel.skip(by: -15) } label: {
                Image(systemName: "gobackward.15")
            }
            .accessibilityLabel(S.Lesson.audioBack15)

            Slider(
                value: Binding(
                    get: { viewModel.position },
                    set: { viewModel.seek(to: $0) }
                ),
                in: 0...max(viewModel.duration, 1)
            )
            .accessibilityLabel(S.Lesson.audioPosition)
            .accessibilityValue(time(viewModel.position))

            Button { viewModel.skip(by: 15) } label: {
                Image(systemName: "goforward.15")
            }
            .accessibilityLabel(S.Lesson.audioForward15)
        }
        .buttonStyle(.plain)
        .foregroundStyle(Theme.Palette.accent)
    }

    private func speedLabel(_ rate: Float) -> String {
        rate == 1 ? "1×" : String(format: "%.2g×", rate)
    }

    private func time(_ seconds: Double) -> String {
        guard seconds.isFinite, seconds >= 0 else { return "0:00" }
        let total = Int(seconds.rounded())
        return String(format: "%d:%02d", total / 60, total % 60)
    }
}
