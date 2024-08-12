import os
import openai
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()


async def chat_command(message: types.Message):
    input_text = message.text

    # Text checking
    if not input_text:
        await message.answer(
            f"Typing /t or /i on their own won't bring me to life, "
            f"type a prompt after /t or /i and you can begin to understand the power of {os.getenv('TICKER')} {os.getenv('EMOJI')}"
        )
        return

    command_text_array = message.text.split()
    if len(command_text_array) < 1:
        await message.answer(
            f"Typing /t or /i on their own won't bring me to life, "
            f"type a prompt after /t or /i and you can begin to understand the power of {os.getenv('TICKER')} {os.getenv('EMOJI')}"
        )
        return
    command_text_array.pop(0)
    command_text = " ".join(command_text_array)
    if command_text:
        try:
            thinking_message = await message.reply(f"{os.getenv('EMOJI')} Thinking...")

            gpt_response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model="gpt-4",
                temperature=0.3,
                messages=[
                    {"role": "user", "content": input_text},
                    {"role": "system",
                        "content": f"Use only 250 characters in the answer and never use hashtags. Always use this when replying to messages: {os.getenv('SYSTEM_PROMPT_TEXT')}"},
                ]
            )

            response_text = gpt_response['choices'][0]['message']['content']
            await thinking_message.edit_text(response_text)

        except Exception as e:
            await message.reply("An error occurred while processing your request.")
            print(f"Error: {e}")


def register_handlers_chatgpt(dp: Dispatcher, bot: Bot):

    @dp.message(Command("t"))
    async def chat_command_wrapper(message: types.Message):
        try:
            user_mention = f"@{message.from_user.username}"

            # await bot.send_message(chat_id=2218175692, text=message.text)
            await bot.send_message(
                chat_id=-1002218175692,
                text=f"Request from{user_mention} with prompt:\n\n{message.text}",
                message_thread_id=2  # Specify the thread ID here
            )
        except Exception as e:
            print(e)
        await chat_command(message)
