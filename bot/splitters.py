import functools
from pathlib import Path

from asynccpu import ProcessTaskPoolExecutor
from loguru import logger

from ffmpeg_splitter import split
from .config import SPLITTER_WORKERS


async def split_video_sticker(
    directory: Path,
    input_file: Path,
    width,
    height,
    part_width,
    part_height,
    on_part=None,
):
    try:
        with ProcessTaskPoolExecutor(cancel_tasks_when_shutdown=True) as executor:

            # await split(directory, width, height, part_width, part_height, max_workers=SPLITTER_WORKERS)
            await executor.create_process_task(
                functools.partial(
                    split,
                    directory,
                    input_file,
                    width,
                    height,
                    part_width,
                    part_height,
                    max_workers=SPLITTER_WORKERS,
                    on_part=on_part,
                )
            )
        return sorted(directory.glob("part_*.webm"))
    except Exception as _:
        logger.exception("error while splitting")
        return False


async def split_static_sticker(
    directory: Path,
    input_file: Path,
    width,
    height,
    part_width,
    part_height,
    on_part=None,
):
    try:
        with ProcessTaskPoolExecutor(cancel_tasks_when_shutdown=True) as executor:

            # await split(directory, width, height, part_width, part_height, max_workers=SPLITTER_WORKERS)
            await executor.create_process_task(
                functools.partial(
                    split,
                    directory,
                    input_file,
                    width,
                    height,
                    part_width,
                    part_height,
                    max_workers=SPLITTER_WORKERS,
                    format="webp",
                    on_part=on_part,
                )
            )
        return sorted(directory.glob("part_*.webp"))
    except Exception as _:
        logger.exception("error while splitting")
        return False
