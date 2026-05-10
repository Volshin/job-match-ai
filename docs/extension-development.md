# Extension Development Guide

## Local Development

### Prerequisites

- Node.js 18+ и npm
- Chrome browser

### Setup

```bash
cd extension
npm install
```

### Build для development

```bash
npm run dev
```

Это запустит Vite в watch mode. Файлы пересобираются автоматически при изменениях.

---

## Загрузка в Chrome

1. Открой `chrome://extensions/`
2. Enable "Developer mode" (toggle в правом верхнем углу)
3. "Load unpacked"
4. Выбери папку `extension/dist`

Расширение появится в списке.

---

## Настройка расширения

1. Кликни на иконку расширения или открой `chrome://extensions/` → "Details" → "Extension options"
2. Введи **Anthropic API Key** (получить на https://console.anthropic.com/settings/keys)
3. Введи **MCP Server URL** (например `https://mcp.yourdomain.com`)
4. "Сохранить"

---

## Использование

1. Открой любую job board (LinkedIn, HH.ru, Habr Career, StackOverflow Jobs)
2. **Выделите текст вакансии** (весь JD или релевантную часть)
3. Right-click → **"🎯 Analyze Job Match"**
4. Расширение отправит запрос к Claude API с твоим профилем из MCP
5. Popup откроется с результатами: match score, flags, recommendation

---

## Development Workflow

### Hot Reload

При изменениях в `src/`:

1. Vite автоматически пересоберёт (watch mode)
2. Иди в `chrome://extensions/` → кликни "Reload" на твоём расширении
3. Перезагрузи страницу где тестируешь

### Debugging

**Background Service Worker:**
```
chrome://extensions/ → твоё расширение → "Inspect views: service worker"
```

Откроется DevTools для background script. Можешь видеть:
- `console.log()` из `background/index.ts`
- Network requests к Anthropic API
- Errors

**Popup:**
Right-click на popup → "Inspect"

**Options Page:**
Right-click на странице настроек → "Inspect"

---

## Testing MCP Integration

### Без MCP server (fallback)

Если MCP URL пустой в настройках, расширение работает без MCP — использует только system prompt. Это позволяет тестировать без поднятия Pi server.

### С MCP server

1. Убедись что MCP server запущен на Pi (см. `mcp-deployment.md`)
2. Убедись что Cloudflare Tunnel работает (см. `cloudflare-tunnel-setup.md`)
3. Проверь MCP URL в настройках: `https://mcp.yourdomain.com`
4. "Проверить подключение" в настройках должен дать ✅

Когда запрос идёт с MCP, в DevTools (Background SW) увидишь:
```json
{
  "mcp_servers": [
    {
      "type": "url",
      "url": "https://mcp.yourdomain.com",
      "name": "career-context"
    }
  ]
}
```

И Claude автоматически вызовет MCP tools (`get_career_context`, `get_current_priorities`).

---

## Структура кода

```
extension/src/
├── background/
│   └── index.ts          # Service worker: API calls, context menu
├── popup/
│   ├── index.html        # Entry point
│   ├── Popup.tsx         # React component для результатов
│   └── Popup.css         # Styles
├── options/
│   ├── index.html        # Entry point
│   ├── Options.tsx       # React component для настроек
│   └── Options.css       # Styles
└── lib/                  # Shared utilities (future)
```

---

## Adding New Features

### Пример: добавить "Copy Analysis" button в popup

1. **Popup.tsx:**

```tsx
const handleCopy = () => {
  const text = `Match Score: ${analysis.match_score}%
Recommendation: ${analysis.recommendation}
Reasoning: ${analysis.reasoning_ru}`;
  
  navigator.clipboard.writeText(text);
  alert('Copied!');
};

// В JSX:
<button onClick={handleCopy}>📋 Copy Analysis</button>
```

2. Пересобери (`npm run dev` уже в watch mode)
3. Reload extension в Chrome
4. Тест

---

## Production Build

Когда готов к релизу:

```bash
npm run build
```

Создаст оптимизированный build в `dist/`. Можешь запаковать:

```bash
cd dist
zip -r ../job-match-ai-v0.1.0.zip .
```

Этот zip можно загрузить в Chrome Web Store (если планируешь публиковать).

---

## Troubleshooting

### "API Key invalid"

Проверь в Options что ключ правильный. Формат: `sk-ant-...`

### "Failed to fetch"

CORS ошибка. Убедись что:
- Header `anthropic-dangerous-direct-browser-access: true` присутствует
- `dangerouslyAllowBrowser: true` в Anthropic client (уже есть в коде)

### MCP server не отвечает

1. Проверь что MCP service запущен на Pi: `sudo systemctl status career-mcp`
2. Проверь Cloudflare tunnel: `sudo systemctl status cloudflared`
3. Curl тест: `curl https://mcp.yourdomain.com`

### Extension не появляется после Load Unpacked

Проверь что выбрал папку `dist`, не `src`. Vite билдит в `dist/`.

---

## Next Steps

После MVP (v0.1):

- [ ] Content scripts для автоматического извлечения job description (без manual selection)
- [ ] Support для HH.ru, Habr Career DOM selectors
- [ ] Application tracker UI (dashboard для saved analyses)
- [ ] Export analyses to CSV/Google Sheets
- [ ] Cover letter generator (V2)

---

Готово! Теперь ты можешь разрабатывать и тестировать расширение локально.
