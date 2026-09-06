import Foundation

/// Build-time and runtime configuration.
///
/// There is deliberately no AI provider key, model name, or provider endpoint here.
/// Evaluation happens server-side only (spec §13, §17, §21).
enum AppConfig {

    /// Overridable at runtime from Profile → Developer so a device build can point at
    /// a Mac on the local network without a rebuild.
    static let baseURLOverrideKey = "pmcoach.apiBaseURLOverride"

    /// Read from Info.plist so the value can differ per build configuration.
    private static var configuredBaseURL: URL {
        if let raw = Bundle.main.object(forInfoDictionaryKey: "APIBaseURL") as? String,
           let url = URL(string: raw.trimmingCharacters(in: .whitespacesAndNewlines)),
           url.scheme != nil {
            return url
        }
        return URL(string: "http://localhost:8000")!
    }

    static var apiBaseURL: URL {
        if let override = UserDefaults.standard.string(forKey: baseURLOverrideKey),
           let url = URL(string: override.trimmingCharacters(in: .whitespacesAndNewlines)),
           url.scheme != nil {
            return url
        }
        return configuredBaseURL
    }

    static func setBaseURLOverride(_ value: String?) {
        let defaults = UserDefaults.standard
        guard let value, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            defaults.removeObject(forKey: baseURLOverrideKey)
            return
        }
        defaults.set(value, forKey: baseURLOverrideKey)
    }

    static var apiVersionPath: String { "/v1" }

    /// Enables the dev sign-in path. Sign in with Apple is the production route; the
    /// server rejects dev auth entirely when ALLOW_DEV_AUTH is false.
    static var allowsDeveloperSignIn: Bool {
        #if DEBUG
        return true
        #else
        return false
        #endif
    }

    static var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "0.0"
    }

    static var buildNumber: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "0"
    }

    /// Bounded polling after submit, so the user never sees an endless spinner (spec §16).
    static let feedbackPollAttempts = 5
    static let feedbackPollInterval: Duration = .seconds(2)

    /// Совпадает с проверкой сервера: короче он не примет, и просить незачем.
    static let passwordMinimum = 8

    static let rationaleMinimum = 30
    static let rationaleMaximum = 600
}
