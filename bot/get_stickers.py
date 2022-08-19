import functools
import io
import asyncio
from pathlib import Path

import aiofiles
from pyrogram import filters

from tgs_splitter import read_sticker, splitter, write_sticker

from .splitters import split_video_sticker, split_static_sticker
from .bot import Client
from .constants import WEB_APP_SPLIT_TIMEOUT
from .utils.get_ffmpeg_dir import get_dir
from .keyboards import create_web_app_keyboard


def cleanup_directory(directory: Path):
    for p in directory.iterdir():
        p.unlink()
    directory.rmdir()


async def get_video_stickers_web(
    client, sticker, user_id, set_width, set_height, part_width, part_height
):
    sticker_id = sticker.file_unique_id
    size = f"{set_width}x{set_height}-{part_width}x{part_height}"
    d = get_dir(sticker_id, user_id, size)
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "original.webm").exists():
        async with aiofiles.open(d / "original.webm", "wb") as f:
            await f.write((await client.download_file(sticker)).read())
    cleanup = functools.partial(cleanup_directory, d)
    web_app_keyboard = create_web_app_keyboard(
        sticker_id=sticker_id,
        set_width=set_width,
        set_height=set_height,
        part_width=part_width,
        part_height=part_height,
    )
    msg = await client.send_message(
        user_id,
        "Processing video stickers is done on user side, so you have to open web app to proceed",
        reply_markup=web_app_keyboard,
    )
    try:
        await client.listen_chat(
            user_id,
            filters.service
            & filters.create(
                lambda x: x.web_app_data
                and x.web_app_data.data == f"done{sticker_id}-{size}"
            ),
            timeout=WEB_APP_SPLIT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        await msg.reply("Hasn't been split in a time. Cancelling", quote=True)
        return None, cleanup

    return sorted(d.glob("part_*.webm")), cleanup


async def get_animated_stickers(
    client, sticker, user_id, set_width, set_height, part_width, part_height
):
    raw_sticker = await client.download_file(sticker)
    sticker_json = read_sticker(raw_sticker)

    stickers = []
    await client.send_message(user_id, f"Splitting to {set_width*set_height} parts..")
    for part_json in splitter(
        sticker_json, dx=-part_width, dy=-part_height, w=set_width, h=set_height
    ):
        s = io.BytesIO()
        s.name = "sticker.tgs"
        write_sticker(part_json, s)
        s.seek(0)
    return stickers, None


async def position_updater(client, task, msg):
    prev_pos = task.get_position() - 1
    while not task.done():
        pos = task.get_position()
        try:
            if task.in_queue and pos != prev_pos:
                if 0 <= pos <= client.queue_manager.size():
                    await msg.edit_text(
                        f"Your position in queue: {pos + 1}/{client.queue_manager.size()}"
                    )
                    prev_pos = pos
                await asyncio.sleep(5)
            else:
                await task
        except asyncio.CancelledError:
            break
    try:
        await msg.delete()
    except asyncio.CancelledError:
        await msg.delete()


async def get_video_stickers(
    client: Client, sticker, user_id, set_width, set_height, part_width, part_height
):
    sticker_id = sticker.file_unique_id
    size = f"{set_width}x{set_height}-{part_width}x{part_height}"
    d = get_dir(sticker_id, user_id, size)
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "original.webm").exists():
        async with aiofiles.open(d / "original.webm", "wb") as f:
            await f.write((await client.download_file(sticker)).read())
    cleanup = functools.partial(cleanup_directory, d)
    msg = await client.send_message(user_id, "Your task has been added to queue.")
    task = await client.queue_manager.add_task(
        split_video_sticker,
        (d, d / "original.webm", set_width, set_height, part_width, part_height),
    )

    pos_upd = asyncio.create_task(position_updater(client, task, msg))
    task.add_done_callback(lambda _: pos_upd.cancel())
    res, _ = await asyncio.gather(task, pos_upd)
    if res:
        return res, cleanup
    await client.send_message(
        user_id, "Couldn't split this sticker, contact the developer."
    )
    return None, cleanup


async def get_static_stickers(
    client: Client, sticker, user_id, set_width, set_height, part_width, part_height
):
    sticker_id = sticker.file_unique_id
    size = f"{set_width}x{set_height}-{part_width}x{part_height}"
    d = get_dir(sticker_id, user_id, size)
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "original.webp").exists():
        async with aiofiles.open(d / "original.webp", "wb") as f:
            await f.write((await client.download_file(sticker)).read())
    cleanup = functools.partial(cleanup_directory, d)
    msg = await client.send_message(user_id, "Your task has been added to queue.")
    task = await client.queue_manager.add_task(
        split_static_sticker,
        (d, d / "original.webp", set_width, set_height, part_width, part_height),
    )

    pos_upd = asyncio.create_task(position_updater(client, task, msg))
    task.add_done_callback(lambda _: pos_upd.cancel())
    res, _ = await asyncio.gather(task, pos_upd)
    if res:
        return res, cleanup
    await client.send_message(
        user_id, "Couldn't split this sticker, contact the developer."
    )
    return None, cleanup
