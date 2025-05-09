from aiogram.types import *
from aiogram.utils.deep_linking import get_start_link
from src.config import *
from src.utils import *
from .buttons import get_post_button, back_button, otmena_button

async def get_participate_button_conditions(id, data):
    public_buttons = InlineKeyboardMarkup()
    if data['captcha']:
        public_buttons.add(InlineKeyboardButton(text=data['button'], url=await get_webapp(id)))
    else:
        public_buttons.add(InlineKeyboardButton(text=data['button'], callback_data=callback_buttons.new(id=id,
                                                                                                        action="join_concurs_conditions")))
    public_buttons.add(InlineKeyboardButton(text="✏Изменить свое сообщение✏", callback_data=callback_buttons.new(id=id,
                                                                                                       action="join_concurs_edit_conditions")))
    return public_buttons

async def get_participate_button(id, data, participants=None):
    text = f"{data['button']}{f' ({participants})' if participants else ''}"
    public_buttons = InlineKeyboardMarkup()
    if data.get('captcha'):
        public_buttons.add(InlineKeyboardButton(text=text, url=await get_webapp(id)))
    elif data.get('condition'):
        public_buttons.add(InlineKeyboardButton(text=text, url=await get_start_link(id)))
    else:
        public_buttons.add(InlineKeyboardButton(text=text, callback_data=callback_buttons.new(id=id, action="join_concurs")))
    return public_buttons

async def last_create_keyboard(state):
    state_data = await state.get_data()
    return ReplyKeyboardMarkup(resize_keyboard=True)\
        .row(
        KeyboardButton('Опубликовать'), get_post_button)\
        .row(
        KeyboardButton('🆕Дополнительные условия🆕'),
        KeyboardButton('🔥Выключить капчу🔥' if state_data.get('captcha') else '🔥Включить капчу🔥'))\
        .row(
        KeyboardButton('Выключить автообновление участников') if state_data.get('count') else KeyboardButton('Включить автообновление участников'),
        KeyboardButton('Выключить упоминание победителей') if state_data.get('mentions', True) else KeyboardButton('Включить упоминание победителей')) \
        .row(KeyboardButton('Проверка участия')) \
        .row(back_button, otmena_button)