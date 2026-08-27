import Foundation

@MainActor
final class LessonViewModel: ObservableObject {

    @Published private(set) var lesson: LessonResponse?
    @Published private(set) var isLoading = false
    @Published private(set) var isCompleting = false
    @Published private(set) var result: LessonCompleteResponse?
    @Published var error: APIError?

    private(set) var lessonId: String

    private let client: any APIClientProtocol
    private let analytics: any AnalyticsTracking
    private var openedAt = Date()

    init(lessonId: String, client: any APIClientProtocol, analytics: any AnalyticsTracking) {
        self.lessonId = lessonId
        self.client = client
        self.analytics = analytics
    }

    var isCompleted: Bool { result != nil || lesson?.completed == true }

    func load() async {
        isLoading = lesson == nil
        defer { isLoading = false }
        do {
            let response = try await client.lesson(id: lessonId)
            lesson = response
            openedAt = Date()
            analytics.track(.lessonOpened(lessonId: response.id, nodeId: response.nodeId))
            error = nil
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }

    /// Marking a lesson read is idempotent on the server, so a double tap is harmless
    /// and a retry after a dropped connection costs nothing.
    func complete() async {
        guard let lesson, !isCompleting else { return }
        isCompleting = true
        defer { isCompleting = false }
        do {
            let response = try await client.completeLesson(id: lesson.id)
            result = response
            analytics.track(
                .lessonCompleted(
                    lessonId: lesson.id,
                    nodeId: lesson.nodeId,
                    seconds: Int(Date().timeIntervalSince(openedAt))
                )
            )
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }

    /// Moving to the next lesson reuses this view model so the reader stays in place.
    func advance(to nextId: String) async {
        lessonId = nextId
        lesson = nil
        result = nil
        await load()
    }
}
