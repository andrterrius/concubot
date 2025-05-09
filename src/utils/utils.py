import json
import time
import re
import datetime
from src.config import *
from src.keyboards import *
from src.states import *
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputTextMessageContent, InlineQueryResultArticle, WebAppInfo
import asyncio
import itertools

async def get_webapp(concurs):
    return f"https://t.me/{short_name}/pass?startapp={concurs}"

def get_postpone_text():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    ten_minutes = (now+datetime.timedelta(minutes=10)).strftime("%d.%m.%Y %H:%M:%S")
    hour = (now+datetime.timedelta(hours=1)).strftime("%d.%m.%Y %H:%M:%S")
    day = (now+datetime.timedelta(days=1)).strftime("%d.%m.%Y %H:%M:%S")
    week = (now+datetime.timedelta(weeks=1)).strftime("%d.%m.%Y %H:%M:%S")
    return f"Введите время в форматах, приведенных ниже:\n" \
           f"\n<code>{ten_minutes}</code> - через 10 минут\n" \
           f"<code>{hour}</code> - через час\n" \
           f"<code>{day}</code> - через день\n" \
           f"<code>{week}</code> - через неделю" \
           f"\n<b>(Московское время)</b>"

async def check_sub(uid):
    try:
        check_user = await bot.get_chat_member(chat_id=-1001734716124, user_id=uid)
        if check_user.status not in ['creator', 'administrator', 'member']:
            return False
    except Exception as e:
        return False
    return True

async def edit_message(message, text, reply_markup=None):
    if "photo" in message or "video" in message:
        return await message.edit_caption(f"<b>{text}</b>", reply_markup=reply_markup)
    return await message.edit_text(f"<b>{text}</b>", reply_markup=reply_markup)

async def check_bots_andrey(uid, botz, concurs_id):
    for bot in bots:
        if bot['name'] in botz:
            collection = cluster["refbots"][bot["db"]]
            check = await collection.find_one({"uid": uid, "succes_ref": True})
            if not check:
                otmena_captcha = InlineKeyboardMarkup()
                otmena_captcha.add(
                    InlineKeyboardButton(text="Проверить", callback_data=callback_buttons.new(id=concurs_id,
                                                                                              action="check_captcha")))
                otmena_captcha.add(InlineKeyboardButton(text="Отмена", callback_data="otmena_captcha"))
                return False, f"‼ Вы должны выполнить условия в боте {bot['link']}", otmena_captcha
    return True, None, None

async def recheck_andrey(concurs_id, uid):
    result = await db.check_participate_concurs(concurs_id, uid)
    if result:
        otmena_captcha = InlineKeyboardMarkup()
        otmena_captcha.add(InlineKeyboardButton(text="Проверить", callback_data=callback_buttons.new(id=concurs_id,
                                                                                                     action="check_captcha")))
        otmena_captcha.add(InlineKeyboardButton(text="Отмена", callback_data="otmena_captcha"))
        result = await db.get_info_concurs(concurs_id)
        if not result['active']:
            return False, "‼️Конкурс уже закончился", None
        if result['need_join']:
            check = await db.check_active_and_participate_concurs(result['need_join'], uid)
            if check:
                return False, f"‼Нужно принять участие в конкурсе №{check} ‼", otmena_captcha
        for channel in result['channels']:
            check = await bot.get_chat_member(chat_id=channel, user_id=uid)
            if check.status not in ['creator', 'administrator', 'member']:
                channel_id = await bot.get_chat(chat_id=channel)
                if channel_id['username']:
                    return False, f"<b>‼️ Подпишитесь на <a href= 't.me/{channel_id['username']}' >{re.sub('[<>]', '', channel_id['title'])}</a> и нажмите на кнопку проверить‼</b>", otmena_captcha
                else:
                    return False, f"<b>‼️ Подпишитесь на {re.sub('[<>]', '', channel_id['title'])} и нажмите на кнопку проверить‼</b>", otmena_captcha
        return True, "✅Ты теперь участвуешь✅", None, result['participants'], result['count'], result['button'], result['public_id'], result['message_id']
    else:
        return False, "⚠️Ты УЖЕ участвуешь в конкурсе⚠️", None

