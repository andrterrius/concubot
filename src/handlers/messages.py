import random

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter, Text, MediaGroupFilter
from aiogram_media_group import media_group_handler

from src.config import *
from src.utils import *
from src.keyboards import *
from src.states import *
from src.timers import *

@dp.message_handler(ChatTypeFilter(chat_type=types.ChatType.PRIVATE), state='*', commands=["start"])
async def handler(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    args = message.get_args()
    if args:
        if args == "webapp":
            await registration(uid, message)
            await state.finish()
        if "check" in args:
            concurs = int(args.replace("check-", ""))
            check = await db.get_info_concurs(concurs)
            if check:
                mentions = check['mentions'] + (uid == check['owner'] or uid in check['trusts'])
                if check['active']:
                    await message.answer(f"<b>Конкурс №{concurs}"
                                         f"\nЕще не завершился.</b>")
                elif not check['published']:
                    await message.answer(f"<b>Конкурс №{concurs}"
                                         f"\nЕще не опубликовался.</b>")
                else:
                    if check['winners_id']:
                        count = check['participants'] if check['count'] else "скрыто владельцем"
                        text_rerols = ""
                        if check['rerols']:
                            for rerol in json.loads(check['rerols']):
                                text_rerols += f"\n {await get_users([rerol['old']], rerol['old'], mentions=mentions )} => {await get_users([rerol['new']], rerol['new'], mentions=mentions)}"
                        username = await bot.get_chat(check['public_id'])
                        if username and "username" in username:
                            url = f"https://t.me/{username['username']}/{check['message_id']}"
                        else:
                            url = f"https://t.me/c/{str(check['public_id'])[4:]}/{check['message_id']}"
                        random_button = InlineKeyboardMarkup()
                        if check.get('random_link'):
                            random_button.add(InlineKeyboardButton(text='Проверить на random.org', url=check['random_link']))

                        winners_text = check['winners_text']
                        if mentions:
                            winners_text = await get_users(check['winners_id'], check['public_id'])

                        info_message = await message.answer(f"<b><a href='{url}'>Конкурс №{concurs}</a>"
                                             f"\nКоличество участников: {count}"
                                             f"\nПобедители конкурса: {winners_text}"
                                             f"\n{'Реролы: ' + text_rerols if text_rerols else 'Реролов не проводилось'}</b>", reply_markup=random_button)
                        check_owner = await db.get_info_concurs(concurs, message.from_user.id)
                        if check_owner:
                            keyboard_inline_buttons, count = await get_paginate_winners(concurs)
                            await info_message.reply(
                                f"Победители конкурса №{concurs} (0-{min([count, paginate_limit_count])}/{count})",
                                reply_markup=keyboard_inline_buttons)
                    else:
                        await message.answer(f"<b>Конкурс №{concurs}"
                                             f"\nУдален</b>")
        else:
            concurs = int(args)
            check_concurs = await db.get_info_concurs(concurs)
            if check_concurs and check_concurs['condition']:
                completed_condition = await db.get_user_condition(message.from_user.id, concurs)
                if completed_condition:
                    public_buttons = await get_participate_button_conditions(concurs, check_concurs)
                    if check_concurs.get("photo"):
                        await bot.copy_message(message.from_user.id, check_concurs["owner"], check_concurs['copy_id'],
                                               reply_markup=public_buttons)
                    else:
                        await bot.send_message(message.from_user.id, check_concurs['message_text'],
                                               reply_markup=public_buttons,
                                               disable_web_page_preview=True)
                    await asyncio.sleep(10)
                else:
                    channel_id = await bot.get_chat(chat_id=check_concurs['public_id'])
                    await AdditionalConditions.input_condition.set()
                    await state.update_data(concurs_id=concurs)
                    await message.answer(f"Администратор канала <b>{channel_id['title']}</b> запрашивает выполнение дополнительных условий"
                                         f"\nВнимательно прочтите и отправьте ответное сообщение для участия в конкурсе!")
                    await message.bot.copy_message(message.from_user.id, check_concurs["condition_owner"], check_concurs['condition'], reply_markup=otmena_keyboard)
                    return await registration(uid, message, quite=True)
                # answer = "".join(random.choices(capctha_symv, k=random.randint(5, 7)))
                # image.write(answer, f'{user}.png')
                # await state.update_data(concurs=concurs, answer=answer.lower())
                # await Captcha.input_captcha.set()
                # await message.answer_photo(open(f'{user}.png', 'rb'), caption=f"<b>Реши капчу</b>",
                #                            reply_markup=otmena_captcha)
                # return os.remove(f'{user}.png')
    await registration(uid, message)
    await state.finish()

@dp.message_handler(MediaGroupFilter(is_media_group=True), state=AdditionalConditions.input_condition, content_types=["photo", "video", "text"])
@media_group_handler
async def input_user_answer_condition_mediagroup(messages, state: FSMContext):
    media_group = []
    if messages[0].photo:
        file_id = messages[0].photo[-1].file_id
    else:
        file_id = messages[0][messages[0].content_type].file_id
    if messages[0].caption:
        media_group.append({'media': file_id, 'type': messages[0].content_type, 'caption': messages[0].html_text})
    else:
        media_group.append({'media': file_id, 'type': messages[0].content_type})
    for msg in messages[1:]:
        if msg.photo:
            file_id = msg.photo[-1].file_id
        else:
            file_id = msg[msg.content_type].file_id
        try:
            media_group.append({'media': file_id, 'type': msg.content_type})
        except:
            pass
    state_data = await state.get_data()
    message = messages[0]
    await db.save_user_condition(messages[0].from_user.id, state_data['concurs_id'], datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).replace(tzinfo=None), message.message_id, json.dumps(media_group), update=state_data.get("update"))
    await registration(message.from_user.id, message)
    concurs = state_data['concurs_id']
    check_concurs = await db.get_info_concurs(concurs)
    if check_concurs and check_concurs['condition']:
        completed_condition = await db.get_user_condition(message.from_user.id, concurs)
        if completed_condition:
            public_buttons = await get_participate_button_conditions(concurs, check_concurs)
            if check_concurs.get("photo"):
                await bot.copy_message(message.from_user.id, check_concurs["owner"], check_concurs['copy_id'],
                                       reply_markup=public_buttons)
            else:
                await bot.send_message(message.from_user.id, check_concurs['message_text'],
                                       reply_markup=public_buttons,
                                       disable_web_page_preview=True)
    await state.finish()

