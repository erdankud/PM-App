"""Оболочка веб-клиента: список предзагрузки и политика кэша.

Обе вещи ломаются молча. Разошедшийся с графом `modulepreload` не мешает
странице работать — она просто снова грузится столбиком, по обходу до сервера на
каждый уровень импортов, и заметить это можно только с секундомером. Шрифт,
уехавший из вечного кэша в перепроверку, тоже никак себя не проявляет.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


def _preload_map():
    """`web/tools/preload_map.py` — не пакет и на пути импорта не лежит."""
    spec = importlib.util.spec_from_file_location(
        "preload_map", WEB_ROOT / "tools" / "preload_map.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_modulepreload_lists_the_whole_module_graph():
    """Список считается по исходникам, а разметка обязана с ним совпадать.

    Новый экран добавляется одним импортом в app.js, и без перезапуска скрипта
    он приезжал бы по цепочке — то есть ровно тем способом, от которого список
    и заведён.
    """
    preload_map = _preload_map()
    markup = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert preload_map.preload_block() in markup, (
        "index.html разошёлся с графом модулей — python3 web/tools/preload_map.py"
    )
    # Список не должен молча выродиться в один app.js: граф глубокий, в этом всё дело.
    assert len(preload_map.module_graph()) > 20


def test_boot_screen_draws_the_same_mark_as_the_tab_icon():
    """Контур на экране загрузки встроен в разметку, а не взят из файла.

    Иначе первый кадр ждал бы ещё один обход до сервера — при том, что весь
    смысл этого экрана в том, чтобы нарисоваться первым байтом. Цена копии —
    возможность разойтись, её и проверяем.
    """
    markup = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    logo = (WEB_ROOT / "logo.svg").read_text(encoding="utf-8")
    start = logo.index('<path d="') + len('<path d="')
    path = logo[start : logo.index('"', start)]
    assert path in markup, "контур в index.html разошёлся с web/logo.svg"


def test_boot_screen_is_in_the_document_itself(client):
    """Ждать приходится модули, поэтому ждущий экран не может быть модулем."""
    markup = client.get("/app/").text
    assert 'id="boot"' in markup
    assert 'rel="modulepreload"' in markup
    # Счётчик обязан уметь досчитать: единицу ставит app.js, не таймер.
    assert "__pmBoot" in markup


def test_fonts_are_immutable_and_everything_else_revalidates(client):
    """Одно исключение, и оно названо по имени.

    Правка модуля должна доезжать до читателя сразу — значит `no-cache`. Шрифт
    под тем же именем не меняется никогда — значит год и `immutable`, иначе
    полмегабайта перепроверяются на каждом заходе впустую.
    """
    font = client.get("/app/fonts/onest-latin.woff2")
    assert font.status_code == 200
    assert "immutable" in font.headers["cache-control"]

    for path in ("/app/src/app.js", "/app/styles.css", "/app/fonts.css", "/app/index.html"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["cache-control"] == "no-cache", path
