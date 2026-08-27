import SwiftUI

/// Текст урока с размеченными терминами.
///
/// Сервер присылает `[[идентификатор|как в тексте]]`. Термин подчёркивается пунктиром
/// и по тапу открывает карточку — для новичка, у которого в первом же уроке шесть
/// незнакомых слов, это условие читаемости, а не украшение. Разметка без известного
/// термина не доезжает до клиента: подчёркивание, ведущее в никуда, хуже обычного слова.
struct TermText: View {
    let raw: String
    let onTapTerm: (String) -> Void

    var body: some View {
        segments.reduce(Text("")) { partial, segment in
            partial + segment.text
        }
        .environment(\.openURL, OpenURLAction { url in
            guard url.scheme == Self.scheme else { return .systemAction }
            onTapTerm(url.host ?? url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
            return .handled
        })
    }

    private static let scheme = "pmterm"

    private struct Segment {
        let text: Text
    }

    /// Разбор идёт вручную, а не регулярным выражением по всей строке: нужно
    /// сохранить порядок обычных кусков и ссылок, а Text склеивается по частям.
    private var segments: [Segment] {
        var result: [Segment] = []
        var rest = Substring(raw)
        while let open = rest.range(of: "[["), let close = rest.range(of: "]]"),
              open.upperBound <= close.lowerBound {
            let before = rest[..<open.lowerBound]
            if !before.isEmpty { result.append(Segment(text: markdown(String(before)))) }

            let inner = rest[open.upperBound..<close.lowerBound]
            let parts = inner.split(separator: "|", maxSplits: 1)
            if parts.count == 2, let url = URL(string: "\(Self.scheme)://\(parts[0])") {
                var link = AttributedString(String(parts[1]))
                link.link = url
                link.underlineStyle = .init(pattern: .dot, color: nil)
                link.foregroundColor = Theme.Palette.primaryText
                result.append(Segment(text: Text(link)))
            } else {
                result.append(Segment(text: Text(String(inner))))
            }
            rest = rest[close.upperBound...]
        }
        if !rest.isEmpty { result.append(Segment(text: markdown(String(rest)))) }
        return result
    }

    /// Авторский текст использует `**жирный**`; неразобранное показываем как есть,
    /// а не теряем абзац.
    private func markdown(_ value: String) -> Text {
        if let attributed = try? AttributedString(
            markdown: value,
            options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        ) {
            return Text(attributed)
        }
        return Text(value)
    }
}