async def select_bots(message):
    keyboard_inline_buttons = InlineKeyboardMarkup()
    count = 0
    for bot in bots:
        try:
            keyboard_inline_buttons.add(InlineKeyboardButton(text=bot['name'], callback_data=f"add_bot_{count} {bot['name']}"))
            count += 1
        except Exception as e:
            pass
    await message.answer('Выбери ботов для проверки', reply_markup=keyboard_inline_buttons.add(InlineKeyboardButton(text="Готово", callback_data="confirm_bots")))


async def inline_share(query):
    articles = [InlineQueryResultArticle(
        id=1,
        title="Поделиться ссылкой на бота",
        input_message_content=InputTextMessageContent(
            message_text=f"Бесплатный бот для создания розыгрышей без ограничений! Защита от ботов, проверка на random.org и многое другое вы найдете тут -  @concubot",
            )
        )]
    return await query.answer(articles, cache_time=1)
async def registration(user, message, quite=False):
    if await db.save_user(user, time.asctime()):
        if not quite:
            await message.answer(start_text, reply_markup=menu)
        await bot.send_message(admin,
                               f"В боте новый пользователь <b>{await get_users([user], user)}</b>")
    elif not quite:
        await message.answer(start_text, reply_markup=menu)

async def get_public_concurs_info(state, message):
    await ConcursCreate.end.set()
    state_data = await state.get_data()
    public_id = await message.bot.get_chat(chat_id=state_data['public'])
    complite = f"\nКонкурс будет завершен <b>{state_data['time_complite_str']}</b>"
    if state_data['channels']:
        channels_text = "\nПроверка подписки в каналах:"
        try:
            for channel in state_data['channels']:
                channel_id = await message.bot.get_chat(chat_id=channel)
                channels_text += f"<b>\n📢{re.sub('[<>]', '', channel_id['title'])}</b>"
        except:
            pass
    else:
        channels_text = ""
    if state_data.get('need_join'):
        needjoin_text = f"\nПроверка участия в конкурсах: {str(state_data['need_join']).strip('[]')}"
    else:
        needjoin_text = ""
    time_published = ""
    if state_data.get('time_publicate_str'):
        time_published = f"\nКонкурс будет опубликован <b>{state_data['time_publicate_str']}</b>"
    additional_conditions_text = ""
    if state_data.get("condition"):
        additional_conditions_text = "\nДополнительные условия включены ✅"
    mesg_text = f"Информация о конкурсе:\nПобедителей: <b><i>{state_data['winners']}</i></b>{complite}{time_published}{channels_text}{needjoin_text}\nПубликуем в канале: <b>{re.sub('[<>]', '', public_id['title'])}{additional_conditions_text}</b>"
    await message.answer(mesg_text, reply_markup=await last_create_keyboard(state))



async def get_channels(user_id, message=None, offset=0):
    channels = await db.get_pagined_user_channels(user_id)
    keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
    if channels:
        count = channels[0]['count']
        for channel in channels:
            channel = json.loads(channel['channels'])
            keyboard_inline_buttons.insert(InlineKeyboardButton(text=re.sub('[<>]', '', channel['title']), callback_data=callback_buttons.new(id=f'{channel["id"]} {offset}', action="settings_channel")))
        if count > paginate_limit_count:
            keyboard_inline_buttons.add(InlineKeyboardButton(text="➡", callback_data=paginate_buttons.new(offset=paginate_limit_count, action="get_paginate_channels")))
            if count >= paginate_limit_count*2:
                keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(offset=count+(paginate_limit_count-count%paginate_limit_count)-paginate_limit_count, action="get_paginate_channels")))
        keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал", callback_data=paginate_buttons.new(offset=offset, action="add_channel")))
        if message:
            await message.edit_text(
                f"Добавленные каналы ({offset}-{min([count, paginate_limit_count])}/{count})",
                reply_markup=keyboard_inline_buttons)
        else:
            await bot.send_message(user_id, f"Добавленные каналы (0-{min([count, paginate_limit_count])}/{count}) ", reply_markup=keyboard_inline_buttons)
    else:
        keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал", callback_data=paginate_buttons.new(offset=offset, action="add_channel")))
        if message:
            await message.edit_text('Каналов еще нет', reply_markup=keyboard_inline_buttons)
        else:
            await bot.send_message(user_id, 'Каналов еще нет', reply_markup=keyboard_inline_buttons)

