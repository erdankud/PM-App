import SwiftUI

/// Dependency container. Feature view models take protocols, so each can be exercised
/// against a stub in tests and previews (spec §16).
@MainActor
final class AppContainer: ObservableObject {

    let apiClient: APIClient
    let keychain: KeychainStore
    let localStore: LocalStore
    let analytics: any AnalyticsTracking
    let language: LanguageStore
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
        let language = LanguageStore()

        self.apiClient = client
        self.keychain = keychain
        self.localStore = localStore
        self.analytics = analytics
        self.language = language
        self.session = SessionStore(
            client: client,
            keychain: keychain,
            localStore: localStore,
            analytics: analytics,
            language: language
        )
    }

    /// Switching language changes both the app's own text and the content the server
    /// sends back. The header on the next request already carries the new value, so the
    /// view tree can rebuild immediately; the profile push only has to land before the
    /// evaluation worker next runs.
    func setLanguage(_ newValue: AppLanguage) {
        guard newValue != language.language else { return }
        language.select(newValue)
        if session.me != nil {
            session.pushLanguage(newValue)
        }
    }

    func makeOnboardingViewModel() -> OnboardingViewModel {
        OnboardingViewModel(client: apiClient, session: session, analytics: analytics)
    }

    func makeTreeViewModel() -> TreeViewModel {
        TreeViewModel(client: apiClient, localStore: localStore, analytics: analytics)
    }

    func makeBlockViewModel(blockId: String) -> BlockViewModel {
        BlockViewModel(blockId: blockId, client: apiClient, analytics: analytics)
    }

    func makeLessonViewModel(lessonId: String) -> LessonViewModel {
        LessonViewModel(lessonId: lessonId, client: apiClient, analytics: analytics)
    }

    func makeLessonAudioViewModel(lessonId: String) -> LessonAudioViewModel {
        LessonAudioViewModel(lessonId: lessonId, client: apiClient, analytics: analytics)
    }

    func makeChallengeViewModel(challenge: ChallengeResponse) -> ChallengeViewModel {
        ChallengeViewModel(
            challenge: challenge,
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
