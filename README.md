# Job Match AI

Chrome extension для анализа вакансий на match с карьерным профилем через Claude API + MCP server.

## Архитектура

```
┌─────────────────┐
│  Chrome Browser │
│                 │
│  ┌───────────┐  │
│  │ Extension │  │──┐
│  └───────────┘  │  │
└─────────────────┘  │
                     │ HTTPS
                     ▼
            ┌─────────────────┐
            │ Anthropic API   │
            │ (Claude Sonnet) │
            └─────────────────┘
                     │
                     │ MCP Protocol
                     ▼
            ┌─────────────────┐
            │   Raspberry Pi  │
            │                 │
            │  ┌───────────┐  │
            │  │MCP Server │  │
            │  │(FastMCP)  │  │
            │  └───────────┘  │
            │        │        │
            │        ▼        │
            │  career-context │
            │  priorities     │
            │  blacklist      │
            └─────────────────┘
```

## Компоненты

### 1. Chrome Extension (`/extension`)
- **Service Worker**: API calls, context menu, storage management
- **Popup**: результаты анализа (match score, flags, recommendation)
- **Options Page**: настройки (API key, MCP URL)
- **Content Scripts**: извлечение текста вакансий с job boards

### 2. MCP Server (`/mcp-server`)
- **FastMCP** на Python
- **Tools**:
  - `get_career_context()` — полный карьерный профиль
  - `get_current_priorities()` — актуальные constraints (location, язык, health)
  - `get_blacklisted_companies()` — список спамных рекрутеров/компаний
  - `save_analysis()` — сохранение результатов анализа (application tracker)

### 3. Deployment (`/docs`)
- Tailscale setup на Pi
- Systemd service для MCP server
- Testing guides

## Quick Start

### Extension (локальная установка)
```bash
cd extension
npm install
npm run dev
# Загрузить unpacked extension из extension/dist в chrome://extensions
```

### MCP Server (на Pi)
```bash
cd mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python career_mcp.py
```

### Tailscale
```bash
# Узнай IP малины
tailscale ip -4
# Укажи в настройках расширения: http://<tailscale-ip>:8765
```

## MVP Features (v0.1)

- ✅ Context menu: "Analyze Job Match" на выделенном тексте
- ✅ MCP integration для динамического профиля
- ✅ Claude Sonnet 4.6 analysis
- ✅ Popup с результатами (score, flags, reasoning на русском)
- ✅ Settings page (API key, MCP URL)

## V2 Features (backlog)

- 📋 Application tracker (сохранение analyzed jobs)
- 📊 Dashboard с историей анализов
- 📝 Cover letter generator
- 📂 Files API для статичного resume (экономия tokens)
- 🌐 Multi-language support (English output option)

## Tech Stack

- **Frontend**: TypeScript, React, Vite, Manifest v3
- **Backend**: Python 3.11+, FastMCP
- **API**: Anthropic Claude Sonnet 4.6
- **Network**: Tailscale
- **Storage**: Chrome Storage API (local + sync)

## Структура проекта

```
job-match-ai/
├── extension/
│   ├── src/
│   │   ├── background/      # Service worker
│   │   ├── popup/           # Popup UI
│   │   ├── options/         # Settings page
│   │   ├── content/         # Content scripts
│   │   └── lib/             # Shared utilities
│   ├── public/
│   │   └── manifest.json
│   └── package.json
├── mcp-server/
│   ├── career_mcp.py        # FastMCP server
│   ├── data/
│   │   ├── profile.json     # Career context
│   │   ├── priorities.json  # Current constraints
│   │   └── blacklist.json   # Filtered companies
│   ├── requirements.txt
│   └── systemd/
│       └── career-mcp.service
└── docs/
    ├── mcp-deployment.md
    └── extension-development.md
```

## License

MIT
