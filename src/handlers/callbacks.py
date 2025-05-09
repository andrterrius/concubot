import base64
import numpy as np

from aiogram.dispatcher.filters import ChatTypeFilter, Text, MediaGroupFilter
from aiogram.types import *
from aiogram.dispatcher import FSMContext
from src.config import *
from src.keyboards import *
from src.states import *
from src.utils import *


@dp.callback_query_handler(callback_buttons.filter(action=["join_concurs"]))
async def callbacks_join_concurs(call: CallbackQuery, callback_data: dict):
    try:
        result = await db.check_participate_concurs(int(callback_data['id']), call['from']['id'])
        if result:
            for channel in result['channels']:
                try:
                    check_user = await bot.get_chat_member(chat_id=channel, user_id=call['from']['id'])
                    if check_user.status not in ['creator', 'administrator', 'member']:
                        channel_id = await bot.get_chat(chat_id=channel)
                        return await call.answer(f"‼️ Нужно подписаться на {channel_id['title']} ‼️", show_alert=True)
                except:
                    pass
            if result['need_join']:
                check = await db.check_active_and_participate_concurs(result['need_join'], call['from']['id'])
                if check:
                    return await call.answer(f"‼Нужно принять участие в конкурсе №{check} ‼", show_alert=True)
            await call.answer("✅Ты теперь участвуешь✅", show_alert=True)
            result2 = await db.participate_concurs(int(callback_data['id']), call['from']['id'])
            part = result2['participants']
            if part != 0 and part % 10 == 0:
                if result2['count'] and result2['active']:
                    button_concurs = await get_participate_button(result2['id'], result2, part)
                    try:
                        await bot.edit_message_reply_markup(result2['public_id'], result2['message_id'],
                                                            reply_markup=button_concurs)
                    except:
                        pass
        else:
            await call.answer("⚠️Ты УЖЕ участвуешь в конкурсе⚠️", show_alert=True)
    except:
        await call.answer()

@dp.callback_query_handler(callback_buttons.filter(action=["join_concurs_conditions"]))
async def callbacks_join_concurs_conditions(call: CallbackQuery, callback_data: dict):
    try:
        concurs = int(callback_data['id'])
        check_concurs = await db.get_info_concurs(concurs)
        if check_concurs and check_concurs['condition']:
            completed_condition = await db.get_user_condition(call['from']['id'], concurs)
            if completed_condition:
                await callbacks_join_concurs(call, callback_data)
            else:
                await call.answer(f"‼Нужно выполнить дополнительные условия ‼", show_alert=True)
    except:
        await call.answer()

@dp.callback_query_handler(callback_buttons.filter(action=["join_concurs_edit_conditions"]))
async def callbacks_join_concurs_edit_conditions(call: CallbackQuery, callback_data: dict, state: FSMContext):
    try:
        concurs = int(callback_data['id'])
        check_concurs = await db.check_participate_concurs(concurs, call['from']['id'])
        if check_concurs:
            check_concurs = await db.get_info_concurs(concurs)
            if check_concurs['condition']:
                completed_condition = await db.get_user_condition(call['from']['id'], concurs)
                if completed_condition:
                    channel_id = await bot.get_chat(chat_id=check_concurs['public_id'])
                    await call.message.answer(
                        f"Администратор канала <b>{channel_id['title']}</b> запрашивает выполнение дополнительных условий"
                        f"\nВнимательно прочтите и отправьте ответное сообщение для участия в конкурсе!")
                    await AdditionalConditions.input_condition.set()
                    await state.update_data(concurs_id=concurs, update=True)
                    await call.message.bot.copy_message(call['from']['id'], check_concurs["condition_owner"], check_concurs['condition'],
                                                   reply_markup=otmena_keyboard)
                    await call.answer()
                else:
                    await call.answer(f"‼Нужно выполнить дополнительные условия ‼", show_alert=True)
        else:
            return await call.answer(f"‼Больше нельзя изменить свое сообщение‼", show_alert=True)
    except:
        await call.answer()

@dp.callback_query_handler(ChatTypeFilter(chat_type=ChatType.PRIVATE), text="create_concurs")
async def callbacks_create_concurs(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.delete()
    usr = await db.get_user(call['from']['id'])
    if usr['ban']:
        return await call.message.answer('Вы заблокированы')
    if len(usr['channels']) == 2:
        keyboard_inline_buttons = InlineKeyboardMarkup()
        keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал",
                                                         callback_data=paginate_buttons.new(offset=0,
                                                                                            action="add_channel")))
        return await call.message.answer('Каналов еще нет', reply_markup=keyboard_inline_buttons)
    check = await check_sub(call['from']['id'])
    if check:
        await call.message.answer('Отправь пост конкурса', reply_markup=otmena_keyboard)
        await ConcursCreate.message.set()
        own_channels = await get_owner_channels(call['from']['id'])
        await state.update_data(own_channels=own_channels)
    else:
        await call.message.answer(need_sub_text, reply_markup=need_sub_news)

@dp.callback_query_handler(callback_buttons.filter(action=["check_concurs"]), state="*")
async def callbacks_check_concurs(call: CallbackQuery, callback_data: dict, state: FSMContext):
    splited = list(map(int, callback_data['id'].split()))
    concurs_id = splited[0]
    offset = 0 if len(splited) == 1 else splited[1]
    await get_info_concurs(concurs_id, call.message.chat.id, 'edit', call.message.message_id, offset=offset)
    await state.finish()


