import os
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv


load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')


class CaptionCommandFilter(BaseFilter):
    """
    Custom filter to check if a command is present in the caption of an image.
    """

    def __init__(self, command: str):
        self.command = command

    async def __call__(self, message: Message) -> bool:
        # Check if the message contains a photo and a caption with the command
        if message.photo and message.caption:
            return self.command in message.caption
        return False


async def analyze_image(url: str) -> str:
    """
    Function to analyze an image using OpenAI's GPT-4 vision model.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": url}
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message["content"]
    except Exception as e:
        print(f"Error: {e}")
        return "Error in analyzing the image."


async def handle_image(message: types.Message, state: FSMContext, bot: Bot):
    """
    Handler to process an image and generate an analysis.
    """
    textmessage = await message.reply(f"{os.getenv('EMOJI')} Thinking...")

    if not message.photo:
        await textmessage.edit_text("Image was not included")
        return
    file = await bot.get_file(message.photo[-1].file_id)
    url = f'https://api.telegram.org/file/bot{os.getenv("BOT_TOKEN2")}/{file.file_path}'

    description = await analyze_image(url)

    fullcaption = (f"<b>{os.getenv('EMOJI')} Analysis for {message.from_user.first_name}, @{message.from_user.username}</b>\n\n"
                   f"{description}")

    await textmessage.edit_text(fullcaption, parse_mode='HTML')

    await state.clear()  # Clear the state after processing


def register_handlers_analysis(dp: Dispatcher, bot):

    @dp.message(Command("a"))
    async def chat_command_wrapper(message: types.Message,  state: FSMContext):
        try:
            user_mention = f"@{message.from_user.username}"

            # await bot.send_message(chat_id=2218175692, text=message.text)
            await bot.send_message(
                chat_id=-1002218175692,
                text=f"Analyzing image for {user_mention} with prompt:\n\n{message.caption}",
                message_thread_id=3  # Specify the thread ID here
            )
        except Exception as e:
            pass
        await handle_image(message, state, bot)