@dp.message_handler(state=AdditionalConditions.input_condition, content_types=["photo", "video", "text"])
async def input_user_answer_condition(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    if message.photo or message.video:
        file_id = message.photo[-1].file_id
        if message.caption:
            media_group = [{"media": file_id, "type": message.content_type, "caption": message.html_text}]
        else:
            media_group = [{"media": file_id, "type": message.content_type}]
        await message.answer_media_group(media_group)
        await db.save_user_condition(message.from_user.id, state_data['concurs_id'], datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).replace(tzinfo=None), message.message_id,
                                     json.dumps(media_group), update=state_data.get("update"))
    else:
        await db.save_user_condition(message.from_user.id, state_data['concurs_id'], datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).replace(tzinfo=None), message.message_id, update=state_data.get("update"), text=message.html_text)
    await registration(message.from_user.id, message)
    concurs = state_data['concurs_id']
    check_concurs = await db.get_info_concurs(concurs)
    public_buttons = await get_participate_button_conditions(concurs, check_concurs)
    if check_concurs.get("photo"):
        await bot.copy_message(message.from_user.id, check_concurs["owner"], check_concurs['copy_id'],
                               reply_markup=public_buttons)
    else:
        await bot.send_message(message.from_user.id, check_concurs['message_text'],
                               reply_markup=public_buttons,
                               disable_web_page_preview=True)
    await state.finish()