@dp.callback_query_handler(callback_buttons.filter(action=["update_concurs_info"]))
async def callbacks_update_concurs_info(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        try:
            if result['participants'] > 0:
                await get_info_concurs(int(callback_data['id']), call.message.chat.id, "edit", call.message.message_id)
                await call.answer('Успешно обновил информацию конкурса')
            else:
                await call.answer('Информация конкурса не изменилась')
        except:
            await call.answer('Данные конкурса не изменились')
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')


@dp.callback_query_handler(callback_buttons.filter(action=["update_count"]))
async def callbacks_update_count(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        try:
            button_concurs = await get_participate_button(result['id'], result, result['participants'])
            await bot.edit_message_reply_markup(result['public_id'], result['message_id'],
                                                reply_markup=button_concurs)
            await call.answer(f'Успешно обновил участников конкурса, теперь их {result["participants"]}')
        except:
            await call.answer('Не удалось обновить участников конкурса, попробуйте еще раз')
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')



@dp.callback_query_handler(callback_buttons.filter(action=["participants_concurs"]))
async def callbacks_check_participants(call: CallbackQuery, callback_data: dict):
    result = await db.get_participants_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if result['participants']:
            await call.answer("Выгружаю список участников...")
            counter = 1
            text = ""
            for chel in result['participants']:
                try:
                    user = await call.message.bot.get_chat_member(chat_id=chel, user_id=chel)
                    if user.user.username:
                        text += f"{counter}. @{user.user.username}\n"
                    else:
                        full_name = user.user.first_name
                        if user.user.last_name:
                            full_name += ' ' + user.user.last_name
                        text += f"{counter}. <a href='tg://user?id={chel}'>{full_name}</a>\n"
                    if counter % 100 == 0:
                        await call.message.answer(text)
                        text = ""
                    counter += 1
                except:
                    try:
                        user = await bot.get_chat_member(chat_id=result['public_id'], user_id=chel)
                        if user.user.username:
                            text += f"{counter}. @{user.user.username}\n"
                        else:
                            full_name = user.user.first_name
                            if user.user.last_name:
                                full_name += ' ' + user.user.last_name
                            text += f"{counter}. <a href='tg://user?id={chel}'>{full_name}</a>\n"
                        if counter % 100 == 0:
                            await call.message.answer(text)
                            text = ""
                        counter += 1
                    except:
                        pass
            await call.message.answer(text)
            await call.message.answer(f"👆Участники конкурса №{callback_data['id']}:", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton(
                                          text="Назад",
                                          callback_data=callback_buttons.new(
                                          id=int(callback_data['id']),
                                          action="check_concurs"))))
        else:
            await call.answer("В конкурсе никто не участвует")
    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")

@dp.callback_query_handler(callback_buttons.filter(action=["complete_concurs_accept"]))
async def callbacks_complete_concurs(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        if result['participants'] > 1:
            if result['winners'] > result['participants']:
                do = result['participants']
            else:
                do = result['winners']
            user = await db.get_user(call['from']['id'])
            participants = await db.get_participants_concurs(int(callback_data['id']), call['from']['id'])
            participants = participants['participants']
            await call.message.edit_text("Подвожу итоги...")
            if user['random'] and result["participants"] < 1000:
                try:
                    random = await random_client.generate_signed_integers(n=do, min=1, max=result['participants'],
                                                                    replacement=False)
                    result_list = random.parse()['result']
                    random = json.dumps(result_list['random'])
                    signature = json.dumps(result_list['signature'])
                    base = base64.b64encode(bytes(random.encode('utf-8')))
                    link = f"https://api.random.org/signatures/form?format=json&random={str(base)[2:].replace('=', '%3D').replace('+', '%2B')}&signature={str(signature)[1:-2].replace('/', r'%2F').replace('+', '%2B')}".replace(
                        "'", '')
                    participants_text = ""
                    counter = 1
                    winners = []
                    for part in participants:
                        try:
                            usr = await bot.get_chat_member(chat_id=result['public_id'], user_id=part)
                            if usr.user.username:
                                participants_text += f"\n<p>{counter}. @{usr.user.username}</p>"
                            else:
                                full_name = usr.user.first_name
                                if usr.user.last_name:
                                    full_name += ' ' + usr.user.last_name
                                participants_text += f"\n<p>{counter}. <a href='tg://user?id={part}'>{full_name}</a></p>"
                            if counter in list(result_list['random']['data']):
                                winners.append(part)
                            if counter % 5 == 0:
                                await call.message.edit_text(f"Генерация статьи...\n{counter}/{result['participants']}")
                            counter += 1
                        except:
                            pass
                    text_winers = await get_users(winners, result['public_id'], mentions=result['mentions'])
                    response = await telegraph.create_page(
                        f"Итоги конкурса №{result['id']}",
                        html_content=f"<p>Победители конкурса: {text_winers}</p>\n<p>Результат рандом орга: <b>{result_list['random']['data']}</b></p>\n<p><a href='{link}'><b>👉Проверить результат на рандом орге👈</b>\n</a></p>\n<p><h3>Участники конкурса:</h3></p>\n<p class='participants'>{participants_text}</p>",
                        author_name="Concu Bot",
                        author_url="https://t.me/concubot"
                    )
                    random_button = InlineKeyboardMarkup()
                    random_button.add(InlineKeyboardButton(text='Проверить на random.org', url=response['url']))
                    linkz = await get_start_link(f"check-{result['id']}")
                    if result['photo']:
                        text = result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}'
                        if len(text) > 1024 or user['sep_result']:
                            await bot.edit_message_reply_markup(result['public_id'], result['message_id'], reply_markup=None)
                            msg_id = await bot.send_message(result['public_id'], f'<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                            reply_to_message_id=result['message_id'], reply_markup=random_button)
                            await db.set_new_message_id(result['id'], msg_id['message_id'])
                        else:
                            await bot.edit_message_caption(result['public_id'], result['message_id'],
                                                           caption=result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                           reply_markup=random_button)
                    else:
                        if user['sep_result']:
                            await bot.edit_message_reply_markup(result['public_id'], result['message_id'],
                                                                reply_markup=None)
                            msg_id = await bot.send_message(result['public_id'],
                                                            f'<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                            reply_to_message_id=result['message_id'],
                                                            reply_markup=random_button)
                            await db.set_new_message_id(result['id'], msg_id['message_id'])
                        else:
                            await bot.edit_message_text(result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                        result['public_id'], result['message_id'],
                                                        reply_markup=random_button, disable_web_page_preview=True)
                    await db.update_winners(result['id'], text_winers, winners)
                    await db.set_random_link(result['id'], response['url'])
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton(text="Перейти к конкурсу",
                                                      url=f"https://t.me/c/{str(result['public_id'])[4:]}/{result['message_id']}"))

                    owner_text_winers = text_winers if result['mentions'] else await get_users(winners, result['public_id'])

                    await call.message.edit_text(
                        f"Конкурс №{result['id']} завершен "
                        f"\nКоличество участников: {result['participants']} "
                        f"\n<b><a href='{linkz}'>Победители</a>:</b> {owner_text_winers}",
                        reply_markup=keyboard)
                    keyboard_inline_buttons, count = await get_paginate_winners(result['id'])
                    await call.message.reply(
                        f"<b>Победители конкурса №{result['id']} (0-{min([count, paginate_limit_count])}/{count})</b>",
                        reply_markup=keyboard_inline_buttons)
                except:
                    await get_info_concurs(result['id'], call.message.chat.id, how='edit',
                                           message_id=call.message.message_id)

            else:
                winers = np.random.choice(participants, do, replace=False)
                text_winers = await get_users(winers, result['public_id'], mentions=result['mentions'])
                try:
                    await call.message.edit_text("Публикую победителей...")
                    linkz = await get_start_link(f"check-{result['id']}")
                    if result['photo']:
                        text = result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}'
                        if len(text) > 1024 or user['sep_result']:
                            await bot.edit_message_reply_markup(result['public_id'], result['message_id'], reply_markup=None)
                            msg_id = await bot.send_message(result['public_id'], f'<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                            reply_to_message_id=result['message_id'])
                            await db.set_new_message_id(result['id'], msg_id['message_id'])
                        else:
                            await bot.edit_message_caption(result['public_id'], result['message_id'],
                                                           caption=result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}')
                    else:
                        if user['sep_result']:
                            await bot.edit_message_reply_markup(result['public_id'], result['message_id'],
                                                                reply_markup=None)
                            msg_id = await bot.send_message(result['public_id'],
                                                            f'<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                            reply_to_message_id=result['message_id'])
                            await db.set_new_message_id(result['id'], msg_id['message_id'])
                        else:
                            await bot.edit_message_text(result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                        result['public_id'], result['message_id'],
                                                        disable_web_page_preview=True)
                    await db.update_winners(result['id'], text_winers, list(winers))
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton(text="Перейти к конкурсу",
                                                      url=f"https://t.me/c/{str(result['public_id'])[4:]}/{result['message_id']}"))

                    owner_text_winers = text_winers if result['mentions'] else await get_users(winers, result['public_id'])

                    await call.message.edit_text(
                        f"Конкурс №{result['id']} завершен "
                        f"\nКоличество участников: {result['participants']} "
                        f"\n<b><a href='{linkz}'>Победители</a>:</b> {owner_text_winers}", reply_markup=keyboard)
                    keyboard_inline_buttons, count = await get_paginate_winners(result['id'])
                    await call.message.reply(
                        f"<b>Победители конкурса №{result['id']} (0-{min([count, paginate_limit_count])}/{count})</b>",
                        reply_markup=keyboard_inline_buttons)
                except Exception as e:
                    await get_info_concurs(result['id'], call.message.chat.id, "edit", call.message.message_id)
                    await call.message.bot.send_message(admin, e)
                    await call.answer("Произошла ошибка, подведите итоги еще раз.")
        else:
            await call.answer("Для подведения итогов должно быть минимум 2 участника")
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')
    await call.answer()


@dp.callback_query_handler(callback_buttons.filter(action=["delete_concurs_accept"]))
async def callbacks_delete_concurs_accept(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        await db.set_inactive(result['id'])
        try:
            await call.message.bot.delete_message(result['public_id'], result['message_id'])
        except:
            pass
        await call.answer(f"Конкурс №{result['id']} удален")
        concurses, count = await db.get_pagined_concurses(call['from']['id'])
        if concurses and count > 0:
            keyboard_inline_buttons, count = await get_paginate_concurses(concurses, count)
            await call.message.edit_text(
                f"Активные конкурсы (0-{min([count, paginate_limit_count])}/{count})",
                reply_markup=keyboard_inline_buttons)
        else:
            await call.message.edit_text("У тебя нет активных конкурсов", reply_markup=create_concurs)
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')


@dp.callback_query_handler(callback_buttons.filter(action=["delete_concurs"]))
async def callbacks_delete_concurs(call: CallbackQuery, callback_data: dict):
    delete_concurs_keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton(text='🗑Удалить🗑',
                                                                              callback_data=callback_buttons.new(
                                                                                  id=int(callback_data['id']),
                                                                                  action="delete_concurs_accept"))).add(
        InlineKeyboardButton(text='Назад',
                             callback_data=callback_buttons.new(id=int(callback_data['id']), action="check_concurs")))
    await bot.edit_message_text(f"Удалить конкурс №{callback_data['id']}?", call.message.chat.id,
                                call.message.message_id, reply_markup=delete_concurs_keyboard)
    await call.answer()

@dp.callback_query_handler(callback_buttons.filter(action=["publicate_concurs"]))
async def callbacks_publicate_concurs(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call["from"]['id'])
    if result:
        if not result['published']:
            public_buttons = await get_participate_button(result['id'], result)
            if result.get("photo"):
                msg_id = await bot.copy_message(result["public_id"], call["from"]['id'], result['copy_id'],
                                                reply_markup=public_buttons)
            else:
                msg_id = await bot.send_message(result["public_id"], result['message_text'], reply_markup=public_buttons,
                                                disable_web_page_preview=True)
            await db.set_concurs_message_id(result['id'], msg_id['message_id'])
            splited = list(map(int, callback_data['id'].split()))
            concurs_id = splited[0]
            offset = 0 if len(splited) == 1 else splited[1]
            await get_info_concurs(concurs_id, call.message.chat.id, 'edit', call.message.message_id, offset=offset)
            await call.answer(f"Конкурс №{result['id']} опубликован!", reply_markup=menu)
        else:
            await call.answer("Конкурс уже опубликован")
            await call.message.delete()
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')
@dp.callback_query_handler(callback_buttons.filter(action=["complete_concurs"]))
async def callbacks_delete_concurs(call: CallbackQuery, callback_data: dict):
    complete_concurs_keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton(
        text='✅Завершить✅',
        callback_data=callback_buttons.new(
        id=int(callback_data['id']),
        action="complete_concurs_accept"))).add(
        InlineKeyboardButton(text='Назад',
                             callback_data=callback_buttons.new(id=int(callback_data['id']), action="check_concurs")))
    await bot.edit_message_text(f"Завершаем конкурс №{callback_data['id']}?", call.message.chat.id,
                                call.message.message_id, reply_markup=complete_concurs_keyboard)
    await call.answer()

