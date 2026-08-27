import SwiftUI

@main
struct PMThinkingCoachApp: App {

    @StateObject private var container = AppContainer()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(container)
                .environmentObject(container.session)
                .environmentObject(container.language)
                // Strings are read at body-evaluation time, so the tree is rebuilt on a
                // language change; `locale` carries the change into dates and numbers.
                .environment(\.locale, container.language.language.locale)
                .id(container.language.language)
                .task { await container.session.bootstrap() }
                .onChange(of: scenePhase) { _, phase in
                    guard phase == .active else { return }
                    // Server challenge state is authoritative; refresh on foreground.
                    Task { await container.session.refreshProfile() }
                }
        }
    }
}