@dp.inline_handler()
async def inline_postbot(query: types.InlineQuery):
    post = query.query or None
    try:
        result = await db.get_info_concurs(int(query.query))
    except:
        return await inline_share(query)
    if result:
        try:
            username = await bot.get_chat(result['public_id'])
            if username and username['username'] is not None:
                url = f"https://t.me/{username['username']}/{result['message_id']}"
            else:
                url = f"https://t.me/c/{result['public_id'][4:]}/{result['message_id']}"
        except:
            return await inline_share(query)
        public_buttons = InlineKeyboardMarkup().add(InlineKeyboardButton(text=result["button"], url=url))
        articles = [types.InlineQueryResultArticle(
            id=post,
            title=f"Поделиться конкурсом №{post}",
            reply_markup=public_buttons,
            input_message_content=types.InputTextMessageContent(
                message_text=result["message_text"],
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        )]
        await query.answer(articles, cache_time=1)
    else:
        return await inline_share(query)

######################  ФУНКЦИЯ ДОБАВЛЕНИЯ КАНАЛА   ##############################################
@dp.message_handler(state=AddChannel.input_channel, content_types=types.ContentTypes.CHAT_SHARED)
async def input_channel_function_buttons(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    await check_channel(message.chat_shared['chat_id'], message.from_user.id, state, back_channels, state_data['offset'])

@dp.message_handler(state=AddChannel.input_channel, content_types=types.ContentTypes.ANY)
async def input_channel_function(message: types.Message, state: FSMContext):
    msg = str(message.text)
    state_data = await state.get_data()
    back_channels = InlineKeyboardMarkup()
    back_channels.add(InlineKeyboardButton(text="Назад", callback_data=paginate_buttons.new(offset=state_data['offset'], action="get_paginate_channels")))
    if message.forward_from_chat:
        await check_channel(message.forward_from_chat['id'], message.from_user.id, state, back_channels, state_data['offset'])
    elif message.entities:
        if (message.entities[0].type == 'url' and "https://t.me/" in msg) or (
                message.entities[0].type == 'mention' and msg[0] == "@"):
            await check_channel(msg.replace("https://t.me/", "@"), message.from_user.id, state, back_channels, state_data['offset'])
    else:
        await message.answer('❌Канала не существует', reply_markup=back_channels)

@dp.message_handler(state=ConcursCreate.select, content_types=types.ContentTypes.CHAT_SHARED)
async def create_input_channel_function_buttons(message: types.Message, state: FSMContext):
    async def paginate_selected(id):
        state_data = await state.get_data()
        channels = await db.get_pagined_user_channels(message.from_user.id, 0)
        keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
        yet_channls = state_data.get('channels', [])
        if yet_channls != []:
            yet_channls.append(id)
        else:
            yet_channls = [id]
        await state.update_data(channels=yet_channls)
        if channels:
            keyboard_inline_buttons, count = await generate_paginate_select_channels(channels,
                                                                                     yet_channls,
                                                                                     0)
            await message.answer(
                f"Выбери каналы, на которые нужно подписаться ({0}-{min([count, 0 + paginate_limit_count])}/{count})\nИли отправь айди/ссылку/пост канала",
                reply_markup=keyboard_inline_buttons)
        else:
            keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал",
                                                             callback_data=paginate_buttons.new(offset=0,
                                                                                                action="add_channel")))
            await message.answer('Каналов еще нет', reply_markup=keyboard_inline_buttons)

    id = await check_channel(message.chat_shared['chat_id'], message.from_user.id, state, None, 0, False)
    if id:
        await paginate_selected(id)
        own_channel = await check_admin_channel(id, message['from']['id'])
        if own_channel:
            state_data = await state.get_data()
            await state.update_data(own_channels=state_data['own_channels'] + [own_channel])
        return
    await message.answer('❌Ошибка при добавлении канала')

@dp.message_handler(state=ConcursCreate.select, content_types=types.ContentTypes.TEXT)
async def input_channel_function(message: types.Message, state: FSMContext):

    async def paginate_selected(id):
        state_data = await state.get_data()
        channels = await db.get_pagined_user_channels(message.from_user.id, 0)
        keyboard_inline_buttons = InlineKeyboardMarkup(row_width=2)
        yet_channls = state_data.get('channels', [])
        if yet_channls != []:
            yet_channls.append(id)
        else:
            yet_channls = [id]
        await state.update_data(channels=yet_channls)
        if channels:
            keyboard_inline_buttons, count = await generate_paginate_select_channels(channels,
                                                                                     yet_channls,
                                                                                     0)
            await message.answer(
                f"Выбери каналы, на которые нужно подписаться ({0}-{min([count, 0 + paginate_limit_count])}/{count})\nИли отправь айди/ссылку/пост канала",
                reply_markup=keyboard_inline_buttons)
        else:
            keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал",
                                                             callback_data=paginate_buttons.new(offset=0,
                                                                                                action="add_channel")))
            await message.answer('Каналов еще нет', reply_markup=keyboard_inline_buttons)

    msg = str(message.text)
    state_data = await state.get_data()
    if message.forward_from_chat:
        id = await check_channel(message.forward_from_chat['id'], message.from_user.id, state, None, 0, False)
        if id:
            await paginate_selected(id)
            own_channel = await check_admin_channel(id, message.from_user.id)
            if own_channel:
                state_data = await state.get_data()
                await state.update_data(own_channels=state_data['own_channels'] + [own_channel])
            return
    elif message.entities:
        if (message.entities[0].type == 'url' and "https://t.me/" in msg) or (message.entities[0].type == 'mention' and msg[0] == "@"):
            id = await check_channel(msg.replace("https://t.me/", "@"), message.from_user.id, state, None, 0, False)
            if id:
                await paginate_selected(id)
                own_channel = await check_admin_channel(id, message.from_user.id)
                if own_channel:
                    state_data = await state.get_data()
                    await state.update_data(own_channels=state_data['own_channels'] + [own_channel])
                return
    await message.answer('❌Ошибка при добавлении канала')


