import Foundation

// Wire models for the skill map (spec v0.2 §12). Every status here is decided by the
// server; the client renders it and never derives availability of its own.

enum BlockStatus: String, Codable, Sendable {
    case locked
    case available
    case inProgress = "in_progress"
    case gateReady = "gate_ready"
    case passed

    var isOpen: Bool { self != .locked }
}

/// Whether the content behind a block has been written yet. Deliberately separate from
/// the learner's own progress: the whole map is visible from day one, so an unwritten
/// block has to be able to say so without pretending to be locked (spec v0.2 §2).
enum BlockContentStatus: String, Codable, Sendable {
    case published
    case comingSoon = "coming_soon"
}

struct TierView: Codable, Identifiable, Sendable {
    let tier: Int
    let title: String
    let subtitle: String

    var id: Int { tier }
}

struct DomainView: Codable, Identifiable, Sendable {
    let key: String
    let title: String
    let order: Int

    var id: String { key }
}

struct BlockSummary: Codable, Identifiable, Sendable {
    let id: String
    let domainKey: String
    let tier: Int
    let title: String
    let contentStatus: BlockContentStatus
    let status: BlockStatus
    let prerequisiteBlockIds: [String]
    let nodeCount: Int
    let lessonsTotal: Int
    let lessonsCompleted: Int
    let gateId: String?
    let attemptCount: Int

    var isWritten: Bool { contentStatus == .published }

    var lessonProgress: Double {
        guard lessonsTotal > 0 else { return 0 }
        return Double(lessonsCompleted) / Double(lessonsTotal)
    }
}

/// Одна из двух карт в переключателе «Продукт» / «Системы».
struct TreeSummary: Codable, Identifiable, Sendable {
    let kind: String
    let title: String
    let subtitle: String
    let blocksTotal: Int
    let blocksPassed: Int
    let blocksAvailable: Int

    var id: String { kind }
}

struct TreesResponse: Codable, Sendable {
    let trees: [TreeSummary]
}

struct TreeResponse: Codable, Sendable {
    let kind: String
    let version: Int
    let sourceAttribution: String
    let tiers: [TierView]
    let domains: [DomainView]
    let blocks: [BlockSummary]

    func blocks(inDomain key: String) -> [BlockSummary] {
        blocks.filter { $0.domainKey == key }.sorted { $0.tier < $1.tier }
    }

    func block(_ id: String) -> BlockSummary? { blocks.first { $0.id == id } }

    /// Название круга приходит из контента: у карты продукта это Junior / Middle /
    /// Senior, у System Design — «Читатель системы» и далее.
    func tierName(_ tier: Int) -> String? { tiers.first { $0.tier == tier }?.title }
}

struct NodeView: Codable, Identifiable, Sendable {
    let id: String
    let title: String
    let keyQuestion: String
    let models: [String]
    let aiImpact: String?
    let order: Int
}

struct LessonSummary: Codable, Identifiable, Sendable {
    let id: String
    let title: String
    let estimatedMinutes: Int
    let order: Int
    let completed: Bool
}

struct NodeDetail: Codable, Identifiable, Sendable {
    let node: NodeView
    let lessons: [LessonSummary]

    var id: String { node.id }
}

struct BlockDetailResponse: Codable, Sendable {
    let block: BlockSummary
    let domainTitle: String
    let tierTitle: String
    let nodes: [NodeDetail]
    let gateAvailable: Bool
    let gateBlockedReason: String?
    let passThreshold: Int

    var lessonsRemaining: Int {
        max(0, block.lessonsTotal - block.lessonsCompleted)
    }
}

/// One rendered element of a lesson. A single struct rather than an enum because the
/// server sends an open set of block types; unknown ones are skipped at render time
/// instead of failing the whole decode.
struct LessonBlockView: Codable, Identifiable, Sendable {
    let type: String
    let text: String?
    let title: String?
    let subtitle: String?
    let tone: String?
    let ordered: Bool?
    let items: [String]?
    let header: [String]?
    let rows: [[String]]?
    let diagramId: String?

    var id: String {
        type + (title ?? "") + (text?.prefix(24) ?? "") + (items?.first ?? "")
            + (diagramId ?? "")
    }
}

/// Секция урока System Design. Порядок фиксирован: вопрос, цена, суть, пример,
/// границы, вывод. Заголовки секций — структура для автора, читателю их не показываем.
struct LessonSectionView: Codable, Identifiable, Sendable {
    let kind: String
    let blocks: [LessonBlockView]

    var id: String { kind }
}

struct TermView: Codable, Identifiable, Sendable {
    let id: String
    let term: String
    let termEn: String
    let definition: String
    let blockId: String
    let sourceLessonId: String?
    let relatedIds: [String]
    let seen: Bool
}

struct GlossaryResponse: Codable, Sendable {
    let version: Int
    let terms: [TermView]
}

/// Схема приходит структурой, а не картинкой: клиент рисует её сам и умеет
/// прочитать вслух — у изображения такой возможности нет.
struct DiagramNodeView: Codable, Identifiable, Sendable {
    let id: String
    let type: String
    let label: String
}

struct DiagramEdgeView: Codable, Identifiable, Sendable {
    let from: String
    let to: String
    let type: String
    let label: String?

    var id: String { from + "->" + to + type }
}

struct DiagramView: Codable, Identifiable, Sendable {
    let id: String
    let title: String
    let nodes: [DiagramNodeView]
    let edges: [DiagramEdgeView]
    let textDescription: String
}

struct LessonResponse: Codable, Sendable {
    let id: String
    let nodeId: String
    let blockId: String
    let nodeTitle: String
    let title: String
    let estimatedMinutes: Int
    let keyTakeaway: String
    let checkQuestion: String?
    let blocks: [LessonBlockView]
    let sections: [LessonSectionView]
    let terms: [TermView]
    let diagrams: [DiagramView]
    let exerciseId: String?
    let crossRefs: [String]
    let audio: LessonAudioView?
    let completed: Bool
    let nextLessonId: String?

    /// Урок основного дерева — плоские блоки, System Design — секции.
    var isSectioned: Bool { !sections.isEmpty }

    func diagram(_ id: String) -> DiagramView? { diagrams.first { $0.id == id } }
}

// MARK: - Упражнения

struct ExerciseInputView: Codable, Identifiable, Sendable {
    let id: String
    let label: String
    let unit: String?
    let type: String
    let choices: [String]
}

struct ExerciseResponse: Codable, Sendable {
    let id: String
    let nodeId: String
    let blockId: String
    let type: String
    let title: String
    let estimatedMinutes: Int
    let promptBlocks: [LessonBlockView]
    let inputs: [ExerciseInputView]
    let submittedValues: [String: String]
    let diagrams: [DiagramView]
}

struct ExerciseInputResult: Codable, Identifiable, Sendable {
    let inputId: String
    let withinRange: Bool?
    let expectedHint: String?

    var id: String { inputId }
}

struct ExerciseSubmitResponse: Codable, Sendable {
    let exerciseId: String
    let results: [ExerciseInputResult]
    let referenceReasoningBlocks: [LessonBlockView]
}

/// Аудиоверсия урока. `available == false` — это норма, а не сбой: файл
/// собирается заранее скриптом, и урок без него просто не показывает плеер.
struct LessonAudioView: Codable, Sendable {
    let available: Bool
    let url: String?
    let durationSeconds: Int?
}

struct LessonCompleteResponse: Codable, Sendable {
    let lessonId: String
    let xpAwarded: Int
    let blockStatus: BlockStatus
    let lessonsCompleted: Int
    let lessonsTotal: Int
    let gateAvailable: Bool
}
