import Foundation

@MainActor
final class ProgressViewModel: ObservableObject {

    @Published private(set) var progress: ProgressResponse?
    @Published private(set) var isLoading = false
    @Published var error: APIError?

    private let client: any APIClientProtocol
    private let analytics: any AnalyticsTracking

    init(client: any APIClientProtocol, analytics: any AnalyticsTracking) {
        self.client = client
        self.analytics = analytics
    }

    func load() async {
        if progress == nil { isLoading = true }
        defer { isLoading = false }
        do {
            let response = try await client.progress()
            progress = response
            error = nil
            analytics.track(
                .progressViewed(level: response.level, completedCount: response.blocksPassed)
            )
        } catch let apiError as APIError {
            if progress == nil { error = apiError }
        } catch {
            if progress == nil { self.error = .server(status: -1, code: "unknown") }
        }
    }
}

@MainActor
final class HistoryViewModel: ObservableObject {

    @Published private(set) var items: [HistoryItem] = []
    @Published private(set) var isLoading = false
    @Published private(set) var canLoadMore = false
    @Published var error: APIError?

    private let client: any APIClientProtocol
    private let analytics: any AnalyticsTracking
    private var nextOffset: Int?

    init(client: any APIClientProtocol, analytics: any AnalyticsTracking) {
        self.client = client
        self.analytics = analytics
    }

    func loadFirstPage() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await client.history(limit: 20, offset: 0)
            items = response.items
            nextOffset = response.nextOffset
            canLoadMore = response.nextOffset != nil
            error = nil
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }

    func loadNextPage() async {
        guard let offset = nextOffset, !isLoading else { return }
        isLoading = true
        defer { isLoading = false }
        if let response = try? await client.history(limit: 20, offset: offset) {
            items.append(contentsOf: response.items)
            nextOffset = response.nextOffset
            canLoadMore = response.nextOffset != nil
        }
    }

    func itemOpened(_ item: HistoryItem) {
        analytics.track(.historyItemOpened(scenarioId: item.scenarioId))
    }
}

/// Read-only view of a completed attempt (spec §10.12). Submitted attempts are
/// immutable, so nothing here can be edited or resubmitted.
@MainActor
final class ResultDetailViewModel: ObservableObject {

    @Published private(set) var feedback: FeedbackResponse?
    @Published private(set) var isLoading = true
    @Published var error: APIError?

    private let attemptId: String
    private let client: any APIClientProtocol

    init(attemptId: String, client: any APIClientProtocol) {
        self.attemptId = attemptId
        self.client = client
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            feedback = try await client.feedback(attemptId: attemptId)
            error = nil
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }

    func retry() async {
        guard let current = feedback, current.status == .failed else { return }
        feedback = try? await client.retryFeedback(attemptId: attemptId)
        await load()
    }
}