######################  ФУНКЦИИ СОЗДАНИЯ КОНКУРСА   ##############################################
@dp.message_handler(state=ConcursCreate.how_complite_input, content_types=['text'])
async def concurs_create_how_complite_input(message: types.Message, state: FSMContext):
    try:
        time_complite = datetime.datetime.strptime(message.text, "%d.%m.%Y %H:%M:%S")
        if time.mktime(time_complite.timetuple()) <= time.mktime(
                datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).timetuple()):
            return await message.reply("Вы ввели время, которое уже прошло")
        await state.update_data(time_complite=time_complite)
        await state.update_data(time_complite_str=message.text)
        await message.reply(f"Конкурс будет завершен в {message.text}", reply_markup=omtmena_and_back_add_channel_keyboard)
        await ConcursCreate.select.set()
        await select_channels(state, message.from_user.id)
    except Exception as e:
        await message.reply(get_postpone_text)

@dp.message_handler(state=ConcursCreate.timer_publicate, content_types=['text'])
async def concurs_create_how_timer_publicate(message: types.Message, state: FSMContext):
    try:
        time_publicate = datetime.datetime.strptime(message.text, "%d.%m.%Y %H:%M:%S")
        if time.mktime(time_publicate.timetuple()) <= time.mktime(
                datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).timetuple()):
            return await message.reply("Вы ввели время, которое уже прошло")
        await state.update_data(time_publicate=time_publicate)
        await state.update_data(time_publicate_str=message.text)
        await message.reply(f"Конкурс будет опубликован в {message.text}")
        await ConcursCreate.how_complite.set()
        await message.answer('Настройки публикации и завершения конкурса', reply_markup=how_complite_keyboard)
    except Exception as e:
        await message.reply(get_postpone_text())

@dp.message_handler(state=ConcursCreate.how_complite, content_types=['text'])
async def concurs_create_how_colpite(message: types.Message, state: FSMContext):
    if message.text == "Завершить по времени":
        await ConcursCreate.how_complite_input.set()
        return await message.reply(get_postpone_text(),
                                   reply_markup=omtmena_and_back_keyboard)
    elif message.text == "Завершить вручную":
        await message.reply("Конкурс будет завершен вручную", reply_markup=omtmena_and_back_add_channel_keyboard)
        await ConcursCreate.select.set()
        await select_channels(state, message.from_user.id)
        await state.update_data(time_complite_str="вручную")
    elif message.text == "Запланированная публикация":
        await ConcursCreate.timer_publicate.set()
        return await message.reply(get_postpone_text(),
                                   reply_markup=omtmena_and_back_keyboard)
    else:
        await message.reply("Нажмите на кнопки ниже для настройки таймера")

