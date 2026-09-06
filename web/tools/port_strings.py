"""Порт таблицы строк из iOS в веб.

`ios/PMThinkingCoach/Core/Localization/Strings.swift` — единственный источник копий
интерфейса: обе строки, английская и русская, стоят там на одной строке, и расхождение
видно в ревью. Веб-клиент не переписывает их руками, а получает этим скриптом:
переписанная вручную вторая копия разъезжается с первой на первой же правке.

    python3 web/tools/port_strings.py

Пишет `web/src/strings.js`. Всё, что не является строкой (единственный случай —
`Tree.statusTint`, возвращающий Color), пропускается: цвет у веба свой.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "ios/PMThinkingCoach/Core/Localization/Strings.swift"
TARGET = ROOT / "web/src/strings.js"

# Члены, у которых нет смысла на вебе: возвращают SwiftUI-цвет.
SKIP = {"Tree.statusTint", "Tree.blockAccessibility"}

# Заполняется на первом проходе: путь enum'а → имена его членов. В Swift соседний
# член виден по имени, в JS-объекте — нет, поэтому такие ссылки надо квалифицировать.
MEMBERS: dict[str, set[str]] = {}
CONTEXT: list[str] = []
# Имена параметров текущего члена: в Swift они перекрывают соседа по enum'у, и в JS
# должны перекрывать тоже. Без этого `evidenceCounter(reviewed:)` подставлял в текст
# строку `S.Challenge.reviewed` вместо числа.
SHADOWED: set[str] = set()

# Ключи enum'ов, которые приходят с сервера snake_case, а в Swift записаны camelCase.
CASE_NAMES = {
    "inProgress": "in_progress",
    "gateReady": "gate_ready",
    "notStarted": "not_started",
    "awaitingFeedback": "awaiting_feedback",
    "feedbackFailed": "feedback_failed",
    "comingSoon": "coming_soon",
    "signedIn": "signed_in",
    "goalSet": "goal_set",
}


def scan_string(src: str, i: int) -> tuple[str, int]:
    """Читает swift-литерал начиная с кавычки; возвращает JS-эквивалент и позицию за ним.

    Интерполяция `\\(...)` переводится в `${...}`, и литерал тогда становится
    шаблонным. Внутри интерполяции снова могут быть строки — отсюда рекурсия.
    """
    assert src[i] == '"'
    i += 1
    parts: list[str] = []
    interpolated = False
    while i < len(src):
        ch = src[i]
        if ch == '"':
            i += 1
            break
        if ch == "\\" and src[i + 1] == "(":
            interpolated = True
            inner, i = scan_interpolation(src, i + 2)
            parts.append("${" + inner + "}")
            continue
        if ch == "\\":
            parts.append(src[i : i + 2])
            i += 2
            continue
        if ch == "`":
            parts.append("\\`")
            i += 1
            continue
        if ch == "$":
            parts.append("\\$")
            i += 1
            continue
        parts.append(ch)
        i += 1
    body = "".join(parts)
    if interpolated:
        return "`" + body + "`", i
    return '"' + body.replace('"', '\\"') + '"', i


def scan_interpolation(src: str, i: int) -> tuple[str, int]:
    """Читает тело `\\(...)` до парной скобки, уважая вложенные строки."""
    depth = 1
    out: list[str] = []
    while i < len(src):
        ch = src[i]
        if ch == '"':
            literal, i = scan_string(src, i)
            out.append(literal)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return translate_code("".join(out)), i + 1
        out.append(ch)
        i += 1
    raise ValueError("unterminated interpolation")


def translate_code(code: str) -> str:
    """Свифтовые идиомы вне строковых литералов."""
    code = code.replace(".joined(separator: ", ".join(")
    code = re.sub(r"\b([A-Za-z_][\w.]*)\.capitalized\b", r"capitalize(\1)", code)
    code = re.sub(r"\blet\b", "const", code)
    # `case .gateReady:` — енам с сервера приезжает строкой.
    def case_name(match: re.Match) -> str:
        name = match.group(1)
        return '"%s"' % CASE_NAMES.get(name, name)

    code = re.sub(r"(?<![\w.])\.([a-zA-Z][\w]*)\b(?=\s*[:,])", case_name, code)
    if CONTEXT:
        path = CONTEXT[0]
        for name in MEMBERS.get(path, ()) - SHADOWED:  # соседи по enum'у
            code = re.sub(
                r"(?<![\w.$])" + re.escape(name) + r"\b", f"S.{path}.{name}", code
            )
    return code


def translate(src: str) -> str:
    """Переводит фрагмент swift-кода, разбирая строковые литералы по пути."""
    out: list[str] = []
    buffer: list[str] = []
    i = 0
    while i < len(src):
        ch = src[i]
        if ch == '"':
            out.append(translate_code("".join(buffer)))
            buffer = []
            literal, i = scan_string(src, i)
            out.append(literal)
            continue
        buffer.append(ch)
        i += 1
    out.append(translate_code("".join(buffer)))
    return "".join(out)


VAR_RE = re.compile(r"^\s*static var (\w+): String \{")
FUNC_RE = re.compile(r"^\s*static func (\w+)\(([^)]*)\) -> (\w+) \{")
ENUM_RE = re.compile(r"^\s*enum (\w+) \{")
LET_RE = re.compile(r"^\s*static let (\w+) = \[")


def params_of(raw: str) -> list[str]:
    """`_ count: Int, fallback: String` → ['count', 'fallback']."""
    names = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        head = part.split(":")[0].strip()
        pieces = head.split()
        names.append(pieces[-1])
    return names


def collect(lines: list[str]) -> None:
    """Первый проход: какие имена объявлены в каком enum'е.

    Тела членов пропускаются целиком: их закрывающая скобка на своей строке ничем
    не отличается от закрывающей скобки enum'а, и без этого стек разъезжается.
    """
    stack: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = ENUM_RE.match(line)
        if match and match.group(1) != "S":
            stack.append(match.group(1))
            MEMBERS.setdefault(".".join(stack), set())
            i += 1
            continue
        if line.strip() == "}" and stack:
            stack.pop()
            i += 1
            continue
        member = VAR_RE.match(line) or FUNC_RE.match(line) or LET_RE.match(line)
        if member:
            if stack:
                MEMBERS[".".join(stack)].add(member.group(1))
            if LET_RE.match(line):
                i = skip_array(lines, i)
            else:
                _, i = read_body(lines, i)
            continue
        i += 1


def emit(lines: list[str]) -> str:
    out: list[str] = []
    stack: list[str] = []
    i = 0
    indent = lambda: "  " * (len(stack))

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("//") or stripped.startswith("///"):
            i += 1
            continue

        match = ENUM_RE.match(line)
        if match and match.group(1) != "S":
            out.append(f"{indent()}{match.group(1)}: {{")
            stack.append(match.group(1))
            i += 1
            continue

        if stripped == "}" and stack:
            stack.pop()
            out.append(f"{indent()}}},")
            i += 1
            continue

        match = LET_RE.match(line)
        if match:
            name = match.group(1)
            end = skip_array(lines, i)
            raw = " ".join(part.strip() for part in lines[i:end])
            values = raw.split("=", 1)[1].strip().rstrip(",")
            out.append(f"{indent()}{name}: {values},")
            i = end
            continue

        match = VAR_RE.match(line)
        if match:
            name = match.group(1)
            body, i = read_body(lines, i)
            path = ".".join(stack + [name])
            if path in SKIP:
                continue
            CONTEXT[:] = [".".join(stack)]
            SHADOWED.clear()
            expr = " ".join(part.strip() for part in translate(body).split("\n") if part.strip())
            out.append(f"{indent()}get {name}() {{ return {expr}; }},")
            continue

        match = FUNC_RE.match(line)
        if match:
            name, raw_params, ret = match.groups()
            body, i = read_body(lines, i)
            path = ".".join(stack + [name])
            if path in SKIP or ret != "String":
                continue
            names = params_of(raw_params)
            args = ", ".join(names)
            CONTEXT[:] = [".".join(stack)]
            SHADOWED.clear()
            SHADOWED.update(names)
            js = translate(body)
            out.append(f"{indent()}{name}({args}) {{")
            for body_line in reformat(js, len(stack) + 1):
                out.append(body_line)
            out.append(f"{indent()}}},")
            continue

        i += 1

    return "\n".join(out)


def skip_array(lines: list[str], i: int) -> int:
    """Возвращает индекс строки за закрывающей `]` массива-константы."""
    depth = 0
    while i < len(lines):
        depth += lines[i].count("[") - lines[i].count("]")
        i += 1
        if depth <= 0:
            return i
    raise ValueError("unterminated array")


def read_body(lines: list[str], i: int) -> tuple[str, int]:
    """Собирает тело члена от открывающей скобки до парной закрывающей."""
    depth = 0
    parts: list[str] = []
    first = True
    while i < len(lines):
        line = lines[i]
        opens = line.count("{")
        closes = line.count("}")
        if first:
            parts.append(line.split("{", 1)[1])
            depth = opens - closes
            first = False
            if depth <= 0:
                # Однострочник: тело — всё до последней скобки.
                body = parts[0].rsplit("}", 1)[0]
                return body, i + 1
        else:
            depth += opens - closes
            if depth <= 0:
                parts.append(line.rsplit("}", 1)[0])
                return "\n".join(parts), i + 1
            parts.append(line)
        i += 1
    raise ValueError("unterminated body")


def reformat(js: str, level: int) -> list[str]:
    """Переносит свифтовый switch в JS-форму и расставляет отступы."""
    pad = "  " * level
    lines = [raw.strip() for raw in js.split("\n") if raw.strip()]
    # Тело из одного выражения в Swift возвращается неявно; в JS нужен `return`.
    if not any(line.startswith(("return", "switch", "const", "if ")) for line in lines):
        lines[0] = "return " + lines[0]
    result: list[str] = []
    for line in lines:
        if line.startswith("switch ") and line.endswith("{"):
            subject = line[len("switch ") : -1].strip()
            result.append(f"{pad}switch ({subject}) {{")
            continue
        result.append(pad + line)
    # `case X: return Y` без точки с запятой валиден, но выравнивание читается хуже;
    # оставляем как есть — ASI справляется.
    return result


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    lines = source.split("\n")
    # Всё, что до `enum S {`, и хвостовые хелперы разбираются вручную.
    start = next(index for index, line in enumerate(lines) if line.startswith("enum S {"))
    end = next(
        index for index, line in enumerate(lines) if line.startswith("/// Russian selects")
    )
    collect(lines[start + 1 : end])
    body = emit(lines[start + 1 : end])

    header = '''// СГЕНЕРИРОВАНО. Не редактируйте здесь.
//
// Источник — `ios/PMThinkingCoach/Core/Localization/Strings.swift`, пересборка:
//     python3 web/tools/port_strings.py
//
// Обе копии интерфейса живут в одном файле именно затем, чтобы перевод нельзя было
// поправить на одной платформе и забыть на другой.

import { t, plural, capitalize } from "./l10n.js";

export const S = {
'''
    footer = "};\n"
    TARGET.write_text(header + body + "\n" + footer, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
