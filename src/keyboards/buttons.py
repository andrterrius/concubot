from aiogram.types import *

otmena_button = KeyboardButton('Отмена')
back_button = KeyboardButton('Назад')
get_post_button = KeyboardButton('Посмотреть пост')

back_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True).add(back_button)
otmena_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True).add(otmena_button)
omtmena_and_back_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
omtmena_and_back_keyboard.row(back_button, otmena_button)

omtmena_and_back_add_channel_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
omtmena_and_back_add_channel_keyboard.row(
        KeyboardButton(text="Выбрать канал",
            request_chat=KeyboardButtonRequestChat(
                request_id=1,
                chat_is_channel=True,
            )),
        KeyboardButton(text="Выбрать группу",
                                request_chat=KeyboardButtonRequestChat(
                                    request_id=2,
                                    chat_is_channel=False,
        ))
)
omtmena_and_back_add_channel_keyboard.row(back_button, otmena_button)

how_complite_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
how_complite_keyboard\
    .row(KeyboardButton(text="Завершить по времени"), KeyboardButton(text="Завершить вручную"))\
    .row(KeyboardButton(text="Запланированная публикация"))\
    .row(KeyboardButton(text="Назад"), otmena_button)

create_button = KeyboardButton('Создать конкурс')
channels_button = KeyboardButton('Каналы')
concurs_button = KeyboardButton('Конкурсы')
settings_button = KeyboardButton('Настройки')
statistic_button = KeyboardButton('Статистика')

back_concurses = InlineKeyboardMarkup()
back_concurses.add(InlineKeyboardButton(text="Назад", callback_data="back_check_concurses"))
create_concurs = InlineKeyboardMarkup()
create_concurs.add(InlineKeyboardButton(text="Создать конкурс", callback_data="create_concurs"))
back_channels = InlineKeyboardMarkup()
back_channels.add(InlineKeyboardButton(text="Назад", callback_data="back_channels"))
otmena_captcha = InlineKeyboardMarkup()
otmena_captcha.add(InlineKeyboardButton(text="Отмена", callback_data="otmena_captcha"))

menu = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
menu.row(create_button, channels_button)
menu.row(concurs_button, settings_button)
menu.add(statistic_button)


names_button = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
names_button.row(KeyboardButton('Участвовать'), KeyboardButton('Участвую'), KeyboardButton('❤'))
names_button.row(back_button, otmena_button)

need_sub_news = InlineKeyboardMarkup()
need_sub_news.add(InlineKeyboardButton(text="Подписаться", url="https://t.me/concubot_news"))
need_sub_news.add(InlineKeyboardButton(text="Проверить", callback_data="create_concurs"))