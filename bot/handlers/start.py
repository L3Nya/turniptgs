import math
import asyncio

from hashlib import blake2b

from loguru import logger
from pyrogram import filters, StopPropagation, raw
from pyrogram.errors.exceptions.not_acceptable_406 import StickersetInvalid
from pyrogram.errors.exceptions.bad_request_400 import StickersTooMuch
from pyrogram.types import ReplyKeyboardRemove

from ..bot import bot
from ..constants import (
    MAX_EMOJI,
    MAX_STICKERS,
    MIN_EMOJI_SET_WIDTH,
    MAX_EMOJI_SET_WIDTH,
    STICKER_SET_WIDTH,
    SET_TITLE_MAX_LENGTH,
    SET_SHORT_NAME_MAX_LENGTH,
    SET_SHORT_NAME_REGEX,
)
from ..config import STATIC_STICKERS_ENABLED, VIDEO_STICKERS_ENABLED, WEB_APP_URL
from ..utils.is_only_emoji import is_only_emoji
from ..keyboards import create_set_type_keyboard, create_width_keyboard
from ..get_stickers import (
    get_static_stickers,
    get_video_stickers,
    get_video_stickers_web,
    get_animated_stickers,
)


async def on_cancel(_, message):
    await message.reply("Cancelled")


async def get_set_short_name(client, chat_id, set_type):
    my_username = (client.me).username
    user_hash = blake2b(str(chat_id).encode(), digest_size=3).hexdigest()
    suffix = f"_{user_hash}_by_{my_username}"
    set_short_name = None
    await client.send_message(chat_id, "Send sticker set short name")

    s = None
    while not set_short_name:
        message = await client.listen_chat(chat_id, filters.text, on_cancel=on_cancel)
        text = message.text + suffix
        if len(text) > SET_SHORT_NAME_MAX_LENGTH:
            await message.reply(f"Too long. {suffix} is added to the end")
        elif not SET_SHORT_NAME_REGEX.match(text):
            await message.reply("Wrong short name")
        else:
            _s, existing_set_type = await check_availability(client, text)
            if s and is_conflicting_types(existing_set_type, set_type):
                await message.reply(
                    f"Set with this short name exists and its type is not {set_type}"
                )
            else:
                set_short_name = text
                s = _s
    return set_short_name, s


async def get_emojis(client, chat_id):
    emojis = None
    await client.send_message(chat_id, "Send emojis corresponding to each part")
    while not emojis:
        message = await client.listen_chat(chat_id, filters.text, on_cancel=on_cancel)
        text = message.text
        if len(text) > 32:
            await message.reply("Too long")
        elif not is_only_emoji(text):
            await message.reply("Wrong emojis")
        else:
            emojis = text
    return emojis


async def get_set_title(client, chat_id):
    set_title = None
    await client.send_message(chat_id, "Send sticker set title")
    while not set_title:
        message = await client.listen_chat(chat_id, filters.text, on_cancel=on_cancel)
        text = message.text + f" by @{client.me.username}"
        if len(text) > SET_TITLE_MAX_LENGTH:
            await message.reply("Too long. {suffix} is added to the end")
        elif text:
            set_title = text
        else:
            await message.reply("Wrong title")
    return set_title


async def get_set_width(client, chat_id, is_emoji_set):
    set_width = 0
    min_width = 2
    max_width = 5
    if is_emoji_set:
        min_width = MIN_EMOJI_SET_WIDTH
        max_width = MAX_EMOJI_SET_WIDTH
        await client.send_message(
            chat_id,
            "Most devices show 8 emoji in a row within menu. It is recommended value.\nSelect emoji set width:",
            reply_markup=create_width_keyboard(min_width, max_width, is_emoji_set),
        )
    else:
        set_width = STICKER_SET_WIDTH

    while set_width <= 1:
        message = await client.listen_chat(chat_id, filters.text, on_cancel=on_cancel)
        text = message.text

        try:
            s = int(text)
            if s < min_width or s > max_width:
                await message.reply("Out of bounds")
            else:
                set_width = s
        except ValueError:
            await message.reply("Not a number")
            continue
    await client.send_message(
        chat_id, f"Set width: {set_width}", reply_markup=ReplyKeyboardRemove()
    )
    return set_width


async def get_sticker(client, chat_id):
    await client.send_message(
        chat_id,
        "Send sticker to make turnip from\n\nUse /cancel if you changed your mind",
    )

    # waiting for sticker
    while True:
        message = await client.listen_chat(chat_id, on_cancel=on_cancel)
        if not message.sticker:
            await message.reply("Not a sticker")
        elif message.sticker.is_video:
            if not VIDEO_STICKERS_ENABLED:
                await message.reply("Video stickers support is disabled")
            else:
                return message.sticker, "video"
        elif not message.sticker.is_animated:
            if not STATIC_STICKERS_ENABLED:
                await message.reply("Static stickers support is disabled")
            else:
                return message.sticker, "static"
        else:
            return message.sticker, "animated"


async def get_is_emoji_set(client, chat_id):
    sticker_set_button, emoji_set_button, set_type_keyboard = create_set_type_keyboard()
    await client.send_message(
        chat_id, "Please choose set type:", reply_markup=set_type_keyboard
    )

    is_emoji_set = None
    while is_emoji_set is None:
        message = await client.listen_chat(chat_id, filters.text, on_cancel=on_cancel)
        text = message.text
        if text == sticker_set_button.text:
            is_emoji_set = False
        elif text == emoji_set_button.text:
            await message.reply("Emoji set creation is not supported by Telegram public API yet")
            # is_emoji_set = True
        else:
            await message.reply("Click the button")
    return is_emoji_set


