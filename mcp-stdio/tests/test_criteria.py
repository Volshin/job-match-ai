from datetime import date

from server import _edit_criteria

TEXT = "# Критерии\n\nНемецкий B2: отсев.\nАнглийский C1: проходит.\n"


def make(tmp_path, text=TEXT):
    path = tmp_path / "criteria.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_unique_match(tmp_path):
    path = make(tmp_path)
    result = _edit_criteria(path, "Немецкий B2: отсев.", "Немецкий B2: проходит.", "смягчил гейт")

    new = path.read_text(encoding="utf-8")
    assert "Немецкий B2: проходит." in new
    assert "Немецкий B2: отсев." not in new
    assert f"## Журнал изменений\n\n- {date.today():%d.%m.%Y}: смягчил гейт." in new
    backups = list((tmp_path / "criteria_history").glob("criteria_*.md"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == TEXT
    assert str(backups[0]) in result
    assert "-Немецкий B2: отсев." in result and "+Немецкий B2: проходит." in result


def test_second_edit_appends_to_journal(tmp_path):
    path = make(tmp_path)
    _edit_criteria(path, "отсев", "проходит", "первая")
    _edit_criteria(path, "Английский C1", "Английский C2", "вторая")

    new = path.read_text(encoding="utf-8")
    assert new.count("## Журнал изменений") == 1
    assert new.index("первая") < new.index("вторая")
    assert len(list((tmp_path / "criteria_history").glob("criteria_*.md"))) == 2


def test_no_match(tmp_path):
    path = make(tmp_path)
    result = _edit_criteria(path, "нет такого текста", "x", "причина")

    assert "найден 0 раз" in result
    assert path.read_text(encoding="utf-8") == TEXT
    assert not (tmp_path / "criteria_history").exists()


def test_multiple_matches(tmp_path):
    path = make(tmp_path)
    result = _edit_criteria(path, ":", "!", "причина")

    assert "найден 2 раз" in result
    assert path.read_text(encoding="utf-8") == TEXT
    assert not (tmp_path / "criteria_history").exists()


def test_deletion(tmp_path):
    path = make(tmp_path)
    _edit_criteria(path, "Английский C1: проходит.\n", "", "убрал строку")

    new = path.read_text(encoding="utf-8")
    assert "Английский" not in new.split("## Журнал изменений")[0]
    assert "убрал строку" in new


def test_symlink_survives(tmp_path):
    target = make(tmp_path)
    link = tmp_path / "link.md"
    link.symlink_to(target.name)
    _edit_criteria(link, "отсев", "проходит", "правка через ссылку")

    assert link.is_symlink()
    assert "проходит" in target.read_text(encoding="utf-8")
