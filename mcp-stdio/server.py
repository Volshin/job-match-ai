"""
Job Match AI — MCP server (FastMCP, stdio transport).

Manages two data files in ../data/:
  vacancies.csv  — UTF-8 BOM, comma-delimited, 12 columns, newest row first
  criteria.md    — free-form markdown with selection criteria

Expose four tools: add_vacancy, list_vacancies, read_criteria, update_vacancy.
"""

from pathlib import Path
from datetime import date, datetime, timedelta
import csv
import difflib
import io
import re
import shutil

import sys

from fastmcp import FastMCP

import dashboard

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
VACANCIES_FILE = DATA_DIR / "vacancies.csv"
CRITERIA_FILE = DATA_DIR / "criteria.md"
# The private dashboard stays in data/ (gitignored); the public one (demo data only) goes to docs/ (GitHub Pages).
PRIVATE_DASHBOARD = DATA_DIR / "dashboard.html"
PUBLIC_DASHBOARD = Path(__file__).parent.parent / "docs" / "index.html"

# ── Closed-list dictionaries (edit here, validation uses these automatically) ──
DICT_STATUS = {"новая", "отклонена", "к отклику", "откликнулся", "в переписке", "интервью", "отказ", "затухла", "отложена (язык)"}
DICT_MATCH  = {"сильный", "хороший", "средний", "слабый"}
DICT_ETYPE  = {"A", "B", "C"}
DICT_LANG   = {"EN", "EN+DE желателен", "DE обязателен", "не указан"}
DICT_LEVEL  = {"Application Manager", "IT Business Partner", "Team Lead", "Project Manager", "Program Manager",
               "Architect / Consultant", "AI", "прочее"}
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


JOURNAL_HEADING = "## Журнал изменений"


def _edit_criteria(criteria_file: Path, old_text: str, new_text: str, reason: str) -> str:
    """Replace one unique fragment of criteria_file; back up first, log the change."""
    # criteria.md is a symlink to a versioned file: write to the target so the link survives.
    real = criteria_file.resolve()
    reason = " ".join(reason.split()).rstrip(".")

    if not old_text:
        return "Ошибка: old_text пустой. Файл не изменён."
    if old_text == new_text:
        return "Ошибка: new_text совпадает с old_text. Файл не изменён."
    if not reason:
        return "Ошибка: не указана причина (reason). Файл не изменён."

    before = real.read_bytes().decode("utf-8")
    count = before.count(old_text)
    if count != 1:
        return f"Ошибка: old_text найден {count} раз, нужно ровно 1. Файл не изменён."

    after = before.replace(old_text, new_text, 1)
    entry = f"- {date.today():%d.%m.%Y}: {reason}."
    if re.search(rf"^{JOURNAL_HEADING}\s*$", after, re.MULTILINE):
        after = after.rstrip("\n") + f"\n{entry}\n"
    else:
        after = after.rstrip("\n") + f"\n\n{JOURNAL_HEADING}\n\n{entry}\n"

    history = real.parent / "criteria_history"
    history.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = history / f"criteria_{stamp}.md"
    n = 2
    while backup.exists():  # two edits within one second
        backup = history / f"criteria_{stamp}_{n}.md"
        n += 1
    shutil.copy2(real, backup)

    tmp = real.with_suffix(".tmp")
    tmp.write_bytes(after.encode("utf-8"))
    shutil.copymode(real, tmp)
    tmp.replace(real)

    diff = "\n".join(difflib.unified_diff(
        before.splitlines(), after.splitlines(),
        "criteria.md (до)", "criteria.md (после)", n=3, lineterm="",
    ))
    return f"Готово. Резервная копия: {backup}\n\n{diff}"


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
def update_criteria(old_text: str, new_text: str, reason: str) -> str:
    """Replace one fragment of criteria.md with new text.

    Call this ONLY after the user has explicitly confirmed the change in chat.
    First show the user the exact edit (old text → new text) and wait for approval.

    Parameters:
        old_text — fragment to replace; must occur in criteria.md exactly once.
                   If it occurs 0 or several times, nothing is changed and the
                   number of matches is returned — quote more surrounding text.
        new_text — replacement; an empty string deletes the fragment.
        reason   — short explanation, written to "## Журнал изменений" at the
                   end of criteria.md as "- DD.MM.YYYY: <reason>."

    Before writing, the current version is copied to criteria_history/ next to
    the file. Returns the backup path and a unified diff of the change.
    """
    _ensure_files()
    return _edit_criteria(CRITERIA_FILE, old_text, new_text, reason)


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