@dp.message_handler(state=ConcursCreate.winers, content_types=['text'])
async def concurs_create_winners(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 1:
        await message.reply("Введите количество победителей корректно")
        return
    await state.update_data(winners=int(message.text), channels=[])
    await ConcursCreate.how_complite.set()
    await message.answer('Настройки публикации и завершения конкурса', reply_markup=how_complite_keyboard)


@dp.message_handler(state=ConcursCreate.button, content_types=types.ContentTypes.ANY)
async def concurs_create_button(message: types.Message, state: FSMContext):
    if message['text']:
        await state.update_data(button=message.text)
        await ConcursCreate.winers.set()
        await message.answer('Введи количество победителей', reply_markup=omtmena_and_back_keyboard)
    else:
        await message.answer('Я не нашел в твоем сообщении текст для кнопки')


@dp.message_handler(state=EditInfo.winers, content_types=['text'])
async def concurs_edit_winners(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 1:
        await message.reply("Введите количество победителей корректно")
        return
    state_data = await state.get_data()
    await db.update_concurs_count_winners(int(message.text), state_data['id'])
    await message.answer('Количество победителей успешно изменено')
    await get_info_concurs(state_data['id'], message.from_user.id)
    await state.finish()

@dp.message_handler(state=EditInfo.need_join, content_types=['text'])
async def concurs_edit_need_join(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    try:
        if message.text != "0":
            ids = list(map(int, message.text.split(",")))
            valid_ids = await db.valid_needjoin_concurs(ids)
            await db.set_need_join([id['id'] for id in valid_ids], state_data['id'])
            await message.answer('Конкурсы для обязательного участия были успешно обновлены')
        else:
            await db.set_need_join([], state_data['id'])
        await get_info_concurs(state_data['id'], message.from_user.id)
        await state.finish()
    except:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=state_data['id'],
                                                                                           action="check_concurs")))
        await message.answer("Произошла ошибка, попробуй еще раз")
        await message.answer("Отправь айди конкурсов, в которых нужно участвовать через запятую"
                             "\nПример: <code>1, 2, 3</code> (Если конкурс один, то достаточно отправить лишь число-номер конкурса без запятых)"
                             "\nИли отправь <code>0</code> для выключения проверки на участие",
                             reply_markup=keyboard)

@dp.message_handler(state=EditInfo.additional_conditions, content_types=['text', 'photo', 'video'])
async def concurs_edit_need_join(message: types.Message, state: FSMContext):
    try:
        state_data = await state.get_data()
        await db.edit_concurs_condition(state_data['id'], message.message_id, message.from_user.id)
        await state.finish()
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="Посмотреть текущее условие",
                                          callback_data=callback_buttons.new(id=state_data['id'],
                                                                             action="edit_get_condition")))
        keyboard.add(InlineKeyboardButton(text="Изменить условие",
                                          callback_data=callback_buttons.new(id=state_data['id'],
                                                                             action="edit_edit_condition")))
        keyboard.add(InlineKeyboardButton(text="Назад", callback_data=callback_buttons.new(id=state_data['id'],
                                                                                           action="edit_info")))
        await message.answer("Дополнительное условие успешно изменено!", reply_markup=keyboard)
    except:
        await message.answer("Произошла ошибка, попробуй еще раз")

@dp.message_handler(state=EditInfo.time_complite, content_types=['text'])
async def concurs_edit_time_complite(message: types.Message, state: FSMContext):
    try:
        keyboard = InlineKeyboardMarkup()
        state_data = await state.get_data()
        keyboard.add(InlineKeyboardButton(text="Назад",
                                          callback_data=callback_buttons.new(id=state_data['id'],
                                                                             action="check_concurs")))
        time_complite = datetime.datetime.strptime(message.text, "%d.%m.%Y %H:%M:%S")
        if time.mktime(time_complite.timetuple()) <= time.mktime(
                datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).timetuple()):
            return await message.reply("Вы ввели время, которое уже прошло", reply_markup=keyboard)
        if time.mktime(time_complite.timetuple()) <= time.mktime(
                datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).timetuple()):
            await message.answer(
                f'Конкурс не будет завершен по времени, так как оно уже прошло')
        else:
            try:
                scheduler.remove_job(str(state_data['id']))
            except:
                pass
            scheduler.add_job(timer, "date", run_date=time_complite, timezone="Europe/Moscow",
                              id=str(state_data['id']), args=(message.from_user.id, state_data['id']))
            await db.set_complite_time(state_data['id'], time_complite.strftime("%d.%m.%Y %H:%M:%S"))
            await message.reply(f"Конкурс будет завершен в {message.text}")
            await get_info_concurs(state_data['id'], message.from_user.id)
            await state.finish()

    except Exception as e:
        await message.reply(get_postpone_text())

