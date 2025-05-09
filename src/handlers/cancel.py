from aiogram.dispatcher import FSMContext
from src.config import *
from src.keyboards import *
from src.states import *
from src.utils import *

@dp.message_handler(state=AddChannel.input_channel, text="Отмена")
async def cancel_function_channel(message, state: FSMContext):
    await state.finish()
    await message.answer(start_text, reply_markup=menu)
    await get_channels(message.from_user.id)

@dp.message_handler(state='*', text="Отмена")
async def cancel_function(message, state: FSMContext):
    await state.finish()
    await message.answer(start_text, reply_markup=menu)