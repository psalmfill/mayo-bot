from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command
from dotenv import load_dotenv

from openai import OpenAI
import asyncio
import os
import io
import requests
from PIL import Image, ImageDraw

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


class DalleStates(StatesGroup):
    waiting_for_prompt = State()
    showing_image = State()
    waiting_for_edit_prompt = State()
    choosing_square = State()


async def generate_image_command(message: types.Message, state: FSMContext):
    prompt = message.get_full_command()[1].strip()

    if prompt:
        await generate_image(message, prompt, state)
    else:
        await message.answer("Please provide a description for the image after the /i command.")


async def generate_image(message: types.Message, prompt: str, state: FSMContext):
    user_id = str(message.from_user.id)
    user_mention = f"@{message.from_user.username}"

    await message.answer(f"{os.getenv('EMOJI')} Thinking..")

    try:
        image_response = await asyncio.to_thread(
            client.images.generate,
            model="dall-e-3",
            prompt=f"{prompt} use for base: {os.getenv('IMAGE_PROMPT')}",
            size="1024x1024",
            user=user_id  # добавлен user_id как строка
        )

        image_url = image_response.data[0].url

        # Save image URL in FSMContext
        async with state.proxy() as data:
            data['image_url'] = image_url
        print(f"Stored image URL in FSMContext: {image_url}")  # Debug statement

        buttons = [
            types.InlineKeyboardButton(f"{os.getenv('EMOJI')} Chat", url=os.getenv('T_link')),
            types.InlineKeyboardButton(f"{os.getenv('EMOJI')} Web", url=os.getenv('W_link')),
            types.InlineKeyboardButton("Edit", callback_data=f"edit:{message.message_id}:{user_id}")
        ]

        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(*buttons)

        caption = f"Generated image for {user_mention} with prompt:\n\n{prompt}"
        await message.reply_photo(photo=image_url, caption=caption, reply_markup=keyboard, parse_mode='Markdown')

    except Exception as e:
        await message.answer(f"An error occurred: {e}")
        return

    await DalleStates.showing_image.set()


async def edit_image_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Please provide a description for the edit:")
    await DalleStates.waiting_for_edit_prompt.set()
    async with state.proxy() as data:
        data['message_id'] = callback_query.message.message_id
        data['user_id'] = str(callback_query.from_user.id)  # добавлен user_id как строка


async def handle_edit_prompt(message: types.Message, state: FSMContext):
    edit_prompt = message.text.strip()
    async with state.proxy() as data:
        data['edit_prompt'] = edit_prompt

    async with state.proxy() as data:
        image_url = data.get('image_url')

    response = requests.get(image_url)
    image_data = io.BytesIO(response.content)
    image = Image.open(image_data).convert("RGBA")
    await message.answer("Please wait ⏳")  # Added wait message

    # Draw grid lines on the image
    draw = ImageDraw.Draw(image)
    square_size = 341
    for i in range(1, 3):
        draw.line((i * square_size, 0, i * square_size, image.size[1]), fill="red", width=3)
        draw.line((0, i * square_size, image.size[0], i * square_size), fill="red", width=3)

    # Convert the image with grid to bytes
    grid_image_bytes = io.BytesIO()
    image.save(grid_image_bytes, format='PNG')
    grid_image_bytes.seek(0)

    await message.answer_photo(photo=grid_image_bytes, caption="Choose the square to edit:")

    # Create buttons for choosing the square
    buttons = [
        types.InlineKeyboardButton(f"Square {i + 1}", callback_data=f"square_{i}")
        for i in range(9)
    ]
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(*buttons)

    await message.answer("Choose the square to edit:", reply_markup=keyboard)
    await DalleStates.choosing_square.set()


async def choose_square(callback_query: types.CallbackQuery, state: FSMContext):
    square_index = int(callback_query.data.split("_")[1])
    async with state.proxy() as data:
        data['square_index'] = square_index

    await edit_image(callback_query.message, state)
    await callback_query.answer()


async def edit_image(message: types.Message, state: FSMContext):
    await message.answer(f"{os.getenv('EMOJI')} Editing image...")

    try:
        async with state.proxy() as data:
            image_url = data.get('image_url')
            edit_prompt = data.get('edit_prompt')
            square_index = data.get('square_index')
            user_id = data.get('user_id')  # добавлен user_id как строка
        print(f"Retrieved image URL from FSMContext: {image_url}")  # Debug statement
        print(f"Square index: {square_index}")  # Debug statement

        if not image_url:
            await message.answer("Original image not found.")
            return

        response = requests.get(image_url)
        image_data = io.BytesIO(response.content)

        # Open the image and create a mask for the chosen square
        image = Image.open(image_data).convert("RGBA")
        mask = Image.new("L", image.size, 255)
        draw = ImageDraw.Draw(mask)

        # Calculate the coordinates of the chosen square
        square_size = (341, 341)
        row, col = divmod(square_index, 3)
        top_left = (col * square_size[0], row * square_size[1])
        bottom_right = (top_left[0] + square_size[0], top_left[1] + square_size[1])
        draw.rectangle([top_left, bottom_right], fill=0)

        # Convert images to bytes
        image_bytes = io.BytesIO()
        mask_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        mask.save(mask_bytes, format='PNG')
        image_bytes.seek(0)
        mask_bytes.seek(0)

        image_response = await asyncio.to_thread(
            client.images.edit,
            model="dall-e-2",
            image=image_bytes,
            mask=mask_bytes,
            prompt=edit_prompt,
            n=1,
            size="1024x1024",
            user=user_id  # добавлен user_id как строка
        )

        edited_image_url = image_response.data[0].url
        print(f"Edited image URL: {edited_image_url}")  # Debug statement

        # Download edited image
        edited_response = requests.get(edited_image_url)
        edited_image_data = io.BytesIO(edited_response.content)
        edited_image = Image.open(edited_image_data).convert("RGBA")

        # Paste the edited square back into the original image
        image.paste(edited_image.crop((top_left[0], top_left[1], bottom_right[0], bottom_right[1])), top_left)

        # Save the final image
        final_image_bytes = io.BytesIO()
        image.save(final_image_bytes, format='PNG')
        final_image_bytes.seek(0)

        await message.reply_photo(photo=final_image_bytes, caption=f"Edited image with prompt:\n\n{edit_prompt}")

        # Clean up the FSMContext after editing
        async with state.proxy() as data:
            del data['image_url']
            del data['edit_prompt']
            del data['square_index']
            del data['user_id']  # удаление user_id
        print(f"Deleted original image URL from FSMContext")  # Debug statement

    except Exception as e:
        await message.answer(f"An error occurred during editing: {e}")
        return

    await DalleStates.showing_image.set()


def register_handlers_dalle(dp):
    dp.register_message_handler(generate_image_command, Command("i"), state="*")
    dp.register_callback_query_handler(edit_image_callback_handler, lambda c: c.data and c.data.startswith('edit'),
                                       state=DalleStates.showing_image)
    dp.register_message_handler(handle_edit_prompt, state=DalleStates.waiting_for_edit_prompt)
    dp.register_callback_query_handler(choose_square, lambda c: c.data.startswith("square_"),
                                       state=DalleStates.choosing_square)
