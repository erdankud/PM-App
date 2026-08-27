import Foundation

/// Глоссарий кэшируется целиком: около 500 терминов — примерно 80 КБ, и меняются они
/// редко. Поиск фильтрует локально, чтобы каждое нажатие клавиши не ходило в сеть.
@MainActor
final class GlossaryViewModel: ObservableObject {

    @Published var query: String = ""
    @Published private(set) var terms: [TermView] = []
    @Published private(set) var isLoading = false

    private var all: [TermView] = []
    private let client: any APIClientProtocol
    private let analytics: any AnalyticsTracking
    private let source: String

    init(client: any APIClientProtocol, analytics: any AnalyticsTracking, source: String) {
        self.client = client
        self.analytics = analytics
        self.source = source
    }

    func load() async {
        guard all.isEmpty else { return }
        isLoading = true
        defer { isLoading = false }
        analytics.track(.glossaryOpened(source: source, searchQueryLength: 0))
        do {
            let response = try await client.glossary(query: nil, blockId: nil)
            all = response.terms
            terms = all
        } catch {
            terms = []
        }
    }

    func scheduleSearch() {
        let needle = query.trimmingCharacters(in: .whitespaces).lowercased()
        guard !needle.isEmpty else {
            terms = all
            return
        }
        terms = all.filter {
            $0.term.lowercased().contains(needle) || $0.termEn.lowercased().contains(needle)
        }
    }
}
