from src.config import *
from src.utils import *
from aiogram.utils.deep_linking import get_start_link
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import numpy as np
import base64
import json

async def auto_publicate(user_id, concurs_id):
    result = await db.get_info_concurs(concurs_id)
    if not result['published'] and result['active']:
        try:
            public_buttons = InlineKeyboardMarkup().add(
                InlineKeyboardButton(text=result['button'], url=await get_webapp(result['id']))) if result[
                'captcha'] else InlineKeyboardMarkup().add(InlineKeyboardButton(text=result['button'],
                                                                                callback_data=callback_buttons.new(
                                                                                    id=result['id'],
                                                                                    action="join_concurs")))
            if result.get("photo"):
                msg_id = await bot.copy_message(result["public_id"], user_id, result['copy_id'],
                                                reply_markup=public_buttons)
            else:
                msg_id = await bot.send_message(result["public_id"], result['message_text'], reply_markup=public_buttons,
                                                disable_web_page_preview=True)
            await db.set_concurs_message_id(result['id'], msg_id['message_id'])
            await get_info_concurs(result['id'], user_id)
            await bot.send_message(user_id, f"Конкурс №{result['id']} опубликован!")
        except Exception as e:
            await bot.send_message(admin, e)
            await bot.send_message(user_id, f"Конкурс №{result['id']} не был опубликован по таймеру")
    else:
        await bot.send_message(user_id, f"Конкурс №{result['id']} не был опубликован по таймеру")

async def timer(user_id, concurs_id):
    result = await db.get_info_concurs(concurs_id)
    try:
        if result["active"]:
            if result['participants'] > 1:
                if result['winners'] > result['participants']:
                    do = result['participants']
                else:
                    do = result['winners']
                user = await db.get_user(user_id)
                participants = await db.get_participants_concurs_admin(concurs_id)
                participants = participants['participants']
                linkz = await get_start_link(f"check-{result['id']}")
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
                                counter += 1
                            except Exception as e:
                                print(e, part)
                        text_winers = await get_users(winners, result['public_id'], mentions=result['mentions'])
                        response = await telegraph.create_page(
                            f"Итоги конкурса №{result['id']}",
                            html_content=f"<p>Победители конкурса: {text_winers}</p>\n<p>Результат рандом орга: <b>{result_list['random']['data']}</b></p>\n<p><a href='{link}'><b>👉Проверить результат на рандом орге👈</b>\n</a></p>\n<p><h3>Участники конкурса:</h3></p>\n<p class='participants'>{participants_text}</p>",
                            author_name="Concu Bot",
                            author_url="https://t.me/concubot"
                        )
                        random_button = InlineKeyboardMarkup()
                        random_button.add(InlineKeyboardButton(text='Проверить на random.org', url=response['url']))
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
                                await bot.edit_message_text(result[
                                                                'message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                            result['public_id'], result['message_id'],
                                                            reply_markup=random_button, disable_web_page_preview=True)
                        await db.update_winners(result['id'], text_winers, winners)
                        await db.set_random_link(result['id'], response['url'])
                        keyboard = InlineKeyboardMarkup()
                        keyboard.add(InlineKeyboardButton(text="Перейти к конкурсу",
                                             url=f"https://t.me/c/{str(result['public_id'])[4:]}/{result['message_id']}"))
                        msg_info = await bot.send_message(user_id,
                            f"Конкурс №{result['id']} завершен"
                            f"\nКоличество участников: {result['participants']} "
                            f"\n<b><a href='{linkz}'>Победители</a>:</b> {text_winers}",
                            reply_markup=keyboard)
                        keyboard_inline_buttons, count = await get_paginate_winners(result['id'])
                        await msg_info.reply(
                            f"<b>Победители конкурса №{result['id']} (0-{min([count, paginate_limit_count])}/{count})</b>",
                            reply_markup=keyboard_inline_buttons)
                    except:
                        await bot.send_message(user_id,
                                               f"Произошла ошибка при подведении итогов по таймеру конкурса {result['id']}")
                        await db.set_complite_time(result['id'])

                else:
                    winers = np.random.choice(participants, do, replace=False)
                    text_winers = await get_users(winers, result['public_id'], mentions=result['mentions'])
                    try:
                        if result['photo']:
                            text = result['message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}'
                            if len(text) > 1024 or user['sep_result']:
                                await bot.edit_message_reply_markup(result['public_id'], result['message_id'],
                                                                    reply_markup=None)
                                msg_id = await bot.send_message(result['public_id'],
                                                                f'<b><a href="{linkz}">Победители</a>:</b> {text_winers}',
                                                                reply_to_message_id=result['message_id'])
                                await db.set_new_message_id(result['id'], msg_id['message_id'])
                            else:
                                await bot.edit_message_caption(result['public_id'], result['message_id'],
                                                               caption=result[
                                                                           'message_text'] + f'\n\n<b><a href="{linkz}">Победители</a>:</b> {text_winers}')
                                rerol_button = InlineKeyboardMarkup()
                                if result['winners'] < result['participants']:
                                    rerol_button.add(InlineKeyboardButton(text='Рерольнуть победителей',
                                                                          callback_data=callback_buttons.new(
                                                                              id=concurs_id,
                                                                              action="get_winers_to_rerol")))
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
                        msg_info = await bot.send_message(user_id,
                                                          f"Конкурс №{result['id']} завершен"
                                                          f"\nКоличество участников: {result['participants']} "
                                                          f"\n<b><a href='{linkz}'>Победители</a>:</b> {text_winers}",
                                                          reply_markup=keyboard)
                        keyboard_inline_buttons, count = await get_paginate_winners(result['id'])
                        await msg_info.reply(
                            f"<b>Победители конкурса №{result['id']} (0-{min([count, paginate_limit_count])}/{count})</b>",
                            reply_markup=keyboard_inline_buttons)
                    except:
                        await bot.send_message(user_id, f"Произошла ошибка при подведении итогов по таймеру конкурса {result['id']}")
                        await db.set_complite_time(result['id'])
            else:
                await bot.send_message(user_id, f"Конкурс №{result['id']} не завершен, потому что в нем участвовало меньше 2 человек")
                await db.set_complite_time(result['id'])
    except Exception as e:
        await bot.send_message(admin, e)
        await bot.send_message(user_id, f"Конкурс №{result['id']} не завершен по времени, потому что произошла какая-то ошибка")
        await db.set_complite_time(result['id'])
