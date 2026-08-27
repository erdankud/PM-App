import Foundation
import SwiftUI

@MainActor
final class ExerciseViewModel: ObservableObject {

    @Published private(set) var exercise: ExerciseResponse?
    @Published private(set) var result: ExerciseSubmitResponse?
    @Published private(set) var isLoading = false
    @Published private(set) var isSubmitting = false
    @Published private var values: [String: String] = [:]

    private let exerciseId: String
    private let client: any APIClientProtocol
    private let analytics: any AnalyticsTracking
    private var startedAt = Date()

    init(exerciseId: String, client: any APIClientProtocol, analytics: any AnalyticsTracking) {
        self.exerciseId = exerciseId
        self.client = client
        self.analytics = analytics
    }

    func binding(for inputId: String) -> Binding<String> {
        Binding(
            get: { self.values[inputId] ?? "" },
            set: { self.values[inputId] = $0 }
        )
    }

    /// Формулировка зависит от типа упражнения и нигде не говорит «неправильно»:
    /// у прикидки сверяется порядок величины, у разбора по категориям — совпадение
    /// с эталоном. Упражнение формирующее, его дело — показать разбор, а не оценить.
    func outcome(for inputId: String) -> String? {
        guard let result, let item = result.results.first(where: { $0.inputId == inputId })
        else { return nil }
        guard let within = item.withinRange else { return S.Exercise.notAnswered }
        let base: String
        if exercise?.type == "classification" {
            base = within ? S.Exercise.sameAsReference : S.Exercise.otherThanReference
        } else {
            base = within ? S.Exercise.orderRight : S.Exercise.orderOff
        }
        if let hint = item.expectedHint, !within { return "\(base) · \(hint)" }
        return base
    }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await client.exercise(id: exerciseId)
            exercise = response
            values = response.submittedValues
            startedAt = Date()
            analytics.track(.exerciseStarted(exerciseId: exerciseId, type: response.type))
        } catch {
            exercise = nil
        }
    }

    func submit(skipped: Bool) async {
        guard !isSubmitting else { return }
        isSubmitting = true
        defer { isSubmitting = false }
        do {
            let response = try await client.submitExercise(
                id: exerciseId, values: skipped ? [:] : values
            )
            result = response
            if skipped {
                analytics.track(.exerciseSkipped(exerciseId: exerciseId))
            } else {
                let within = response.results.allSatisfy { $0.withinRange == true }
                analytics.track(
                    .exerciseSubmitted(
                        exerciseId: exerciseId,
                        type: exercise?.type ?? "open",
                        withinRange: within,
                        seconds: Int(Date().timeIntervalSince(startedAt))
                    )
                )
            }
        } catch {
            result = nil
        }
    }
}

