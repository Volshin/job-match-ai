# Job Match AI — Vacancy Registry for Claude Desktop

A local MCP server that gives Claude Desktop structured tools to manage
a job search registry. Log vacancies, update statuses, filter by any
combination of classifiers, and analyze your pipeline — all through
conversation with Claude.

**Dashboard demo (generated data):** https://volshin.github.io/job-match-ai/

Designed for a deliberate, low-volume search: ~100 carefully selected
vacancies per quarter rather than mass applications.


---

## How it works

Claude Desktop (or Claude Code) connects to the server via stdio. You talk
to Claude; Claude calls the tools; the registry stays on your machine.
A dashboard is built from the registry on demand.

```
Agent (Claude Desktop / Claude Code)
     │  MCP over stdio
     ▼
mcp-stdio/server.py
     │
     ├──▶ data/criteria.md      ← selection criteria (backed up on every edit)
     └──▶ data/vacancies.csv    ← structured registry, 12 columns
               │
               │  build_dashboard
               ▼
     data/dashboard.html        ← personal version, stays local
     docs/index.html            ← public demo version → GitHub Pages
```

Both dashboard files are single HTML pages with the data embedded at build
time (charts are drawn by d3, loaded from a CDN). They are snapshots:
rebuild after the registry changes.

## Tools

| Tool | Description |
|---|---|
| `add_vacancy` | Append a new vacancy (inserted at top, newest-first) |
| `list_vacancies` | List with optional filters by Status and Employer type |
| `update_vacancy` | Update any fields; find by Company + Position substring |
| `read_criteria` | Return full contents of criteria.md |
| `update_criteria` | Replace one unique fragment of criteria.md; backs up the file first, logs the change, returns a diff |
| `analyze_pipeline` | Funnel stats, status/type/match distributions, activity timeline |
| `build_dashboard` | Build the HTML dashboard: `public=false` → `data/dashboard.html` (full), `public=true` → `docs/index.html` (demo data) |

## Dashboard

Blocks: funnel, statuses, vacancies per week, language in rejections,
response rate by role level, and a filterable table of open vacancies.

The public version is built from generated demo data, not from the registry:
the real search never leaves the machine. The page says so in its subtitle.

```bash
# from the Claude chat: ask for build_dashboard, or from a terminal:
cd mcp-stdio
uv run python server.py build-dashboard             # personal → data/dashboard.html
uv run python server.py build-dashboard --public    # public   → docs/index.html

# build the public version, commit docs/ and push (from main):
./publish.sh
./publish.sh --dry-run    # build only
```

GitHub Pages: Settings → Pages → Deploy from a branch → `main` / `/docs`.
`launchd/com.pet9.publish-dashboard.plist` is a ready daily-publish job;
it is not enabled, see the comments inside for how to turn it on.

## Registry schema

12 columns, UTF-8 with BOM, comma-delimited. Six are free-form; six are
closed-list classifiers validated on write.

| Column | Type | Values |
|---|---|---|
| Дата | free | DD.MM.YYYY |
| Компания | free | — |
| Позиция | free | — |
| Локация | free | — |
| Источник | classifier | LinkedIn, Xing, рекрутер, сайт компании, джоб-борд, прочее |
| Тип работодателя | classifier | A (inhouse), B (inhouse via agency), C (SI / consulting / vendor) |
| Язык (требование) | classifier | EN, EN+DE желателен, DE обязателен, не указан |
| Уровень роли | classifier | Application Manager, IT Business Partner, Team Lead, Project Manager, Architect / Consultant, прочее |
| Статус | classifier | новая, отклонена, к отклику, откликнулся, в переписке, интервью, отказ, затухла |
| Оценка матча | classifier | сильный, хороший, средний, слабый |
| Вывод / причина | free | — |
| Версия CV | free | — |

New entries go to the top. Atomic writes (temp file + rename).

## Setup

**Requirements:** Python 3.10+, [uv](https://github.com/astral-sh/uv)

```bash
cd mcp-stdio
uv sync          # installs fastmcp and dependencies into .venv
uv run python server.py   # verify it starts
```

**Claude Desktop config** — `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "job-match-ai": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--project", "/Users/olegbolsunov/Projects/MatchJobAIExt9/mcp-stdio",
        "python", "/Users/olegbolsunov/Projects/MatchJobAIExt9/mcp-stdio/server.py"
      ]
    }
  }
}
```

Full Quit + relaunch Claude Desktop after saving the config.

## Data files

Versioned files are kept with a date suffix (`vacancies1209.csv`).
`data/vacancies.csv` and `data/criteria.md` are symlinks pointing to
the current versions. To switch to a new file:

```bash
ln -sf vacancies1301.csv ~/Projects/MatchJobAIExt9/data/vacancies.csv
```

The `data/` directory is in `.gitignore` — registry contents stay local.

## Project layout

```
MatchJobAIExt9/
├── mcp-stdio/          # v2 — active
│   ├── server.py       # MCP tools
│   ├── dashboard.py    # dashboard builder
│   ├── tests/
│   ├── pyproject.toml
│   └── uv.lock
├── docs/               # GitHub Pages: public dashboard (index.html)
├── launchd/            # optional daily publish job (disabled)
├── publish.sh          # build public dashboard + git push
├── data/               # working data, not tracked by git
│   ├── vacancies.csv   → vacancies1209.csv (symlink)
│   ├── criteria.md     → criteria-v2_1.md  (symlink)
│   └── dashboard.html  # personal dashboard
├── extension/          # v1 — archived, not maintained
└── mcp-server/         # v1 — archived, not maintained
```

## Why v1 was retired

The original Chrome extension was built around high-frequency screening —
scoring dozens of vacancies per day in the browser. The actual search
volume turned out to be ~100 vacancies per quarter, which made the
infrastructure (extension + Raspberry Pi + Tailscale + API key wiring)
disproportionate to the task.

The "AI match scoring" niche is also well covered by free tools
(Simplify, Teal, JobScan). v2 focuses on what those tools don't do:
structured tracking and pipeline analysis for a deliberate search,
directly inside Claude Desktop.