@dp.callback_query_handler(callback_buttons.filter(action=["settings_channel"]))
async def callbacks_settings_channel(call: CallbackQuery, callback_data: dict):
    result = await db.get_user_channels(call['from']['id'])
    chnl_id = int(callback_data['id'].split()[0])
    offset = int(callback_data['id'].split()[1])
    if result:
        for channel in result:
            if channel['id'] == chnl_id:
                try:
                    chnl = await bot.get_chat(chat_id=channel['id'])
                    buttons = [
                        InlineKeyboardButton(text="Обновить название", callback_data=callback_buttons.new(id=f"{chnl_id} {offset}", action="update_channel_name")),
                        InlineKeyboardButton(text="Удалить", callback_data=callback_buttons.new(id=f"{chnl_id} {offset}", action="delete_channel")),
                        InlineKeyboardButton(text="Назад", callback_data=paginate_buttons.new(offset=offset, action="get_paginate_channels"))
                    ]
                    keyboard = InlineKeyboardMarkup(row_width=1)
                    keyboard.add(*buttons)
                    channel_name = f"<b>{re.sub('<>', '', channel['title'])}</b>"
                    if "username" in chnl:
                        channel_name = f"<b><a href='t.me/{chnl['username']}'>{re.sub('<>', '', channel['title'])}</></b>"
                    await call.message.edit_text(channel_name, reply_markup=keyboard)
                except Exception as e:
                    buttons = [
                        InlineKeyboardButton(text="Удалить", callback_data=callback_buttons.new(id=f"{chnl_id} {offset}", action="delete_channel")),
                        InlineKeyboardButton(text="Назад", callback_data=paginate_buttons.new(offset=offset, action="get_paginate_channels"))
                    ]
                    keyboard = InlineKeyboardMarkup(row_width=1)
                    keyboard.add(*buttons)
                    await call.message.edit_text("Канал недоступен для бота", reply_markup=keyboard)

    return await call.answer()


@dp.callback_query_handler(callback_buttons.filter(action=["delete_channel"]))
async def callbacks_delete_channel(call: CallbackQuery, callback_data: dict):
    result = await db.get_user_channels(call['from']['id'])
    chnl_id = int(callback_data['id'].split()[0])
    offset = int(callback_data['id'].split()[1])
    if result:
        try:
            channels = []
            for channel in result:
                if channel['id'] != chnl_id:
                    channels.append({'id': channel['id'], 'title': channel['title']})
            await db.update_channels(json.dumps(channels), call['from']['id'])
            channels = await db.get_pagined_user_channels(call['from']['id'], offset)
            if channels:
                keyboard_inline_buttons, count = await generate_paginate_channels(channels, offset)
                await call.message.edit_text(f"Добавленные каналы ({offset}-{count}/{count})", reply_markup=keyboard_inline_buttons)
            else:
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton(text="Добавить канал", callback_data=paginate_buttons.new(offset=0, action="add_channel")))
                await call.message.edit_text('Каналов еще нет', reply_markup=keyboard)
        except:
            return await call.answer("Произошла ошибка")
    return await call.answer("Канал удален")


