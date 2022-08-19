from aiohttp import web
from pathlib import Path
from .index import routes as index_routes
from .get_sticker import routes as get_sticker_routes


async def web_app():
    app = web.Application()
    app.add_routes(
        [
            web.static(prefix="/static", path=Path("./static")),
        ]
    )
    app.add_routes(index_routes)
    app.add_routes(get_sticker_routes)
    return app
