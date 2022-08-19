import json
import aiofiles

from aiohttp import web
from aiohttp.web_request import Request
from .constants import WORK_DIR
from .validate_data import validate
from .config import BOT_TOKEN

routes = web.RouteTableDef()


def get_dir(request: Request):
    try:
        validate(BOT_TOKEN, request.query)
    except AssertionError:
        raise web.HTTPNonAuthoritativeInformation
    data = request.match_info
    user = json.loads(request.query["user"])
    return WORK_DIR / (data["id"] + str(user["id"])) / data["size"]


@routes.get("/sticker/{id}/{size}")
async def index(request):
    try:
        async with aiofiles.open(get_dir(request) / "original.webm", "rb") as f:
            return web.Response(
                body=await f.read(),
                content_type="video/webm",
            )
    except FileNotFoundError:
        return web.Response(text="Sticker not found", status=404)


@routes.get("/sticker/{id}/{size}/lastPart")
async def last_part(request):
    d = list(get_dir(request).glob("part_*"))
    if d:
        return web.Response(text=sorted(d)[-1].name.split("part_")[1])
    else:
        return web.Response(text="0")


@routes.get(r"/sticker/{id}/{size}/{part_id:\d+}")
async def get_part_id(request):
    try:
        data = request.match_info
        part_id = int(data["part_id"])
        async with aiofiles.open(get_dir(request) / f"part_{part_id:03}", "rb") as f:
            return web.Response(
                body=await f.read(),
                content_type="video/webm",
            )
    except FileNotFoundError:
        return web.Response(text="Sticker part not found", status=404)


@routes.post("/sticker/{id}/{size}/{part_id}")
async def upload_part(request):
    data = request.match_info
    part_id = int(data["part_id"])
    fn = get_dir(request) / f"part_{part_id:03}"

    data = await request.multipart()
    field = await data.next()
    async with aiofiles.open(fn, "wb") as f:
        while True:
            chunk = await field.read_chunk()  # 8192 bytes by default.
            if not chunk:
                break
            await f.write(chunk)

    return web.Response(text=f"part_{part_id:03}")