@dp.callback_query_handler(callback_buttons.filter(action=["update_channel_name"]))
async def callbacks_update_channel_name(call: CallbackQuery, callback_data: dict):
    result = await db.get_user_channels(call['from']['id'])
    chnl_id = int(callback_data['id'].split()[0])
    offset = int(callback_data['id'].split()[1])
    if result:
        try:
            channels = []
            for channel in result:
                if channel['id'] == chnl_id:
                    try:
                        channel_id = await bot.get_chat(chat_id=channel['id'])
                        channels += [{'id': channel['id'], 'title': channel_id['title']}]
                        buttons = [
                            InlineKeyboardButton(text="Обновить название", callback_data=callback_buttons.new(id=f"{chnl_id} {offset}", action="update_channel_name")),
                            InlineKeyboardButton(text="Удалить", callback_data=callback_buttons.new(id=f"{chnl_id} {offset}", action="delete_channel")),
                            InlineKeyboardButton(text="Назад", callback_data=paginate_buttons.new(offset=offset, action="get_paginate_channels"))
                        ]
                        keyboard = InlineKeyboardMarkup(row_width=1)
                        keyboard.add(*buttons)
                        channel_name = f"<b>{channel['title']}</b>"
                        if "username" in channel:
                            channel_name = f"<b><a href='t.me/{channel['username']}'>{channel['title']}</></b>"
                        await call.message.edit_text(channel_name, reply_markup=keyboard)
                    except:
                        await call.answer("Название канала не изменилось")
                else:
                    channels += [{'id': channel['id'], 'title': channel['title']}]
            await db.update_channels(json.dumps(channels), call['from']['id'])
        except Exception as e:
            pass
    return await call.answer()

@dp.callback_query_handler(callback_buttons.filter(action=["edit_info"]), state="*")
async def callbacks_edit_info(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await state.finish()
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        buttons = [
            InlineKeyboardButton(text="Упоминание победителей",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                    action="edit_mentions_winners")),
            InlineKeyboardButton(text="Количество победителей",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                    action="edit_count_winners")),
            InlineKeyboardButton(text="Условия подписки",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                    action="edit_check_channels")),
            InlineKeyboardButton(text="Обновление участников на кнопке",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                    action="edit_update_count")),
            InlineKeyboardButton(text="Время подведения итогов",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                    action="edit_time_complite")),
            InlineKeyboardButton(text="Условие участия в других конкурсах",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                    action="edit_need_join")),
        ]
        if result['condition']:
            buttons.append(InlineKeyboardButton(text="Дополнительное условие",
                                                callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                   action="edit_check_condition")))
        buttons.append(InlineKeyboardButton(text="Назад",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']), action="check_concurs")))
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        await call.message.edit_text("Что будем изменять?", reply_markup=keyboard)
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')

@dp.callback_query_handler(callback_buttons.filter(action=["take_away_rights_trusts"]))
async def callbacks_take_away_rights_trusts(call: CallbackQuery, callback_data: dict):
    splited = callback_data['id'].split("_")
    concurs_id = int(splited[0])
    subowner = int(splited[1])
    result = await db.get_info_concurs(concurs_id, call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        await db.remove_trusts(concurs_id, subowner)
        user = await call.message.bot.get_chat_member(chat_id=subowner, user_id=subowner)
        subowner_text = user.user.full_name
        if user.user.username:
            subowner_text = f"@{user.user.username}"
        await call.answer(f"{subowner_text} больше не совладелец конкурса №{concurs_id}")
        await get_info_concurs(concurs_id, call.message.chat.id, "edit", call.message.message_id)
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')

@dp.callback_query_handler(callback_buttons.filter(action=["edit_trusts_info"]))
async def callbacks_edit_trusts_info(call: CallbackQuery, callback_data: dict):
    splited = callback_data['id'].split("_")
    concurs_id = int(splited[0])
    subowner = int(splited[1])
    result = await db.get_info_concurs(concurs_id, call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        keyboard = InlineKeyboardMarkup(row_width=1)
        user = await call.message.bot.get_chat_member(chat_id=subowner, user_id=subowner)
        subowner_text = user.user.full_name
        if user.user.username:
            subowner_text = f"@{user.user.username}"
        keyboard.add(InlineKeyboardButton(text="Забрать права",
                                          callback_data=callback_buttons.new(id=callback_data['id'],
                                                                             action="take_away_rights_trusts")))
        keyboard.add(InlineKeyboardButton(text="Назад",
                                 callback_data=callback_buttons.new(id=concurs_id, action="check_concurs")))
        await call.message.edit_text(f"Совладелец конкурса №{concurs_id}"
                                     f"\n{subowner_text}", reply_markup=keyboard)
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')

@dp.callback_query_handler(callback_buttons.filter(action=["get_trusts"]))
async def callbacks_get_trusts(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        keyboard = InlineKeyboardMarkup(row_width=1)
        for subowner in result['trusts']:
            user = await call.message.bot.get_chat_member(chat_id=subowner, user_id=subowner)
            subowner_text = user.user.full_name
            if user.user.username:
                subowner_text = f"@{user.user.username}"
            keyboard.add(InlineKeyboardButton(text=subowner_text,
                                              callback_data=callback_buttons.new(id=f"{callback_data['id']}_{subowner}",
                                                                                 action="edit_trusts_info")))
        keyboard.add(InlineKeyboardButton(text="Назад",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']), action="check_concurs")))
        await call.message.edit_text(f"Совладельцы конкурса №{int(callback_data['id'])}", reply_markup=keyboard)
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')

@dp.callback_query_handler(callback_buttons.filter(action=["add_new_trusts"]))
async def callbacks_edit_trusts(call: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        if result["owner"] == call['from']['id']:
            await state.update_data(id=int(callback_data['id']))
            await TrustsUsers.input_trust_id.set()
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton(text="Назад",
                                     callback_data=callback_buttons.new(id=int(callback_data['id']), action="check_concurs")))
            await call.message.edit_text(f"Перешли сообщение от человека, которому хочешь выдать доступ на управление конкурсом", reply_markup=keyboard)
        else:
            await call.answer('Управлять правами на конкурс может только его владелец')
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')

@dp.callback_query_handler(callback_buttons.filter(action=["edit_trusts"]))
async def callbacks_edit_trusts(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if result["owner"] == call['from']['id']:
            if not result['active']:
                return await call.answer("Конкурс неактивен")
            keyboard = InlineKeyboardMarkup(row_width=1)
            count_subowners = len(result['trusts'])
            if count_subowners > 0:
                keyboard.add(InlineKeyboardButton(text="Список совладельцев",
                                     callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                        action="get_trusts")))
            keyboard.add(InlineKeyboardButton(text="Выдать права на управление",
                                              callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                 action="add_new_trusts")))
            keyboard.add(InlineKeyboardButton(text="Назад",
                                     callback_data=callback_buttons.new(id=int(callback_data['id']), action="check_concurs")))
            await call.message.edit_text(f"Количество совладельцев: {count_subowners}", reply_markup=keyboard)
        else:
            await call.answer('Управлять правами на конкурс может только его владелец')
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')

@dp.callback_query_handler(callback_buttons.filter(action=["get_right_trusts"]))
async def callbacks_edit_trusts(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if not result['active']:
            return await call.answer("Конкурс неактивен")
        keyboard = InlineKeyboardMarkup(row_width=1)
        count_subowners = len(result['trusts'])
        if count_subowners > 0:
            keyboard.add(InlineKeyboardButton(text="Список совладельцев",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                    action="get_trusts")))
        keyboard.add(InlineKeyboardButton(text="Выдать права на управление",
                                          callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                             action="get_right_trusts")))
        keyboard.add(InlineKeyboardButton(text="Назад",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']), action="check_concurs")))
        await call.message.edit_text(f"Количество совладельцев: {count_subowners}", reply_markup=keyboard)
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')

@dp.callback_query_handler(callback_buttons.filter(action=["edit_time_complite"]))
async def callbacks_edit_time_complite(call: CallbackQuery, callback_data: dict, state: FSMContext):
    info_concurs = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if info_concurs:
        keyboard = InlineKeyboardMarkup()
        if info_concurs['time_complite'] == "вручную":
            keyboard.add(InlineKeyboardButton(text="Установить время завершения",
                                 callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                    action="set_new_complite_time")))
        else:
            keyboard.add(InlineKeyboardButton(text="Установить новое время завершения",
                                              callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                 action="set_new_complite_time")))
            keyboard.add(InlineKeyboardButton(text="Включить завершение вручную",
                                              callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                 action="set_handi_complite")))
        keyboard.add(InlineKeyboardButton(text="Назад",
                                     callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                        action="check_concurs")))
        await call.message.edit_text("Как меняем время завершения?", reply_markup=keyboard)
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')

@dp.callback_query_handler(callback_buttons.filter(action=["set_handi_complite"]))
async def callbacks_set_handi_complite(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await db.set_complite_time(int(callback_data['id']))
    scheduler.remove_job(callback_data['id'])
    await call.answer("Теперь конкурс не будет подведен автоматически")
    await get_info_concurs(int(callback_data['id']), call.message.chat.id, 'edit', call.message.message_id)

@dp.callback_query_handler(callback_buttons.filter(action=["set_new_complite_time"]))
async def callbacks_set_new_complite_time(call: CallbackQuery, callback_data: dict, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Назад",
                                      callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                         action="edit_info")))
    await EditInfo.time_complite.set()
    await state.update_data(id=int(callback_data['id']))
    return await call.message.edit_text(get_postpone_text(),
                                   reply_markup=keyboard)

@dp.callback_query_handler(callback_buttons.filter(action=["edit_check_channels"]))
async def callbacks_edit_check_channels(call: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        await EditInfo.channels.set()
        await state.update_data(id=int(callback_data['id']))
        await select_channels(state, call['from']['id'], edit_concurs_id=int(callback_data['id']))
    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")


@dp.callback_query_handler(callback_buttons.filter(action=["edit_update_count"]))
async def callbacks_edit_update_count(call: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        if result['count']:
            button = InlineKeyboardButton(text="Выключить автообновление",
                                          callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                             action="count_off"))
        else:
            button = InlineKeyboardButton(text="Включить автообновление",
                                          callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                             action="count_on"))
        keyboard = InlineKeyboardMarkup()
        keyboard.add(button)
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                           action="edit_info")))
        await call.message.edit_text("Что делаем?", reply_markup=keyboard)
    else:
        await call.answer('У Вас нет доступа к управлению этим конкурсом')