async def generate_paginate_channels(channels, offset):
    keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
    count = channels[0]['count']
    for channel in channels:
        channel = json.loads(channel['channels'])
        keyboard_inline_buttons.insert(InlineKeyboardButton(text=re.sub('[<>]', '', channel['title']), callback_data=callback_buttons.new(
            id=f'{channel["id"]} {offset}', action="settings_channel")))
    if count > paginate_limit_count:
        if offset - paginate_limit_count >= 0:
            keyboard_inline_buttons.add(InlineKeyboardButton(text="⬅", callback_data=paginate_buttons.new(
                offset=offset - paginate_limit_count, action="get_paginate_channels")))
        if count > offset + paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="➡", callback_data=paginate_buttons.new(
                offset=offset + paginate_limit_count, action="get_paginate_channels")))
            if offset >= paginate_limit_count:
                keyboard_inline_buttons.add(InlineKeyboardButton(text="⏪", callback_data=paginate_buttons.new(offset=0,
                                                                                                              action="get_paginate_channels")))
                if count >= offset + paginate_limit_count * 2:
                    keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(
                        offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count,
                        action="get_paginate_channels")))
            elif count >= offset + paginate_limit_count * 2:
                keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(
                    offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count,
                    action="get_paginate_channels")))
        elif offset >= paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏪", callback_data=paginate_buttons.new(offset=0,
                                                                                                             action="get_paginate_channels")))
    keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал",
                                                     callback_data=paginate_buttons.new(offset=offset,
                                                                                        action="add_channel")))
    return keyboard_inline_buttons, count

async def check_channel(channel, user, state, back_channels, offset=0, just=True):
    try:
        chnl = await bot.get_chat_member(chat_id=channel, user_id=bot_id)
        if chnl.status == "administrator" and (chnl.can_post_messages or chnl.can_manage_chat):
            channel_id = await bot.get_chat(chat_id=channel)
            channels = await db.get_user_channels(user)
            title = re.sub('[<>]', '', channel_id['title'])
            readd = False
            for channel in channels:
                if channel_id["id"] == channel["id"]:
                    chnnls = [{'id': channel_id['id'], 'title': channel['title']}]
                    for chnnl in channels:
                        if chnnl['id'] != channel_id["id"]:
                            chnnls.append({'id': chnnl['id'], 'title': chnnl['title']})
                    await db.update_channels(json.dumps(chnnls), user)
                    readd = True
            if not readd:
                if channels:
                    await db.add_channel(json.dumps([{"id": channel_id["id"], "title": title}] + channels), user)
                else:
                    await db.add_channel(
                        json.dumps([{"id": channel_id["id"], "title": title}]), user)
            if "username" in channel_id:
                await bot.send_message(admin, f"<b>{await get_users([user], user)}</b> добавил @{channel_id['username']}", disable_web_page_preview=True)
            else:
                await bot.send_message(admin,
                                       f"<b>{await get_users([user], user)}</b> добавил {title}")
            if just:
                await bot.send_message(user, 'Канал успешно добавлен!', reply_markup=menu)
                await state.finish()
                channels = await db.get_pagined_user_channels(user, offset)
                keyboard_inline_buttons, count = await generate_paginate_channels(channels, offset)
                await bot.send_message(user, f"Добавленные каналы ({offset}-{count}/{count})",
                                             reply_markup=keyboard_inline_buttons)
            else:
                return channel_id['id']
        else:
            if just:
                back_channels2 = InlineKeyboardMarkup()
                back_channels2.add(InlineKeyboardButton(text="Дать админку в канале",
                                                        url="tg://resolve?domain=concubot&startchannel&admin=post_messages+invite_users"))
                back_channels2.add(InlineKeyboardButton(text="Дать админку в группе",
                                                        url="tg://resolve?domain=concubot&startgroup&admin=post_messages+invite_users"))
                await bot.send_message(user, '❌У бота нет админки', reply_markup=back_channels2)
            else:
                await bot.send_message(user, '❌У бота нет админки')
    except Exception as e:
        if str(e) in ["Forbidden: bot is not a member of the channel chat", "Member list is inaccessible", "Chat not found"]:
            if just:
                back_channels2 = InlineKeyboardMarkup()
                back_channels2.add(InlineKeyboardButton(text="Дать админку в канале",
                                                        url="tg://resolve?domain=concubot&startchannel&admin=post_messages+invite_users"))
                back_channels2.add(InlineKeyboardButton(text="Дать админку в группе",
                                                        url="tg://resolve?domain=concubot&startgroup&admin=post_messages+invite_users"))
                await bot.send_message(user, '❌У бота нет админки', reply_markup=back_channels2)
            else:
                await bot.send_message(user, '❌У бота нет админки')
        else:
            if just:
                await bot.send_message(user, '❌Канала не существует', reply_markup=back_channels)
            else:
                await bot.send_message(user, '❌Канала не существует')
        await bot.send_message(admin, f"{e} {e == 'Forbidden: bot is not a member of the channel chat'} {user}")

