import SwiftUI

/// Full-screen challenge flow. Each step owns its own state; back only moves among
/// Brief, Investigate and Decide, and only before submission (spec §9).
struct ChallengeFlowView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel: ChallengeViewModel
    @State private var showingLeaveConfirmation = false

    init(viewModel: @autoclosure @escaping () -> ChallengeViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.phase {
                case .loading:
                    LoadingState(message: S.Challenge.loadingScenario)
                case .failed(let error):
                    ErrorState(title: S.Common.couldntLoad, message: error.userMessage) {
                        Task { await viewModel.load() }
                    }
                case .ready:
                    steps
                }
            }
            .animation(Motion.standard, value: viewModel.phase)
            .background(Theme.Palette.background)
            .navigationTitle(viewModel.form.step.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(closeLabel) { close() }
                }
                ToolbarItem(placement: .principal) {
                    if viewModel.phase == .ready {
                        StepProgressBar(
                            current: viewModel.form.step.rawValue + 1,
                            total: ChallengeFormState.Step.allCases.count
                        )
                        .frame(width: 120)
                    }
                }
            }
            .confirmationDialog(
                S.Challenge.leaveTitle,
                isPresented: $showingLeaveConfirmation,
                titleVisibility: .visible
            ) {
                Button(S.Challenge.saveAndLeave) {
                    viewModel.leave()
                    dismiss()
                }
                Button(S.Challenge.keepWorking, role: .cancel) {}
            } message: {
                Text(S.Challenge.leaveMessage)
            }
        }
        .task { await viewModel.load() }
        .interactiveDismissDisabled(viewModel.form.hasDraftProgress && !viewModel.form.isSubmitted)
    }

    private var closeLabel: String {
        viewModel.form.isSubmitted ? S.Common.done : S.Common.close
    }

    private func close() {
        if viewModel.form.isSubmitted || !viewModel.form.hasDraftProgress {
            viewModel.leave()
            dismiss()
        } else {
            showingLeaveConfirmation = true
        }
    }

    @ViewBuilder
    private var steps: some View {
        Group {
            switch viewModel.form.step {
            case .brief:
                BriefStepView(viewModel: viewModel)
            case .investigate:
                InvestigateStepView(viewModel: viewModel)
            case .decide:
                DecideStepView(viewModel: viewModel)
            case .consequence:
                ConsequenceStepView(viewModel: viewModel)
            case .feedback:
                FeedbackStepView(viewModel: viewModel, onFinish: {
                    viewModel.leave()
                    dismiss()
                })
            }
        }
        .transition(.stepForward)
        .animation(Motion.standard, value: viewModel.form.step)
    }
}
