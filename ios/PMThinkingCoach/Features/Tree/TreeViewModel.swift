import Foundation

/// Выбранная карта переживает перезапуск; при первом заходе — «Продукт».
private let kindDefaultsKey = "pmcoach.treeKind"

/// Loads the whole map in one request. 18 blocks is small, and the map being visible in
/// full from the first launch is the product's promise rather than an optimisation.
@MainActor
final class TreeViewModel: ObservableObject {

    enum LoadState: Equatable {
        case idle
        case loading
        case loaded(TreeResponse)
        case failed(APIError)

        static func == (lhs: LoadState, rhs: LoadState) -> Bool {
            switch (lhs, rhs) {
            case (.idle, .idle), (.loading, .loading): return true
            case let (.loaded(a), .loaded(b)):
                return a.blocks.map(\.status) == b.blocks.map(\.status)
                    && a.blocks.map(\.lessonsCompleted) == b.blocks.map(\.lessonsCompleted)
            case let (.failed(a), .failed(b)): return a == b
            default: return false
            }
        }
    }

    @Published private(set) var state: LoadState = .idle
    @Published private(set) var trees: [TreeSummary] = []
    @Published var selectedBlockId: String?

    /// Какая карта открыта. Выбор запоминается между запусками; при первом
    /// заходе — «Продукт» (спека System Design §6.1).
    @Published var kind: String = UserDefaults.standard.string(forKey: kindDefaultsKey)
        ?? "product" {
        didSet {
            guard kind != oldValue else { return }
            UserDefaults.standard.set(kind, forKey: kindDefaultsKey)
            analytics.track(.treeSwitched(from: oldValue, to: kind))
            state = .idle
            Task { await load() }
        }
    }



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

    var tree: TreeResponse? {
        if case .loaded(let tree) = state { return tree }
        return nil
    }

    /// The block the learner should open next: the one furthest along that is still
    /// open to them. Recommendation only — every unlocked block stays reachable.
    var suggested: BlockSummary? {
        guard let tree else { return nil }
        let open = tree.blocks.filter { $0.status.isOpen && $0.status != .passed && $0.isWritten }
        return open.first { $0.status == .gateReady }
            ?? open.first { $0.status == .inProgress }
            ?? open.first
    }

    func load(showLoading: Bool = true) async {
        if showLoading, tree == nil { state = .loading }
        do {
            async let summaries = client.trees()
            let response = try await client.tree(kind: kind)
            trees = (try? await summaries)?.trees ?? trees
            if kind == "product" { await localStore.cacheTree(response) }
            state = .loaded(response)
            analytics.track(
                .treeViewed(
                    blocksPassed: response.blocks.filter { $0.status == .passed }.count,
                    blocksAvailable: response.blocks.filter { $0.status.isOpen }.count
                )
            )
        } catch let error as APIError {
            // A cold offline launch still shows the map as it was last seen.
            if kind == "product", let cached = await localStore.cachedTree(), tree == nil {
                state = .loaded(cached.payload)
            } else if tree == nil {
                state = .failed(error)
            }
        } catch {
            if tree == nil { state = .failed(.server(status: -1, code: "unknown")) }
        }
    }

    func open(_ block: BlockSummary) {
        analytics.track(.blockOpened(blockId: block.id, status: block.status.rawValue))
        selectedBlockId = block.id
    }
}
