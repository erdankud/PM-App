import AVFoundation
import Foundation
import MediaPlayer

/// Аудиоверсия урока — тот же авторский текст, прочитанный вслух.
///
/// Файл сначала скачивается целиком и только потом играет. Так дороже на старте,
/// но урок слушают в дороге, и второй раз он должен открываться без сети. По той же
/// причине здесь настроены категория аудиосессии и элементы управления на экране
/// блокировки: слушать с погашенным экраном — основной сценарий, а не крайний случай.
@MainActor
final class LessonAudioViewModel: NSObject, ObservableObject {

    enum State: Equatable {
        case unavailable
        /// Обзора нет, но собрать его можно — это авторский режим.
        case buildable
        case building
        case buildFailed
        case idle
        case loading
        case ready
        case failed
    }

    @Published private(set) var state: State = .unavailable
    @Published private(set) var isPlaying = false
    @Published private(set) var position: Double = 0
    @Published private(set) var duration: Double = 0
    @Published var rate: Float = 1.0 {
        didSet {
            guard isPlaying else { return }
            player?.rate = rate
        }
    }

    static let rates: [Float] = [1.0, 1.25, 1.5, 1.75]

    private let lessonId: String
    private let client: any APIClientProtocol
    private let analytics: any AnalyticsTracking
    private var player: AVPlayer?
    private var timeObserver: Any?
    private var endObserver: NSObjectProtocol?
    private var audio: LessonAudioView?
    private var startedListening = false

    init(lessonId: String, client: any APIClientProtocol, analytics: any AnalyticsTracking) {
        self.lessonId = lessonId
        self.client = client
        self.analytics = analytics
        super.init()
    }

    deinit {
        if let endObserver { NotificationCenter.default.removeObserver(endObserver) }
    }

    func configure(with audio: LessonAudioView?) {
        self.audio = audio
        guard let audio else {
            state = .unavailable
            return
        }
        guard audio.available, audio.url != nil else {
            // Обзора нет. Для автора это приглашение собрать, для всех остальных —
            // просто отсутствие плеера.
            switch audio.status {
            case "generating": state = .building
            case "failed": state = audio.canGenerate ? .buildFailed : .unavailable
            default: state = audio.canGenerate ? .buildable : .unavailable
            }
            return
        }
        duration = Double(audio.durationSeconds ?? 0)
        if state != .ready { state = .idle }
    }

    /// Просит сервер собрать обзор и ждёт результата, переспрашивая урок.
    ///
    /// Сборка занимает около минуты, поэтому это опрос, а не одно ожидание ответа:
    /// запрос, висящий минуту, оборвётся на первом же переключении сети.
    func build(reload: @escaping () async -> LessonAudioView?) async {
        guard state == .buildable || state == .buildFailed else { return }
        state = .building
        do {
            _ = try await client.generateAudio(lessonId: lessonId)
        } catch {
            state = .buildFailed
            return
        }
        for _ in 0..<60 {
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            let fresh = await reload()
            if fresh?.available == true || fresh?.status == "failed" {
                configure(with: fresh)
                return
            }
        }
        state = .buildFailed
    }

    /// Одна кнопка на все состояния: не загружено — загрузит и заиграет.
    func toggle() async {
        switch state {
        case .unavailable, .loading, .buildable, .building, .buildFailed:
            return
        case .idle, .failed:
            await load()
            if state == .ready { play() }
        case .ready:
            isPlaying ? pause() : play()
        }
    }

    private func load() async {
        guard let audio, let path = audio.url else { return }
        state = .loading
        do {
            // Ключ кэша — отпечаток сценария из адреса: правка урока отменяет файл.
            let key = URLComponents(string: path)?
                .queryItems?.first(where: { $0.name == "v" })?.value ?? lessonId
            let file = try await client.downloadAudio(path: path, cacheKey: "\(lessonId)-\(key)")
            try await prepare(file)
            state = .ready
        } catch {
            state = .failed
        }
    }

    private func prepare(_ file: URL) async throws {
        try AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio)
        try AVAudioSession.sharedInstance().setActive(true)

        let item = AVPlayerItem(url: file)
        let player = AVPlayer(playerItem: item)
        player.actionAtItemEnd = .pause
        self.player = player

        // Длительность из файла точнее оценки сервера, которая считается по словам.
        if let loaded = try? await item.asset.load(.duration).seconds,
           loaded.isFinite, loaded > 0 {
            duration = loaded
        }

        timeObserver = player.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 0.5, preferredTimescale: 600), queue: .main
        ) { [weak self] time in
            MainActor.assumeIsolated { self?.position = time.seconds }
        }
        endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime, object: item, queue: .main
        ) { [weak self] _ in
            MainActor.assumeIsolated { self?.finish() }
        }
        setUpRemoteControls()
    }

    func play() {
        guard let player else { return }
        player.playImmediately(atRate: rate)
        isPlaying = true
        updateNowPlaying()
        if !startedListening {
            startedListening = true
            analytics.track(.lessonAudioStarted(lessonId: lessonId))
        }
    }

    func pause() {
        player?.pause()
        isPlaying = false
        updateNowPlaying()
    }

    func seek(to seconds: Double) {
        guard let player else { return }
        let clamped = max(0, min(seconds, duration))
        player.seek(to: CMTime(seconds: clamped, preferredTimescale: 600))
        position = clamped
        updateNowPlaying()
    }

    func skip(by seconds: Double) {
        seek(to: position + seconds)
    }

    private func finish() {
        isPlaying = false
        position = duration
        analytics.track(.lessonAudioFinished(lessonId: lessonId))
        updateNowPlaying()
    }

    /// Плеер живёт вместе с экраном урока: уходя, звук не оставляем.
    func teardown() {
        pause()
        if let timeObserver { player?.removeTimeObserver(timeObserver) }
        timeObserver = nil
        if let endObserver { NotificationCenter.default.removeObserver(endObserver) }
        endObserver = nil
        player = nil
        MPNowPlayingInfoCenter.default().nowPlayingInfo = nil
        UIApplication.shared.endReceivingRemoteControlEvents()
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    // MARK: - Экран блокировки

    private func setUpRemoteControls() {
        let center = MPRemoteCommandCenter.shared()
        center.playCommand.addTarget { [weak self] _ in
            MainActor.assumeIsolated { self?.play() }
            return .success
        }
        center.pauseCommand.addTarget { [weak self] _ in
            MainActor.assumeIsolated { self?.pause() }
            return .success
        }
        center.skipForwardCommand.preferredIntervals = [15]
        center.skipBackwardCommand.preferredIntervals = [15]
        center.skipForwardCommand.addTarget { [weak self] _ in
            MainActor.assumeIsolated { self?.skip(by: 15) }
            return .success
        }
        center.skipBackwardCommand.addTarget { [weak self] _ in
            MainActor.assumeIsolated { self?.skip(by: -15) }
            return .success
        }
        UIApplication.shared.beginReceivingRemoteControlEvents()
    }

    var nowPlayingTitle: String = ""

    private func updateNowPlaying() {
        MPNowPlayingInfoCenter.default().nowPlayingInfo = [
            MPMediaItemPropertyTitle: nowPlayingTitle,
            MPMediaItemPropertyArtist: S.Lesson.audioTitle,
            MPMediaItemPropertyPlaybackDuration: duration,
            MPNowPlayingInfoPropertyElapsedPlaybackTime: position,
            MPNowPlayingInfoPropertyPlaybackRate: isPlaying ? Double(rate) : 0,
        ]
    }
}
