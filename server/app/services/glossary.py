"""Глоссарий System Design и текстовые описания схем.

Отметка «встречал» ставится сама, когда термин попадается в открытом уроке: список
терминов урока известен из контента, поэтому отдельного действия от человека не нужно.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app import tree_content
from app.models import TermEncounter

# Как читается каждый примитив нотации — для скринридера и для описания схемы словами.
# Описание строится из структуры, поэтому оно всегда совпадает с нарисованным; ради
# этого словарь и держится здесь, а не в контенте.
NODE_WORDS = {
    "ru": {
        "client": "клиент",
        "service": "сервис",
        "store": "хранилище",
        "cache": "кэш",
        "queue": "очередь",
        "external": "внешняя система",
        "boundary": "граница",
        "actor": "участник",
    },
    "en": {
        "client": "client",
        "service": "service",
        "store": "store",
        "cache": "cache",
        "queue": "queue",
        "external": "external system",
        "boundary": "boundary",
        "actor": "actor",
    },
}
EDGE_WORDS = {
    "ru": {
        "sync": "синхронно вызывает",
        "async": "асинхронно отправляет в",
        "data": "передаёт данные в",
    },
    "en": {
        "sync": "calls synchronously",
        "async": "sends asynchronously to",
        "data": "passes data to",
    },
}
_FRAME = {
    "ru": ("Схема «{title}».", "Схема.", "Элементы: ", "Связи: "),
    "en": ('Diagram "{title}".', "Diagram.", "Elements: ", "Links: "),
}


def seen_term_ids(db: Session, user_id: str) -> set[str]:
    rows = db.query(TermEncounter.term_id).filter(TermEncounter.user_id == user_id).all()
    return {row[0] for row in rows}


def mark_seen(db: Session, user_id: str, term_ids: list[str]) -> None:
    """Идемпотентно: повторный заход в урок ничего не меняет."""
    if not term_ids:
        return
    known = seen_term_ids(db, user_id)
    for term_id in term_ids:
        if term_id in known or tree_content.glossary_term(term_id) is None:
            continue
        db.add(TermEncounter(user_id=user_id, term_id=term_id))
        known.add(term_id)


def describe_diagram(diagram: dict[str, Any], language: str = "ru") -> str:
    """Схема словами.

    Структура даёт то, чего не даёт картинка: описание строится автоматически и
    всегда совпадает с тем, что нарисовано (спека System Design §10).
    """
    labels = {node["id"]: node["label"] for node in diagram["nodes"]}
    titled, untitled, elements, links_word = _FRAME.get(language, _FRAME["ru"])
    node_words = NODE_WORDS.get(language, NODE_WORDS["ru"])
    edge_words = EDGE_WORDS.get(language, EDGE_WORDS["ru"])
    dash = " — " if language == "ru" else " - "

    parts = [titled.format(title=diagram["title"]) if diagram.get("title") else untitled]
    parts.append(
        elements
        + ", ".join(
            f"{node['label']}{dash}{node_words.get(node['type'], node['type'])}"
            for node in diagram["nodes"]
        )
        + "."
    )
    if diagram["edges"]:
        links = []
        for edge in diagram["edges"]:
            verb = edge_words.get(edge["type"], edge["type"])
            tail = f" ({edge['label']})" if edge.get("label") else ""
            links.append(
                f"{labels.get(edge['from'], edge['from'])} {verb} "
                f"{labels.get(edge['to'], edge['to'])}{tail}"
            )
        parts.append(links_word + "; ".join(links) + ".")
    return " ".join(parts)


def diagram_view(diagram: dict, language: str = "ru") -> Any:
    """Схема для клиента: примитивы плюс описание словами.

    Живёт здесь, а не в роутере, потому что схему отдают и урок, и упражнение, —
    а описание словами должно строиться одинаково в обоих местах.
    """
    from app.schemas import DiagramEdgeView, DiagramNodeView, DiagramView

    return DiagramView(
        id=diagram["id"],
        title=diagram["title"],
        nodes=[DiagramNodeView(**node) for node in diagram["nodes"]],
        edges=[
            DiagramEdgeView(
                **{
                    "from": edge["from"],
                    "to": edge["to"],
                    "type": edge["type"],
                    "label": edge.get("label"),
                }
            )
            for edge in diagram["edges"]
        ],
        # Схема — структура, поэтому текстовое описание строится само: у картинки
        # такой возможности нет (спека SD §10).
        text_description=describe_diagram(diagram, language),
    )
