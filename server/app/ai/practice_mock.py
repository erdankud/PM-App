"""Офлайн-заглушка модуля Practice — ТОЛЬКО ДЛЯ РАЗРАБОТКИ.

Это не ИИ и выдавать её за ИИ нельзя. Существует ровно затем, чтобы экран,
сохранение и повторное открытие тренировки проверялись без ключа провайдера и без
сети. Задачи берутся из короткого кольца заготовок, разбор считается по длине и
наличию конкретики в каждом поле канвы.

Что заглушка обязана делать честно — так это проходить `practice_validation`: если
подделка не проходит собственную проверку, проверка ничего не проверяет.
"""

from __future__ import annotations

import json
import re

from app.practice_catalogue import Track

_NUMBERS = re.compile(r"\d")
_BECAUSE = re.compile(
    r"\b(because|since|so that|which means|therefore|the reason|in order to)\b", re.IGNORECASE
)
_TRADEOFF = re.compile(
    r"\b(trade[- ]?off|instead of|at the cost of|rather than|downside|risk|"
    r"we would lose|give up|sacrific)\w*",
    re.IGNORECASE,
)

_BRIEFS = (
    {
        "title": "Weeknight cooking on a grocery app",
        "company": "Larder (fictional grocery delivery, 2.1m monthly users)",
        "kind": "improve",
        "context": (
            "Larder delivers groceries in ninety minutes across twelve cities. Orders are "
            "healthy overall, but the team has noticed that weeknight baskets are small and "
            "repetitive, and that a third of sessions between 17:00 and 19:00 end with no "
            "order at all. Retention among people who order only on weekends is well below "
            "the average."
        ),
        "prompt": "How would you improve the weeknight experience for Larder's shoppers?",
        "constraints": [
            "No change to delivery windows — logistics is committed for two quarters",
            "Whatever you build must work on the mobile app, where 88% of orders happen",
        ],
        "clarifiers": [
            {
                "question": "Who abandons the 17:00-19:00 sessions?",
                "answer": "Mostly households of two to four who ordered at least twice in the last month.",
            },
            {
                "question": "Is basket size falling or has it always been low on weeknights?",
                "answer": "Flat for eighteen months. It has always been about 40% of a weekend basket.",
            },
            {
                "question": "What do people do in those abandoned sessions?",
                "answer": "They search, open two or three products, and leave without adding anything.",
            },
        ],
    },
    {
        "title": "A first product for field engineers",
        "company": "Sunder (fictional B2B, industrial maintenance)",
        "kind": "design",
        "context": (
            "Sunder sells maintenance software to factories. Its buyers are plant managers, "
            "and its product is used almost entirely at a desk. The field engineers who "
            "actually do the maintenance have never had a tool of their own; they work from "
            "printed job sheets and phone calls. Sales keeps hearing about it, and the "
            "company has funded a small team to do something about it."
        ),
        "prompt": "Design Sunder's first product for the field engineer.",
        "constraints": [
            "Many plants have no reliable network on the factory floor",
            "The team is three engineers and one designer for two quarters",
        ],
        "clarifiers": [
            {
                "question": "How many engineers are there per plant?",
                "answer": "Between four and thirty, depending on plant size. The median plant has nine.",
            },
            {
                "question": "Who decides whether they adopt it — the engineer or the plant manager?",
                "answer": "The plant manager buys it, but engineers can and do refuse to use tools.",
            },
        ],
    },
    {
        "title": "Reading time is up, subscriptions are not",
        "company": "Column (fictional news subscription, 400k subscribers)",
        "kind": "diagnose",
        "context": (
            "Column shipped a redesigned article page last quarter. Average reading time per "
            "session rose 18% and has held. Subscription starts from article pages, however, "
            "are down 9% over the same period, and the trend did not exist before the "
            "redesign. Nothing else about pricing or acquisition changed."
        ),
        "prompt": "Reading time is up and subscription starts are down. What is going on, and what would you do?",
        "constraints": [
            "You cannot roll the redesign back — it is the basis of this year's ad contracts",
            "Any change has to ship within one quarter",
        ],
        "clarifiers": [
            {
                "question": "Did traffic mix change over the same period?",
                "answer": "Search traffic grew from 31% to 38% of article sessions after the redesign.",
            },
            {
                "question": "Where did the paywall sit before and after?",
                "answer": "It sat at the same article count, but it now appears further down a longer page.",
            },
            {
                "question": "Did cancellation change?",
                "answer": "No. Churn among existing subscribers is flat.",
            },
        ],
    },
)


def brief(track: Track, sequence: int) -> str:
    payload = dict(_BRIEFS[sequence % len(_BRIEFS)])
    return json.dumps(payload, ensure_ascii=False)


def _score(text: str) -> int:
    words = len(text.split())
    if words < 5:
        return 0 if words == 0 else 1
    value = 2
    if words >= 25:
        value += 1
    if _BECAUSE.search(text):
        value += 1
    if _NUMBERS.search(text) or _TRADEOFF.search(text):
        value += 1
    return min(5, value)


def feedback(track: Track, answers: dict[str, str]) -> str:
    fields = []
    for item in track.canvas:
        text = (answers.get(item.id) or "").strip()
        value = _score(text)
        fields.append(
            {
                "id": item.id,
                "score": value,
                "note": (
                    f"Offline stub: {len(text.split())} words in “{item.label}”. "
                    "This is not model feedback — set a real EVALUATOR_PROVIDER to get it."
                ),
            }
        )
    total = sum(entry["score"] for entry in fields)
    ceiling = 5 * max(1, len(fields))
    bar = "above" if total >= ceiling * 0.8 else "at" if total >= ceiling * 0.5 else "below"
    return json.dumps(
        {
            "headline": (
                "Offline stub feedback — the evaluator is not configured, so nothing here "
                "reflects what you actually wrote."
            ),
            "bar": bar,
            "fields": fields,
            "strengths": [
                {
                    "title": "You filled the canvas",
                    "detail": (
                        "Working through the steps in order is the habit this track trains, "
                        "and you did that. Real feedback needs a configured provider."
                    ),
                }
            ],
            "improvements": [
                {
                    "title": "Configure a provider",
                    "detail": (
                        "EVALUATOR_PROVIDER is set to mock, which scores by counting words. "
                        "Point it at a real model to get feedback on your reasoning."
                    ),
                }
            ],
            "missed_question": (
                "Not available offline — the stub cannot tell which question you should "
                "have asked, because it has not read your answer."
            ),
            "sharper_approach": (
                "There is no sharper approach to offer here. This response is generated by "
                "a deterministic development stub that counts words and looks for a few "
                "keywords; it has no understanding of the brief you were given or of the "
                "answer you wrote. Configure a real evaluator provider on the server and "
                "submit again to see what your reasoning is actually worth."
            ),
        },
        ensure_ascii=False,
    )
