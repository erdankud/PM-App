import Foundation

/// Today (spec §10.5, P0-05).
///
/// The last successful payload is cached so a cold, offline launch still shows
/// something useful — but any server response replaces it immediately. The client
/// never invents an assignment locally.
@MainActor
final class TodayViewModel: ObservableObject {

    enum LoadState: Equatable {
        case idle
        case loading
        case loaded(TodayResponse, isStale: Bool)
        case failed(APIError)

        static func == (lhs: LoadState, rhs: LoadState) -> Bool {
            switch (lhs, rhs) {
            case (.idle, .idle), (.loading, .loading): return true
            case let (.loaded(a, staleA), .loaded(b, staleB)):
                return a.assignment.assignmentId == b.assignment.assignmentId
                    && a.assignment.state == b.assignment.state
                    && staleA == staleB
            case let (.failed(a), .failed(b)): return a == b
            default: return false
            }
        }
    }

    @Published private(set) var state: LoadState = .idle
    @Published var presentedAssignmentId: String?

    private let client: any APIClientProtocol
    private let localStore: LocalStore
    private let analytics: any AnalyticsTracking

    init(
        client: any APIClientProtocol,
        localStore: LocalStore,
        analytics: any AnalyticsTracking
    ) {
        self.client = client
        self.localStore = localStore
        self.analytics = analytics
    }

    var payload: TodayResponse? {
        if case .loaded(let response, _) = state { return response }
        return nil
    }

    func load(showLoading: Bool = true) async {
        if showLoading, payload == nil { state = .loading }
        do {
            let response = try await client.today()
            await localStore.cacheToday(response)
            state = .loaded(response, isStale: false)
            analytics.track(
                .todayViewed(
                    assignmentState: response.assignment.state.rawValue,
                    scenarioId: response.assignment.scenarioId
                )
            )
        } catch let error as APIError {
            if let cached = await localStore.cachedToday(), payload == nil {
                state = .loaded(cached.payload, isStale: true)
            } else if payload == nil {
                state = .failed(error)
            }
            // A refresh failure with data already on screen is left silent; the pull-to-
            // refresh control is the affordance to try again.
        } catch {
            if payload == nil { state = .failed(.server(status: -1, code: "unknown")) }
        }
    }

    func openChallenge() {
        guard let assignment = payload?.assignment else { return }
        analytics.track(
            .challengeStarted(
                scenarioId: assignment.scenarioId,
                level: assignment.level,
                primarySkill: assignment.primarySkill
            )
        )
        presentedAssignmentId = assignment.assignmentId
    }

    func challengeDismissed() async {
        presentedAssignmentId = nil
        await load(showLoading: false)
    }
}