@dp.callback_query_handler(callback_buttons.filter(action=["edit_count_winners"]))
async def callbacks_edit_count_winners(call: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                           action="edit_info")))
        await EditInfo.winers.set()
        await state.update_data(id=int(callback_data['id']))
        await call.message.edit_text("Введи новое количество победителей", reply_markup=keyboard)
    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")

@dp.callback_query_handler(callback_buttons.filter(action=["edit_mentions_winners"]))
async def callbacks_edit_mentions_winners(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        keyboard = InlineKeyboardMarkup()
        if result['mentions']:
            mentions_info_text = "<b>Упоминание победителей включено ✅\nЛюбой пользователь сможет перейти на профили победителей</b>"
            keyboard.add(InlineKeyboardButton(text="Выключить упоминание ❌", callback_data=callback_buttons.new(id=callback_data['id'],
                                                                                               action="edit_mentions_winners_change")))
        else:
            mentions_info_text = "<b>Упоминание победителей выключено ❌\nТолько владелец и совладельцы конкурса смогут перейти на профили победителей</b>"
            keyboard.add(InlineKeyboardButton(text="Включить упоминание ✅",
                                              callback_data=callback_buttons.new(id=callback_data['id'],
                                                                                 action="edit_mentions_winners_change")))

        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=callback_data['id'],
                                                                                           action="edit_info")))
        await call.message.edit_text(mentions_info_text, reply_markup=keyboard)

    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")

@dp.callback_query_handler(callback_buttons.filter(action=["edit_mentions_winners_change"]))
async def callbacks_edit_mentions_winners_change(call: CallbackQuery, callback_data: dict):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        await db.set_mentions(not(result['mentions']), int(callback_data['id']))
        await callbacks_edit_mentions_winners(call, callback_data)
    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")

@dp.callback_query_handler(callback_buttons.filter(action=["edit_need_join"]))
async def callbacks_edit_need_join(call: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                           action="edit_info")))
        await EditInfo.need_join.set()
        await state.update_data(id=int(callback_data['id']))
        await call.message.edit_text("Отправь айди конкурсов, в которых нужно участвовать через запятую"
                             "\nПример:<code>1, 2, 3</code> (Если конкурс один, то достаточно отправить лишь число-номер конкурса без запятых)"
                             "\nИли отправь <code>0</code> для выключения проверки на участие",
                             reply_markup=keyboard)
    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")

@dp.callback_query_handler(callback_buttons.filter(action=["edit_check_condition"]), state="*")
async def callbacks_edit_check_condition(call: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        await state.finish()
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="Посмотреть текущее условие", callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                           action="edit_get_condition")))
        keyboard.add(InlineKeyboardButton(text="Изменить условие",
                                          callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                             action="edit_edit_condition")))
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                           action="edit_info")))
        await call.message.edit_text("Что делаем с дополнительными условиями?",
                             reply_markup=keyboard)
    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")

@dp.callback_query_handler(callback_buttons.filter(action=["edit_get_condition"]))
async def callbacks_edit_get_condition(call: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        await call.message.delete()
        await call.message.bot.copy_message(call['from']['id'], result["owner"], result['condition'])
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="Посмотреть текущее условие", callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                           action="edit_get_condition")))
        keyboard.add(InlineKeyboardButton(text="Изменить условие",
                                          callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                             action="edit_edit_condition")))
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                           action="edit_info")))
        await call.message.answer("Что делаем с дополнительными условиями?",
                             reply_markup=keyboard)
    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")

@dp.callback_query_handler(callback_buttons.filter(action=["edit_edit_condition"]))
async def callbacks_edit_get_condition(call: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if result:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=int(callback_data['id']),
                                                                                           action="edit_check_condition")))
        await state.update_data(id=int(callback_data['id']))
        await EditInfo.additional_conditions.set()
        await call.message.edit_text("Отправь сообщение, в котором будут указаны дополнительные условия (что именно должен предоставить участник для участия)",
                             reply_markup=keyboard)
    else:
        await call.answer("У Вас нет доступа к управлению этим конкурсом")

@dp.callback_query_handler(callback_buttons.filter(action=["count_on"]))
async def callbacks_random_on(call: CallbackQuery, callback_data: dict):
    await db.switch_concurs_count(int(callback_data['id']), True)
    await get_info_concurs(int(callback_data['id']), call.message.chat.id, 'edit', call.message.message_id)
    await call.answer("Автообновление кнопки было включено")


@dp.callback_query_handler(callback_buttons.filter(action=["count_off"]))
async def callbacks_random_off(call: CallbackQuery, callback_data: dict):
    await db.switch_concurs_count(int(callback_data['id']), False)
    await get_info_concurs(int(callback_data['id']), call.message.chat.id, 'edit', call.message.message_id)
    await call.answer("Автообновление кнопки было выключено")

