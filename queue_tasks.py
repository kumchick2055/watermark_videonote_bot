from aiogram import Bot
from arq.connections import RedisSettings
from config import BOT_TOKEN, QUEUE_NAME
import os
from uuid import uuid4
from aiogram.types import FSInputFile
import subprocess
import asyncio
import json


REDIS_SETTINGS = RedisSettings()


async def get_gif_dimensions(gif_file):
    command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', gif_file]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    info = json.loads(stdout)
    width = info['streams'][0]['width']
    height = info['streams'][0]['height']
    return width, height


async def run_ffmpeg(input_video, overlay_image, output_video, width, height):
    command = [
        'ffmpeg',
        '-i', input_video,
        '-ignore_loop', '0',
        '-i', overlay_image,
        '-filter_complex', f"[1:v]scale=w=iw:h=ih[fg];[0:v]scale=w={width}:h={height}[bg];[fg]chromakey=0x00ff22:0.3:0.0[ck];[bg][ck]overlay=0:0:shortest=1,format=yuv420p",
        '-c:v', 'libx264',
        '-crf', '18',
        '-preset', 'slow',
        '-c:a', 'aac',
        '-b:a', '192k',
        output_video
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        print(f"Successfully created {output_video}")
    else:
        print(f"Error occurred: {stderr.decode()}")



async def edit_video_note(ctx, user_id: int, file_path_dc: str):
    bot: Bot = ctx['bot']
    file_path_tmp = f'./tmp_storage/{str(uuid4())}.mp4'
    await bot.download_file(file_path_dc, file_path_tmp)
    complete_file_path = f'./tmp_storage/{str(uuid4())}.mp4'
    width, height = await get_gif_dimensions('./overlay.gif')

    await run_ffmpeg(file_path_tmp, './overlay.gif', complete_file_path, width, height)

    print(complete_file_path)
    try:
        await bot.send_video_note(user_id, FSInputFile(complete_file_path))
    except Exception as ex:
        print(ex)
        await bot.send_message(user_id, 'Не удалось отправить видео')
    finally:
        os.remove(file_path_tmp)
        os.remove(complete_file_path)



async def startup(ctx):
    bot = Bot(BOT_TOKEN)
    ctx['bot'] = bot 
    

async def shutdown(ctx):
    await ctx['bot'].close()


class WorkerSettings:
    functions = [
        edit_video_note
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = REDIS_SETTINGS
    queue_name = QUEUE_NAME
