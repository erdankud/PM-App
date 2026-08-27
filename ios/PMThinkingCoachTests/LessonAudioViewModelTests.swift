import XCTest
@testable import PMThinkingCoach

/// Плеер аудиоурока. Проверяется не воспроизведение (для него нужен файл и сессия),
/// а решения вокруг него: когда плеер вообще предлагается и по какому ключу кэшируется.
@MainActor
final class LessonAudioViewModelTests: XCTestCase {

    private func makeViewModel(
        _ client: StubAPIClient = StubAPIClient()
    ) -> (LessonAudioViewModel, StubAPIClient, NoopAnalytics) {
        let analytics = NoopAnalytics()
        let viewModel = LessonAudioViewModel(
            lessonId: "ds1-n1-l1", client: client, analytics: analytics
        )
        return (viewModel, client, analytics)
    }

    func testLessonWithoutAudioOffersNoPlayer() {
        let (viewModel, _, _) = makeViewModel()
        viewModel.configure(with: LessonAudioView(available: false, url: nil, durationSeconds: nil))
        XCTAssertEqual(viewModel.state, .unavailable)
    }

    func testMissingAudioSectionIsNotAnError() {
        let (viewModel, _, _) = makeViewModel()
        viewModel.configure(with: nil)
        XCTAssertEqual(viewModel.state, .unavailable)
    }

    func testAvailableAudioShowsTheServerEstimateBeforeAnythingIsDownloaded() {
        let (viewModel, client, _) = makeViewModel()
        viewModel.configure(
            with: LessonAudioView(
                available: true, url: "/v1/lessons/ds1-n1-l1/audio?v=abc123", durationSeconds: 261
            )
        )
        XCTAssertEqual(viewModel.state, .idle)
        XCTAssertEqual(viewModel.duration, 261)
        // Полтора мегабайта не качаются, пока человек не попросил звук.
        XCTAssertTrue(client.downloadedAudioPaths.isEmpty)
    }

    /// Ключ кэша содержит отпечаток сценария из адреса: иначе правка урока оставила бы
    /// на устройстве прошлую редакцию, и человек слушал бы не тот текст, что читает.
    func testCacheKeyCarriesTheScriptDigest() async {
        let client = StubAPIClient()
        client.audioFileURL = URL(fileURLWithPath: "/tmp/does-not-exist.mp3")
        let (viewModel, _, _) = makeViewModel(client)
        viewModel.configure(
            with: LessonAudioView(
                available: true, url: "/v1/lessons/ds1-n1-l1/audio?v=c94dcfe184d3", durationSeconds: 261
            )
        )
        await viewModel.toggle()
        XCTAssertEqual(client.downloadedAudioPaths, ["/v1/lessons/ds1-n1-l1/audio?v=c94dcfe184d3"])
    }

    func testFailedDownloadCanBeRetried() async {
        let (viewModel, _, _) = makeViewModel()  // audioFileURL не задан — загрузка падает
        viewModel.configure(
            with: LessonAudioView(
                available: true, url: "/v1/lessons/ds1-n1-l1/audio?v=abc123", durationSeconds: 261
            )
        )
        await viewModel.toggle()
        XCTAssertEqual(viewModel.state, .failed)
        XCTAssertFalse(viewModel.isPlaying)
        // Из .failed кнопка снова ведёт к загрузке, а не остаётся мёртвой.
        await viewModel.toggle()
        XCTAssertEqual(viewModel.state, .failed)
    }

    func testRatesAreOfferedForListening() {
        XCTAssertEqual(LessonAudioViewModel.rates.first, 1.0)
        XCTAssertTrue(LessonAudioViewModel.rates.contains(1.5))
    }
}
