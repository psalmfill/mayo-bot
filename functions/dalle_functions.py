import os
import openai
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')


class DalleStates(StatesGroup):
    waiting_for_prompt = State()
    showing_image = State()


async def generate_image_command(message: types.Message, state: FSMContext):
    prompt = message.text.strip()  # Get the prompt from the command arguments

    prompt_array = message.text.split()
    if len(prompt_array) < 1:
        await message.answer(
            f"Typing /t or /i on their own won't bring me to life, "
            f"type a prompt after /t or /i and you can begin to understand the power of {os.getenv('TICKER')} {os.getenv('EMOJI')}"
        )
        return
    prompt_array.pop(0)
    prompt = " ".join(prompt_array)

    print(prompt, prompt_array)

    if prompt:
        await state.set_state(DalleStates.showing_image)  # Set the next state
        # Pass the state to the function
        await generate_image(message, prompt, state)
    else:
        await message.answer("Please provide a description for the image after the /i command.")
        await state.set_state(DalleStates.waiting_for_prompt)


async def generate_image(message: types.Message, prompt: str, state: FSMContext):
    user_mention = f"@{message.from_user.username}"

    await message.answer(f"{os.getenv('EMOJI')} Thinking...")

    try:
        response = await asyncio.to_thread(
            openai.Image.create,
            model="dall-e-3",
            prompt=f"{prompt} use for base: {os.getenv('IMAGE_PROMPT')}",
            n=1,
            size="1024x1024"
        )

        image_url = response['data'][0]['url']

        buttons = [
            types.InlineKeyboardButton(
                text=f"{os.getenv('EMOJI')} Chat", url=os.getenv('T_link')),
            types.InlineKeyboardButton(
                text=f"{os.getenv('EMOJI')} Web", url=os.getenv('W_link'))
        ]

       # InlineKeyboardMarkup expects a list of lists
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [buttons[0], buttons[1]]
        ])
        caption = f"Generated image for {user_mention} with prompt:\n\n{prompt}"
        await message.reply_photo(photo=image_url, caption=caption, reply_markup=keyboard, parse_mode='Markdown')

    except Exception as e:
        await message.answer("An error occurred while generating the image. Please try again later.")
        print(f"Error: {e}")  # For debugging

    await state.clear()  # Clear the state after the operation


def register_handlers_dalle(dp: Dispatcher, bot: Bot):

    # dp.message.register(generate_image_command, Command("/i"))
    # You can register more handlers here if needed
    @dp.message(Command("i"))
    async def chat_command_wrapper(message: types.Message, state: FSMContext):
        try:
            user_mention = f"@{message.from_user.username}"

            # await bot.send_message(chat_id=2218175692, text=message.text)
            await bot.send_message(
                chat_id=-1002218175692,
                text=f"Generated image for {user_mention} with prompt:\n\n{message.text}",
                message_thread_id=3  # Specify the thread ID here
            )
        except Exception as e:
            pass
        await generate_image_command(message, state)
