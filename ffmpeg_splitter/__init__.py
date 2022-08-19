import math
import functools
import asyncio
from pathlib import Path
import ffmpeg
from asynccpu import ProcessTaskPoolExecutor
from asyncffmpeg import FFmpegCoroutineFactory, StreamSpec


async def split_part_spec(
    input_file,
    output_file,
    part_n,
    width,
    height,
    part_width,
    part_height,
    title="created by turniptgs",
) -> StreamSpec:
    y = math.floor(part_n / width)
    x = part_n % width
    args = (
        ffmpeg.input(input_file)
        .filter(
            "crop",
            w=f"iw/{width}",
            # h=f"ih/{height}",
            h=f"iw/{width}",
            x=f"{x}*iw/{width}",
            y=f"{y}*ih/{height}",
            keep_aspect="0",
            exact="1",
        )
        .filter(
            "scale",
            w=part_width,
            h="-1",
            eval="init",
            flags="bicubic",
            interl=0,
        )
        .output(
            output_file,
            **{
                "metadata": f"title={title}"
                # "deadline": "realtime",
                # "c:v": "libvpx-vp9",
                # "b:v": "0",
                # "crf": "10"
            },
        )
    )
    return args


async def _split_part(
    ffmpeg_coroutine,
    input_file,
    output_file,
    part_n,
    total_parts,
    width,
    height,
    part_width,
    part_height,
    on_part,
):
    if on_part:
        await on_part(part_n, total_parts)
    spec = functools.partial(
        split_part_spec,
        input_file,
        output_file,
        part_n,
        width,
        height,
        part_width,
        part_height,
    )
    await ffmpeg_coroutine.execute(spec)


async def split(
    directory: Path,
    input_file: Path,
    width,
    height,
    part_width,
    part_height,
    max_workers=3,
    format="webm",
    on_part=None,
):
    ffmpeg_coroutine = FFmpegCoroutineFactory.create()
    parts = sorted(directory.glob(f"part_*.{format}"))
    last_part = int(parts[-1].stem.split("part_")[-1]) if parts else -1
    with ProcessTaskPoolExecutor(
        max_workers=max_workers, cancel_tasks_when_shutdown=True
    ) as executor:
        awaitables = (
            executor.create_process_task(
                _split_part,
                ffmpeg_coroutine,
                str(input_file.absolute()),
                str(directory / f"part_{part_n:03}.{format}"),
                part_n,
                width * height - (last_part + 1),
                width,
                height,
                part_width,
                part_height,
                on_part,
            )
            for part_n in range(last_part + 1, width * height)
        )
        await asyncio.gather(*awaitables)
