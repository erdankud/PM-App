"""Корень отдаёт витрину, /app остаётся клиентом.

Проверка выглядит мелкой ровно до первого раза, когда её нет: раньше на `/`
стоял редирект в приложение, и вернуть его — это одна строка, после которой
человек по ссылке попадает сразу в форму входа, не узнав, куда пришёл.
"""

from __future__ import annotations


def test_root_serves_the_landing_and_app_still_serves_the_client(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.headers["content-type"].startswith("text/html")
    assert "PM Thinking Coach" in root.text
    # Единственная кнопка, ради которой страница существует.
    assert 'href="/app/"' in root.text

    app_page = client.get("/app/")
    assert app_page.status_code == 200
    assert 'src="/app/src/app.js"' in app_page.text or "app.js" in app_page.text


def test_landing_assets_are_served_from_the_same_origin(client):
    """Лендинг не ходит на сторонние хосты — как и клиент."""
    for path, media in (("/landing.css", "text/css"), ("/landing.js", "text/javascript")):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith(media)

    markup = client.get("/").text
    assert "//fonts.googleapis.com" not in markup
    assert "//cdn" not in markup
    assert "/app/fonts.css" in markup
