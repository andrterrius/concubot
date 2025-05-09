import os
import motor.motor_asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher
from apscheduler.jobstores.mongodb import MongoDBJobStore
from telegraph.aio import Telegraph
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.callback_data import CallbackData
from captcha.image import ImageCaptcha
from motor import motor_asyncio

from randomorg import RandomJSONRPC
from src.database import DB

from dotenv_vault import load_dotenv
load_dotenv()

pg_dsn = os.getenv("POSTGRESQL-DSN")

cluster = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB-DSN"))
andrey_concurses = cluster["Terri"]["andrconcu"]
bots = []

webapp_domen = "https://concubot.site"

admin = 1109091191
bot_token = os.getenv("BOT-TOKEN")

bot = Bot(bot_token, parse_mode="HTML", disable_web_page_preview=True)
bot_id = int(bot_token.split(":")[0])

short_name = os.getenv("BOT-USERNAME")

dp = Dispatcher(bot, storage=MemoryStorage())

jobstores = {
  'default': MongoDBJobStore(database='shedulers', collection='shedulers', host=os.getenv("MONGODB-DSN"), port=27017)
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

random_api = os.getenv("RANDOMORG-TOKEN")
telegraph = Telegraph()
random_client = RandomJSONRPC(random_api)

start_text = 'Наш бот поможет вам провести конкурс в своем канале <b>совершенно бесплатно</b>!\nДля создания конкурса добавь свой канал, нажав на кнопку "Каналы" и после нажать "Создать конкурс"\nКанал с новостями: @concubot_news'
need_sub_text = "<b>Для создания конкурса необходимо подписаться на наш <a href='https://t.me/concubot_news'>новостной канал❗</a></b>"

image = ImageCaptcha(width=200, height=90)
capctha_symv = "01234567890123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+-!%&*()#@"

callback_buttons = CallbackData("button", "id", "action")
winner_info = CallbackData("button", "offset", "id", "uid", "action")
rerol_button_data = CallbackData("button", "id", "uid", "action")
paginate_buttons = CallbackData("button", "offset", "action")
paginate_winners = CallbackData("button", "offset", "id", "action")

paginate_limit_count = 10

db = DB(pg_dsn, paginate_limit_count)