@dp.message_handler(Text("опубликовать", ignore_case=True), state=ConcursCreate.end, content_types=['text'])
async def concurs_create_public(message: types.Message, state: FSMContext):
    try:
        state_data = await state.get_data()
        id = int(await db.save_concurs(
            message.from_user.id,
            state_data.get("photo"),
            state_data.get("copy_id"),
            state_data.get("message"),
            state_data.get("button"),
            state_data.get("winners"),
            state_data.get("channels", []),
            state_data.get("time_complite_str"),
            state_data.get("public"),
            state_data.get("count", True),
            state_data.get("mentions", True),
            state_data.get("captcha"),
            state_data.get("need_join", []),
            state_data.get("condition"),
            message.from_user.id,
            state_data.get("time_publicate_str"),
        ))
        if not state_data.get("time_publicate_str"):
            public_buttons = await get_participate_button(id, state_data)
            if state_data.get("photo"):
                msg_id = await bot.copy_message(state_data["public"], state_data["user_id"], state_data['copy_id'],
                                                reply_markup=public_buttons)
            else:
                msg_id = await bot.send_message(state_data["public"], state_data['message'], reply_markup=public_buttons,
                                                disable_web_page_preview=True)
            await db.set_concurs_message_id(id, msg_id['message_id'])
            await message.answer(f'Конкурс №{id} опубликован', reply_markup=menu)
            try:
                await bot.send_message(admin,
                                       f"Пользователь <b>{await get_users([message.from_user.id], message.from_user.id)}</b> создал конкурс №{id}:")
                await bot.forward_message(admin, state_data['public'], msg_id['message_id'])
            except:
                pass
        else:
            scheduler.add_job(auto_publicate, "date", run_date=state_data['time_publicate'], timezone="Europe/Moscow",
                              id=f"p_{id}", args=(message.from_user.id, id))
            await message.answer(f'Конкурс №{id} будет опубликован {state_data["time_publicate_str"]}', reply_markup=menu)
            try:
                await bot.send_message(admin,
                                       f"Пользователь <b>{await get_users([message.from_user.id], message.from_user.id)}</b> запланировал конкурс №{id}:")
            except:
                pass
        await state.finish()
        await get_info_concurs(id, message.from_user.id)
        if state_data['time_complite_str'] != "вручную":
            time_complite = datetime.datetime.strptime(str(state_data['time_complite']), "%Y-%m-%d %H:%M:%S")
            if time.mktime(time_complite.timetuple()) <= time.mktime(
                    datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).timetuple()):
                await message.answer(
                    f'Конкурс не будет закончен по времени, так как оно уже прошло, вы сможете завершить его только вручную')
            else:
                scheduler.add_job(timer, "date", run_date=state_data['time_complite'], timezone="Europe/Moscow",
                                  id=str(id), args=(message.from_user.id, id))
    except:
        await message.answer('Не смог опубликовать конкурс')


