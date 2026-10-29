import csv
import re
from pathlib import Path

import pytest

import dashboard
import dictionaries
import server

DATA = Path(__file__).parent.parent.parent / "data"


def test_server_dicts_come_from_the_json():
    for param, (allowed, _col) in server._DICT_MAP.items():
        assert allowed == set(dictionaries.VALUES[param])


def test_dashboard_statuses_are_known():
    statuses = set(dictionaries.VALUES["status"])
    for group in (dashboard.APPLIED, dashboard.REPLIED, dashboard.OPEN):
        assert set(group) <= statuses
    assert set(dashboard.STATUS_LABELS) == statuses  # every status has a label


def test_dashboard_languages_are_labelled_or_known():
    assert set(dashboard.LANG_LABELS) <= set(dictionaries.VALUES["language_requirement"])


def test_dashboard_levels_are_the_dictionary():
    assert dashboard.LEVELS == dictionaries.VALUES["role_level"]
    assert set(dashboard.LEVEL_LABELS) <= set(dashboard.LEVELS)


def test_level_matching_ignores_case():
    assert dashboard._level_key("Прочее") == "прочее"
    assert dashboard._level_key("ai") == "AI"
    assert dashboard._level_key("что-то новое") == "прочее"


@pytest.mark.skipif(not (DATA / "vacancies.csv").exists(), reason="registry is not in the repo")
def test_registry_values_are_in_the_dictionaries():
    rows = list(csv.DictReader(open(DATA / "vacancies.csv", encoding="utf-8-sig")))
    for param, (allowed, column) in server._DICT_MAP.items():
        bad = {r[column] for r in rows if r[column] and r[column] not in allowed}
        assert not bad, f"{column}: values outside the dictionary: {bad}"


def _criteria_list(text: str, label: str) -> list[str]:
    m = re.search(rf"Значения (?:колонки )?«{re.escape(label)}»:\s*(.+?)\.(?:\s|$)", text)
    assert m, f"no «{label}» values line in criteria.md"
    return [v.strip() for v in m.group(1).split(",")]


@pytest.mark.skipif(not (DATA / "criteria.md").exists(), reason="criteria.md is not in the repo")
@pytest.mark.parametrize("param,label", [("role_level", "Уровень роли"),
                                          ("language_requirement", "Язык (требование)")])
def test_criteria_lists_match_the_dictionaries(param, label):
    text = (DATA / "criteria.md").read_text(encoding="utf-8")
    assert set(_criteria_list(text, label)) == set(dictionaries.VALUES[param])
