import SwiftUI

struct RootView: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var container: AppContainer

    var body: some View {
        Group {
            switch session.route {
            case .launching:
                LaunchView()
            case .signedOut:
                WelcomeView()
            case .onboarding:
                OnboardingFlowView(viewModel: container.makeOnboardingViewModel())
                    .id(session.me?.userId ?? "onboarding")
            case .main:
                MainTabView()
            }
        }
        .animation(.easeInOut(duration: 0.2), value: session.route)
    }
}

private struct LaunchView: View {
    var body: some View {
        VStack(spacing: Theme.Spacing.l) {
            Image(systemName: "brain.head.profile")
                .font(.system(size: 44))
                .foregroundStyle(Theme.Palette.accent)
            ProgressView()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Palette.background)
    }
}

/// Exactly three root tabs. Future modes are not exposed as empty tabs (spec §9, §24).
struct MainTabView: View {
    @EnvironmentObject private var container: AppContainer

    var body: some View {
        TabView {
            TodayView(viewModel: container.makeTodayViewModel())
                .tabItem { Label("Today", systemImage: "sun.max") }

            ProgressTabView(viewModel: container.makeProgressViewModel())
                .tabItem { Label("Progress", systemImage: "chart.line.uptrend.xyaxis") }

            ProfileView(viewModel: container.makeProfileViewModel())
                .tabItem { Label("Profile", systemImage: "person.crop.circle") }
        }
    }
}
