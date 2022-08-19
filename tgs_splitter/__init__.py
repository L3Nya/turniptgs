import json
import gzip
from io import BytesIO

from .constants import STEP_X, STEP_Y, WIDTH, HEIGHT

from .lottie_lib import move_layer, create_asset, scale_layer, move_anchor_point


def read_sticker(path):
    with gzip.open(path, "rb") as f:
        sticker = json.load(f)
    if isinstance(path, BytesIO):
        path.seek(0)
    return sticker


def write_sticker(obj, path):
    with gzip.open(path, "w") as f:
        s = json.dumps(obj)
        f.write(s.encode())


def splitter(sticker, dx=STEP_X, dy=STEP_Y, w=WIDTH, h=HEIGHT):
    op = sticker["op"]

    asset, layer = create_asset(
        "main_sticker", sticker["layers"].copy(), op, abs(w * dx), abs(h * dy)
    )

    sticker.setdefault("assets", list())
    sticker["assets"].append(asset)
    sticker["layers"] = [layer]

    # move_anchor_point(layer, w*dx, h*dy)
    scale_layer(layer, w, h)

    for y in range(h):
        for x in range(w):
            yield sticker
            move_layer(layer, dx, 0)
        move_layer(layer, -dx * w, dy)