def _parse_date(s: str) -> date | None:
    """Parse DD.MM.YYYY; return None for approximate (~) or unparseable dates."""
    s = s.strip()
    if not s or s[0] not in "0123456789":
        return None
    try:
        return datetime.strptime(s[:10], "%d.%m.%Y").date()
    except ValueError:
        return None


@mcp.tool()
def analyze_pipeline(from_date: str = "") -> dict:
    """Analyze the vacancy pipeline and return structured statistics.

    Use this tool when the user asks about their job search pipeline,
    funnel conversion rates, activity patterns, or search intensity.

    Parameters:
        from_date — optional start date in DD.MM.YYYY format; when set,
                    only vacancies whose date parses to on-or-after this
                    value are counted. Rows with approximate dates (starting
                    with ~) are excluded from date-filtered results but
                    included when no filter is set.

    Returns a dict with these keys:

        total               — int, vacancies in scope
        by_status           — {status: count}
        by_employer_type    — {type: count}
        by_match            — {score: count}

        funnel              — pipeline from first application to outcome:
          applied           — int (откликнулся + в переписке + интервью + отказ)
          in_dialogue       — int (в переписке + интервью + отказ)
          at_interview      — int (интервью + отказ)
          rejected          — int (отказ)
          rate_to_dialogue  — float, in_dialogue / applied, or null
          rate_to_interview — float, at_interview / in_dialogue, or null
          rate_to_rejection — float, rejected / at_interview, or null

        rejections          — breakdown of rows with Статус=отказ:
          by_language       — {language: count}
          by_employer_type  — {type: count}

        by_role_level       — for each Уровень роли:
          {level: {total, got_response, went_silent}}
          got_response: в переписке + интервью + отказ
          went_silent:  затухла

        activity            — temporal patterns (only rows with parseable dates):
          by_week           — {"YYYY-Www": count} sorted chronologically
          by_month          — {"YYYY-MM": count} sorted chronologically
          gaps_over_7_days  — list of {from, to, days} for gaps > 7 days
          days_since_last   — int, days from most recent parseable date to today
    """
    rows = _read_rows()

    cutoff: date | None = None
    if from_date.strip():
        cutoff = _parse_date(from_date)

    if cutoff:
        rows = [r for r in rows if (d := _parse_date(r.get("Дата", ""))) and d >= cutoff]

    total = len(rows)

    def count_field(field: str) -> dict:
        result: dict[str, int] = {}
        for r in rows:
            v = r.get(field, "") or "—"
            result[v] = result.get(v, 0) + 1
        return result

    by_status = count_field("Статус")
    by_etype  = count_field("Тип работодателя")
    by_match  = count_field("Оценка матча")

    s = by_status
    applied      = sum(s.get(k, 0) for k in ("откликнулся", "в переписке", "интервью", "отказ"))
    in_dialogue  = sum(s.get(k, 0) for k in ("в переписке", "интервью", "отказ"))
    at_interview = sum(s.get(k, 0) for k in ("интервью", "отказ"))
    rejected     = s.get("отказ", 0)

    def rate(num: int, den: int) -> float | None:
        return round(num / den, 3) if den else None

    funnel = {
        "applied":           applied,
        "in_dialogue":       in_dialogue,
        "at_interview":      at_interview,
        "rejected":          rejected,
        "rate_to_dialogue":  rate(in_dialogue,  applied),
        "rate_to_interview": rate(at_interview, in_dialogue),
        "rate_to_rejection": rate(rejected,     at_interview),
    }

    rejection_rows = [r for r in rows if r.get("Статус") == "отказ"]
    rejections = {
        "by_language":      count_field_in("Язык (требование)", rejection_rows),
        "by_employer_type": count_field_in("Тип работодателя", rejection_rows),
    }

    role_stats: dict[str, dict] = {}
    for r in rows:
        level = r.get("Уровень роли") or "—"
        st    = r.get("Статус", "")
        entry = role_stats.setdefault(level, {"total": 0, "got_response": 0, "went_silent": 0})
        entry["total"] += 1
        if st in ("в переписке", "интервью", "отказ"):
            entry["got_response"] += 1
        if st == "затухла":
            entry["went_silent"] += 1

    dated = sorted(
        ((d, r) for r in rows if (d := _parse_date(r.get("Дата", "")))),
        key=lambda x: x[0],
    )

    by_week:  dict[str, int] = {}
    by_month: dict[str, int] = {}
    for d, _ in dated:
        wk = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
        mo = d.strftime("%Y-%m")
        by_week[wk]  = by_week.get(wk, 0) + 1
        by_month[mo] = by_month.get(mo, 0) + 1

    gaps = []
    for (d1, _), (d2, _) in zip(dated, dated[1:]):
        delta = (d2 - d1).days
        if delta > 7:
            gaps.append({"from": d1.strftime("%d.%m.%Y"), "to": d2.strftime("%d.%m.%Y"), "days": delta})

    today = date.today()
    days_since = (today - dated[-1][0]).days if dated else None

    activity = {
        "by_week":          by_week,
        "by_month":         by_month,
        "gaps_over_7_days": gaps,
        "days_since_last":  days_since,
    }

    return {
        "total":            total,
        "by_status":        by_status,
        "by_employer_type": by_etype,
        "by_match":         by_match,
        "funnel":           funnel,
        "rejections":       rejections,
        "by_role_level":    role_stats,
        "activity":         activity,
    }


