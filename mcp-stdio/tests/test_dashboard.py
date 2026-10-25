import json
import re

import dashboard
from server import _build_dashboard

COLUMNS = ["Дата", "Компания", "Позиция", "Локация", "Источник", "Тип работодателя",
           "Язык (требование)", "Уровень роли", "Статус", "Оценка матча", "Вывод / причина", "Версия CV"]


def row(**kw):
    base = {c: "" for c in COLUMNS}
    base.update({"Дата": "13.07.2026", "Компания": "Acme GmbH", "Позиция": "SAP Lead",
                 "Локация": "Munich (Hybrid)", "Тип работодателя": "A", "Язык (требование)": "EN",
                 "Уровень роли": "Team Lead", "Статус": "новая", "Оценка матча": "хороший",
                 "Вывод / причина": "секретная заметка", "Версия CV": "cv-secret-v3"})
    base.update(kw)
    return base


ROWS = [
    row(Статус="отклонена", **{"Язык (требование)": "DE обязателен"}),
    row(Статус="откликнулся", Дата="21.07.2026"),
    row(Статус="в переписке", Дата="22.07.2026"),
    row(Статус="затухла", Дата="23.07.2026"),
    row(Статус="новая", Дата="~31.08.2026"),
    row(Статус="новая", Позиция="DUPLICATE of Acme"),
]


def counts(data, key="funnel"):
    return [x["count"] for x in data[key]]


def test_funnel_and_duplicates():
    d = dashboard.build_data(ROWS, public=False)
    assert d["meta"]["total"] == 5  # DUPLICATE row is not counted
    # reviewed, passed, applied, replied, dialogue, interview, offer
    assert counts(d) == [5, 4, 3, 1, 1, 0, 0]


def test_weekly_fills_gaps_and_skips_approximate_dates():
    d = dashboard.build_data(ROWS, public=False)
    weeks = {w["week"]: w["count"] for w in d["weekly"]}
    assert weeks["2026-07-13"] == 1
    assert weeks["2026-07-20"] == 3
    assert len(d["weekly"]) == 2  # "~31.08.2026" is ignored


def test_language_only_counts_rejected():
    d = dashboard.build_data(ROWS, public=False)
    assert d["lang"] == [{"label": "Немецкий обязателен", "count": 1}]


def test_roles_responded_and_silent():
    d = dashboard.build_data(ROWS, public=False)
    lead = next(r for r in d["roles"] if r["label"] == "Team Lead")
    assert (lead["total"], lead["responded"], lead["silent"]) == (5, 1, 1)


def test_open_rows_private_vs_public():
    private = dashboard.build_data(ROWS, public=False)["open"]
    public = dashboard.build_data(ROWS, public=True)["open"]
    assert len(private) == len(public) == 2  # откликнулся и новая (~дата); дубликат не считается
    assert private[0]["company"] == "Acme GmbH" and private[0]["note"] == "секретная заметка"
    assert public[0]["company"] == "Tier A, DE"
    assert public[0]["position"] == "Team Lead"
    assert not {"note", "cv"} & set(public[0])


def test_country_of():
    assert dashboard.country_of("Amsterdam, NL (Hybrid)") == "NL"
    assert dashboard.country_of("Munich") == "DE"
    assert dashboard.country_of("Sankt Leon-Rot, DE") == "DE"
    assert dashboard.country_of("Москва") == ""


def test_public_html_has_no_private_strings(tmp_path):
    out = tmp_path / "docs" / "index.html"
    msg = _build_dashboard(ROWS, True, out)
    text = out.read_text(encoding="utf-8")
    assert str(out) in msg
    for secret in ("Acme", "секретная заметка", "cv-secret-v3", "SAP Lead"):
        assert secret not in text


def test_private_html_has_details_and_valid_json(tmp_path):
    out = tmp_path / "dashboard.html"
    _build_dashboard(ROWS, False, out)
    text = out.read_text(encoding="utf-8")
    assert "d3@7.9.0" in text and "sha384-" in text
    payload = re.search(r'id="data">(.*?)</script>', text, re.S).group(1)
    data = json.loads(payload)
    assert data["open"][0]["note"] == "секретная заметка"


def test_script_end_tag_in_data_is_escaped(tmp_path):
    out = tmp_path / "x.html"
    _build_dashboard([row(Статус="новая", **{"Вывод / причина": "</script><b>"})], False, out)
    text = out.read_text(encoding="utf-8")
    assert text.count("</script>") == 3  # d3, data, code: none from the note
    payload = re.search(r'id="data">(.*?)</script>', text, re.S).group(1)
    assert json.loads(payload)["open"][0]["note"] == "</script><b>"


def test_empty_registry(tmp_path):
    out = tmp_path / "x.html"
    _build_dashboard([], True, out)
    assert out.exists()
