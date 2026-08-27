import Foundation

@MainActor
final class ProfileViewModel: ObservableObject {

    @Published var isDeleting = false
    @Published var error: APIError?
    @Published var baseURLOverride: String = UserDefaults.standard.string(
        forKey: AppConfig.baseURLOverrideKey
    ) ?? ""

    private let client: any APIClientProtocol
    private let session: SessionStore

    init(client: any APIClientProtocol, session: SessionStore) {
        self.client = client
        self.session = session
    }

    var me: MeResponse? { session.me }

    func changeRole(_ role: String) async {
        do {
            // The role only highlights part of the map; it changes no unlock order and
            // rewrites no history (spec v0.2 §7).
            let profile = try await client.updateProfile(
                ProfileUpdateRequest(targetRole: role, timezone: nil, completeOnboarding: nil)
            )
            session.apply(profile)
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }

    func signOut() async {
        await session.signOut()
    }

    func deleteAccount() async {
        isDeleting = true
        defer { isDeleting = false }
        do {
            try await session.deleteAccount()
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }

    func applyBaseURLOverride() {
        AppConfig.setBaseURLOverride(baseURLOverride.isEmpty ? nil : baseURLOverride)
    }
}
