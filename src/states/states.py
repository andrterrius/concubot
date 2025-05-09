from aiogram.dispatcher.filters.state import State, StatesGroup

class ConcursCreate(StatesGroup):
    message = State()
    button = State()
    winers = State()
    how_complite = State()
    how_complite_input = State()
    timer_publicate = State()
    select = State()
    accept = State()
    public = State()
    end = State()
    need_join = State()
    additional_conditions = State()

class AddChannel(StatesGroup):
    input_channel = State()

class EditInfo(StatesGroup):
    winers = State()
    channels = State()
    time_complite = State()
    need_join = State()
    additional_conditions = State()

class Captcha(StatesGroup):
    input_captcha = State()

class TrustsUsers(StatesGroup):
    input_trust_id = State()

class AdditionalConditions(StatesGroup):
    input_condition = State()