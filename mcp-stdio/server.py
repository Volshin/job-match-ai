"""
Job Match AI — MCP server (FastMCP, stdio transport).

Manages two data files in ../data/:
  vacancies.csv  — UTF-8 BOM, comma-delimited, 12 columns, newest row first
  criteria.md    — free-form markdown with selection criteria

Expose four tools: add_vacancy, list_vacancies, read_criteria, update_vacancy.
"""

from pathlib import Path
import csv
import io

from fastmcp import FastMCP

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
VACANCIES_FILE = DATA_DIR / "vacancies.csv"
CRITERIA_FILE = DATA_DIR / "criteria.md"

# ── Closed-list dictionaries (edit here, validation uses these automatically) ──
DICT_STATUS = {"новая", "отклонена", "к отклику", "откликнулся", "в переписке", "интервью", "отказ", "затухла"}
DICT_MATCH  = {"сильный", "хороший", "средний", "слабый"}
DICT_ETYPE  = {"A", "B", "C"}
DICT_LANG   = {"EN", "EN+DE желателен", "DE обязателен", "не указан"}
DICT_LEVEL  = {"Application Manager", "IT Business Partner", "Team Lead", "Project Manager", "Architect / Consultant", "прочее"}
DICT_SOURCE = {"LinkedIn", "Xing", "рекрутер", "сайт компании", "джоб-борд", "прочее"}

# Maps parameter name → (dict, column label)
_DICT_MAP = {
    "status":               (DICT_STATUS, "Статус"),
    "match_score":          (DICT_MATCH,  "Оценка матча"),
    "employer_type":        (DICT_ETYPE,  "Тип работодателя"),
    "language_requirement": (DICT_LANG,   "Язык (требование)"),
    "role_level":           (DICT_LEVEL,  "Уровень роли"),
    "source":               (DICT_SOURCE, "Источник"),
}


def _validate_dicts(**kwargs) -> str | None:
    """Return an error string if any dict-bound param is outside its allowed set, else None."""
    errors = []
    for param, value in kwargs.items():
        if param not in _DICT_MAP or not value:
            continue
        allowed, col_label = _DICT_MAP[param]
        if value not in allowed:
            errors.append(f'  {col_label}: «{value}» — допустимые значения: {", ".join(sorted(allowed))}')
    return "\n".join(errors) if errors else None


COLUMNS = [
    "Дата",
    "Компания",
    "Позиция",
    "Локация",
    "Источник",
    "Тип работодателя",
    "Язык (требование)",
    "Уровень роли",
    "Статус",
    "Оценка матча",
    "Вывод / причина",
    "Версия CV",
]

REQUIRED_COLUMNS = {
    "Дата",
    "Компания",
    "Позиция",
    "Локация",
    "Источник",
    "Тип работодателя",
    "Язык (требование)",
    "Статус",
    "Оценка матча",
    "Вывод / причина",
}

# ── Internal helpers ───────────────────────────────────────────────────────────

