# -*- coding: utf-8 -*-
"""Проставляет упражнениям System Design поля ввода и приёмку.

Импортёр выводит упражнения из авторского markdown и не может угадать, какие из
них проверяемы: все выходят как `open`. Разметка живёт в
`scripts/sd_exercise_types.py` и применяется здесь — отдельным шагом, потому что
это авторское решение, а не свойство исходного текста.

Порядок конвейера:

    python -m scripts.import_system_design docs/system-design-course.md
    python -m scripts.publish_system_design
    python -m scripts.type_exercises
    python -m scripts.validate_content
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sd_exercise_types import TYPES

EXERCISES = Path(__file__).resolve().parents[1] / "content" / "system-design" / "exercises"


def apply(exercise_id: str, spec: dict) -> bool:
    path = EXERCISES / f"{exercise_id}.json"
    if not path.exists():
        raise SystemExit(f"{exercise_id}: файла нет — разметка ссылается на несуществующее упражнение")
    data = json.loads(path.read_text(encoding="utf-8"))

    inputs, rules, seen = [], [], set()
    default_choices = spec.get("choices")
    for item in spec["inputs"]:
        field, rule = dict(item["input"]), dict(item["rule"])
        if field["id"] in seen:
            raise SystemExit(f"{exercise_id}: поле {field['id']} описано дважды")
        seen.add(field["id"])
        if field["type"] == "choice":
            choices = field.get("choices", default_choices)
            if not choices:
                raise SystemExit(f"{exercise_id}/{field['id']}: у поля выбора нет вариантов")
            field["choices"] = choices
            if rule["expected"] not in choices:
                raise SystemExit(
                    f"{exercise_id}/{field['id']}: ответ «{rule['expected']}» не из вариантов"
                )
        elif rule["min"] >= rule["max"]:
            raise SystemExit(f"{exercise_id}/{field['id']}: пустой интервал приёмки")
        inputs.append(field)
        rules.append(rule)

    prompt = list(data["promptBlocks"])
    diagram_id = spec.get("diagram")
    if diagram_id and not any(
        block["type"] == "diagram_ref" and block["diagramId"] == diagram_id for block in prompt
    ):
        prompt.append({"type": "diagram_ref", "diagramId": diagram_id})

    updated = {
        **data,
        "type": spec["type"],
        "promptBlocks": prompt,
        "inputs": inputs,
        "acceptance": rules,
    }
    if updated == data:
        return False
    path.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return True


def main() -> None:
    changed = sum(apply(exercise_id, spec) for exercise_id, spec in sorted(TYPES.items()))
    total = len(list(EXERCISES.glob("*.json")))
    fields = sum(len(spec["inputs"]) for spec in TYPES.values())
    print(f"размечено упражнений: {len(TYPES)} из {total} (изменено файлов: {changed})")
    print(f"проверяемых полей: {fields}")
    print(f"осталось open: {total - len(TYPES)} — ответ формулируется текстом, поля его не проверят")


if __name__ == "__main__":
    main()
