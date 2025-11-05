"""Обработчики для Telegram бота"""
import logging
import re
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from ..converter.singbox import convert_to_singbox, format_json, create_full_config
from ..converter.clash import convert_to_clash, convert_multiple_to_clash, format_yaml
from ..converter.xray import convert_multiple_to_xray, format_json as format_xray_json
from ..converter.parser import VPNLinkParser
from ..converter.subscription import is_subscription_url, download_subscription, extract_vpn_links
from .keyboards import get_format_keyboard, get_subscription_format_keyboard
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

router = Router()

# Хранилище для временного хранения ссылок пользователей
user_links = {}
# Хранилище для множественных ссылок из подписок
user_subscription_links = {}
# Хранилище для URL подписок (для генерации имени файла)
user_subscription_urls = {}


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я конвертирую VPN ссылки в конфигурации для sing-box.\n\n"
        "Просто отправь мне VPN ссылку, и я преобразую её в формат sing-box.\n\n"
        "Поддерживаемые протоколы:\n"
        "• Hysteria2 (hy2://)\n"
        "• VLESS (vless://)\n"
        "• VMess (vmess://)\n"
        "• Trojan (trojan://)\n"
        "• Shadowsocks (ss://)\n"
        "• SOCKS5 (socks5://)\n"
        "• HTTP/HTTPS (http://, https://)\n"
        "• Wireguard (wg://)\n"
        "• TUIC (tuic://)\n"
        "• Hysteria (hysteria://)\n\n"
        "Используй /help для получения справки."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help"""
    await message.answer(
        "📖 Справка\n\n"
        "Как использовать:\n"
        "1. Отправь мне VPN ссылку любого поддерживаемого протокола\n"
        "2. Или отправь ссылку на подписку / текст подписки - получишь все VPN ссылки\n"
        "3. Выбери формат конфигурации (полная или только outbound)\n"
        "4. Получи готовую JSON конфигурацию для sing-box\n\n"
        "Команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n\n"
        "Примеры ссылок:\n"
        "• hy2://password@server.com:443?sni=example.com\n"
        "• vless://uuid@server.com:443?security=reality&sni=example.com\n\n"
        "Подписки:\n"
        "• Отправь ссылку на подписку (http/https)\n"
        "• Или текст подписки (base64 или список ссылок)"
    )


@router.message(F.text)
async def handle_vpn_link(message: Message) -> None:
    """Обработчик VPN ссылок и подписок"""
    text = message.text.strip()
    
    # Проверяем, является ли это подпиской (HTTP/HTTPS ссылки считаются подписками)
    from urllib.parse import urlparse
    parsed = urlparse(text)
    
    is_http_subscription = parsed.scheme in ['http', 'https']
    
    # Если это не HTTP/HTTPS и не начинается с VPN протокола, проверяем на подписку
    is_vpn_protocol = any(text.startswith(proto) for proto in [
        'hy2://', 'hysteria2://', 'vless://', 'vmess://', 'trojan://',
        'ss://', 'shadowsocks://', 'socks5://', 'socks://',
        'wg://', 'wireguard://', 'tuic://', 'hysteria://'
    ])
    
    is_likely_subscription = is_subscription_url(text) or (is_http_subscription and not is_vpn_protocol)
    
    # Если текст не похож на VPN ссылку, но может быть base64 подпиской - проверяем
    if not is_vpn_protocol and not is_http_subscription and not is_likely_subscription:
        # Пробуем определить, может ли это быть base64 подпиской
        text_stripped = text.strip()
        if len(text_stripped) > 20 and not ' ' in text_stripped and '\n' not in text_stripped:
            import base64
            try:
                for padding in ['', '=', '==', '===']:
                    try:
                        decoded_bytes = base64.b64decode(text_stripped + padding)
                        decoded = decoded_bytes.decode('utf-8', errors='ignore')
                        # Если декодирование успешно и содержит VPN ссылки - это подписка
                        if any(proto in decoded for proto in ['vless://', 'vmess://', 'trojan://', 'ss://', 'hy2://', 'tuic://']):
                            is_likely_subscription = True
                            logger.info("Обнаружена base64 подписка через агрессивную проверку")
                            break
                    except Exception:
                        continue
            except Exception:
                pass
    
    if is_likely_subscription:
        try:
            # Если это HTTP/HTTPS ссылка, загружаем содержимое
            if is_http_subscription:
                await message.answer("🔄 Загружаю подписку...")
                try:
                    content = await download_subscription(text)
                    # Проверяем Content-Type, если это HTML - парсим его
                    # extract_vpn_links уже умеет парсить HTML
                except Exception as e:
                    await message.answer(
                        f"❌ Ошибка при загрузке подписки:\n{str(e)}"
                    )
                    return
            else:
                content = text
                # Пробуем декодировать base64 если нужно
                import base64
                try:
                    # Пробуем разные варианты padding
                    for padding in ['', '=', '==', '===']:
                        try:
                            decoded = base64.b64decode(content + padding).decode('utf-8')
                            # Если декодирование успешно и содержит VPN ссылки, используем декодированный контент
                            if any(proto in decoded for proto in ['vless://', 'vmess://', 'trojan://', 'ss://', 'hy2://', 'tuic://', 'socks5://', 'socks://']):
                                content = decoded
                                logger.info("Успешно декодирован base64 контент")
                                break
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug(f"Ошибка при декодировании base64: {e}")
            
            # Извлекаем VPN ссылки (функция сама определит HTML и распарсит его)
            vpn_links = extract_vpn_links(content)
            
            # Логируем для отладки
            logger.info(f"Извлечено {len(vpn_links)} ссылок из подписки")
            
            if not vpn_links:
                await message.answer(
                    "❌ Не удалось извлечь VPN ссылки из подписки.\n\n"
                    "Проверь правильность формата подписки."
                )
                return
            
            # Если ссылок больше одной - сохраняем для последующей конвертации
            if len(vpn_links) > 1:
                # Сохраняем все ссылки из подписки и URL
                user_subscription_links[message.from_user.id] = vpn_links
                user_subscription_urls[message.from_user.id] = text if is_http_subscription else None
                
                await message.answer(
                    f"✅ Извлечено {len(vpn_links)} VPN ссылок из подписки\n\n"
                    f"Выбери формат экспорта:",
                    reply_markup=get_subscription_format_keyboard()
                )
                return
            else:
                # Если только одна ссылка, продолжаем обычную обработку
                text = vpn_links[0]
        except Exception as e:
            logger.error(f"Ошибка при парсинге подписки: {e}", exc_info=True)
            await message.answer(
                f"❌ Ошибка при обработке подписки:\n{str(e)}\n\n"
                "Проверь правильность формата подписки."
            )
            return
    
    # Проверяем, похоже ли на VPN ссылку (исключаем http/https, они уже обработаны как подписки)
    if not any(text.startswith(proto) for proto in [
        'hy2://', 'hysteria2://', 'vless://', 'vmess://', 'trojan://',
        'ss://', 'shadowsocks://', 'socks5://', 'socks://',
        'wg://', 'wireguard://', 'tuic://', 'hysteria://'
    ]):
        await message.answer(
            "❌ Это не похоже на VPN ссылку или подписку.\n\n"
            "Отправь мне:\n"
            "• VPN ссылку (hy2://, vless://, vmess:// и т.д.)\n"
            "• Ссылку на подписку (http/https)\n"
            "• Текст подписки (base64 или список ссылок)"
        )
        return
    
    try:
        # Определяем протокол
        protocol = VPNLinkParser.detect_protocol(text)
        if not protocol:
            await message.answer("❌ Неподдерживаемый протокол.")
            return
        
        # Сохраняем ссылку для пользователя
        user_links[message.from_user.id] = text
        
        # Просим выбрать формат
        await message.answer(
            f"✅ Распознан протокол: {protocol.upper()}\n\n"
            "Выбери формат конфигурации:",
            reply_markup=get_format_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке ссылки: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при обработке ссылки:\n{str(e)}\n\n"
            "Проверь правильность формата ссылки."
        )


def generate_filename_from_url(url: str, extension: str) -> str:
    """Генерирует имя файла из URL подписки"""
    if not url:
        return f"subscription.{extension}"
    
    try:
        parsed = urlparse(url)
        # Пробуем использовать домен или IP
        hostname = parsed.hostname or parsed.netloc
        if hostname:
            # Убираем порт если есть
            if ':' in hostname:
                hostname = hostname.split(':')[0]
            # Очищаем от недопустимых символов для имени файла
            # Заменяем только недопустимые символы
            hostname = re.sub(r'[<>:"/\\|?*]', '-', hostname)
            # Если имя слишком длинное, обрезаем
            if len(hostname) > 50:
                hostname = hostname[:50]
            return f"{hostname}.{extension}"
    except Exception:
        pass
    
    return f"subscription.{extension}"


@router.callback_query(F.data.startswith("sub_format:"))
async def handle_subscription_format_choice(callback: CallbackQuery) -> None:
    """Обработчик выбора формата экспорта подписки"""
    await callback.answer()
    
    user_id = callback.from_user.id
    format_type = callback.data.split(":")[1]
    
    if user_id not in user_subscription_links:
        await callback.message.answer("❌ Подписка не найдена. Отправь подписку заново.")
        return
    
    subscription_links = user_subscription_links[user_id]
    subscription_url = user_subscription_urls.get(user_id)
    
    # Удаляем сохраненные данные
    del user_subscription_links[user_id]
    if user_id in user_subscription_urls:
        del user_subscription_urls[user_id]
    
    try:
        from aiogram.types import BufferedInputFile
        
        if format_type == "text":
            # Текстовый файл со ссылками
            file_content = "\n".join(subscription_links)
            filename = generate_filename_from_url(subscription_url, "txt")
            file = BufferedInputFile(
                file_content.encode('utf-8'),
                filename=filename
            )
            await callback.message.answer_document(
                file,
                caption=f"✅ Текстовый файл\n({len(subscription_links)} ссылок)"
            )
        
        elif format_type == "clash":
            # Clash YAML
            await callback.message.answer("🔄 Конвертирую в Clash YAML...")
            try:
                config = convert_multiple_to_clash(subscription_links)
                yaml_config = format_yaml(config)
                filename = generate_filename_from_url(subscription_url, "yaml")
                file = BufferedInputFile(
                    yaml_config.encode('utf-8'),
                    filename=filename
                )
                await callback.message.answer_document(
                    file,
                    caption=f"✅ Конфигурация Clash YAML\n({len(subscription_links)} серверов)"
                )
            except Exception as e:
                await callback.message.answer(
                    f"❌ Ошибка при конвертации в Clash:\n{str(e)}"
                )
        
        elif format_type == "singbox":
            # sing-box JSON (полная конфигурация)
            await callback.message.answer("🔄 Конвертирую в sing-box JSON...")
            try:
                # Конвертируем все ссылки в outbounds
                outbounds = []
                for link in subscription_links:
                    try:
                        outbound = VPNLinkParser.to_singbox_outbound(link)
                        outbounds.append(outbound)
                    except Exception:
                        continue
                
                if not outbounds:
                    raise ValueError("Не удалось конвертировать ни одну ссылку")
                
                config = create_full_config(outbounds)
                json_config = format_json(config)
                filename = generate_filename_from_url(subscription_url, "json")
                file = BufferedInputFile(
                    json_config.encode('utf-8'),
                    filename=filename
                )
                await callback.message.answer_document(
                    file,
                    caption=f"✅ Конфигурация sing-box JSON\n({len(outbounds)} серверов)"
                )
            except Exception as e:
                await callback.message.answer(
                    f"❌ Ошибка при конвертации в sing-box:\n{str(e)}"
                )
        
        elif format_type == "xray":
            # Xray Core JSON
            await callback.message.answer("🔄 Конвертирую в Xray Core...")
            try:
                config = convert_multiple_to_xray(subscription_links)
                json_config = format_xray_json(config)
                filename = generate_filename_from_url(subscription_url, "json")
                file = BufferedInputFile(
                    json_config.encode('utf-8'),
                    filename=filename
                )
                await callback.message.answer_document(
                    file,
                    caption=f"✅ Конфигурация Xray Core\n({len(subscription_links)} серверов)"
                )
            except Exception as e:
                await callback.message.answer(
                    f"❌ Ошибка при конвертации в Xray:\n{str(e)}"
                )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке формата подписки: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при обработке:\n{str(e)}"
        )


@router.callback_query(F.data.startswith("format:"))
async def handle_format_choice(callback: CallbackQuery) -> None:
    """Обработчик выбора формата конфигурации"""
    await callback.answer()
    
    user_id = callback.from_user.id
    format_type = callback.data.split(":")[1]
    
    try:
        from aiogram.types import BufferedInputFile
        
        # Обработка одиночной ссылки (подписки обрабатываются отдельным обработчиком)
        if user_id not in user_links:
            await callback.message.answer("❌ Ссылка не найдена. Отправь ссылку заново.")
            return
        
        vpn_link = user_links[user_id]
        del user_links[user_id]
        
        if format_type == "clash":
            # Конвертация в Clash YAML
            config = convert_to_clash(vpn_link)
            yaml_config = format_yaml(config)
            
            # Отправляем результат
            if len(yaml_config) > 4096:
                file = BufferedInputFile(
                    yaml_config.encode('utf-8'),
                    filename='clash-config.yaml'
                )
                await callback.message.answer_document(
                    file,
                    caption="✅ Конфигурация Clash YAML"
                )
            else:
                await callback.message.answer(
                    "✅ Конфигурация Clash YAML:\n\n"
                    f"```yaml\n{yaml_config}\n```",
                    parse_mode="Markdown"
                )
        else:
            # Конвертация в sing-box
            full_config = format_type == "full"
            config = convert_to_singbox(vpn_link, full_config=full_config)
            json_config = format_json(config)
            
            # Отправляем результат
            if len(json_config) > 4096:
                file = BufferedInputFile(
                    json_config.encode('utf-8'),
                    filename='sing-box-config.json'
                )
                await callback.message.answer_document(
                    file,
                    caption=f"✅ Конфигурация ({'полная' if full_config else 'только outbound'})"
                )
            else:
                await callback.message.answer(
                    f"✅ Конфигурация ({'полная' if full_config else 'только outbound'}):\n\n"
                    f"```json\n{json_config}\n```",
                    parse_mode="Markdown"
                )
    except Exception as e:
        logger.error(f"Ошибка при конвертации: {e}", exc_info=True)
        await callback.message.answer(
            f"❌ Ошибка при конвертации:\n{str(e)}"
        )

