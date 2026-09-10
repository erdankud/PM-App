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

_PRODUCT_SENSE_BRIEFS = (
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


_PRODUCT_STRATEGY_BRIEFS = (
    {
        "title": "Same-day delivery in a market that already has it",
        "company": "Harrow (fictional home goods retailer, 340m EUR revenue)",
        "kind": "enter",
        "context": (
            "Harrow sells furniture and homeware through 60 stores and a web shop that "
            "takes 31% of revenue. Two marketplaces now offer same-day delivery on small "
            "homeware in the same cities and have taken roughly four points of category "
            "share in eighteen months. Harrow's own delivery is a three-day promise run "
            "by a contracted carrier at 6.20 EUR a parcel. Board members are asking "
            "whether the stores are a same-day network nobody is using."
        ),
        "prompt": "Should Harrow enter same-day delivery, and if so on what basis?",
        "counter": (
            "Same-day is a race we cannot win. The marketplaces are subsidising delivery "
            "out of advertising revenue we do not have, and we would be spending margin "
            "to match a promise our customers have never asked us for."
        ),
        "constraints": [
            "The carrier contract runs for two more years at a fixed volume commitment",
            "Store staffing is set by the retail P&L and cannot grow this year",
        ],
        "clarifiers": [
            {
                "question": "What share of orders is within same-day range of a store?",
                "answer": "About 54% of online orders ship to a postcode within 15 km of a store.",
            },
            {
                "question": "How does basket size differ between the marketplaces and Harrow?",
                "answer": "Marketplace homeware baskets average 28 EUR; Harrow's online basket is 96 EUR.",
            },
            {
                "question": "What does a store fulfilment pick cost today?",
                "answer": "Click-and-collect picks cost about 2.40 EUR in staff time, measured last year.",
            },
        ],
    },
)

_ANALYTICAL_BRIEFS = (
    {
        "title": "Weekly active teams flat after a launch that tested well",
        "company": "Ledger Room (fictional B2B accounting tool, 9,400 paying teams)",
        "kind": "flat",
        "context": (
            "Ledger Room shipped a redesigned month-end close checklist six weeks ago. In "
            "the beta it raised on-time closes by eleven points. Since general "
            "availability, weekly active teams have held at 6,100, exactly where they were "
            "before, and on-time closes have moved by less than a point. The team has "
            "already ruled out a tracking outage: event volume is continuous, and the two "
            "release cohorts show identical instrumentation coverage."
        ),
        "prompt": "The launch moved nothing. Work out why, and say what you would do about it.",
        "constraints": [
            "The next release train is in three weeks and the slot is already allocated",
            "Event data older than 90 days is not retained",
        ],
        "clarifiers": [
            {
                "question": "Split weekly active teams by whether they have opened the new checklist.",
                "answer": "1,900 teams have opened it; they are up 14%. The other 4,200 are down 6%.",
            },
            {
                "question": "How do teams reach the checklist?",
                "answer": "Only from the close screen, which 2,300 teams visited in the last 30 days.",
            },
            {
                "question": "Break on-time closes down by team size.",
                "answer": "Teams under five people: up 9 points. Teams over twenty: down 2 points.",
            },
            {
                "question": "Did anything else ship in the same window?",
                "answer": "A pricing page change on the marketing site. No product surface was touched.",
            },
            {
                "question": "What did the beta cohort look like?",
                "answer": "412 teams, all of whom had asked to be in it, median size four people.",
            },
        ],
    },
)

_LEADERSHIP_BRIEFS = (
    {
        "title": "Disagreeing with someone who outranked you",
        "company": "Senior PM, payments at a fictional travel marketplace",
        "kind": "conflict",
        "context": (
            "This interviewer is listening for whether you can disagree without stalling "
            "the work, and whether the decision that came out of it was better for your "
            "having pushed. At this level they expect the disagreement to have been about "
            "something that mattered to the business, not about process."
        ),
        "prompt": (
            "Tell me about a time you disagreed with someone more senior than you about a "
            "decision you owned. What did you do?"
        ),
        "constraints": [
            "From the last three years, in a professional setting",
            "You have to be able to say what the decision cost or saved",
        ],
        "clarifiers": [
            {
                "question": "Do you want the disagreement itself or how it was resolved?",
                "answer": "Both, but spend most of the time on what you personally did about it.",
            },
            {
                "question": "Does it matter whether I turned out to be right?",
                "answer": "No. I care how you handled being unsure, and what you did afterwards.",
            },
        ],
    },
)

_TECHNICAL_BRIEFS = (
    {
        "title": "Answers that cite the wrong policy document",
        "company": "Kestrel (fictional HR software, 700 enterprise customers)",
        "kind": "tradeoff",
        "context": (
            "Kestrel's assistant answers employee questions about company policy by "
            "retrieving from each customer's uploaded documents. Support has logged 240 "
            "cases in a quarter where the answer was confidently wrong because it "
            "retrieved a superseded version of a policy. Engineering has proposed two "
            "fixes: re-rank retrieved passages with a larger model, adding about 900 ms "
            "per answer, or require customers to mark documents as current, which shifts "
            "work onto them. You are explaining the choice to the support lead, who has "
            "to tell customers what is changing."
        ),
        "prompt": "Explain what is going wrong and say which fix you would ship.",
        "counter": (
            "Re-ranking does not fix this. The superseded document is genuinely the best "
            "match for the query — it says the same things in the same words. You are "
            "spending 900 milliseconds on every answer to maybe help one in fifty."
        ),
        "constraints": [
            "The answer latency budget is 3 seconds end to end; today it averages 2.1",
            "No engineering time for a document versioning system before Q3",
        ],
        "clarifiers": [
            {
                "question": "How many of the 240 cases involve documents that have a newer version uploaded?",
                "answer": "218 of 240. In those cases the current version is present and was not retrieved.",
            },
            {
                "question": "Do uploads carry any date we can trust?",
                "answer": "File upload timestamps are reliable. Dates inside documents are not.",
            },
            {
                "question": "What does an answer cost today?",
                "answer": "About 0.004 EUR. Re-ranking would roughly triple it, on 1.2m answers a month.",
            },
        ],
    },
)

_TAKE_HOME_BRIEFS = (
    {
        "title": "Two quarters for a product with good numbers and bad retention",
        "company": "Bellhop (fictional shift-scheduling app for hospitality)",
        "kind": "roadmap",
        "context": (
            "Bellhop has 3,100 paying venues and grew signups 40% last year. Month-three "
            "retention is 46%, against 71% for the two venues-per-manager cohort. Support "
            "volume is dominated by shift-swap disputes: 38% of tickets. A manager in a "
            "user interview said «I still keep the real rota in a spreadsheet, the app is "
            "where I publish it». Sales says every lost deal mentions payroll export. The "
            "team is six engineers, one designer, and runway to the end of next year."
        ),
        "prompt": (
            "Write a one-page recommendation for the next two quarters. We expect this to "
            "take about 90 minutes and we do not reward more."
        ),
        "constraints": [
            "Six engineers and one designer, no hiring before next year",
            "A signed commitment to ship payroll export to one chain by the end of Q1",
        ],
        "clarifiers": [
            {
                "question": "How long should the document be?",
                "answer": "One page of argument. Appendices are fine but we may not read them.",
            },
            {
                "question": "Who is the audience?",
                "answer": "Me and the CTO. Assume we know the product and not your reasoning.",
            },
        ],
    },
)

# Кольцо заготовок на каждое направление. У пяти из шести оно длиной в одну
# задачу: заглушка существует, чтобы проверялись экран и сохранение, а не чтобы
# заменять модель — «другая задача» вернёт ту же самую, и это видно сразу.
_BRIEFS: dict[str, tuple[dict, ...]] = {
    "product_sense": _PRODUCT_SENSE_BRIEFS,
    "product_strategy": _PRODUCT_STRATEGY_BRIEFS,
    "analytical_execution": _ANALYTICAL_BRIEFS,
    "leadership_drive": _LEADERSHIP_BRIEFS,
    "technical_fluency": _TECHNICAL_BRIEFS,
    "take_home": _TAKE_HOME_BRIEFS,
}


def brief(track: Track, sequence: int) -> str:
    ring = _BRIEFS[track.id]
    payload = dict(ring[sequence % len(ring)])
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
