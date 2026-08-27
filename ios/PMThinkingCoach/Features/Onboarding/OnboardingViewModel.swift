import Foundation

/// Onboarding is two screens now: how the route works, and an optional target role.
///
/// The v0.1 diagnostic is gone. A complete beginner has nothing to diagnose, and the
/// questions were a barrier in front of the first lesson (spec v0.2 §10).
@MainActor
final class OnboardingViewModel: ObservableObject {

    enum Step: Equatable {
        case howItWorks
        case role
    }

    @Published private(set) var step: Step = .howItWorks
    @Published var selectedRole: String?
    @Published private(set) var isBusy = false
    @Published var error: APIError?

    /// Roles come from the source map. Until the node mapping is transcribed the choice
    /// is stored but highlights nothing, which is why it is skippable (spec v0.2 §7).
    let roles = S.Roles.keys

    private let client: any APIClientProtocol
    private let session: SessionStore
    private let analytics: any AnalyticsTracking

    init(client: any APIClientProtocol, session: SessionStore, analytics: any AnalyticsTracking) {
        self.client = client
        self.session = session
        self.analytics = analytics
        self.selectedRole = session.me?.targetRole
    }

    func advance() {
        step = .role
    }

    func finish(withRole role: String?) async {
        isBusy = true
        error = nil
        defer { isBusy = false }
        do {
            let profile = try await client.updateProfile(
                ProfileUpdateRequest(
                    targetRole: role,
                    timezone: TimeZone.current.identifier,
                    completeOnboarding: true
                )
            )
            analytics.track(.onboardingCompleted(targetRole: role ?? "none"))
            session.apply(profile)
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }
}
