import Foundation
import SwiftUI

/// Owns the session: tokens, the signed-in profile, and the top-level route.
///
/// Nothing here computes score, XP, level or "today" — those arrive from the server
/// and are only displayed (spec §12, §16).
@MainActor
final class SessionStore: ObservableObject {

    enum Route: Equatable {
        case launching
        case signedOut
        case onboarding
        case main
    }

    @Published private(set) var route: Route = .launching
    @Published private(set) var me: MeResponse?
    @Published var authError: APIError?
    @Published private(set) var isAuthenticating = false

    private let client: APIClient
    private let keychain: KeychainStore
    private let localStore: LocalStore
    private let analytics: any AnalyticsTracking

    private var accessToken: String?
    private var refreshTokenValue: String?
    private var refreshTask: Task<String?, Never>?

    init(
        client: APIClient,
        keychain: KeychainStore,
        localStore: LocalStore,
        analytics: any AnalyticsTracking
    ) {
        self.client = client
        self.keychain = keychain
        self.localStore = localStore
        self.analytics = analytics
        self.accessToken = keychain.string(for: .accessToken)
        self.refreshTokenValue = keychain.string(for: .refreshToken)
        client.attach(tokenProvider: self)
    }

    // MARK: - Bootstrap

    func bootstrap() async {
        analytics.track(.appOpened(source: "cold_start"))
        guard accessToken != nil || refreshTokenValue != nil else {
            route = .signedOut
            return
        }
        do {
            let profile = try await client.me()
            apply(profile)
        } catch APIError.unauthorized {
            await clearSession()
        } catch {
            // Offline or server trouble with credentials that still look valid: continue
            // into the app and let feature screens show their own recovery state rather
            // than bouncing the user back to sign-in (spec §18).
            route = .main
        }
    }

    /// Called when the app returns to the foreground (spec §16).
    func refreshProfile() async {
        guard route == .main || route == .onboarding else { return }
        if let profile = try? await client.me() {
            apply(profile)
        }
    }

    // MARK: - Sign in

    func signInWithApple(identityToken: String) async {
        await signIn(method: "apple") {
            try await self.client.signInWithApple(
                identityToken: identityToken, timezone: TimeZone.current.identifier
            )
        }
    }

    func signInAsDeveloper() async {
        let deviceId = keychain.deviceIdentifier()
        await signIn(method: "dev") {
            try await self.client.signInDeveloper(
                deviceId: deviceId, timezone: TimeZone.current.identifier
            )
        }
    }

    private func signIn(method: String, operation: @escaping () async throws -> AuthResponse) async {
        isAuthenticating = true
        authError = nil
        analytics.track(.authStarted(method: method))
        defer { isAuthenticating = false }
        do {
            let response = try await operation()
            store(tokens: response)
            apply(response.user)
            analytics.track(.authCompleted(method: method))
        } catch let error as APIError {
            authError = error
            analytics.track(.authFailed(method: method, errorCode: error.code))
        } catch {
            authError = .server(status: -1, code: "unknown")
            analytics.track(.authFailed(method: method, errorCode: "unknown"))
        }
    }

    // MARK: - Session state

    func apply(_ profile: MeResponse) {
        me = profile
        route = profile.status == .complete ? .main : .onboarding
    }

    func signOut() async {
        let token = refreshTokenValue
        try? await client.signOut(refreshToken: token)
        await clearSession()
    }

    func deleteAccount() async throws {
        analytics.track(.accountDeletionRequested)
        try await client.deleteAccount()
        await clearSession()
    }

    private func clearSession() async {
        accessToken = nil
        refreshTokenValue = nil
        keychain.removeAll()
        await localStore.clearAll()
        me = nil
        route = .signedOut
    }

    private func store(tokens response: AuthResponse) {
        accessToken = response.accessToken
        refreshTokenValue = response.refreshToken
        keychain.set(response.accessToken, for: .accessToken)
        keychain.set(response.refreshToken, for: .refreshToken)
    }
}

// MARK: - TokenProviding

extension SessionStore: TokenProviding {

    nonisolated func currentAccessToken() async -> String? {
        await MainActor.run { self.accessToken }
    }

    nonisolated func refreshAccessToken() async -> String? {
        await performRefresh()
    }

    nonisolated func handleAuthenticationFailure() async {
        await MainActor.run { self.route = .signedOut }
        await clearSessionFromBackground()
    }

    private func clearSessionFromBackground() async {
        await MainActor.run {
            self.accessToken = nil
            self.refreshTokenValue = nil
            self.keychain.removeAll()
            self.me = nil
        }
        await localStore.clearAll()
    }

    /// Single-flight: concurrent 401s share one refresh call.
    private func performRefresh() async -> String? {
        if let existing = refreshTask {
            return await existing.value
        }
        guard let refreshToken = refreshTokenValue else { return nil }

        let task = Task<String?, Never> { [client] in
            do {
                let response = try await client.refresh(refreshToken: refreshToken)
                await MainActor.run {
                    self.store(tokens: response)
                    self.me = response.user
                }
                return response.accessToken
            } catch {
                return nil
            }
        }
        refreshTask = task
        let result = await task.value
        refreshTask = nil
        return result
    }
}
