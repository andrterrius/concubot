import asyncio
import time
import json

from typing import Union, Optional

import asyncpg
from asyncpg.pool import Pool

class DB:
    def __init__(self, dsn, paginate_limit_count):
        self.dsn = dsn
        self.paginate_limit_count = paginate_limit_count
        self.pool: Optional[asyncpg.Pool] = None
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_init())

    async def async_init(self):
        self.pool: asyncpg.Pool = await asyncpg.create_pool(
            dsn=self.dsn,
            max_cached_statement_lifetime=0
        )
        return self

    async def get_all_concurses(self):
        async with self.pool.acquire() as conn:
            return await conn.fetchval('SELECT COUNT(id) FROM concurses')

    async def get_all_users(self):
        async with self.pool.acquire() as conn:
            return await conn.fetchval('SELECT COUNT(uid) FROM users')

    async def get_today_users(self, date):
        async with self.pool.acquire() as conn:
            return await conn.fetchval('SELECT COUNT(uid) FROM users WHERE reg_time similar to $1', date)

    async def get_user(self, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT * FROM users WHERE uid = $1', uid)

    async def get_user_channels(self, uid):
        start = time.time()
        async with self.pool.acquire() as conn:
            f = json.loads(await conn.fetchval('SELECT channels FROM users WHERE uid = $1', uid))
            print(time.time()-start)
            return f

    async def get_pagined_user_channels(self, uid, offset=0):
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch('SELECT jsonb_array_elements(channels) as channels, jsonb_array_length(channels) as count FROM users WHERE uid = $1 LIMIT $2 OFFSET $3', uid, self.paginate_limit_count, offset)
            except:
                return []

    async def get_pagined_concurses(self, owner, offset=0):
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                'SELECT id FROM concurses '
                'WHERE (owner = $1 OR trusts @> ARRAY[$1]::bigint[]) AND active = true '
                'ORDER BY id DESC '
                'LIMIT $2 OFFSET $3',
                owner,
                self.paginate_limit_count,
                offset
            )
            total_count = await conn.fetchval(
                'SELECT COUNT(*) FROM concurses '
                'WHERE (owner = $1) AND active = true',
                owner
            )
            return records, total_count

    async def get_pagined_winners(self, id, offset=0):
        async with self.pool.acquire() as conn:
            f = await conn.fetchval('SELECT winners_id FROM concurses WHERE id = $1', id)
            return f[offset:offset + self.paginate_limit_count], len(f)

    async def get_concurses(self, owner):
        async with self.pool.acquire() as conn:
            return await conn.fetch('SELECT id FROM concurses WHERE (owner = $1 OR trusts @> ARRAY[$1]::bigint[]) AND active = true ORDER BY id DESC', owner)

    async def get_info_concurs(self, id, uid=None):
        async with self.pool.acquire() as conn:
            select_values = "cardinality(participants) AS participants, id, count, winners_text, winners_id, winners, photo, button, message_text, time_complite, channels, public_id, message_id, copy_id, active, captcha, rerols, need_join, published, time_published, owner, trusts, condition, condition_owner, random_link, mentions"

            if uid:
                query = f'SELECT {select_values} FROM concurses WHERE (owner = $1 OR trusts @> ARRAY[$1]::bigint[]) AND id = $2'
                return await conn.fetchrow(query, uid, id)
            else:
                query = f'SELECT {select_values} FROM concurses WHERE id = $1'
                return await conn.fetchrow(query, id)

    async def get_info_concurs_not_owner(self, id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT cardinality(participants) AS participants, id, count, winners_text, winners_id, winners, photo, button, message_text, time_complite, channels, public_id, message_id, copy_id, active, captcha, rerols, need_join, published, time_published, owner, trusts, condition, condition_owner, random_link FROM concurses WHERE id = $1', id)

    async def get_owner_concurs(self, id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT owner FROM concurses WHERE id = $1', id)

    async def update_winners(self, id, winners_text, winners_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('UPDATE concurses SET active=false, winners_text = $1, winners_id = $2 WHERE id = $3', winners_text, winners_id, id)

    async def set_random_link(self, id, link):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('UPDATE concurses SET random_link = $1 WHERE id = $2', link, id)

    async def set_inactive(self, id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('UPDATE concurses SET active=false WHERE id = $1', id)

    async def rerol_change_winners(self, id, winners_id, winners_text, rerols):
        async with self.pool.acquire() as conn:
            return await conn.fetch('UPDATE concurses SET winners_id = $1, winners_text = $2, rerols = $3 WHERE id = $4', winners_id, winners_text, rerols, id)

    async def get_participants_concurs(self, id, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT participants, public_id FROM concurses WHERE (owner = $1 OR trusts @> ARRAY[$1]::bigint[]) AND id = $2', uid, id)

    async def get_participants_concurs_admin(self, id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT participants, public_id FROM concurses WHERE id = $1', id)

    async def get_stats(self, owner):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT count(cardinality(participants)) AS count, AVG(cardinality(participants)) AS avg, MAX(cardinality(participants)) AS max, MIN(cardinality(participants)) AS min FROM concurses WHERE owner = $1', owner)

    async def save_concurs(self, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval('INSERT INTO concurses (owner, photo, copy_id, message_text, button, winners, channels, time_complite, public_id, count, mentions,captcha, need_join, condition, condition_owner, time_published, published) '
                                      'VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, false) RETURNING id', *args)

    async def save_user(self, uid, reg_time):
        async with self.pool.acquire() as conn:
            return await conn.fetch('INSERT INTO users (uid, reg_time) '
                                      'VALUES($1, $2) ON CONFLICT DO NOTHING RETURNING id', uid, reg_time)

    async def set_concurs_message_id(self, id, message_id):
        async with self.pool.acquire() as conn:
            return await conn.execute('UPDATE concurses SET message_id = $1, published=true WHERE id = $2', message_id, id)

    async def switch_concurs_count(self, id, boolean):
        async with self.pool.acquire() as conn:
            return await conn.execute('UPDATE concurses SET count = $1 WHERE id = $2', boolean, id)

    async def switch_random(self, uid, boolean):
        async with self.pool.acquire() as conn:
            return await conn.execute('UPDATE users SET random = $1 WHERE uid = $2', boolean, uid)

    async def switch_sep(self, uid, boolean):
        async with self.pool.acquire() as conn:
            return await conn.execute('UPDATE users SET sep_result = $1 WHERE uid = $2', boolean, uid)

    async def get_settings_channel(self, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT channels FROM users WHERE uid = $1", uid)

    async def update_channels(self, channels, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("UPDATE users SET channels = $1 WHERE uid = $2", channels, uid)

    async def update_concurs_channels(self, channels, id):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("UPDATE concurses SET channels = $1 WHERE id = $2", channels, id)

    async def update_concurs_count_winners(self, winners, id):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("UPDATE concurses SET winners = $1 WHERE id = $2", winners, id)

    async def add_channel(self, channel, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("UPDATE users SET channels = $1 WHERE uid = $2", channel, uid)

    async def check_participate_concurs(self, id, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT id, channels, need_join FROM concurses WHERE id = $1 AND $2 != ALL(participants) AND active=true", id, uid)

    async def check_active_and_participate_concurs(self, need_join, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT id FROM concurses WHERE id=ANY($1::int[]) AND active=true AND $2 != ALL(participants)", need_join, uid)

    async def check_ban_user(self, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT ban FROM users WHERE uid = $1", uid)

    async def valid_needjoin_concurs(self, need_join):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT id FROM concurses WHERE id=ANY($1::int[]) AND active=true", need_join)

    async def participate_concurs(self, id, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('UPDATE concurses SET participants = array_append(participants, $1) WHERE id = $2 and $1 != ALL(participants) RETURNING cardinality(participants) AS participants, id, count, active, channels, public_id, message_id, button, condition, captcha', uid, id)

    async def set_complite_time(self, id, time='вручную'):
        async with self.pool.acquire() as conn:
            return await conn.fetch("UPDATE concurses SET time_complite = $1 WHERE id = $2", time, id)

    async def set_need_join(self, need_join, id):
        async with self.pool.acquire() as conn:
            return await conn.fetch("UPDATE concurses SET need_join = $1 WHERE id = $2", need_join, id)

    async def set_mentions(self, mentions, id):
        async with self.pool.acquire() as conn:
            return await conn.fetch("UPDATE concurses SET mentions = $1 WHERE id = $2", mentions, id)

    async def set_new_message_id(self, id, message_id):
        async with self.pool.acquire() as conn:
            return await conn.fetch("UPDATE concurses SET message_id = $1, photo = $2 WHERE id = $3", message_id, False, id)

    async def add_new_trusts(self, id, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetch("UPDATE concurses SET trusts = array_append(trusts, $1) WHERE id = $2 AND $1 != ALL(trusts)", uid, id)

    async def remove_trusts(self, id, uid):
        async with self.pool.acquire() as conn:
            return await conn.fetch("UPDATE concurses SET trusts = array_remove(trusts, $1) WHERE id = $2", uid, id)

    async def edit_concurs_condition(self, id, condition, condition_owner):
        async with self.pool.acquire() as conn:
            return await conn.fetch("UPDATE concurses SET condition = $1, condition_owner = $2 WHERE id = $3", condition, condition_owner, id)

    async def save_user_condition(self, uid, concurs_id, date, message, mediagroup=None, text=None, update=False):
        async with self.pool.acquire() as conn:
            if update:
                return await conn.fetch('UPDATE conditions SET date = $1, message = $2, mediagroup = $3, text = $4 WHERE uid = $5 AND concurs_id = $6', date, message, mediagroup, text, uid, concurs_id)
            else:
                return await conn.fetch('INSERT INTO conditions (uid, concurs_id, date, message, mediagroup, text) '
                                          'VALUES($1, $2, $3, $4, $5, $6)', uid, concurs_id, date, message, mediagroup, text)
    async def get_user_condition(self, uid, concurs_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT uid, concurs_id, date, message, mediagroup, text FROM conditions WHERE uid = $1 AND concurs_id = $2', uid, concurs_id)