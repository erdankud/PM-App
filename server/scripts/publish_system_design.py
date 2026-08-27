#!/usr/bin/env python3
"""Достройка импортированных сценариев System Design до публикуемых.

    python -m scripts.publish_system_design

Импорт (`scripts/import_system_design.py`) переносит из авторского markdown всё, что
в нём есть: бриф, evidence, опции с последствиями, сигналы рубрики и ремедиацию. Чего
в источнике нет — весов опций и QA-фикстур, — дописывается здесь: веса выводятся из
формулировок рубрики («Reference: C», «B защитима… полный балл», «D слаба»), а
фикстуры и несколько полей брифа берутся из `scripts/sd_supplements.py`.

Сценарий без фикстур не публикуется: без них порог 70 не с чем калибровать.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.sd_supplements import SUPPLEMENTS  # noqa: E402

SRC = ROOT / "content" / "system-design" / "scenarios-draft"
OUT = ROOT / "content" / "system-design" / "scenarios"
TREE = ROOT / "content" / "system-design" / "tree.json"
GATES = ROOT / "content" / "system-design" / "gates.json"

COMPANY = (
    "«Полка» — вымышленный сервис доставки продуктов из локальных магазинов: "
    "900 магазинов-партнёров, приложение покупателя и кабинет партнёра."
)
ROLE = "Вы продакт «Полки»."

CARD_TYPES = [
    (("метрик", "разбор времени", "аналитик", "числ", "нагрузк", "логи", "замер",
      "статистик", "показател", "трафик"), "quantitative"),
    (("инженер", "техлид", "устроен", "архитектур", "код", "поиск", "нарезк",
      "схема данных", "инфраструктур", "техническ"), "technical"),
    (("финанс", "деньг", "стоимост", "бюджет", "партнёр", "маркетинг", "продаж",
      "клиент", "сделк", "контракт", "регулятор", "юрист", "бизнес"), "business"),
]

TIER_LEVEL = {1: "foundation", 2: "developing", 3: "advanced"}


def slug(value: str) -> str:
    table = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
        "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    out = []
    for ch in value.lower():
        if ch in table:
            out.append(table[ch])
        elif ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
    return re.sub(r"-+", "-", "".join(out)).strip("-")[:40] or "card"


def card_type(title: str, body: str) -> str:
    haystack = (title + " " + body[:200]).lower()
    for words, kind in CARD_TYPES:
        if any(word in haystack for word in words):
            return kind
    return "qualitative"


def evidence_cards(raw: str) -> list[dict[str, Any]]:
    """Evidence в источнике — абзацы вида «*Заголовок.* текст»."""
    chunks = re.split(r"\*([^*]+?)\.\*", raw)
    cards: list[dict[str, Any]] = []
    for index in range(1, len(chunks) - 1, 2):
        title = chunks[index].strip()
        body = " ".join(chunks[index + 1].split()).strip()
        if not body:
            continue
        # Совсем короткая карточка вроде «Внедрение — неделя» без заголовка теряет
        # смысл: заголовок несёт половину факта, поэтому возвращаем его в текст.
        content = body if len(body) >= 40 else f"{title}. {body}"
        cards.append({
            "id": slug(title),
            "title": title[:60],
            "type": card_type(title, body),
            "order": len(cards) + 1,
            "content": content[:2000],
        })
    return cards[:4]


def option_weights(reference: str, rubric_text: str, option_ids: list[str]) -> dict[str, int]:
    """Веса опций из формулировок рубрики.

    Эталон — 25. Защитимая с полным баллом — 20, защитимая с оговорками — 13.
    Названная слабой — 7. Остальные — 10: не эталон, но и не разобранная ошибка.
    """
    weights = {option_id: 10 for option_id in option_ids}
    head = reference.split(".")[0]
    # Рубрика часто называет две опции: «B сейчас, C планово». Решение — первая,
    # вторая это следующий шаг, и она защитима с полным баллом.
    referenced = [
        (match.start(), option_id)
        for option_id in option_ids
        if (match := re.search(rf"\b{option_id}\b", head))
    ]
    referenced.sort()
    ordered = [option_id for _, option_id in referenced]
    if ordered:
        weights[ordered[0]] = 25
    for option_id in ordered[1:]:
        weights[option_id] = 20
    referenced = ordered[:1]

    for option_id in option_ids:
        if option_id in referenced:
            continue
        pattern = re.compile(
            rf"\*\*{option_id}[^*]*\*\*(.{{0,400}})", re.S
        )
        match = pattern.search(rubric_text)
        window = match.group(1).lower() if match else ""
        if not window:
            window = rubric_text.lower()
            near = window.find(f"{option_id.lower()} ")
            window = window[near:near + 260] if near >= 0 else ""
        if "защитим" in window:
            weights[option_id] = 20 if "полный балл" in window else 13
        elif "слаб" in window or "опасн" in window:
            weights[option_id] = 7
    # Правило v0.1: хотя бы одна не-эталонная опция стоит не меньше восьми.
    others = sorted((w for o, w in weights.items() if o not in referenced), reverse=True)
    if not others or others[0] < 8:
        for option_id in option_ids:
            if option_id not in referenced:
                weights[option_id] = max(weights[option_id], 12)
                break
    return weights


def decision_prompt(raw: str) -> str:
    """Вопрос решения. Короткие формулировки источника дополняются требованием
    назвать цену — именно её и проверяет рубрика."""
    prompt = raw[0].upper() + raw[1:]
    if len(prompt) < 40:
        prompt = f"{prompt} Назовите цену вашего решения."
    return prompt[:300]


def remediation(draft: dict[str, Any], supplement: dict[str, Any]) -> list[dict[str, str]]:
    """Каждый покрытый урок должен иметь, куда вернуть провалившегося.

    Источник разбирает не все уроки сценария, поэтому недостающие пробелы
    дописываются в `sd_supplements` — без этого провал ведёт в никуда.
    """
    entries = list(draft["rubric"]["remediation"]) + list(supplement.get("remediation", []))
    covered = {entry["lessonId"] for entry in entries}
    missing = [lesson for lesson in draft["coveredLessonIds"] if lesson not in covered]
    if missing:
        raise SystemExit(
            f"{draft['id']}: нет ремедиации для {', '.join(missing)} — допишите в sd_supplements"
        )
    return entries


def default_note(weight: int) -> str:
    """Пояснение к опции, если автор не написал своего: вес уже сказал главное."""
    if weight >= 25:
        return "Эталон: закрывает задачу, не покупая результат ценой, которой не видно."
    if weight >= 20:
        return "Защитима полностью при явном признании цены и плана на остаток."
    if weight >= 12:
        return "Частичный кредит: отвечает на часть задачи, оставляя причину нетронутой."
    return "Слабо: закрывает симптом и оставляет то, из-за чего он появился."


def build(draft: dict[str, Any], blocks: dict[str, Any]) -> dict[str, Any] | None:
    supplement = SUPPLEMENTS.get(draft["id"])
    if supplement is None:
        return None

    block = blocks[draft["blockId"]]
    rubric_text = draft["rubric"].get("defensible", "")
    weights = option_weights(draft["rubric"]["reference"], rubric_text,
                             [o["id"] for o in draft["options"]])

    notes = supplement["rubricNotes"]
    # Пара последствий в источнике сведена до фразы: их дописывают в supplements,
    # потому что последствие обязано описывать исход, а не намекать на него.
    consequences = supplement.get("consequences", {})
    # Описание опции видно до решения, поэтому дополнять его последствием нельзя —
    # это выдало бы исход. Слишком краткие описания дописываются вручную.
    descriptions = supplement.get("descriptions", {})
    options = []
    for option in draft["options"]:
        note = notes.get(option["id"]) or default_note(weights[option["id"]])
        options.append({
            "id": option["id"].lower(),
            "label": option["label"][:80],
            # В источнике описание опции иногда сводится к сроку («Ноль недель»):
            # тогда к нему возвращается её название, иначе строка ничего не говорит.
            "description": (
                descriptions.get(option["id"])
                or (
                    option["description"]
                    if len(option["description"]) >= 40
                    else f"{option['label']}. {option['description']}".strip()
                )
            )[:600],
            "consequence": consequences.get(option["id"], option["consequence"])[:2000],
            "decisionPoints": weights[option["id"]],
            "rubricNote": note[:400],
        })

    positives = [
        {"lessonId": signal["lessonId"], "skill": "system_design", "signal": signal["signal"]}
        for signal in draft["rubric"]["positiveSignals"]
        if signal["lessonId"]
    ]
    # Сигналы без урока в источнике помечены «—»: это про изложение, а не про
    # применение конкретного урока, поэтому они уходят в communication и
    # привязываются к первому покрытому уроку — иначе схема их не примет.
    fallback = draft["coveredLessonIds"][0]
    for signal in draft["rubric"]["positiveSignals"]:
        if not signal["lessonId"]:
            positives.append(
                {"lessonId": fallback, "skill": "communication", "signal": signal["signal"]}
            )

    negatives = [
        {"skill": "system_design", "signal": text}
        for text in draft["rubric"]["negativeSignals"]
    ]

    return {
        "id": draft["id"],
        "version": 1,
        "status": "published",
        "blockId": draft["blockId"],
        "coveredLessonIds": draft["coveredLessonIds"],
        "title": f"«Полка»: {draft['title'][0].lower()}{draft['title'][1:]}",
        "summary": supplement["summary"],
        "estimatedMinutes": 13,
        "level": TIER_LEVEL[block["tier"]],
        "primarySkill": "system_design",
        "secondarySkills": ["communication"],
        "tags": supplement["tags"],
        "brief": {
            "role": ROLE,
            "company": COMPANY,
            "context": " ".join(draft["brief"].split())[:900],
            "objective": supplement["objective"],
            "constraints": supplement["constraints"],
            "task": supplement["task"],
        },
        "evidenceCards": evidence_cards(draft["evidenceRaw"]),
        "decisionPrompt": decision_prompt(draft["decisionPrompt"]),
        "decisionOptions": options,
        "rubric": {
            "referenceReasoning": supplement["reference"],
            "evidenceSignals": supplement["evidenceSignals"],
            "positiveSignals": positives,
            "negativeSignals": negatives,
            "remediation": remediation(draft, supplement),
        },
        "learnTakeaway": supplement["takeaway"],
        "qaSubmissions": supplement["qa"],
    }


def main() -> int:
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    blocks = {block["id"]: block for block in tree["blocks"]}
    gates = json.loads(GATES.read_text(encoding="utf-8"))["gates"]
    by_block: dict[str, list[str]] = {}

    written = 0
    for path in sorted(SRC.glob("*.json")):
        draft = json.loads(path.read_text(encoding="utf-8"))
        scenario = build(draft, blocks)
        if scenario is None:
            continue
        (OUT / f"{scenario['id']}.json").write_text(
            json.dumps(scenario, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        by_block.setdefault(scenario["blockId"], []).append(scenario["id"])
        written += 1

    # Уже написанные вручную сценарии (DS1) остаются как есть.
    for path in sorted(OUT.glob("*.json")):
        scenario = json.loads(path.read_text(encoding="utf-8"))
        ids = by_block.setdefault(scenario["blockId"], [])
        if scenario["id"] not in ids:
            ids.append(scenario["id"])

    existing = {gate["blockId"]: gate for gate in gates}
    for block_id, scenario_ids in sorted(by_block.items()):
        if len(scenario_ids) < 2:
            continue
        gate = existing.setdefault(
            block_id,
            {"id": f"gate-{block_id.lower()}", "blockId": block_id, "passThreshold": 70,
             "scenarioIds": []},
        )
        gate["scenarioIds"] = sorted(scenario_ids)
    GATES.write_text(
        json.dumps({"gates": [existing[k] for k in sorted(existing)]}, indent=2,
                   ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    publishable = {block_id for block_id, ids in by_block.items() if len(ids) >= 2}
    for block in tree["blocks"]:
        if block["id"] in publishable:
            block["status"] = "published"
    TREE.write_text(json.dumps(tree, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"дописано сценариев: {written}")
    print(f"блоков с гейтом: {len(publishable)} из {len(tree['blocks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
