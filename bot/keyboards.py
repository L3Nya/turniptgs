from urllib.parse import urlencode
import math
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)
from .constants import WIDTH_KEYBOARD_ROW_SIZE
from .config import WEB_APP_URL


def create_set_type_keyboard():
    sticker_set_button = KeyboardButton(text="Sticker set")
    emoji_set_button = KeyboardButton(text="Emoji set")
    set_type_keyboard = ReplyKeyboardMarkup(
        keyboard=[[sticker_set_button, emoji_set_button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return sticker_set_button, emoji_set_button, set_type_keyboard


def create_width_keyboard(min_width, max_width, is_emoji_set=False):
    if is_emoji_set:
        numbers = [8]
    else:
        numbers = range(min_width, max_width + 1)
    buttons = [KeyboardButton(text=str(i)) for i in numbers]
    rows = [
        list(buttons[i * WIDTH_KEYBOARD_ROW_SIZE : (i + 1) * WIDTH_KEYBOARD_ROW_SIZE])
        for i in range(math.ceil(len(buttons) / WIDTH_KEYBOARD_ROW_SIZE) + 1)
    ]
    width_keyboard = ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True,
        placeholder=f"Write number from {min_width} to {max_width}..",
    )
    return width_keyboard


def create_web_app_keyboard(**kwargs):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Run",
                    web_app=WebAppInfo(url=WEB_APP_URL + "#" + urlencode(kwargs)),
                )
            ]
        ]
    )
