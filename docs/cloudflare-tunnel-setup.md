# Cloudflare Tunnel Setup для MCP Server

## Зачем нужен Cloudflare Tunnel?

Твой MCP server на Raspberry Pi стоит за NAT (внутренний IP типа 192.168.x.x). Anthropic API требует **публичный HTTPS адрес** для MCP. Cloudflare Tunnel создаёт защищённый туннель от публичного домена к твоему Pi.

**Преимущества:**
- ✅ Бесплатный (unlimited bandwidth)
- ✅ Автоматический HTTPS (Let's Encrypt через Cloudflare)
- ✅ Фиксированный адрес (не меняется при рестарте)
- ✅ DDoS protection из коробки

---

## Prerequisites

1. **Домен** (нужен для named tunnel). Варианты:
   - Купить дешёвый ($10/год на Namecheap, Porkbun)
   - Использовать subdomain существующего домена
   - Можно использовать бесплатный от Freenom (но они ненадёжны)

2. **Cloudflare аккаунт** (бесплатный): https://dash.cloudflare.com/sign-up

---

## Шаг 1: Добавить домен в Cloudflare

1. Залогинься на https://dash.cloudflare.com
2. "Add a Site" → введи домен (например `yourdomain.com`)
3. Выбери **Free Plan**
4. Cloudflare даст тебе nameservers (типа `ns1.cloudflare.com`)
5. Иди в регистратор домена (Namecheap, Porkbun, и т.д.) → **замени nameservers** на те что дал Cloudflare
6. Жди 5-60 минут пока DNS propagate (проверяй в Cloudflare dashboard: статус должен стать "Active")

---

## Шаг 2: Установить `cloudflared` на Raspberry Pi

SSH на Pi:

```bash
ssh pi@your-pi-ip
```

Установи `cloudflared`:

```bash
# Download latest release
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64

# Make executable
chmod +x cloudflared-linux-arm64

# Move to system path
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared

# Verify
cloudflared --version
```

---

## Шаг 3: Authenticate с Cloudflare

```bash
cloudflared tunnel login
```

Откроется браузер → выбери свой домен → Authorize. Файл cert.pem сохранится в `~/.cloudflared/`.

---

## Шаг 4: Создать Named Tunnel

```bash
# Создать tunnel с именем "mcp-job-match"
cloudflared tunnel create mcp-job-match
```

Вывод покажет **Tunnel ID** (сохрани его). Credentials сохранятся в `~/.cloudflared/<tunnel-id>.json`.

---

## Шаг 5: Связать tunnel с доменом

Выбери subdomain (например `mcp.yourdomain.com`):

```bash
cloudflared tunnel route dns mcp-job-match mcp.yourdomain.com
```

Cloudflare автоматически создаст CNAME запись `mcp.yourdomain.com` → `<tunnel-id>.cfargotunnel.com`.

---

## Шаг 6: Создать конфиг `cloudflared`

```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Вставь:

```yaml
tunnel: mcp-job-match
credentials-file: /home/pi/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: mcp.yourdomain.com
    service: http://localhost:8765
  - service: http_status:404
```

Замени:
- `<TUNNEL_ID>` на реальный ID из Шага 4
- `mcp.yourdomain.com` на твой subdomain
- `8765` на порт MCP сервера (если изменил)

Сохрани (Ctrl+O, Enter, Ctrl+X).

---

## Шаг 7: Запустить tunnel (тест)

```bash
cloudflared tunnel run mcp-job-match
```

Если видишь `Connection established`, всё работает. Проверь в браузере: `https://mcp.yourdomain.com` (должен вернуть 404 или ошибку если MCP server не запущен, что OK).

Останови (Ctrl+C).

---

## Шаг 8: Настроить systemd service (автозапуск)

Создай systemd unit для `cloudflared`:

```bash
sudo nano /etc/systemd/system/cloudflared.service
```

Вставь:

```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/local/bin/cloudflared tunnel run mcp-job-match
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Сохрани. Затем:

```bash
# Enable и start
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# Check status
sudo systemctl status cloudflared
```

Должен показать `active (running)`.

---

## Шаг 9: Проверка

1. **MCP server запущен** (см. `mcp-deployment.md`)
2. **Cloudflare tunnel запущен**
3. Проверь: `curl https://mcp.yourdomain.com` (должен вернуть что-то от MCP server или 404)

Если всё OK, используй `https://mcp.yourdomain.com` как **MCP URL** в настройках расширения.

---

## Troubleshooting

### Tunnel не стартует
```bash
# Проверь логи
sudo journalctl -u cloudflared -f
```

### "Failed to connect to origin"
MCP server не запущен на Pi:8765. Проверь:
```bash
sudo systemctl status career-mcp
```

### "DNS resolution error"
DNS ещё не propagate. Жди 5-30 минут после `tunnel route dns`.

---

## Полезные команды

```bash
# List tunnels
cloudflared tunnel list

# Delete tunnel
cloudflared tunnel delete mcp-job-match

# View tunnel info
cloudflared tunnel info mcp-job-match
```

---

Готово! Твой MCP server теперь доступен по HTTPS через Cloudflare Tunnel.
