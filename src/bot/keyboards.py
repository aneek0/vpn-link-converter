"""Клавиатуры для Telegram бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_format_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора формата конфигурации (для одиночных ссылок)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Clash YAML",
                    callback_data="format:clash"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Xray Core",
                    callback_data="format:xray"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 sing-box",
                    callback_data="format:singbox"
                ),
            ],
        ]
    )


def get_singbox_format_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа конфигурации sing-box"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Полная конфигурация",
                    callback_data="format:full"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 Только outbound",
                    callback_data="format:outbound"
                ),
            ],
        ]
    )


def get_subscription_format_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора формата экспорта подписки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Текстовый файл",
                    callback_data="sub_format:text"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Clash YAML",
                    callback_data="sub_format:clash"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 sing-box JSON",
                    callback_data="sub_format:singbox"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Xray Core",
                    callback_data="sub_format:xray"
                ),
            ],
        ]
    )

