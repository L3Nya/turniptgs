import os
import io
import asyncio

from collections import OrderedDict

from loguru import logger
from pyrogram.client import Client as PyroClient
from pyrogram import filters, raw, StopPropagation
from pyrogram.file_id import FileId
from pyrogram.handlers.message_handler import MessageHandler

from .config import API_ID, API_HASH, BOT_TOKEN, TEST_MODE

from .queue_manager import QueueManager


class Listener(asyncio.Future):
    def __init__(self, client, _filters, ignore_cancel, on_cancel):
        super().__init__()
        self.filters = _filters
        self.client = client
        self.ignore_cancel = ignore_cancel
        self.on_cancel = on_cancel

        self.handler, self.group = add_handler_no_threadsafe(
            client, MessageHandler(self.handler_func, self.filters), -1
        )

    async def handler_func(self, client, message):
        if not self.done():
            remove_handler_no_threadsafe(self.client, self.handler, self.group)
            if (
                not self.ignore_cancel
                and message.text == "/cancel"
                or message.caption == "/cancel"
            ):
                if self.on_cancel:
                    await self.on_cancel(client, message)
                self.cancel()
                raise StopPropagation

            self.set_result(message)
            raise StopPropagation


def add_handler_no_threadsafe(client, handler, group: int = 0):
    dp = client.dispatcher
    if group not in dp.groups:
        dp.groups[group] = []
        dp.groups = OrderedDict(sorted(dp.groups.items()))

    dp.groups[group].append(handler)
    return handler, group


def remove_handler_no_threadsafe(client, handler, group: int):
    dp = client.dispatcher
    if group not in dp.groups:
        raise ValueError(f"Group {group} does not exist. Handler was not removed.")

    try:
        dp.groups[group].remove(handler)
    except ValueError:
        pass


class Client(PyroClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.listeners = []
        self.queue_manager = QueueManager()

    async def download_file(self, document, file=None):
        file_id_obj = FileId.decode(document.file_id)
        file_size = document.file_size
        if not file:
            file = io.BytesIO()
        is_bytes_io = isinstance(file, io.BytesIO)
        async for chunk in self.get_file(file_id_obj, file_size):
            file.write(chunk)
        if is_bytes_io:
            file.seek(0)
            file.name = document.file_name
            if document.mime_type == "video/webm":
                file.name = "sticker.webm"
        return file

    async def listen(self, _filters, timeout=None, ignore_cancel=False, on_cancel=None):
        listener = Listener(self, _filters, ignore_cancel, on_cancel)
        listener.add_done_callback(self.remove_listener)
        self.listeners.append(listener)
        try:
            return await asyncio.wait_for(listener, timeout)
        except asyncio.CancelledError as exc:
            raise StopPropagation from exc

    async def listen_chat(
        self, chat_id, _filters=None, timeout=None, ignore_cancel=False, on_cancel=None
    ):
        f = filters.chat(chat_id) & filters.incoming
        if _filters:
            f = f & _filters
        response = await self.listen(
            f, timeout=timeout, ignore_cancel=ignore_cancel, on_cancel=on_cancel
        )
        return response

    async def ask(
        self,
        chat_id,
        text,
        *args,
        _filters=None,
        timeout=None,
        ignore_cancel=False,
        on_cancel=None,
        **kwargs,
    ):
        await self.send_message(chat_id, text, *args, **kwargs)
        response = await self.listen_chat(
            chat_id,
            _filters,
            timeout=timeout,
            ignore_cancel=ignore_cancel,
            on_cancel=on_cancel,
        )
        return response

    def remove_listener(self, f):
        self.listeners.remove(f)

    async def create_sticker_set(
        self,
        user_id,
        title: str,
        short_name: str,
        stickers: [raw.types.InputStickerSetItem],
        masks: bool | None = None,
        animated: bool | None = None,
        videos: bool | None = None,
        emojis: bool | None = None,
        thumb: raw.base.InputDocument | raw.types.InputDocumentEmpty | None = None,
        software: str | None = None,
    ):
        peer = await self.resolve_peer(user_id)
        return await self.invoke(
            raw.functions.stickers.CreateStickerSet(
                user_id=peer,
                title=title,
                short_name=short_name,
                stickers=stickers,
                masks=masks,
                animated=animated,
                videos=videos,
                emojis=emojis,
                thumb=thumb,
                software=software,
            )
        )

    async def add_sticker_to_set_by_short_name(
        self, short_name: str, sticker: raw.types.InputStickerSetItem
    ):
        return await self.invoke(
            raw.functions.stickers.AddStickerToSet(
                stickerset=raw.types.InputStickerSetShortName(short_name=short_name),
                sticker=sticker,
            )
        )

    async def upload_document(self, file, thumb=None):
        is_bytes_io = isinstance(file, io.BytesIO)
        if is_bytes_io and not hasattr(file, "name"):
            file.name = "file"
        filename_attribute = [
            raw.types.DocumentAttributeFilename(
                file_name=file.name if is_bytes_io else os.path.basename(file)
            )
        ]
        media = raw.types.InputMediaUploadedDocument(
            mime_type=(None if is_bytes_io else self.guess_mime_type(file))
            or "application/zip",
            thumb=await self.save_file(thumb) if thumb else None,
            file=await self.save_file(file),
            attributes=filename_attribute,
            force_file=True,
        )
        uploaded_media = await self.invoke(
            raw.functions.messages.UploadMedia(
                peer=raw.types.InputPeerSelf(), media=media
            )
        )
        if is_bytes_io:
            file.seek(0)
        return raw.types.InputDocument(
            id=uploaded_media.document.id,
            access_hash=uploaded_media.document.access_hash,
            file_reference=uploaded_media.document.file_reference,
        )

    # NOT WORKING WITH BOTS
    async def check_set_short_name(self, short_name):
        return await self.invoke(
            raw.functions.stickers.CheckShortName(short_name=short_name)
        )

    async def get_sticker_set_by_short_name(self, short_name):
        return await self.invoke(
            raw.functions.messages.GetStickerSet(
                stickerset=raw.types.InputStickerSetShortName(short_name=short_name),
                hash=0,
            )
        )

    async def start(self):
        await super().start()
        self.queue_manager.start()

    async def stop(self):
        logger.info("stopping all listeners..")
        for listener in self.listeners:
            if not listener.done():
                listener.cancel()
        self.queue_manager.stop()
        logger.info("stopping normally..")
        await super().stop()


if TEST_MODE:
    logger.warning("running on a test server")
bot = Client(
    "bot",
    # in_memory=True,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    test_mode=TEST_MODE,
)