def _ensure_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not VACANCIES_FILE.exists():
        with VACANCIES_FILE.open("w", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()
    if not CRITERIA_FILE.exists():
        CRITERIA_FILE.write_text("", encoding="utf-8")


def _read_rows() -> list[dict]:
    _ensure_files()
    text = VACANCIES_FILE.read_bytes().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _write_rows(rows: list[dict]) -> None:
    """Atomic write: write to .tmp then rename, so a crash won't corrupt the file."""
    tmp = VACANCIES_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(VACANCIES_FILE)  # atomic on POSIX / macOS


# ── MCP server ─────────────────────────────────────────────────────────────────
mcp = FastMCP("job-match-ai")


@mcp.tool()
def add_vacancy(
    date: str,
    company: str,
    position: str,
    location: str,
    source: str,
    employer_type: str,
    language_requirement: str,
    status: str,
    match_score: str,
    conclusion: str,
    role_level: str = "",
    cv_version: str = "",
) -> str:
    """Add a new job vacancy to the registry.

    Use this tool whenever the user wants to log a vacancy they found or were
    contacted about. The record is inserted at the top (newest first).

    Parameter → CSV column mapping:
        date                 → Дата                  (format DD.MM.YYYY, e.g. 13.09.2026)
        company              → Компания
        position             → Позиция
        location             → Локация
        source               → Источник
        employer_type        → Тип работодателя
        language_requirement → Язык (требование)
        status               → Статус
        match_score          → Оценка матча
        conclusion           → Вывод / причина
        role_level           → Уровень роли          (optional, default "")
        cv_version           → Версия CV             (optional, default "")

    All parameters except role_level and cv_version are required.
    Returns an error message listing missing fields without writing anything.
    """
    field_values = {
        "Дата": date,
        "Компания": company,
        "Позиция": position,
        "Локация": location,
        "Источник": source,
        "Тип работодателя": employer_type,
        "Язык (требование)": language_requirement,
        "Статус": status,
        "Оценка матча": match_score,
        "Вывод / причина": conclusion,
    }
    missing = [col for col, val in field_values.items() if not str(val).strip()]
    if missing:
        return f"Ошибка: не заполнены обязательные поля: {', '.join(missing)}. Вакансия не добавлена."

    dict_err = _validate_dicts(
        status=status, match_score=match_score, employer_type=employer_type,
        language_requirement=language_requirement, role_level=role_level, source=source,
    )
    if dict_err:
        return f"Ошибка: значения вне словаря. Вакансия не добавлена.\n{dict_err}"

    new_row = {
        "Дата": date,
        "Компания": company,
        "Позиция": position,
        "Локация": location,
        "Источник": source,
        "Тип работодателя": employer_type,
        "Язык (требование)": language_requirement,
        "Уровень роли": role_level,
        "Статус": status,
        "Оценка матча": match_score,
        "Вывод / причина": conclusion,
        "Версия CV": cv_version,
    }

    existing = _read_rows()
    _write_rows([new_row] + existing)
    return f"Добавлена вакансия: {company} — {position} ({date})"


@mcp.tool()
def list_vacancies(
    status: str = "",
    employer_type: str = "",
) -> list[dict]:
    """Return vacancies from the registry, optionally filtered.

    Use this tool when the user wants to see, review, or analyse their vacancy
    history. Both filters are optional and use case-insensitive substring matching.

    Parameters:
        status        — filter by Статус column
                        (e.g. "Отклонена", "Рассматривается", "Оффер")
        employer_type — filter by Тип работодателя column
                        (e.g. "Inhouse", "агентство", "стартап")

    Omit both to get the full list.
    Returns a list of dicts, one per vacancy, with all 12 columns.
    """
    rows = _read_rows()
    if status:
        rows = [r for r in rows if status.lower() in r.get("Статус", "").lower()]
    if employer_type:
        rows = [
            r for r in rows
            if employer_type.lower() in r.get("Тип работодателя", "").lower()
        ]
    return rows


@mcp.tool()
def read_criteria() -> str:
    """Return the full contents of criteria.md — the candidate's job-matching criteria.

    Call this before evaluating a vacancy, explaining a match score, or deciding
    whether a position is worth applying to. The file is edited manually by the user.
    """
    _ensure_files()
    return CRITERIA_FILE.read_text(encoding="utf-8")


@mcp.tool()
def update_vacancy(
    company_search: str,
    position_search: str,
    date: str = "",
    company: str = "",
    position: str = "",
    location: str = "",
    source: str = "",
    employer_type: str = "",
    language_requirement: str = "",
    role_level: str = "",
    status: str = "",
    match_score: str = "",
    conclusion: str = "",
    cv_version: str = "",
) -> str:
    """Update fields of an existing vacancy found by company + position.

    Use this tool when the user wants to change the status, conclusion, or any
    other field of a vacancy already in the registry. Most common use: marking
    a vacancy as rejected/offer/closed and updating the conclusion.

    Search parameters (both required for lookup):
        company_search  — substring to match against Компания (case-insensitive)
        position_search — substring to match against Позиция  (case-insensitive)

    If the search matches more than one row, returns the list of matches and
    makes no changes — the user should narrow the search terms.

    Update parameters (all optional — only non-empty values are applied):
        date, company, position, location, source, employer_type,
        language_requirement, role_level, status, match_score,
        conclusion, cv_version

    Parameter → CSV column mapping (same as add_vacancy):
        date                 → Дата
        company              → Компания
        position             → Позиция
        location             → Локация
        source               → Источник
        employer_type        → Тип работодателя
        language_requirement → Язык (требование)
        role_level           → Уровень роли
        status               → Статус
        match_score          → Оценка матча
        conclusion           → Вывод / причина
        cv_version           → Версия CV

    Returns a before/after summary of changed fields so the user can confirm
    what was updated.
    """
    rows = _read_rows()

    matches = [
        (i, r) for i, r in enumerate(rows)
        if company_search.lower() in r.get("Компания", "").lower()
        and position_search.lower() in r.get("Позиция", "").lower()
    ]

    if not matches:
        return (
            f"Вакансия не найдена: компания содержит «{company_search}», "
            f"позиция содержит «{position_search}»."
        )

    if len(matches) > 1:
        lines = [
            f"Найдено {len(matches)} совпадения — уточни поиск:\n"
        ]
        for _, r in matches:
            lines.append(f"  • {r['Компания']} — {r['Позиция']} ({r['Дата']})")
        return "\n".join(lines)

    idx, old_row = matches[0]

    param_to_column = {
        "date": "Дата",
        "company": "Компания",
        "position": "Позиция",
        "location": "Локация",
        "source": "Источник",
        "employer_type": "Тип работодателя",
        "language_requirement": "Язык (требование)",
        "role_level": "Уровень роли",
        "status": "Статус",
        "match_score": "Оценка матча",
        "conclusion": "Вывод / причина",
        "cv_version": "Версия CV",
    }
    updates = {
        "date": date,
        "company": company,
        "position": position,
        "location": location,
        "source": source,
        "employer_type": employer_type,
        "language_requirement": language_requirement,
        "role_level": role_level,
        "status": status,
        "match_score": match_score,
        "conclusion": conclusion,
        "cv_version": cv_version,
    }

    dict_err = _validate_dicts(
        status=status, match_score=match_score, employer_type=employer_type,
        language_requirement=language_requirement, role_level=role_level, source=source,
    )
    if dict_err:
        return f"Ошибка: значения вне словаря. Запись не изменена.\n{dict_err}"

    new_row = dict(old_row)
    changes = []
    for param, value in updates.items():
        if value.strip():
            col = param_to_column[param]
            old_val = old_row.get(col, "")
            if old_val != value:
                new_row[col] = value
                changes.append(f"  {col}:\n    было: {old_val}\n    стало: {value}")

    if not changes:
        return "Нечего обновлять: переданные значения совпадают с текущими или не указаны."

    rows[idx] = new_row
    _write_rows(rows)

    header = f"Обновлена вакансия: {old_row['Компания']} — {old_row['Позиция']}\n"
    return header + "\n".join(changes)


if __name__ == "__main__":
    mcp.run(transport="stdio")
