# MCP Server Deployment на Raspberry Pi

## Prerequisites

- Raspberry Pi с SSH доступом
- Python 3.11+ установлен
- Git установлен

---

## Шаг 1: Склонировать проект на Pi

SSH на Pi:

```bash
ssh pi@your-pi-ip
```

Создай директорию:

```bash
mkdir -p ~/projects
cd ~/projects
```

Скопируй файлы MCP server с локальной машины:

```bash
# На локальной машине (из корня проекта)
scp -r mcp-server pi@your-pi-ip:~/projects/job-match-ai-mcp

# Или через Git если есть repo
# git clone https://github.com/yourusername/job-match-ai.git
# cd job-match-ai
```

---

## Шаг 2: Setup Python environment

На Pi:

```bash
cd ~/projects/job-match-ai-mcp  # или твоя директория
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Шаг 3: Настроить данные профиля

Файлы в `data/`:
- `profile.json` — твой карьерный профиль
- `priorities.json` — текущие constraints
- `blacklist.json` — filtered companies

**Важно**: обнови `profile.json` и `priorities.json` со своими реальными данными. Примеры там уже есть, но замени на актуальные.

```bash
nano data/profile.json
# Вставь свой полный профиль (см. пример)

nano data/priorities.json
# Обнови текущие constraints (location, языки, health protocol)
```

---

## Шаг 4: Тест запуска

```bash
source venv/bin/activate
python career_mcp.py
```

Если видишь:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8765
```

Всё работает! Останови (Ctrl+C).

---

## Шаг 5: Создать systemd service

```bash
sudo nano /etc/systemd/system/career-mcp.service
```

Вставь (замени `/home/pi/projects/job-match-ai-mcp` на реальный путь):

```ini
[Unit]
Description=Career MCP Server for Job Match AI
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/projects/job-match-ai-mcp
Environment="PATH=/home/pi/projects/job-match-ai-mcp/venv/bin"
ExecStart=/home/pi/projects/job-match-ai-mcp/venv/bin/python career_mcp.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Сохрани (Ctrl+O, Enter, Ctrl+X).

---

## Шаг 6: Enable и start service

```bash
sudo systemctl daemon-reload
sudo systemctl enable career-mcp
sudo systemctl start career-mcp

# Check status
sudo systemctl status career-mcp
```

Должен показать `active (running)`.

---

## Шаг 7: Проверка работы

### Тест локально на Pi

```bash
curl http://localhost:8765
```

Должен вернуть что-то типа:
```json
{"error": "Method not allowed"}
```

Это OK (MCP protocol использует специальные endpoints, но сервер живой).

### Тест MCP tools через curl

```bash
curl -X POST http://localhost:8765 \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

Должен вернуть список tools:
```json
{
  "tools": [
    {"name": "get_career_context", "description": "..."},
    {"name": "get_current_priorities", "description": "..."},
    ...
  ]
}
```

---

## Шаг 8: Доступ через Tailscale

MCP server запущен на `:8765`. Доступ с других устройств — через Tailscale IP.

Узнай Tailscale IP малины:

```bash
tailscale ip -4
```

Проверь доступность с другого устройства в Tailscale сети:

```bash
curl http://<tailscale-ip>:8765
```

В настройках расширения укажи MCP URL: `http://<tailscale-ip>:8765`

---

## Полезные команды

```bash
# View logs
sudo journalctl -u career-mcp -f

# Restart service
sudo systemctl restart career-mcp

# Stop service
sudo systemctl stop career-mcp

# Check status
sudo systemctl status career-mcp
```

---

## Обновление профиля

Когда меняется жизненная ситуация (язык улучшился до B1, health protocol закончился, переехал):

```bash
cd ~/projects/job-match-ai-mcp
nano data/priorities.json
# Обнови constraints

sudo systemctl restart career-mcp
```

MCP server перечитает файлы при рестарте.

---

## Application Tracker

Результаты анализов сохраняются в `data/tracker.jsonl` (по одной записи на строку).

Посмотреть последние анализы:

```bash
tail -n 10 data/tracker.jsonl | jq .
```

(Установи `jq` если нет: `sudo apt install jq`)

---

Готово! MCP server работает на Pi и доступен через Tailscale.
