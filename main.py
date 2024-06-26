import asyncio
import logging
import sys
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from config import BOT_TOKEN, QUEUE_NAME

TOKEN = BOT_TOKEN

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Привет я бот который накладывает изображение на видео кружки\nТвой ID: {html.code(message.from_user.id)}")


@dp.message(F.video_note)
async def video_note_handler(message: Message, arq: ArqRedis) -> None:
    file_id = message.video_note.file_id

    file = await bot.get_file(file_id)
    file_path_dc = file.file_path

    await arq.enqueue_job(
        'edit_video_note',
        message.from_user.id,
        file_path_dc,
        _queue_name=QUEUE_NAME
    )

    await message.answer('делаю дело...')


async def main() -> None:

    arq: ArqRedis = await create_pool(
        RedisSettings()
    )

    await dp.start_polling(
        bot,
        arq=arq
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
