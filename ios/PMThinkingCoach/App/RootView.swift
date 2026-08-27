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
                    .transition(.opacity)
            case .onboarding:
                OnboardingFlowView(viewModel: container.makeOnboardingViewModel())
                    .id(session.me?.userId ?? "onboarding")
                    .transition(.opacity.combined(with: .scale(scale: 0.98)))
            case .main:
                MainTabView()
                    .transition(.opacity.combined(with: .scale(scale: 1.02)))
            }
        }
        .animation(Motion.standard, value: session.route)
    }
}

/// The launch screen doubles as the app mark: the same decision fork as the icon,
/// drawn with SF Symbols so it inherits the accent colour and Dynamic Type.
private struct LaunchView: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hasSettled = false

    var body: some View {
        VStack(spacing: Theme.Spacing.l) {
            Image(systemName: "circle.hexagongrid")
                .font(.system(size: 48, weight: .semibold))
                .foregroundStyle(Theme.Palette.accent)
                .scaleEffect(hasSettled ? 1 : 0.8)
                .opacity(hasSettled ? 1 : 0)
            ProgressView()
                .opacity(hasSettled ? 1 : 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Palette.background)
        .onAppear {
            if reduceMotion {
                hasSettled = true
            } else {
                withAnimation(Motion.celebratory) { hasSettled = true }
            }
        }
    }
}

/// Exactly three root tabs. Future modes are not exposed as empty tabs (spec §9, §24).
struct MainTabView: View {
    @EnvironmentObject private var container: AppContainer
    @State private var selection = Tab.tree

    private enum Tab: Hashable { case tree, progress, profile }

    var body: some View {
        TabView(selection: $selection) {
            TreeView(viewModel: container.makeTreeViewModel())
                .tabItem { Label(S.Tab.tree, systemImage: "circle.hexagongrid") }
                .tag(Tab.tree)

            ProgressTabView(viewModel: container.makeProgressViewModel())
                .tabItem { Label(S.Tab.progress, systemImage: "chart.line.uptrend.xyaxis") }
                .tag(Tab.progress)

            ProfileView(viewModel: container.makeProfileViewModel())
                .tabItem { Label(S.Tab.profile, systemImage: "person.crop.circle") }
                .tag(Tab.profile)
        }
        .onChange(of: selection) { _, _ in Haptics.selection() }
    }
}
