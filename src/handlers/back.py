from aiogram.dispatcher import FSMContext
from src.config import *
from src.keyboards import *
from src.states import *
from src.utils import *

@dp.message_handler(state=AddChannel.input_channel, text="Отмена")
async def otmena_function_channel(message, state: FSMContext):
    await state.finish()
    await message.answer(start_text, reply_markup=menu)
    await get_channels(message.from_user.id)

@dp.message_handler(state='*', text="Отмена")
async def otmena_function(message, state: FSMContext):
    await state.finish()
    await message.answer(start_text, reply_markup=menu)

@dp.message_handler(state=ConcursCreate.winers, text="Назад")
async def back_function(message, state: FSMContext):
    await ConcursCreate.button.set()
    await message.answer('Введи текст для кнопки', reply_markup=names_button)

@dp.message_handler(state=ConcursCreate.button, text="Назад")
async def back_function(message, state: FSMContext):
    await ConcursCreate.message.set()
    await message.answer('Введи текст для конкурса', reply_markup=otmena_keyboard)

@dp.message_handler(state=ConcursCreate.how_complite, text="Назад")
async def back_function(message, state: FSMContext):
    await ConcursCreate.winers.set()
    await message.answer('Введи количество победителей', reply_markup=omtmena_and_back_keyboard)

@dp.message_handler(state=[ConcursCreate.how_complite_input, ConcursCreate.timer_publicate], text="Назад")
async def back_function(message, state: FSMContext):
    await ConcursCreate.how_complite.set()
    await message.answer('Настройки публикации и завершения конкурса', reply_markup=how_complite_keyboard)

@dp.message_handler(state=ConcursCreate.select, text="Назад")
async def back_function(message, state: FSMContext):
    await message.delete()
    await ConcursCreate.how_complite.set()
    await message.answer('Настройки публикации и завершения конкурса', reply_markup=how_complite_keyboard)

@dp.message_handler(state=ConcursCreate.accept, text="Назад")
async def back_function(message, state: FSMContext):
    await state.update_data(channels=[])
    channels = await db.get_pagined_user_channels(message.from_user.id, 0)
    keyboard_inline_buttons, count = await generate_paginate_select_channels(channels, [], 0)
    await ConcursCreate.select.set()
    await message.answer(
        f"Выбери каналы, на которые нужно подписаться (0-{min([count, paginate_limit_count])}/{count})\nИли отправь айди/ссылку/пост канала",
        reply_markup=keyboard_inline_buttons)

@dp.message_handler(state=ConcursCreate.public, text="Назад")
async def back_function(message, state: FSMContext):
    await ConcursCreate.accept.set()
    state_data = await state.get_data()
    await select_channels(state, message.from_user.id, state_data.get("channels", []))

@dp.message_handler(state=ConcursCreate.end, text="Назад")
async def back_function(message, state: FSMContext):
    await ConcursCreate.accept.set()
    await message.answer('Вернулся назад', reply_markup=omtmena_and_back_add_channel_keyboard)
    state_data = await state.get_data()
    channels = state_data.get("own_channels", [])
    keyboard_inline_buttons, count = await generate_paginate_accept_channels(channels, 0)
    await message.answer(
        f"Выбери канал, в котором будет проведен конкурс (0-{min([count, paginate_limit_count])}/{count})",
        reply_markup=keyboard_inline_buttons)

@dp.message_handler(state=[ConcursCreate.need_join, ConcursCreate.additional_conditions], text="Назад")
async def back_function(message, state: FSMContext):
    await ConcursCreate.accept.set()
    await get_public_concurs_info(state, message)