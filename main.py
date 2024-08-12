from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command,CommandStart
from aiogram import types
from dotenv import load_dotenv
import os
import asyncio

from functions.chatgpt_functions import register_handlers_chatgpt
from functions.dalle_functions import register_handlers_dalle
from functions.analysis_function import register_handlers_analysis

# Load environment variables from .env file
load_dotenv()

bot = Bot(os.getenv('BOT_TOKEN2'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def get_me():
    getme = await bot.get_me()
    botusername = getme.username
    print('Bot was launched, it is username of bot: ', botusername)
    print("BOT_TOKEN:", os.getenv('BOT_TOKEN2'))
    print("TICKER:", os.getenv('TICKER'))
    print("EMOJI:", os.getenv('EMOJI'))
    return botusername

register_handlers_chatgpt(dp, bot)
register_handlers_dalle(dp, bot)
register_handlers_analysis(dp, bot)

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.reply(f"<b>You've found me, step into the world of {os.getenv('TICKER')} {os.getenv('EMOJI')}</b>\n\n"
                        f"Respond with /t to talk to me.\n\n"
                        f"Respond with /i to visualize with me.\n\n"
                        f"Respond with /a to analyze any image ever.", parse_mode='HTML')

async def on_startup(dp):
    await get_me()

async def main():
    try:
        await get_me()
        await dp.start_polling(bot)
    except Exception as e :
        print("Error:" e)



if __name__ == "__main__":
    asyncio.run(main())