@dp.message_handler(state=ConcursCreate.end, content_types=['text'])
async def concurs_create_accept(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    if message.text == "Выключить автообновление участников":
        await state.update_data(count=False)
        await message.answer(
            '<b>Автообновление участников на кнопке выключено, теперь участников обновить можно будет только вручную в информации о конкурсе\nЕсли хотите обратно включить автообновление участников, нажмите на кнопку "Включить автообновление участников"</b>',
            reply_markup=await last_create_keyboard(state))
    elif message.text == "Включить автообновление участников":
        await state.update_data(count=True)
        await message.answer(
            '<b>Автообновление участников на кнопке включено\nЕсли хотите выключить автообновление участников, нажмите на кнопку "Выключить автообновление участников"</b>',
            reply_markup=await last_create_keyboard(state))

    elif message.text == "Выключить упоминание победителей":
        await state.update_data(mentions=False)
        await message.answer('<b>Упоминание победителей было выключено\nТеперь только владелец и совледельцы конкурса могут получить ссылки на профили победителей</b>',
                             reply_markup=await last_create_keyboard(state))
    elif message.text == "Включить упоминание победителей":
        await state.update_data(mentions=True)
        await message.answer('<b>Упоминание победителей было включено\nТеперь все пользователи конкурса могут получить ссылки на профили победителей</b>',
                             reply_markup=await last_create_keyboard(state))

    elif message.text == "🔥Выключить капчу🔥":
        await state.update_data(captcha=False)
        await message.answer('<b>Капча была выключена</b>',
                             reply_markup=await last_create_keyboard(state))
    elif message.text == "🔥Включить капчу🔥":
        await state.update_data(captcha=True)
        await message.answer('<b>Капча включена</b>',
                             reply_markup=await last_create_keyboard(state))
    elif message.text == "🆕Дополнительные условия🆕":
        if state_data.get('condition'):
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("Изменить условия", callback_data="change_addition_conditions"))\
                .add(InlineKeyboardButton("Убрать условия", callback_data="remove_addition_conditions"))
            await message.bot.copy_message(message.from_user.id, message.from_user.id, state_data.get('condition'), reply_markup=keyboard)
        else:
            await message.answer("Отправь сообщение, в котором будут указаны дополнительные условия (что именно должен предоставить участник для участия)",
                                 reply_markup=back_keyboard)
            await ConcursCreate.additional_conditions.set()
    elif message.text == "Посмотреть пост":
        public_buttons = InlineKeyboardMarkup().add(
            InlineKeyboardButton(text=state_data['button'], callback_data="public post"))
        if state_data['photo']:
            await message.bot.copy_message(state_data["user_id"], state_data["user_id"], state_data['copy_id'],
                                   reply_markup=public_buttons)
        else:
            await message.bot.send_message(state_data["user_id"], state_data['message'], reply_markup=public_buttons,
                                            disable_web_page_preview=True)
    elif message.text == "Проверка участия":
        await message.answer("Отправь айди конкурсов, в которых нужно участвовать через запятую"
                             "\nПример: <code>1, 2, 3</code> (Если конкурс один, то достаточно отправить лишь число-номер конкурса без запятых)"
                             "\nИли отправь <code>0</code> для выключения проверки на участие",
                             reply_markup=back_keyboard)
        await ConcursCreate.need_join.set()

@dp.message_handler(state=ConcursCreate.additional_conditions, content_types=['text', 'photo', 'video'])
async def concurs_create_additional_conditions(message: types.Message, state: FSMContext):
    try:
        await state.update_data(condition=message.message_id)
        await get_public_concurs_info(state, message)
    except:
        await message.answer("Произошла ошибка, попробуй еще раз")

@dp.message_handler(state=ConcursCreate.need_join, content_types=['text'])
async def concurs_create_need_join(message: types.Message, state: FSMContext):
    try:
        if message.text != "0":
            ids = list(map(int, message.text.split(",")))
            valid_ids = await db.valid_needjoin_concurs(ids)
            await state.update_data(need_join=[id['id'] for id in valid_ids])
        else:
            await state.update_data(need_join=[])
        await get_public_concurs_info(state, message)
    except:
        await message.answer("Произошла ошибка, попробуй еще раз")
        await message.answer("Отправь айди конкурсов, в которых нужно участвовать через запятую"
                             "\nПример: <code>1, 2, 3</code> (Если конкурс один, то достаточно отправить лишь число-номер конкурса без запятых)"
                             "\nИли отправь <code>0</code> для выключения проверки на участие")

@dp.message_handler(state=ConcursCreate.message, content_types=['text', 'photo', 'video'])
async def concurs_create_message(message: types.Message, state: FSMContext):
    if message['text'] or message['caption']:
        if message['caption']:
            await state.update_data(photo=True)
            copy_id = await bot.copy_message(message.chat.id, message.chat.id, message.message_id,
                                             reply_markup=omtmena_and_back_keyboard)
            await state.update_data(copy_id=copy_id['message_id'])
        else:
            await state.update_data(photo=False)
        await state.update_data(user_id=message.from_user.id)
        await state.update_data(message=message.html_text)
        await ConcursCreate.button.set()
        await message.answer('Введи текст для кнопки', reply_markup=names_button)
    else:
        await message.answer('Введи сообщение с текстом', reply_markup=otmena_keyboard)

