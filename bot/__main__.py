import asyncio
import logging
import sys

from loguru import logger
from pyrogram.sync import idle
from pyrogram import raw


from .bot import bot
from . import handlers as _


async def test(client):
    N = 1
    short_name = f"test_lenya{N}"
    short_name = f"test_{N}_by_{client.me.username}"
    title = "test"
    user = 714974074
    print(short_name)

    # doc = await client.upload_document("test.tgs")
    doc = await client.upload_document("test.png")
    sticker = raw.types.input_sticker_set_item.InputStickerSetItem(
        document=doc, emoji="😎"
    )
    s = await client.create_sticker_set(
        user,
        title,
        short_name,
        emojis=True,
        animated=False,
        stickers=[sticker],
        software="StickersBot",
    )
    print(s.set.emojis, s.set.short_name)


async def main():
    async with bot:
        me = await bot.get_me()
        logger.info(f"started on {me.username}")
        await idle()
        # await test(bot)


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level=logging.INFO)
    logger.add("debug.log", level=logging.DEBUG)
    logger.add("info.log", level=logging.INFO)
    asyncio.get_event_loop().run_until_complete(main())