async def get_paginate_concurses(concurses, count, offset=0):
    keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
    for concurs in concurses:
        keyboard_inline_buttons.insert(InlineKeyboardButton(text=f"Конкурс №{concurs['id']}", callback_data=callback_buttons.new(id=f"{concurs['id']} {offset}", action="check_concurs")))
    if count > paginate_limit_count:
        if offset - paginate_limit_count >= 0:
            keyboard_inline_buttons.add(InlineKeyboardButton(text="⬅", callback_data=paginate_buttons.new(
                offset=offset - paginate_limit_count, action="get_paginate_concurses")))
        if count > offset + paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="➡", callback_data=paginate_buttons.new(
                offset=offset + paginate_limit_count, action="get_paginate_concurses")))
            if offset >= paginate_limit_count:
                keyboard_inline_buttons.add(InlineKeyboardButton(text="⏪", callback_data=paginate_buttons.new(offset=0, action="get_paginate_concurses")))
                if count >= offset + paginate_limit_count * 2:
                    keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(
                        offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count,
                        action="get_paginate_concurses")))
            elif count >= offset + paginate_limit_count * 2:
                keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(
                    offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count,
                    action="get_paginate_concurses")))
        elif offset >= paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏪", callback_data=paginate_buttons.new(offset=0, action="get_paginate_concurses")))
    return keyboard_inline_buttons, count

async def get_paginate_winners(id, offset=0):
    keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
    winners, count = await db.get_pagined_winners(id, offset)
    for winner in winners:
        keyboard_inline_buttons.insert(InlineKeyboardButton(text=await get_users([winner], winner, mentions=False), callback_data=winner_info.new(id=id, uid=winner, offset=offset, action="info_winner")))
    if count > paginate_limit_count:
        if offset - paginate_limit_count >= 0:
            keyboard_inline_buttons.add(InlineKeyboardButton(text="⬅", callback_data=paginate_winners.new(
                offset=offset - paginate_limit_count, id=id, action="get_paginate_winners")))
        if count > offset + paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="➡", callback_data=paginate_winners.new(
                offset=offset + paginate_limit_count, id=id, action="get_paginate_winners")))
            if offset >= paginate_limit_count:
                keyboard_inline_buttons.add(InlineKeyboardButton(text="⏪", callback_data=paginate_winners.new(offset=0, id=id, action="get_paginate_winners")))
                if count >= offset + paginate_limit_count * 2:
                    keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_winners.new(
                        offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count, id=id,
                        action="get_paginate_winners")))
            elif count >= offset + paginate_limit_count * 2:
                keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_winners.new(
                    offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count, id=id,
                    action="get_paginate_winners")))
        elif offset >= paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏪", callback_data=paginate_winners.new(offset=0, id=id, action="get_paginate_winners")))
    return keyboard_inline_buttons, count

