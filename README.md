# VPN Link Converter

Telegram бот и веб-сайт для конвертации VPN ссылок в JSON конфигурации для sing-box ядра.

## Возможности

- Поддержка всех основных VPN протоколов (hy2, vless, vmess, trojan, shadowsocks, wireguard, tuic и др.)
- Парсинг подписок VPN серверов (извлечение всех ссылок из подписки)
- Конвертация в формат sing-box
- Выбор между полной конфигурацией и только outbound секцией
- Telegram бот для удобной конвертации
- Веб-интерфейс для использования через браузер
- CLI утилита для консольного использования

## Установка

```bash
# Используя uv
uv sync

# Или используя pip
pip install -r requirements.txt
```

## Настройка

1. Скопируйте `.env.example` в `.env`
2. Заполните `BOT_TOKEN` токеном вашего Telegram бота

## Запуск

### CLI утилита (консольная версия)

Самый простой способ использования:

```bash
uv run python cli.py
```

Или после установки:

```bash
uv run vpn-convert
```

### Telegram бот

```bash
uv run python bot.py
```

### Веб-сайт

```bash
uv run python web.py
```

## Использование

### Telegram бот

Отправьте боту VPN ссылку, выберите формат (полная конфигурация или только outbound) и получите JSON конфигурацию.

### Веб-сайт

Откройте браузер и перейдите на `http://localhost:8000`, введите VPN ссылку и выберите формат.

## Поддерживаемые протоколы

- hysteria2 (hy2://)
- vless (vless://)
- vmess (vmess://)
- trojan (trojan://)
- shadowsocks (ss://)
- socks5 (socks5://)
- http/https (http://, https://)
- wireguard (wg://)
- tuic (tuic://)
- hysteria (hysteria://)

