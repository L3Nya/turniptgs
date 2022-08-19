from aiohttp import web

routes = web.RouteTableDef()
HTML = open("index.html").read()


@routes.get("/")
async def index(_):
    return web.Response(
        text=HTML,
        content_type="text/html",
        headers={
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Embedder-Policy": "require-corp",
        },
    )