@dp.callback_query_handler(paginate_buttons.filter(action=["add_channel"]), state='*')
async def callbacks_add_channel(call: CallbackQuery, state: FSMContext, callback_data: dict):
    offset = int(callback_data['offset'])
    await AddChannel.input_channel.set()
    await state.update_data(offset=offset)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.row(
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
    keyboard.add(KeyboardButton(text="Отмена"))
    await call.message.delete()
    await call.message.answer(
        'Для добавления канала нужно выполнить одно из условий'
        '\n1. Отправить id канала в формате <b>@канал</b>'
        '\n2. Отправить публичную ссылку на канал в формате <b>https://t.me/канал</b>'
        '\n3. Переслать сообщение из канала'
        '\n4. Выбрать канал/группу по кнопкам ниже',
        reply_markup=keyboard)
    await call.answer()

@dp.callback_query_handler(paginate_buttons.filter(action=["get_paginate_accept_channels"]), state=ConcursCreate.accept)
async def callbacks_get_paginate_owner_channels(call: CallbackQuery, state: FSMContext, callback_data: dict):
    await call.answer()
    offset = int(callback_data['offset'])
    state_data = await state.get_data()
    channels = state_data.get("own_channels")
    if channels:
        keyboard_inline_buttons, count = await generate_paginate_accept_channels(channels, offset)
        await call.message.edit_text(f"Выбери канал, в котором будет проведен конкурс ({offset}-{min([count, offset+paginate_limit_count])}/{count})", reply_markup=keyboard_inline_buttons)

@dp.callback_query_handler(paginate_buttons.filter(action=["get_paginate_channels"]), state="*")
async def callbacks_get_paginate_channels(call: CallbackQuery, state: FSMContext, callback_data: dict):
    await state.finish()
    await call.answer()
    offset = int(callback_data['offset'])
    channels = await db.get_pagined_user_channels(call['from']['id'], offset)
    keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
    if channels:
        keyboard_inline_buttons, count = await generate_paginate_channels(channels, offset)
        await call.message.edit_text(f"Добавленные каналы ({offset}-{min([count, offset+paginate_limit_count])}/{count})", reply_markup=keyboard_inline_buttons)
    else:
        keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал", callback_data=paginate_buttons.new(offset=offset, action="add_channel")))
        await call.message.edit_text('Каналов еще нет', reply_markup=keyboard_inline_buttons)

@dp.callback_query_handler(paginate_buttons.filter(action=["get_paginate_select_channels"]), state=[EditInfo.channels, ConcursCreate.select])
async def callbacks_get_paginate_channels(call: CallbackQuery, state: FSMContext, callback_data: dict):
    await call.answer()
    offset = int(callback_data['offset'])
    state_data = await state.get_data()
    channels = await db.get_pagined_user_channels(call['from']['id'], offset)
    keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
    if channels:
        keyboard_inline_buttons, count = await generate_paginate_select_channels(channels, state_data.get('channels', []), offset)
        await call.message.edit_text(f"Выбери каналы, на которые нужно подписаться ({offset}-{min([count, offset+paginate_limit_count])}/{count})", reply_markup=keyboard_inline_buttons)
    else:
        keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал", callback_data=paginate_buttons.new(offset=offset, action="add_channel")))
        await call.message.answer('Каналов еще нет', reply_markup=keyboard_inline_buttons)

@dp.callback_query_handler(paginate_buttons.filter(action=["get_paginate_concurses"]), state="*")
async def callbacks_get_paginate_concurses(call: CallbackQuery, state: FSMContext, callback_data: dict):
    await state.finish()
    await call.answer()
    offset = int(callback_data['offset'])
    concurses, count = await db.get_pagined_concurses(call['from']['id'], offset)
    if concurses and count > 0:
        keyboard_inline_buttons, count = await get_paginate_concurses(concurses, count, offset)
        await call.message.edit_text(f"Активные конкурсы ({offset}-{min([count, offset+paginate_limit_count])}/{count})", reply_markup=keyboard_inline_buttons)
    else:
        await call.message.edit_text('У вас нет активных конкурсов')

@dp.callback_query_handler(paginate_winners.filter(action=["get_paginate_winners"]), state="*")
async def callbacks_get_paginate_winners(call: CallbackQuery, state: FSMContext, callback_data: dict):
    await state.finish()
    await call.answer()
    offset = int(callback_data['offset'])
    id = int(callback_data['id'])
    keyboard_inline_buttons, count = await get_paginate_winners(id, offset)
    await call.message.edit_text(f"Победители конкурса №{id} ({offset}-{min([count, offset+paginate_limit_count])}/{count})", reply_markup=keyboard_inline_buttons)

@dp.callback_query_handler(winner_info.filter(action=["info_winner"]), state="*")
async def callbacks_get_info_winner(call: CallbackQuery, state: FSMContext, callback_data: dict):
    info_concurs = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    await call.answer()
    if info_concurs:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="Рерольнуть",
                                 callback_data=rerol_button_data.new(id=callback_data['id'], uid=callback_data['uid'], action="rerol"))
        )
        if info_concurs['condition']:
            keyboard.add(
                InlineKeyboardButton(text="Посмотреть выполненное условие",
                                     callback_data=winner_info.new(offset=callback_data['offset'], uid=callback_data['uid'], id=callback_data['id'], action="get_winner_conditions"))
            )
        keyboard.add(
            InlineKeyboardButton(text="Назад",
                                          callback_data=paginate_winners.new(offset=callback_data['offset'], id=callback_data['id'], action="get_paginate_winners"))
        )
        user = await get_users([callback_data['uid']], callback_data['uid'])
        await call.message.edit_text(f"Победитель конкурса №{callback_data['id']}:"
                                     f"\n{user}", reply_markup=keyboard)

@dp.callback_query_handler(winner_info.filter(action=["get_winner_conditions"]), state="*")
async def callbacks_get_winner_conditions(call: CallbackQuery, state: FSMContext, callback_data: dict):
    info_concurs = await db.get_info_concurs(int(callback_data['id']), call['from']['id'])
    if info_concurs:
        completed_condition = await db.get_user_condition(int(callback_data['uid']), int(callback_data['id']))
        if completed_condition:
            info_user = await get_users([int(callback_data['uid'])], int(callback_data['uid']))
            await call.message.reply(f"Выполненные условия, которые {info_user} прислал {completed_condition['date']} для участия в конкурсе №{callback_data['id']}")
            if completed_condition['mediagroup']:
                mg = MediaGroup()
                for media in json.loads(completed_condition['mediagroup']):
                    mg.attach(media)
                await call.message.answer_media_group(mg)
            else:
                await call.message.bot.send_message(call['from']['id'], completed_condition.get('text'))
        else:
            await call.answer("Выполненные условия не были получены от этого победителя", show_alert=True)
    await call.answer()

