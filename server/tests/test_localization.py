"""Interface language and the language coaching is written in.

Content itself is authored in the content language now rather than translated at
request time (spec v0.2 §16), so what is tested here is the machinery that still
carries a choice: server-owned copy, the derived vocabularies, and the language the
evaluator is told to write in.
"""

from __future__ import annotations

import re

from conftest import onboard, read_all_lessons, start_gate

from app import tree_content
from app.i18n import Language, copy, tag_label
from app.services.scoring import score_band
from app.services.skills import label as skill_label
from app.worker import run_once

CYRILLIC = re.compile(r"[а-яА-ЯёЁ]")


def _russian(text: str) -> bool:
    return bool(CYRILLIC.search(text or ""))


def switch(client, headers, language: str) -> dict:
    return client.patch(
        "/v1/me/profile", headers=headers, json={"language": language}
    ).json()


# --- Vocabularies ------------------------------------------------------------


def test_every_competency_has_both_languages():
    from app.models import SKILL_KEYS

    # Восемь компетенций: шесть доменов карты, communication и system_design
    # (спека v0.2 §7 плюс спека System Design §2.2).
    assert len(SKILL_KEYS) == 8
    for key in SKILL_KEYS:
        assert _russian(skill_label(key, Language.RU)), key
        assert not _russian(skill_label(key, Language.EN)), key


def test_bands_and_tags_and_copy_have_both_languages():
    assert _russian(score_band(90, Language.RU))
    assert score_band(90, Language.EN) == "Strong reasoning"
    assert _russian(tag_label("discovery", Language.RU))
    for key in ("what_good_looks_like", "progress_footnote"):
        assert _russian(copy(key, Language.RU))
        assert not _russian(copy(key, Language.EN))


def test_unknown_values_degrade_readably():
    assert Language.coerce(None) is Language.EN
    assert Language.coerce("de") is Language.EN
    assert Language.coerce("ru-RU") is Language.RU
    assert skill_label("brand_new", Language.RU) == "brand_new"
    assert tag_label("brand-new", Language.RU) == "Brand New"


# --- Authored content --------------------------------------------------------


def test_lessons_and_gate_scenarios_are_written_in_the_content_language():
    content = tree_content.tree_content()
    assert content["lessons"], "no lessons authored"
    for lesson in content["lessons"].values():
        assert _russian(lesson["title"]), lesson["id"]
        assert _russian(lesson["keyTakeaway"]), lesson["id"]
        for block in lesson["blocks"]:
            for field in ("text", "title", "subtitle"):
                # A model card's title is the model's own name — "Feedback Matrix",
                # "5 Whys", "HEART". Those are terms of art and stay as they are.
                if field == "title" and block["type"] == "model_card":
                    continue
                if block.get(field):
                    assert _russian(block[field]), f"{lesson['id']}/{field}"
    for scenario in content["scenarios"].values():
        assert _russian(scenario["title"]), scenario["id"]
        for value in scenario["brief"].values():
            assert _russian(value), scenario["id"]
        for card in scenario["evidenceCards"]:
            assert _russian(card["content"]), f"{scenario['id']}/{card['id']}"


def test_tree_titles_are_written_in_the_content_language():
    content = tree_content.tree_content()
    for block in content["tree"]["blocks"]:
        assert _russian(block["title"]), block["id"]
        for node in block["nodes"]:
            assert _russian(node["title"]), node["id"]
            assert _russian(node["keyQuestion"]), node["id"]


# --- API ---------------------------------------------------------------------


def test_language_persists_and_the_header_overrides_one_request(client):
    headers, me = onboard(client)
    assert me["language"] == "ru"  # the ICP is Russian-speaking (spec v0.2 §16)

    assert switch(client, headers, "en")["language"] == "en"
    english = client.get("/v1/progress", headers=headers).json()
    assert not _russian(english["footnote"])
    assert not _russian(english["skills"][0]["label"])

    # The header closes the gap between switching in the app and the PATCH landing.
    russian = client.get(
        "/v1/progress", headers={**headers, "X-Content-Language": "ru"}
    ).json()
    assert _russian(russian["footnote"])
    assert client.get("/v1/me", headers=headers).json()["language"] == "en"


def test_coaching_is_written_in_the_learners_language(client):
    headers, _ = onboard(client)
    read_all_lessons(client, headers, "D1")
    challenge = start_gate(client, headers)
    attempt_id = challenge["attempt"]["attemptId"]
    for card in challenge["scenario"]["evidenceCards"]:
        client.post(
            f"/v1/attempts/{attempt_id}/evidence",
            headers=headers,
            json={"evidenceCardId": card["id"]},
        )
    client.post(
        f"/v1/attempts/{attempt_id}/submit",
        headers=headers,
        json={
            "selectedOptionId": challenge["scenario"]["decisionOptions"][0]["id"],
            "rationale": (
                "Разложу обратную связь по задаче и разрежу метрики по сегментам, "
                "потому что среднее 3,1 скрывает распределение. Компромисс в том, что "
                "я сдвину звонки на два дня. Буду измерять долю обменов без сообщения "
                "владельцу."
            ),
        },
    )
    while run_once():
        pass

    feedback = client.get(f"/v1/attempts/{attempt_id}/feedback", headers=headers).json()
    body = feedback["feedback"]
    assert _russian(body["band"])
    assert _russian(body["sharperApproach"])
    for point in body["strengths"] + body["improvements"]:
        assert _russian(point["title"])
        assert _russian(point["detail"])
    for impact in body["skillImpact"]:
        assert _russian(impact["label"])


def test_language_choice_does_not_change_the_score(client):
    scores = {}
    rationale = (
        "Пишут сотрудники, а платит владелец. Среднее 3,1 скрывает распределение, "
        "поэтому сначала разрежу по сегментам. Компромисс — сдвиг звонков на два дня. "
        "Измерять буду долю обменов без сообщения владельцу."
    )
    for language in ("ru", "en"):
        headers, _ = onboard(client)
        switch(client, headers, language)
        read_all_lessons(client, headers, "D1")
        challenge = start_gate(client, headers)
        attempt_id = challenge["attempt"]["attemptId"]
        for card in challenge["scenario"]["evidenceCards"]:
            client.post(
                f"/v1/attempts/{attempt_id}/evidence",
                headers=headers,
                json={"evidenceCardId": card["id"]},
            )
        client.post(
            f"/v1/attempts/{attempt_id}/submit",
            headers=headers,
            json={
                "selectedOptionId": challenge["scenario"]["decisionOptions"][0]["id"],
                "rationale": rationale,
            },
        )
        while run_once():
            pass
        scores[language] = client.get(
            f"/v1/attempts/{attempt_id}/feedback", headers=headers
        ).json()["feedback"]["score"]

    assert scores["ru"] == scores["en"]
