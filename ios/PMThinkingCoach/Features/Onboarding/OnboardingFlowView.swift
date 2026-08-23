import SwiftUI

/// Onboarding → Assessment → Path reveal → Today (spec §9).
struct OnboardingFlowView: View {

    @StateObject private var viewModel: OnboardingViewModel

    /// The autoclosure keeps construction lazy so `@StateObject` builds it exactly once.
    init(viewModel: @autoclosure @escaping () -> OnboardingViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.step {
                case .goal:
                    GoalSelectionView(viewModel: viewModel)
                case .assessment:
                    AssessmentView(viewModel: viewModel)
                case .pathReveal:
                    PathRevealView(viewModel: viewModel)
                }
            }
            .background(Theme.Palette.background)
        }
        .task {
            switch viewModel.step {
            case .assessment: await viewModel.loadAssessment()
            case .pathReveal: await viewModel.loadResultIfNeeded()
            case .goal: break
            }
        }
    }
}