@dp.callback_query_handler(rerol_button_data.filter(action=["rerol"]), state="*")
async def callbacks_rerol(call: CallbackQuery, state: FSMContext, callback_data: dict):
    try:
        id = int(callback_data['id'])
        winer = int(callback_data['uid'])
        result = await db.get_info_concurs(int(id), call['from']['id'])
        user = await db.get_user(call['from']['id'])
        if result:
            if result['random_link'] and result['winners'] != result['participants']:
                try:
                    participants = await db.get_participants_concurs_admin(result['id'])
                    user = await db.get_user(call['from']['id'])
                    await call.message.edit_text("Реролю победителя...")
                    random = await random_client.generate_signed_integers(n=1, min=1, max=result['participants'],
                                                                    replacement=False)
                    result_list = random.parse()['result']
                    while participants['participants'][int(result_list['random']['data'][0])-1] in result["winners_id"]:
                        random = await random_client.generate_signed_integers(n=1, min=1, max=result['participants'],
                                                                        replacement=False)
                        result_list = random.parse()['result']
                    random = json.dumps(result_list['random'])
                    signature = json.dumps(result_list['signature'])
                    base = base64.b64encode(bytes(random.encode('utf-8')))
                    link_random = f"https://api.random.org/signatures/form?format=json&random={str(base)[2:].replace('=', '%3D').replace('+', '%2B')}&signature={str(signature)[1:-2].replace('/', r'%2F').replace('+', '%2B')}".replace(
                        "'", '')
                    await call.message.edit_text(f"Генерация статьи...")
                    winners = result["winners_id"]
                    new_winer = participants['participants'][int(result_list['random']['data'][0])-1]
                    winers = [new_winer if chel == winer else chel for chel in winners]
                    new_winer_text = await get_users([new_winer], result['public_id'], mentions=result['mentions'])
                    last_winer = await get_users([winer], result['public_id'], mentions=result['mentions'])
                    text_winers = await get_users(winers, result['public_id'], mentions=result['mentions'])
                    link = await get_start_link(f"check-{result['id']}")
                    if result['photo']:
                        await bot.edit_message_caption(result['public_id'], result['message_id'],
                                                       caption=result[
                                                                   'message_text'] + f'\n\n<b><a href="{link}">Победители</a>:</b> {text_winers}')
                    else:
                        await bot.edit_message_text(
                            result['message_text'] + f'\n\n<b><a href="{link}">Победители</a>:</b> {text_winers}',
                            result['public_id'], result['message_id'], disable_web_page_preview=True)
                    if result['rerols']:
                        await db.rerol_change_winners(int(id), winers, text_winers, json.dumps(
                            json.loads(result['rerols']) + [
                                {"old": winer, "new": new_winer, "time": time.time()}]))
                    else:
                        await db.rerol_change_winners(int(id), winers, text_winers, json.dumps(
                            [{"old": winer, "new": new_winer, "time": time.time()}]))
                    old_contend = await telegraph.get_page(result['random_link'].lstrip("https://telegra.ph/"))
                    response = await telegraph.create_page(
                        old_contend['title'],
                        html_content=old_contend['content'].replace('</p> ', '</p>\n').replace(
                        '<h3 id="Участники-конкурса:">Участники конкурса:</h3>', f"<p><h3>🔄 РЕРОЛ</h3></p>"
                        f"\n<p>{last_winer} ({participants['participants'].index(winer)+1}) ==> {new_winer_text} ({int(result_list['random']['data'][0])})</p><p>Новые победители конкурса: {text_winers}</p>"
                        f"\n<p>Результат рандом орга для рерола: <b>{result_list['random']['data']}</b></p>"
                        f"\n<p><a href='{link_random}'><b>👉Проверить результат на рандом орге👈</b>\n</a></p>" + '\n<p><h3>Участники конкурса:</h3></p>'
                        ),
                        author_name="Concu Bot",
                        author_url="https://t.me/concubot"
                    )
                    random_button = InlineKeyboardMarkup()
                    random_button.add(InlineKeyboardButton(text='Проверить на random.org', url=response['url']))
                    linkz = await get_start_link(f"check-{result['id']}")
                    if result['photo']:
                        text = result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}'
                        if len(text) > 1024 or user['sep_result']:
                            await bot.edit_message_reply_markup(result['public_id'], result['message_id'],
                                                                reply_markup=None)
                            msg_id = await bot.send_message(result['public_id'],
                                                            f'<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                            reply_to_message_id=result['message_id'],
                                                            reply_markup=random_button)
                            await db.set_new_message_id(result['id'], msg_id['message_id'])
                        else:
                            await bot.edit_message_caption(result['public_id'], result['message_id'],
                                                           caption=result[
                                                                       'message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                           reply_markup=random_button)
                    else:
                        if user['sep_result']:
                            await bot.edit_message_reply_markup(result['public_id'], result['message_id'],
                                                                reply_markup=None)
                            msg_id = await bot.send_message(result['public_id'],
                                                            f'<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                            reply_to_message_id=result['message_id'],
                                                            reply_markup=random_button)
                            await db.set_new_message_id(result['id'], msg_id['message_id'])
                        else:
                            await bot.edit_message_text(
                                result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                result['public_id'], result['message_id'],
                                reply_markup=random_button, disable_web_page_preview=True)
                    await db.update_winners(result['id'], text_winers, winners)
                    await db.set_random_link(result['id'], response['url'])
                    if result['rerols']:
                        await db.rerol_change_winners(result['id'], winers, text_winers, json.dumps(
                            json.loads(result['rerols']) + [
                                {"old": winer, "new": new_winer, "time": time.time()}]))
                    else:
                        await db.rerol_change_winners(result['id'], winers, text_winers, json.dumps(
                            [{"old": winer, "new": new_winer, "time": time.time()}]))
                    keyboard, count = await get_paginate_winners(result['id'])
                    await call.message.edit_text(
                        f"Конкурс №{result['id']} рерольнут" + f"\n{last_winer} ==> {new_winer_text}\n"
                                                               f"<b>Победители конкурса №{result['id']} (0-{min([count, paginate_limit_count])}/{count})</b>",
                        reply_markup=keyboard)
                except:
                    keyboard_inline_buttons, count = await get_paginate_winners(result['id'])
                    await call.message.edit_text(
                        f"<b>Победители конкурса №{result['id']} (0-{min([count, paginate_limit_count])}/{count})</b>",
                        reply_markup=keyboard_inline_buttons)
                    await call.answer("произошла ошибка", show_alert=True)
            else:
                winners = result["winners_id"]
                part = await db.get_participants_concurs(int(id), call['from']['id'])
                part_list = part['participants']
                for win in winners:
                    part_list.remove(int(win))
                new_winer = np.random.choice(part_list, 1)
                winers = [int(new_winer[0]) if chel == winer else chel for chel in winners]
                new_winer_text = await get_users([int(new_winer[0])], result['public_id'], mentions=result['mentions'])
                last_winer = await get_users([winer], result['public_id'], mentions=result['mentions'])
                text_winers = await get_users(winers, result['public_id'], mentions=result['mentions'])
                await call.message.edit_text("Реролю победителя...")
                link = await get_start_link(f"check-{result['id']}")
                if result['photo']:
                    await bot.edit_message_caption(result['public_id'], result['message_id'],
                                                   caption=result['message_text'] + f'\n\n<b><a href="{link}">Победители</a>:</b> {text_winers}')
                else:
                    await bot.edit_message_text(result['message_text'] + f'\n\n<b><a href="{link}">Победители</a>:</b> {text_winers}',
                                                result['public_id'], result['message_id'], disable_web_page_preview=True)
                if result['rerols']:
                    await db.rerol_change_winners(int(id), winers, text_winers, json.dumps(json.loads(result['rerols']) + [{"old": winer, "new": int(new_winer[0]), "time": time.time()}]))
                else:
                    await db.rerol_change_winners(int(id), winers, text_winers, json.dumps([{"old": winer, "new": int(new_winer[0]), "time": time.time()}]))
                keyboard, count = await get_paginate_winners(result['id'])
                await call.message.edit_text(
                    f"Конкурс №{result['id']} рерольнут" + f"\n{last_winer} ==> {new_winer_text}\n"
                                                           f"<b>Победители конкурса №{result['id']} (0-{min([count, paginate_limit_count])}/{count})</b>",
                    reply_markup=keyboard)
        else:
            await call.answer('У Вас нет доступа к управлению этим конкурсом')
    except Exception as e:
        print(e)
@dp.callback_query_handler(callback_buttons.filter(action=["change_select_channel"]), state=[ConcursCreate.select, EditInfo.channels])
async def callbacks_get_paginate_channels(call: CallbackQuery, state: FSMContext, callback_data: dict):
    splited = list(map(int, callback_data['id'].split()))
    channel_id = splited[0]
    offset = splited[1]
    state_data = await state.get_data()
    channels = state_data.get('channels', [])
    try:
        chnl = await bot.get_chat_member(chat_id=channel_id, user_id=bot_id)
        if chnl.can_post_messages or chnl.can_manage_chat:
            if channel_id in channels:
                channels.remove(channel_id)
            else:
                channels.append(channel_id)
            await state.update_data(channels=channels)
            state_data = await state.get_data()
            offseted_channels = await db.get_pagined_user_channels(call['from']['id'], offset)
            keyboard, count = await generate_paginate_select_channels(offseted_channels, channels, offset)
            await call.message.edit_reply_markup(keyboard)
            await call.answer()
        else:
            await call.answer("Бот не является администратором выбранного канала и не сможет проверять подписку на него", show_alert=True)
    except Exception as e:
        await call.answer("Бот не является администратором выбранного канала и не сможет проверять подписку на него", show_alert=True)

@dp.callback_query_handler(callback_buttons.filter(action=["public_channel"]), state=ConcursCreate.accept)
async def callbacks_public_channel(call: CallbackQuery, state: FSMContext, callback_data: dict):
    channel = int(callback_data['id'])
    try:
        chnl = await bot.get_chat_member(chat_id=channel, user_id=bot_id)
        can_post = chnl.can_post_messages or chnl.can_manage_chat
    except:
        can_post = False
    if can_post:
        check = await bot.get_chat_member(chat_id=channel, user_id=call['from']['id'])
        if check.status in ["administrator", "creator"] and check.can_post_messages:
            await call.message.delete()
            await state.update_data(public=channel, captcha=False, count=True)
            await get_public_concurs_info(state, call.message)
        else:
            await call.answer("Вы не являетесь администратором или редактором данного канала!", show_alert=True)
    else:
        await call.answer("Бот не является администратором выбранного канала!", show_alert=True)

@dp.callback_query_handler(state="*", text="otmena_captcha")
async def callbacks_omtena_captcha(call: CallbackQuery, state: FSMContext):
    await call.answer("Вы отказались от участия в конкурсе.")
    await call.message.delete()
    await state.finish()
    await registration(call['from']['id'], call.message)


@dp.callback_query_handler(text="random_button_on")
async def callbacks_random_on(call: CallbackQuery):
    await db.switch_random(call['from']['id'], True)
    await edit_settings_button(call.message, call['from']['id'], "edit")
    await call.answer("Кнопка рандома была включена")


@dp.callback_query_handler(text="random_button_off")
async def callbacks_random_off(call: CallbackQuery):
    await db.switch_random(call['from']['id'], False)
    await edit_settings_button(call.message, call['from']['id'], "edit")
    await call.answer("Кнопка рандома была отключена")

@dp.callback_query_handler(text="sep_button_on")
async def callbacks_random_on(call: CallbackQuery):
    await db.switch_sep(call['from']['id'], True)
    await edit_settings_button(call.message, call['from']['id'], "edit")
    await call.answer("Отдельный пост итогов был включен, список победителей опубликуется отдельным постом", show_alert=True)


@dp.callback_query_handler(text="sep_button_off")
async def callbacks_random_off(call: CallbackQuery):
    await db.switch_sep(call['from']['id'], False)
    await edit_settings_button(call.message, call['from']['id'], "edit")
    await call.answer("Отдельный пост итогов был выключен, основной пост розыгрыша будет отредактирован после подведения итогов", show_alert=True)

@dp.callback_query_handler(text="back_check_concurses")
async def callbacks_back_check_concurses(call: CallbackQuery):
    concurses, count = await db.get_pagined_concurses(call['from']['id'])
    if concurses:
        keyboard_inline_buttons, count = await get_paginate_concurses(concurses, count)
        await call.message.edit_text(
            f"Активные конкурсы (0-{min([count, paginate_limit_count])}/{count})",
            reply_markup=keyboard_inline_buttons)
    await call.answer()

@dp.callback_query_handler(text="back_channels", state='*')
async def callbacks_back_channel(call: CallbackQuery, state: FSMContext):
    await get_channels(call['from']['id'], call.message)
    await state.finish()
    await call.answer()

@dp.callback_query_handler(state=EditInfo.channels, text="Готово")
async def callbacks_add_channel(call: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await db.update_concurs_channels(state_data.get("channels", []), state_data['id'])
    await get_info_concurs(state_data['id'], call['from']['id'])
    await state.finish()
    await call.message.delete()
    return await call.answer("Каналы были успешно изменены")

@dp.callback_query_handler(state=ConcursCreate.select, text="Готово")
async def callbacks_add_channel(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    own_channels = data.get("own_channels", [])
    if len(own_channels):
        keyboard, count = await generate_paginate_accept_channels(own_channels, 0)
        await call.message.edit_text(f"Выбери канал, в котором будет проведен конкурс (0-{min([count, 0 + paginate_limit_count])}/{count})", reply_markup=keyboard)
        await ConcursCreate.accept.set()
    else:
        await call.message.answer("Не найдено добавленных каналов, в которых вы являетесь администратором или редактором", reply_markup=menu)
        await call.answer("Добавь канал, в котором ты администратор или редактор", show_alert=True)
        await call.message.delete()
        await state.finish()
    await call.answer()

@dp.callback_query_handler(state=ConcursCreate.end, text="change_addition_conditions")
async def callbacks_change_addition_conditions(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.delete()
    await call.message.answer(
        "Отправь сообщение, в котором будут указаны дополнительные условия (что именно должен предоставить участник для участия)",
        reply_markup=back_keyboard)
    await ConcursCreate.additional_conditions.set()

@dp.callback_query_handler(state=ConcursCreate.end, text="remove_addition_conditions")
async def callbacks_remove_addition_conditions(call: CallbackQuery, state: FSMContext):
    await call.answer("Дополнительные условия успешно отключены", show_alert=True)
    await state.update_data(condition=None)
    await call.message.delete()
    await get_public_concurs_info(state, call.message)

@dp.callback_query_handler(state="*")
async def callback(call: CallbackQuery, state: FSMContext):
    if "add_sub_" in call.data or "add_bot_" in call.data:
        await call.answer()
        data = call.data.replace("add_sub_", "").replace("add_bot_", "")
        button = data[0:data.find(" ")]
        if "✅" not in call.message.reply_markup['inline_keyboard'][int(button)][0]['text']:
            call.message.reply_markup['inline_keyboard'][int(button)][0]['text'] = "✅" + call.message.reply_markup[
                'inline_keyboard'][int(button)][0]['text']
            await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                                reply_markup=call.message.reply_markup)
        else:
            call.message.reply_markup['inline_keyboard'][int(button)][0]['text'] = \
            call.message.reply_markup['inline_keyboard'][int(button)][0]['text'].replace("✅", "")
            await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                                reply_markup=call.message.reply_markup)