async def edit_settings_button(message, id, how=None):
    result = await db.get_user(id)
    settings_buttons = InlineKeyboardMarkup()
    if result.get("random"):
        settings_buttons.add(InlineKeyboardButton(text='✅ Кнопка рандома', callback_data="random_button_off"))
    else:
        settings_buttons.add(InlineKeyboardButton(text='❌ Кнопка рандома', callback_data="random_button_on"))
    if result.get("sep_result"):
        settings_buttons.add(InlineKeyboardButton(text='✅ Отдельный пост итогов', callback_data="sep_button_off"))
    else:
        settings_buttons.add(InlineKeyboardButton(text='❌ Отдельный пост итогов', callback_data="sep_button_on"))
    if how:
        await message.edit_reply_markup(reply_markup=settings_buttons)
    else:
        await message.answer("Настройки", reply_markup=settings_buttons)

async def get_users(users, chat_id, mentions=True, retry=True):
    text_users = ""
    if mentions:
        for user in users:
            try:
                tg_user = await bot.get_chat_member(chat_id=chat_id, user_id=user)
                if tg_user.user.username:
                    text_users += f", @{tg_user.user.username}"
                else:
                    text_users += f", <a href='tg://user?id={user}'>{tg_user.user.full_name}</a>"
            except:
                if retry:
                    try:
                        await get_users(users, chat_id, mentions=mentions, retry=False)
                    except Exception as e2:
                        print("error", e2)
    else:
        for user in users:
            try:
                tg_user = await bot.get_chat_member(chat_id=chat_id, user_id=user)
                text_users += f", {tg_user.user.full_name}"
            except:
                if retry:
                    try:
                        await get_users(users, chat_id, mentions=mentions, retry=False)
                    except Exception as e2:
                        print("error", e2)
    return text_users[2:]