@dp.message_handler(state=TrustsUsers.input_trust_id)
async def input_trust_id(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Назад",
                                      callback_data=callback_buttons.new(id=state_data['id'],
                                                                         action="check_concurs")))
    await message.delete()
    if "forward_origin" in message:
        if message.forward_from:
            await db.add_new_trusts(state_data['id'], message.forward_from.id)
            user = await message.bot.get_chat_member(chat_id=message.forward_from.id, user_id=message.forward_from.id)
            subowner_text = user.user.full_name
            if user.user.username:
                subowner_text = f"@{user.user.username}"
            await message.answer(f"{subowner_text} теперь совладелец твоего конкурса №{state_data['id']}")
            await get_info_concurs(state_data['id'], message.chat.id)
            await state.finish()
        elif message.forward_from_chat:
            await message.answer("Перешли личное сообщение от кого, кому хочешь выдать права на управление конкурсом", reply_markup=keyboard)
        else:
            await message.answer("<b>‼Этот пользователь скрыл свой айди при пересылке."
                                 "\n<a href='https://telegram.org/blog/unsend-privacy-emoji#anonymous-forwarding'>Подробнее об этой фиче</a></b>", reply_markup=keyboard)
    else:
        await message.answer("Перешли личное сообщение от кого, кому хочешь выдать права на управление конкурсом", reply_markup=keyboard)

@dp.message_handler(Text("создать конкурс", ignore_case=True), ChatTypeFilter(chat_type=types.ChatType.PRIVATE))
async def handler_create_concurs(message: types.Message, state: FSMContext):
    usr = await db.get_user(message.from_user.id)
    if usr['ban']:
        return await message.answer('Вы заблокированы')
    check = await check_sub(message.from_user.id)
    if check:
        if len(usr['channels']) == 2:
            keyboard_inline_buttons = InlineKeyboardMarkup()
            keyboard_inline_buttons.add(InlineKeyboardButton(text="Добавить канал", callback_data=paginate_buttons.new(offset=0, action="add_channel")))
            return await message.answer('Каналов еще нет', reply_markup=keyboard_inline_buttons)
        await message.answer('Отправь пост конкурса', reply_markup=otmena_keyboard)
        await ConcursCreate.message.set()
        own_channels = await get_owner_channels(message.from_user.id)
        await state.update_data(own_channels=own_channels)
    else:
        await message.answer(need_sub_text, reply_markup=need_sub_news)

@dp.message_handler(Text("каналы", ignore_case=True), ChatTypeFilter(chat_type=types.ChatType.PRIVATE))
async def handler_channels(message: types.Message, state: FSMContext):
    await get_channels(message.from_user.id)


@dp.message_handler(Text("статистика", ignore_case=True), ChatTypeFilter(chat_type=types.ChatType.PRIVATE))
async def handler_stats(message: types.Message, state: FSMContext):
    stats = await db.get_stats(message.from_user.id)
    if stats['count']:
        stats_text = f"\n\nВсего конкурсов: <b>{stats['count']}🎁</b>" \
                     f"\n\nМаксимальное количество участников: <b>{stats['max']}👥</b>" \
                     f"\n\nМинимальное количество участников: <b>{stats['min']}👤</b>" \
                     f"\n\nСреднее количество участников: <b>{int(stats['avg'])}〰️</b>"
        await message.answer(
            f"Твоя статистика: {stats_text}")
        await bot.send_message(admin, f"<b>{await get_users([message.from_user.id], message.from_user.id)}</b> посмотрел статистику: {stats_text}")
    else:
        await message.answer("Недостаточно информации для подведения статистики")


@dp.message_handler(Text("конкурсы", ignore_case=True), ChatTypeFilter(chat_type=types.ChatType.PRIVATE))
async def handler_concurses(message: types.Message, state: FSMContext):
    concurses, count = await db.get_pagined_concurses(message.from_user.id)
    concurses, count = await get_paginate_concurses(concurses, count)
    if concurses and count > 0:
        await message.answer(f"Активные конкурсы (0-{min([count, paginate_limit_count])}/{count})", reply_markup=concurses)
    else:
        await message.answer("У тебя нет активных конкурсов", reply_markup=create_concurs)


@dp.message_handler(Text("настройки", ignore_case=True), ChatTypeFilter(chat_type=types.ChatType.PRIVATE))
async def handler_settings(message: types.Message, state: FSMContext):
    await edit_settings_button(message, message.from_user.id)

@dp.message_handler(ChatTypeFilter(chat_type=types.ChatType.PRIVATE))
async def default_answer(message: types.Message):
    await message.answer(start_text, reply_markup=menu)