def count_field_in(field: str, rows: list[dict]) -> dict:
    result: dict[str, int] = {}
    for r in rows:
        v = r.get(field, "") or "—"
        result[v] = result.get(v, 0) + 1
    return result


def _build_dashboard(rows: list[dict], public: bool, out_file: Path) -> str:
    """Render the dashboard for rows into out_file (atomic write)."""
    data = dashboard.build_data(rows, public)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_file.with_suffix(".tmp")
    tmp.write_text(dashboard.render_html(data), encoding="utf-8")
    tmp.replace(out_file)
    kind = "публичная" if public else "личная"
    return (f"Готово ({kind} версия): {out_file}\n"
            f"Вакансий в учёте: {data['meta']['total']}, незакрытых: {len(data['open'])}")


@mcp.tool()
def build_dashboard(public: bool = False) -> str:
    """Build a single-file HTML dashboard (funnel, statuses, weekly activity,
    language in rejections, response rate by role level, table of open vacancies)
    from the registry.

    Parameters:
        public — False (default): full personal version, written to
                 data/dashboard.html (not tracked by git).
                 True: demo version for GitHub Pages, written to
                 docs/index.html. Built from generated demo data, not from
                 the registry: the real search never leaves this machine.

    The file is a snapshot: data is embedded at build time, so rebuild after
    registry changes.
    """
    out = PUBLIC_DASHBOARD if public else PRIVATE_DASHBOARD
    return _build_dashboard(_dashboard_rows(public), public, out)


def _dashboard_rows(public: bool) -> list[dict]:
    return dashboard.demo_rows() if public else _read_rows()


if __name__ == "__main__":
    if sys.argv[1:2] == ["build-dashboard"]:
        # CLI for scripts (publish.sh): server.py build-dashboard [--public]
        _public = "--public" in sys.argv[2:]
        print(_build_dashboard(_dashboard_rows(_public), _public, PUBLIC_DASHBOARD if _public else PRIVATE_DASHBOARD))
    else:
        mcp.run(transport="stdio")
