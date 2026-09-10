"""Список модулей для `modulepreload` в `web/index.html`.

Зачем это вообще нужно. Сборки у клиента нет — это принципиально (CLAUDE.md,
«Web client»), — а значит браузер узнаёт о существовании модуля только после
того, как скачает и разберёт того, кто его импортирует. Граф от `app.js` уходит
на шесть уровней вглубь, и каждый уровень — это отдельный обход до сервера.
На канале с задержкой 150 мс семь ступеней стоят секунду чистого ожидания,
причём каждый раз: файлы отдаются с `no-cache`, поэтому даже уже скачанный
модуль сначала спрашивают, не устарел ли он.

`modulepreload` убирает ступени, не добавляя сборки: браузер видит весь список
прямо в разметке и запрашивает все модули сразу, в один заход. Глубина графа
перестаёт что-либо стоить.

Список считается по исходникам, а не пишется рукой: рукописный разошёлся бы с
графом на первом же новом экране, и разошёлся бы молча — страница продолжала бы
работать, просто снова медленно. `tests/test_web_shell.py` сравнивает разметку
с тем, что вернёт эта функция, так что расхождение падает в CI.

    python3 web/tools/preload_map.py          # переписать index.html
    python3 web/tools/preload_map.py --check  # только проверить
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parent.parent
ENTRY = WEB_ROOT / "src" / "app.js"
INDEX = WEB_ROOT / "index.html"

BEGIN = "    <!-- modulepreload:begin -->"
END = "    <!-- modulepreload:end -->"

# Относительные спецификаторы: только они и ведут внутрь src/. Голых имён здесь
# нет и быть не может — ни npm, ни импортных карт у клиента нет.
_IMPORT = re.compile(r"""(?:^|[\s;])(?:import|export)[^'"();]*?['"](\.[^'"]+)['"]""", re.M)


def module_graph(entry: Path = ENTRY) -> list[Path]:
    """Все модули, достижимые из точки входа, в порядке обхода в ширину.

    Порядок — от точки входа к листьям. Браузеру он безразличен, все запросы
    уходят разом; он нужен, чтобы разметка не переставлялась от запуска к
    запуску и диффы читались.
    """
    seen: dict[Path, None] = {}
    queue = [entry.resolve()]
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen[current] = None
        try:
            source = current.read_text(encoding="utf-8")
        except OSError:
            continue
        for specifier in _IMPORT.findall(source):
            target = (current.parent / specifier).resolve()
            if target.suffix == ".js" and target.is_file() and target not in seen:
                queue.append(target)
    return list(seen)


def preload_block(entry: Path = ENTRY) -> str:
    """Готовый кусок разметки — ровно то, что должно лежать между маркерами."""
    lines = [BEGIN]
    for module in module_graph(entry):
        href = "./" + module.relative_to(WEB_ROOT).as_posix()
        lines.append(f'    <link rel="modulepreload" href="{href}" />')
    lines.append(END)
    return "\n".join(lines)


def rewrite(index: Path = INDEX, entry: Path = ENTRY) -> bool:
    """Заменить блок между маркерами. Возвращает True, если файл изменился."""
    markup = index.read_text(encoding="utf-8")
    start = markup.find(BEGIN)
    stop = markup.find(END)
    if start < 0 or stop < 0:
        raise SystemExit(f"{index}: не найдены маркеры modulepreload:begin/end")
    updated = markup[:start] + preload_block(entry) + markup[stop + len(END) :]
    if updated == markup:
        return False
    index.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="не переписывать, только сверить")
    args = parser.parse_args()

    markup = INDEX.read_text(encoding="utf-8")
    expected = preload_block()
    if args.check:
        if expected in markup:
            print(f"index.html: список актуален ({len(module_graph())} модулей)")
            return 0
        print("index.html: список разошёлся с графом — запустите без --check", file=sys.stderr)
        return 1

    changed = rewrite()
    print(f"index.html: {'обновлён' if changed else 'без изменений'}, {len(module_graph())} модулей")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
