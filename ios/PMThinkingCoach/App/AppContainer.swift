import SwiftUI

/// Dependency container. Feature view models take protocols, so each can be exercised
/// against a stub in tests and previews (spec §16).
@MainActor
final class AppContainer: ObservableObject {

    let apiClient: APIClient
    let keychain: KeychainStore
    let localStore: LocalStore
    let analytics: any AnalyticsTracking
    let session: SessionStore

    init() {
        let configuration = URLSessionConfiguration.default
        configuration.waitsForConnectivity = false
        configuration.timeoutIntervalForRequest = 30
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData

        let client = APIClient(session: URLSession(configuration: configuration))
        let keychain = KeychainStore()
        let localStore = LocalStore()
        let analytics = AnalyticsService(client: client)

        self.apiClient = client
        self.keychain = keychain
        self.localStore = localStore
        self.analytics = analytics
        self.session = SessionStore(
            client: client, keychain: keychain, localStore: localStore, analytics: analytics
        )
    }

    func makeOnboardingViewModel() -> OnboardingViewModel {
        OnboardingViewModel(client: apiClient, session: session, analytics: analytics)
    }

    func makeTodayViewModel() -> TodayViewModel {
        TodayViewModel(client: apiClient, localStore: localStore, analytics: analytics)
    }

    func makeChallengeViewModel(assignmentId: String) -> ChallengeViewModel {
        ChallengeViewModel(
            assignmentId: assignmentId,
            client: apiClient,
            localStore: localStore,
            analytics: analytics
        )
    }

    func makeProgressViewModel() -> ProgressViewModel {
        ProgressViewModel(client: apiClient, analytics: analytics)
    }

    func makeHistoryViewModel() -> HistoryViewModel {
        HistoryViewModel(client: apiClient, analytics: analytics)
    }

    func makeProfileViewModel() -> ProfileViewModel {
        ProfileViewModel(client: apiClient, session: session)
    }
}
