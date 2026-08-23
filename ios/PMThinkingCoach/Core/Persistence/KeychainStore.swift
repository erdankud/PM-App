import Foundation
import Security

/// Tokens live in the Keychain, never in UserDefaults (spec §16, §17).
struct KeychainStore: Sendable {

    enum Key: String {
        case accessToken = "pmcoach.accessToken"
        case refreshToken = "pmcoach.refreshToken"
        case deviceIdentifier = "pmcoach.deviceIdentifier"
    }

    private let service: String

    init(service: String = Bundle.main.bundleIdentifier ?? "com.pmthinkingcoach.app") {
        self.service = service
    }

    func string(for key: Key) -> String? {
        guard let data = data(for: key) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func data(for key: Key) -> Data? {
        var query = baseQuery(for: key)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess else { return nil }
        return result as? Data
    }

    @discardableResult
    func set(_ value: String?, for key: Key) -> Bool {
        guard let value, let data = value.data(using: .utf8) else {
            return remove(key)
        }
        let query = baseQuery(for: key)
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]

        let updateStatus = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if updateStatus == errSecSuccess { return true }
        if updateStatus == errSecItemNotFound {
            var insert = query
            insert.merge(attributes) { current, _ in current }
            return SecItemAdd(insert as CFDictionary, nil) == errSecSuccess
        }
        return false
    }

    @discardableResult
    func remove(_ key: Key) -> Bool {
        SecItemDelete(baseQuery(for: key) as CFDictionary) == errSecSuccess
    }

    func removeAll() {
        remove(.accessToken)
        remove(.refreshToken)
    }

    /// Stable per-install identifier used only by the development sign-in path.
    func deviceIdentifier() -> String {
        if let existing = string(for: .deviceIdentifier) { return existing }
        let generated = "ios-" + UUID().uuidString
        set(generated, for: .deviceIdentifier)
        return generated
    }

    private func baseQuery(for key: Key) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key.rawValue
        ]
    }
}
