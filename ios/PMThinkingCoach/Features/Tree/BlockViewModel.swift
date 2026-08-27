import Foundation

@MainActor
final class BlockViewModel: ObservableObject {

    @Published private(set) var detail: BlockDetailResponse?
    @Published private(set) var isLoading = false
    @Published private(set) var isStartingGate = false
    @Published var error: APIError?
    @Published var startedGate: ChallengeResponse?

    let blockId: String

    private let client: any APIClientProtocol
    private let analytics: any AnalyticsTracking

    init(blockId: String, client: any APIClientProtocol, analytics: any AnalyticsTracking) {
        self.blockId = blockId
        self.client = client
        self.analytics = analytics
    }

    func load() async {
        if detail == nil { isLoading = true }
        defer { isLoading = false }
        do {
            detail = try await client.block(id: blockId)
            error = nil
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }

    func startGate() async {
        guard let detail, let gateId = detail.block.gateId else { return }
        isStartingGate = true
        defer { isStartingGate = false }
        do {
            let challenge = try await client.startGate(id: gateId)
            analytics.track(
                .gateStarted(
                    gateId: gateId,
                    scenarioId: challenge.scenario.id,
                    attemptIndex: challenge.attemptIndex,
                    lessonsCompletedRatio: detail.block.lessonProgress
                )
            )
            startedGate = challenge
        } catch let apiError as APIError {
            // The server refuses a gate the block has not earned, whatever the UI showed.
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }
}
