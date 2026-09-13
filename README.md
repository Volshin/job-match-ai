# Job Match AI

Pet-проект для ведения реестра вакансий и анализа job-match через Claude.

## Статус

**v1 (Chrome extension) — закрыт.**
**v2 (MCP server для Claude Desktop) — активная разработка.**

### Почему v1 закрыт

Chrome-расширение решало не ту задачу. Оно было заточено под высокочастотный
скрининг — быстро анализировать десятки вакансий в день прямо в браузере.
Реальный поток оказался другим: ~100 вакансий в квартал, а не в день.
При таком ритме накладные расходы (держать расширение, Pi, Tailscale,
настраивать API-ключ) не оправданы.

Параллельно ниша «AI match-scoring для вакансий» оказалась плотно
занята бесплатными аналогами — Simplify, Teal, JobScan и другими.
Делать конкурента без явного преимущества смысла нет.

Код v1 сохранён в `/extension` и `/mcp-server` как есть.

---

## v2 — MCP server для Claude Desktop

Новая точка входа: не браузер, а прямой разговор с Claude в десктопном
приложении. MCP-сервер даёт Claude инструменты для работы с реестром
вакансий — добавлять, обновлять, фильтровать, читать критерии.

### Архитектура

```
Claude Desktop
     │  stdio
     ▼
MCP Server (mcp-stdio/server.py)
     │  Path(__file__).parent.parent / "data"
     ▼
data/
  vacancies.csv   ← реестр, UTF-8 BOM, 12 колонок
  criteria.md     ← критерии отбора, редактируется вручную
```

Сервер не знает о браузере, Pi и Tailscale. Всё локально.

### Инструменты

| Инструмент | Что делает |
|---|---|
| `add_vacancy` | Добавить вакансию в реестр (новые записи сверху) |
| `list_vacancies` | Список с фильтрами по Статусу и Типу работодателя |
| `update_vacancy` | Обновить поля существующей записи (поиск по Компания + Позиция) |
| `read_criteria` | Прочитать criteria.md целиком |

### Словари классификаторов

Шесть колонок с закрытым списком значений:

| Колонка | Значения |
|---|---|
| Статус | новая, отклонена, к отклику, откликнулся, в переписке, интервью, отказ, затухла |
| Оценка матча | сильный, хороший, средний, слабый |
| Тип работодателя | A (inhouse), B (inhouse через агентство), C (SI / консалтинг / вендор) |
| Язык (требование) | EN, EN+DE желателен, DE обязателен, не указан |
| Уровень роли | Application Manager, IT Business Partner, Team Lead, Project Manager, Architect / Consultant, прочее |
| Источник | LinkedIn, Xing, рекрутер, сайт компании, джоб-борд, прочее |

Сервер валидирует эти поля при добавлении и обновлении записей.

### Запуск

```bash
cd mcp-stdio
uv run python server.py
```

### Подключение к Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "job-match-ai": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--project",
        "/Users/olegbolsunov/Projects/MatchJobAIExt9/mcp-stdio",
        "python",
        "/Users/olegbolsunov/Projects/MatchJobAIExt9/mcp-stdio/server.py"
      ]
    }
  }
}
```

После сохранения — полный Quit и перезапуск Claude Desktop.

### Структура проекта

```
MatchJobAIExt9/
├── mcp-stdio/          # v2 — MCP server (активный)
│   ├── server.py
│   ├── pyproject.toml
│   └── uv.lock
├── data/               # рабочие данные (в .gitignore)
│   ├── vacancies.csv   # симлинк на актуальную версию
│   └── criteria.md     # симлинк на актуальную версию
├── extension/          # v1 — Chrome extension (закрыт)
└── mcp-server/         # v1 — FastAPI server на Pi (закрыт)
```

### Обновление файлов данных

Данные хранятся с датой в имени (`vacancies1209.csv`).
При сохранении новой версии обновить симлинк:

```bash
ln -sf vacancies1301.csv ~/Projects/MatchJobAIExt9/data/vacancies.csv
```
