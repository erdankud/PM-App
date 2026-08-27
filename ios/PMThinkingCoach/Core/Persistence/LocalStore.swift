import Foundation

/// On-device cache for drafts, the last Today payload, and pending idempotency keys.
///
/// The server remains the source of truth for score, XP, dates and skills; this exists
/// so an interrupted session never loses the user's writing (spec §16, §18).
/// Files are written with complete protection because drafts contain user content.
actor LocalStore {

    struct Draft: Codable, Sendable, Equatable {
        var attemptId: String
        var assignmentId: String
        var selectedOptionId: String?
        var rationale: String
        var reviewedEvidenceIds: [String]
        var updatedAt: Date
        var pendingSync: Bool
    }

    struct PendingSubmission: Codable, Sendable, Equatable {
        var attemptId: String
        var idempotencyKey: String
        var createdAt: Date
    }

    private struct Snapshot: Codable {
        var drafts: [String: Draft] = [:]
        var submissions: [String: PendingSubmission] = [:]
        var cachedTree: TreeResponse?
        var cachedTreeSavedAt: Date?
    }

    private let fileURL: URL
    private var snapshot: Snapshot

    init(filename: String = "pmcoach-local-store.json") {
        let directory = (try? FileManager.default.url(
            for: .applicationSupportDirectory, in: .userDomainMask,
            appropriateFor: nil, create: true
        )) ?? FileManager.default.temporaryDirectory
        self.fileURL = directory.appendingPathComponent(filename)

        if let data = try? Data(contentsOf: fileURL),
           let decoded = try? JSONDecoder().decode(Snapshot.self, from: data) {
            self.snapshot = decoded
        } else {
            self.snapshot = Snapshot()
        }
    }

    // MARK: - Drafts

    func draft(forAttempt attemptId: String) -> Draft? {
        snapshot.drafts[attemptId]
    }

    func saveDraft(_ draft: Draft) {
        snapshot.drafts[draft.attemptId] = draft
        persist()
    }

    func markDraftSynced(attemptId: String) {
        snapshot.drafts[attemptId]?.pendingSync = false
        persist()
    }

    func removeDraft(attemptId: String) {
        snapshot.drafts.removeValue(forKey: attemptId)
        persist()
    }

    func unsyncedDrafts() -> [Draft] {
        snapshot.drafts.values.filter(\.pendingSync).sorted { $0.updatedAt < $1.updatedAt }
    }

    // MARK: - Submissions

    /// The key persists until the submission resolves, so a retry after a crash or a
    /// network drop is recognised by the server as the same submission (spec §16).
    func idempotencyKey(forAttempt attemptId: String) -> String {
        if let existing = snapshot.submissions[attemptId] { return existing.idempotencyKey }
        let created = PendingSubmission(
            attemptId: attemptId, idempotencyKey: UUID().uuidString, createdAt: Date()
        )
        snapshot.submissions[attemptId] = created
        persist()
        return created.idempotencyKey
    }

    func clearSubmission(attemptId: String) {
        snapshot.submissions.removeValue(forKey: attemptId)
        persist()
    }

    // MARK: - Map cache

    /// The map is what a cold, offline launch can still show: the route is meaningful
    /// even when nothing new can be fetched.
    func cacheTree(_ response: TreeResponse) {
        snapshot.cachedTree = response
        snapshot.cachedTreeSavedAt = Date()
        persist()
    }

    func cachedTree() -> (payload: TreeResponse, savedAt: Date)? {
        guard let payload = snapshot.cachedTree, let savedAt = snapshot.cachedTreeSavedAt else {
            return nil
        }
        return (payload, savedAt)
    }

    // MARK: - Lifecycle

    /// Called on sign-out and account deletion. Local user content must not outlive
    /// the session (spec §18).
    func clearAll() {
        snapshot = Snapshot()
        try? FileManager.default.removeItem(at: fileURL)
    }

    private func persist() {
        guard let data = try? JSONEncoder().encode(snapshot) else { return }
        try? data.write(to: fileURL, options: [.atomic, .completeFileProtection])
    }
}