def get_emoji_type(s):
    return "animated" if s.set.animated else "video" if s.set.videos else "static"


async def check_availability(client, set_short_name):
    try:
        s = await client.get_sticker_set_by_short_name(set_short_name)
        g_t = get_emoji_type(s)
        return s, g_t
    except StickersetInvalid:
        return None, None


def is_conflicting_types(a, b):
    return (a != "video" or b != "static") if a != b else False


@bot.on_message(filters.text & filters.command(["start"]))
@logger.catch(exclude=(StopPropagation,))
async def start(client, message):
    chat_id = message.chat.id
    sticker, set_type = await get_sticker(client, chat_id)

    set_short_name, s = await get_set_short_name(client, chat_id, set_type)
    # set_short_name, exists = f"test_{sticker.file_unique_id}_by_{client.me.username}", False

    if not s:
        set_title = await get_set_title(client, chat_id)
        is_emoji_set = await get_is_emoji_set(client, chat_id)
    else:
        set_title = None
        set_type = get_emoji_type(s)
        is_emoji_set = s.set.emojis
    if is_emoji_set:
        await client.send_message(
            chat_id, "Emoji sets are not supported yet so this option was disabled."
        )
        is_emoji_set = False

    set_width = await get_set_width(client, chat_id, is_emoji_set)
    # set_width = 5

    is_animated = set_type == "animated"
    is_video = set_type == "video"
    # set_title = "test"

    part_emoji = await get_emojis(client, chat_id)
    # part_emoji = '😎' # await get_emojis(client, chat_id)

    if is_animated:
        part_width = 512
        part_height = 512
        set_height = set_width
    else:
        if is_emoji_set:
            part_width = 100
            part_height = 100
        else:
            part_width = 512
            part_height = 512
        set_height = math.ceil(set_width * (sticker.height / sticker.width))

    n = set_width * set_height
    await message.reply(
        f"Title: {set_title}\n"
        f"Short name: {set_short_name}\n"
        f"Set type: {'emoji' if is_emoji_set else 'regular'} {set_type}\n"
        f"Width: {set_width} [{part_width}]\n"
        f"Height: {set_height} [{part_height}]\n"
        f"Total stickers: {n}\n"
    )
    # TODO: make thumbnail for static and video sets: 100x100 resolution
    thumb = None

    if (tn := (n + (len(s.documents) if s else 0))) > (
        mx := (MAX_EMOJI if is_emoji_set else MAX_STICKERS)
    ):
        await message.reply(f"Too much stickers in the set ({tn} > {mx})")
        return

    if is_animated:
        stickers, cleanup = await get_animated_stickers(
            client,
            sticker,
            message.from_user.id,
            set_width,
            set_height,
            part_width,
            part_height,
        )
    elif is_video:
        if WEB_APP_URL:
            stickers, cleanup = await get_video_stickers_web(
                client,
                sticker,
                message.from_user.id,
                set_width,
                set_height,
                part_width,
                part_height,
            )
        else:
            stickers, cleanup = await get_video_stickers(
                client,
                sticker,
                message.from_user.id,
                set_width,
                set_height,
                part_width,
                part_height,
            )
    else:
        stickers, cleanup = await get_static_stickers(
            client,
            sticker,
            message.from_user.id,
            set_width,
            set_height,
            part_width,
            part_height,
        )

    if stickers:
        sticker_documents = []
        sticker_documents_tasks = []
        msg = await client.send_message(message.from_user.id, f"Uploading {n} parts..")
        for sticker in stickers:
            task = asyncio.create_task(client.upload_document(sticker))
            # part = await upload_part(client, msg, i+1, n, sticker)
            # sticker_documents.append(part)
            sticker_documents_tasks.append(task)

        sticker_documents = await asyncio.gather(*sticker_documents_tasks)
        stickers = [
            raw.types.InputStickerSetItem(document=doc, emoji=part_emoji)
            for doc in sticker_documents
        ]

        s, existing_set_type = await check_availability(client, set_short_name)
        if s and existing_set_type != set_type:
            await message.reply(
                f"Set with this short name exists and its type is not {set_type}"
            )
            return
        if not s:
            if not set_title:
                await message.reply(
                    "Existing sticker set has been deleted while I was splitting.."
                )
                set_title = await get_set_title(client, chat_id)

            await msg.edit_text("Creating sticker set..")
            try:
                s = await bot.create_sticker_set(
                    message.from_user.id,
                    set_title,
                    set_short_name,
                    emojis=is_emoji_set,
                    animated=is_animated,
                    videos=is_video,
                    stickers=stickers,
                    thumb=thumb,
                    software="turniptgs",
                )
            except StickersTooMuch:
                await msg.edit_text("Too much stickers in the set")
                return
        else:
            await msg.edit_text("Adding stickers to set..")
            for sticker in stickers:
                try:
                    s = await client.add_sticker_to_set_by_short_name(
                        set_short_name, sticker
                    )
                except StickersTooMuch:
                    await msg.edit_text(f"Too much stickers in the set")
                    break
        link = "t.me/addstickers/" if not is_emoji_set else "t.me/addemoji/"
        link += s.set.short_name
        await msg.delete()
        await message.reply(f"Done!\n{len(s.documents)} stickers\n\n{link}")
    if cleanup and not KEEP_CACHE:
        cleanup()
