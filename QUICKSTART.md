# Quick Start Guide

## Для быстрого старта: Extension без MCP

Если хочешь сначала протестировать расширение **без поднятия MCP server** на Pi:

### 1. Build extension

```bash
cd extension
npm install
npm run dev
```

### 2. Load в Chrome

1. `chrome://extensions/`
2. "Developer mode" ON
3. "Load unpacked" → выбери `extension/dist`

### 3. Настройки

1. Кликни на иконку расширения → "⚙️ Настройки"
2. Введи **Anthropic API Key** (с https://console.anthropic.com/settings/keys)
3. **MCP Server URL оставь пустым** (для начала)
4. "Сохранить"

### 4. Тест

1. Открой любую вакансию (LinkedIn, HH.ru, и т.д.)
2. Выдели текст вакансии
3. Right-click → "🎯 Analyze Job Match"
4. Popup покажет результат

**В этом режиме** Claude использует только system prompt без MCP tools. Профиль хардкоднут в промпте (см. `background/index.ts`, константа `SYSTEM_PROMPT`).

---

## С MCP (полная версия)

Когда будешь готов добавить MCP:

### 1. Deploy MCP server на Pi

Следуй `docs/mcp-deployment.md`

### 2. Узнай Tailscale IP малины

```bash
tailscale ip -4
```

### 3. Обнови настройки расширения

Введи MCP URL: `http://<tailscale-ip>:8765`

Теперь Claude будет вызывать MCP tools для получения актуального профиля и constraints.

---

## Что дальше?

- Посмотри `docs/extension-development.md` для development workflow
- Обнови `mcp-server/data/profile.json` со своими реальными данными
- Обнови `mcp-server/data/priorities.json` с актуальными constraints

---

Всё готово к работе!
