import SwiftUI

/// Схема из структуры, а не картинка.
///
/// Восемь примитивов и три типа связи, раскладка по слоям: клиенты слева, сервисы в
/// середине, хранилища ниже, внешние системы справа. Постоянство расположения важнее
/// компактности — человек должен узнавать схему, а не разбирать её заново.
/// Побочная выгода структуры: VoiceOver читает схему словами, чего картинка не умеет.
struct DiagramCanvas: View {
    let diagram: DiagramView
    var compact: Bool = true

    private static let layers: [[String]] = [
        ["actor", "client"],
        ["service", "queue", "cache"],
        ["store"],
        ["external"],
    ]

    private var columns: [[DiagramNodeView]] {
        var result: [[DiagramNodeView]] = Array(repeating: [], count: Self.layers.count)
        var leftovers: [DiagramNodeView] = []
        for node in diagram.nodes {
            if let index = Self.layers.firstIndex(where: { $0.contains(node.type) }) {
                result[index].append(node)
            } else {
                leftovers.append(node)
            }
        }
        if !leftovers.isEmpty { result[1].append(contentsOf: leftovers) }
        return result.filter { !$0.isEmpty }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            if !diagram.title.isEmpty {
                Text(diagram.title)
                    .font(.caption)
                    .foregroundStyle(Theme.Palette.secondaryText)
            }
            HStack(alignment: .top, spacing: Theme.Spacing.l) {
                ForEach(Array(columns.enumerated()), id: \.offset) { _, column in
                    VStack(spacing: Theme.Spacing.s) {
                        ForEach(column) { node in
                            DiagramNodeShape(node: node)
                        }
                    }
                }
            }
            if !diagram.edges.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(diagram.edges) { edge in
                        EdgeRow(edge: edge, labels: labels)
                    }
                }
            }
        }
        .padding(Theme.Spacing.m)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.Palette.surfaceTinted, in: RoundedRectangle(cornerRadius: Theme.Radius.card))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(diagram.textDescription)
    }

    private var labels: [String: String] {
        Dictionary(uniqueKeysWithValues: diagram.nodes.map { ($0.id, $0.label) })
    }
}

/// Один примитив. Форма несёт смысл: цилиндр — данные, пунктир — чужое или ненадёжное.
private struct DiagramNodeShape: View {
    let node: DiagramNodeView

    var body: some View {
        Text(node.label)
            .font(.caption)
            .multilineTextAlignment(.center)
            .foregroundStyle(Theme.Palette.primaryText)
            .padding(.horizontal, Theme.Spacing.s)
            .padding(.vertical, 6)
            .frame(minWidth: 84)
            .background(background)
            .overlay(border)
    }

    @ViewBuilder private var background: some View {
        switch node.type {
        case "service":
            RoundedRectangle(cornerRadius: Theme.Radius.control).fill(Theme.Palette.accent.opacity(0.12))
        case "store", "cache":
            RoundedRectangle(cornerRadius: Theme.Radius.card).fill(Theme.Palette.surface)
        case "actor":
            Capsule().fill(Theme.Palette.surface)
        default:
            RoundedRectangle(cornerRadius: Theme.Radius.control).fill(Theme.Palette.surface)
        }
    }

    @ViewBuilder private var border: some View {
        let dashed = node.type == "cache" || node.type == "external"
        let style = StrokeStyle(lineWidth: 1, dash: dashed ? [4, 3] : [])
        switch node.type {
        case "actor":
            Capsule().strokeBorder(Theme.Palette.separator, style: style)
        case "store", "cache":
            RoundedRectangle(cornerRadius: Theme.Radius.card)
                .strokeBorder(Theme.Palette.separator, style: style)
        default:
            RoundedRectangle(cornerRadius: Theme.Radius.control)
                .strokeBorder(Theme.Palette.separator, style: style)
        }
    }
}

private struct EdgeRow: View {
    let edge: DiagramEdgeView
    let labels: [String: String]

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: symbol)
                .font(.caption2)
                .foregroundStyle(Theme.Palette.secondaryText)
            Text(text)
                .font(.caption)
                .foregroundStyle(Theme.Palette.secondaryText)
        }
    }

    private var symbol: String {
        switch edge.type {
        case "async": return "arrow.right.to.line.compact"
        case "data": return "minus"
        default: return "arrow.right"
        }
    }

    private var text: String {
        let from = labels[edge.from] ?? edge.from
        let to = labels[edge.to] ?? edge.to
        let suffix = edge.label.map { " — \($0)" } ?? ""
        return "\(from) → \(to)\(suffix)"
    }
}