async def get_info_concurs(concurs_id, chat_id, how=None, message_id=None, offset=0):
    result = await db.get_info_concurs(concurs_id, chat_id)
    if result:
        buttons = [
            InlineKeyboardButton(text="Завершить конкурс",
                                 callback_data=callback_buttons.new(id=concurs_id, action="complete_concurs")),
            InlineKeyboardButton(text="Перейти к конкурсу",
                                 url=f"https://t.me/c/{str(result['public_id'])[4:]}/{result['message_id']}"),
            InlineKeyboardButton(text="Получить список участников",
                                 callback_data=callback_buttons.new(id=concurs_id, action="participants_concurs")),
            InlineKeyboardButton(text="Удалить конкурс",
                                 callback_data=callback_buttons.new(id=concurs_id, action="delete_concurs")),
            InlineKeyboardButton(text="Обновить участников на кнопке",
                                 callback_data=callback_buttons.new(id=concurs_id, action="update_count")),
            InlineKeyboardButton(text="Обновить информацию",
                                 callback_data=callback_buttons.new(id=concurs_id, action="update_concurs_info")),
            InlineKeyboardButton(text="Изменить информацию",
                                 callback_data=callback_buttons.new(id=concurs_id, action="edit_info")),
            InlineKeyboardButton(text="Права на управление",
                                 callback_data=callback_buttons.new(id=concurs_id, action="edit_trusts"))
        ]
        if not result['published']:
            buttons = [
                InlineKeyboardButton(text="Опубликовать конкурс",
                                     callback_data=callback_buttons.new(id=concurs_id, action="publicate_concurs")),
                InlineKeyboardButton(text="Удалить конкурс",
                                     callback_data=callback_buttons.new(id=concurs_id, action="delete_concurs")),
                InlineKeyboardButton(text="Обновить информацию",
                                     callback_data=callback_buttons.new(id=concurs_id, action="update_concurs_info")),
                InlineKeyboardButton(text="Изменить информацию",
                                     callback_data=callback_buttons.new(id=concurs_id, action="edit_info")),
                InlineKeyboardButton(text="Права на управление",
                                     callback_data=callback_buttons.new(id=concurs_id, action="edit_trusts"))
            ]
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        channels_text = ""
        if result['channels']:
            try:
                channels_text = "\nПроверка подписки в каналах:"
                for channel in result['channels']:
                    channel_id = await bot.get_chat(chat_id=channel)
                    channels_text += f"<b>\n📢{re.sub('[<>]', '', channel_id['title'])}</b>"
            except:
                pass
        needjoin_text = ""
        if result['need_join']:
            needjoin_text = f"\nПроверка участия в конкурсах: <b>{str(result['need_join']).strip('[]')}</b>"
        time_published = ""
        if result['time_published'] and not result['published']:
            time_published = f"\nКонкурс будет опубликован <b>{result['time_published']}</b>"
        mesg_text = f"Конкурс №<b><i>{concurs_id}</i></b>" \
                    f"\nУчастников: <b><i>{result['participants']}</i></b>" \
                    f"\nПобедителей: <b><i>{result['winners']}</i></b>" \
                    f"\nКонкурс будет завершен: <b>{result['time_complite']}</b>" \
                    f"{time_published}" \
                    f"{channels_text}" \
                    f"{needjoin_text}" \
                    f"\nПоделиться конкурсом: <code>@concubot {concurs_id}</code>"
        if how:
            await bot.edit_message_text(mesg_text, chat_id, message_id, reply_markup=keyboard.add(InlineKeyboardButton(text="Назад", callback_data=paginate_buttons.new(offset=offset, action="get_paginate_concurses"))))
        else:
            await bot.send_message(chat_id, mesg_text, reply_markup=keyboard)
    else:
        if how:
            await bot.edit_message_text("У Вас нет доступа к управлению этим конкурсом", chat_id, message_id)
        else:
            await bot.send_message(chat_id, "У Вас нет доступа к управлению этим конкурсом")

async def generate_paginate_select_channels(channels, yet_selected, offset):
    keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
    count = channels[0]['count']
    for channel in channels:
        channel = json.loads(channel['channels'])
        if channel['id'] in yet_selected:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="✅ " + re.sub('[<>]', '', channel['title']), callback_data=callback_buttons.new(id=f'{channel["id"]} {offset}', action="change_select_channel")))
        else:
            keyboard_inline_buttons.insert(
                InlineKeyboardButton(text=re.sub('[<>]', '', channel['title']), callback_data=callback_buttons.new(id=f'{channel["id"]} {offset}', action="change_select_channel")))
    if count > paginate_limit_count:
        if offset - paginate_limit_count >= 0:
            keyboard_inline_buttons.add(InlineKeyboardButton(text="⬅", callback_data=paginate_buttons.new(
                offset=offset - paginate_limit_count, action="get_paginate_select_channels")))
        if count > offset + paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="➡", callback_data=paginate_buttons.new(
                offset=offset + paginate_limit_count, action="get_paginate_select_channels")))
            if offset >= paginate_limit_count:
                keyboard_inline_buttons.add(InlineKeyboardButton(text="⏪", callback_data=paginate_buttons.new(offset=0, action="get_paginate_select_channels")))
                if count >= offset + paginate_limit_count * 2:
                    keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(
                        offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count,
                        action="get_paginate_select_channels")))
            elif count >= offset + paginate_limit_count * 2:
                keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(
                    offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count,
                    action="get_paginate_select_channels")))
        elif offset >= paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏪", callback_data=paginate_buttons.new(offset=0, action="get_paginate_select_channels")))
    keyboard_inline_buttons.add(InlineKeyboardButton(text="Готово", callback_data="Готово"))
    return keyboard_inline_buttons, count


async def select_channels(state, uid, yet_channels=[], edit_concurs_id=None):
    channels = await db.get_pagined_user_channels(uid)
    keyboard_inline_buttons = InlineKeyboardMarkup()
    if channels:
        try:
            keyboard_inline_buttons, count = await generate_paginate_select_channels(channels, yet_channels, 0)
            if count != 0:
                if edit_concurs_id:
                    keyboard_inline_buttons.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=edit_concurs_id,
                                                                                           action="edit_info")))
                back_id = await bot.send_message(uid, f"Выбери каналы, на которые нужно будет подписаться (0-{min([count, 0 + paginate_limit_count])}/{count})\nИли отправь айди/ссылку/пост канала", reply_markup=keyboard_inline_buttons)
                await state.update_data(back_id=back_id['message_id'])
            else:
                keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить свой канал", callback_data="add_channel"))
                await bot.send_message(uid, 'Еще нет каналов', reply_markup=keyboard_inline_buttons)
        except:
            pass
    else:
        keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал", callback_data="add_channel"))
        await bot.send_message(uid, 'Каналов еще нет', reply_markup=keyboard_inline_buttons)

async def generate_paginate_accept_channels(channels, offset):
    keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
    count = len(channels)
    channels = channels[offset:offset+paginate_limit_count]
    for channel in channels:
        keyboard_inline_buttons.insert(InlineKeyboardButton(text=re.sub('[<>]', '', channel['title']), callback_data=callback_buttons.new(
            id=channel["id"], action="public_channel")))
    if count > paginate_limit_count:
        if offset - paginate_limit_count >= 0:
            keyboard_inline_buttons.add(InlineKeyboardButton(text="⬅", callback_data=paginate_buttons.new(
                offset=offset - paginate_limit_count, action="get_paginate_accept_channels")))
        if count > offset + paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="➡", callback_data=paginate_buttons.new(
                offset=offset + paginate_limit_count, action="get_paginate_accept_channels")))
            if offset >= paginate_limit_count:
                keyboard_inline_buttons.add(InlineKeyboardButton(text="⏪", callback_data=paginate_buttons.new(offset=0,
                                                                                                              action="get_paginate_accept_channels")))
                if count >= offset + paginate_limit_count * 2:
                    keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(
                        offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count,
                        action="get_paginate_accept_channels")))
            elif count >= offset + paginate_limit_count * 2:
                keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏩", callback_data=paginate_buttons.new(
                    offset=count + (paginate_limit_count - count % paginate_limit_count) - paginate_limit_count,
                    action="get_paginate_accept_channels")))
        elif offset >= paginate_limit_count:
            keyboard_inline_buttons.insert(InlineKeyboardButton(text="⏪", callback_data=paginate_buttons.new(offset=0,
                                                                                                             action="get_paginate_accept_channels")))
    return keyboard_inline_buttons, count

def partition(l, size):
    for i in range(0, len(l), size):
        yield list(itertools.islice(l, i, i + size))

async def sliced_channels(channels, user):
    own_channels = []
    for channel in channels:
        try:
            chnl = await bot.get_chat_member(chat_id=channel["id"], user_id=bot_id)
            if chnl.can_post_messages or chnl.can_manage_chat:
                check = await bot.get_chat_member(chat_id=channel["id"], user_id=user)
                if check.status in ["administrator", "creator"] and (chnl.can_post_messages or chnl.can_manage_chat):
                    own_channels.append(channel)
        except Exception as e:
            pass
    return own_channels

async def check_admin_channel(id, user):
    try:
        chnl = await bot.get_chat_member(chat_id=id, user_id=bot_id)
        if chnl.can_post_messages or chnl.can_manage_chat:
            check = await bot.get_chat_member(chat_id=id, user_id=user)
            if check.status in ["administrator", "creator"] and (chnl.can_post_messages or chnl.can_manage_chat):
                channel_id = await bot.get_chat(chat_id=id)
                return {"id": id, "title": channel_id["title"]}
    except Exception as e:
        print(e)

async def get_owner_channels(user):
    channels = await db.get_user_channels(user)
    channels = partition(channels, 10)
    response = await asyncio.gather(*[sliced_channels(chnls, user) for chnls in channels])
    result = []
    for chunk in response:
        result.extend(chunk)
    return result