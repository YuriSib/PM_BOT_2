import os
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types.input_file import FSInputFile
from psycopg.errors import InvalidTextRepresentation

from add_to_vk import ProductIntegrations
from settings import TOKEN, path_to_tables, WORK_CNT_DB, POL_MEL_DB
from xl_worker import line_breaks, cards_count, work_cnt, name_update, price_update
import app.keyboards as kb
import sqlite_comands as sql
from logger import logger


router = Router()
bot = Bot(TOKEN)


@router.message(F.text == '/start')
async def menu(message: Message):
    DB = sql.DBMagic(POL_MEL_DB)
    user_data = await DB.check_exist("Users", "tg_id", str(message.from_user.id))
    logger.debug(user_data)

    if user_data:
        user_name = user_data[0][1]
        if message.from_user.id != 674796107:
            await bot.send_message(chat_id=message.from_user.id, text=f'Здравствуй, {user_name}! Cтарт работы бота:',
                                   reply_markup=kb.menu)
        else:
            await bot.send_message(chat_id=message.from_user.id,
                                   text=f'Здравствуй, {user_name}! У тебя права администратора',
                                   reply_markup=kb.admin_menu)
    else:
        await message.answer('Старт работы бота:', reply_markup=kb.start_menu)


@router.callback_query(lambda callback_query: callback_query.data.startswith('back_to_menu'))
async def sign_in(callback: CallbackQuery, bot):
    try:
        await bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)
    except Exception:
        pass
    if callback.from_user.id != 674796107:
        await bot.send_message(chat_id=callback.from_user.id, text='Выберите пункт:', reply_markup=kb.menu)
    else:
        await bot.send_message(chat_id=callback.from_user.id, text='Выберите пункт:', reply_markup=kb.admin_menu)


class WorkerName(StatesGroup):
    name = State()


@router.callback_query(lambda callback_query: callback_query.data.startswith('sign_in'))
async def sign_in(message: Message, state: FSMContext):
    await state.set_state(WorkerName.name)
    await message.answer(f'Ваше имя')
    await bot.send_message(chat_id=message.from_user.id, text='Введите ваше имя:')


@router.message(WorkerName.name)
async def save_user(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    name = message.text

    DB = sql.DBMagic(POL_MEL_DB)
    user_data = await DB.check_exist("Users", "user_name", name)
    logger.debug(user_data)
    if not user_data:
        logger.warning(f"Пользователь с ником {name} зарегестрировался!", message.chat.id, message.chat.full_name)
        await DB.add_data("Users", {"tg_id": int(message.from_user.id), "user_name": name})
        await message.bot.send_message(chat_id=message.chat.id, text=f'{name}, вы успешно авторизовались!',
                                       reply_markup=kb.menu)
    else:
        await message.bot.send_message(chat_id=message.chat.id, text=f'Имя {name} уже зарегестрированно!',
                                       reply_markup=kb.start_menu)


@router.callback_query(lambda callback_query: callback_query.data.startswith('work_count'))
async def sign_in(message: Message):
    current_date = datetime.now()
    formatted_date = current_date.strftime('%d-%m-%y')
    table_name = f'work_cnt_{formatted_date}.xlsx'

    DB = sql.DBMagic(POL_MEL_DB)
    verified_status = await DB.check_exist("Tables", "verified_status", False)
    if verified_status:
        await work_cnt(table_name)
        await bot.send_document(chat_id=message.from_user.id, document=FSInputFile(path=f'{path_to_tables}/{table_name}'))
        DB = sql.DBMagic(POL_MEL_DB)
        await DB.update_verified_status()
    else:
        await bot.send_message(chat_id=message.from_user.id, text='Новых таблиц нет!')


@router.callback_query(lambda callback_query: callback_query.data.startswith('info'))
async def get_xl(callback: CallbackQuery, bot):
    await bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)
    await bot.send_message(chat_id=callback.from_user.id,
                           text='Карточки в зависимости от их наполненности будут подразделятся на 2 типа. \n'
                                '   1. Полный - в карточке не менее 3-х строк описания, "Бренд", "Страна" и другой '
                                'аттрибут фильтрации, например "Тип". Такая карточка оценевается в 9 рублей. \n'
                                '   2. Не полный - не менее 2-х строк описания, "Бренд" и "Страна". Такая карточка '
                                'оценивается в 6 рублей.',
                           reply_markup=kb.menu)


class FileBox(StatesGroup):
    file = State()
    document_name = State()
    file_path = State()

    # min_cost, max_cost = State(), State()


@router.callback_query(lambda callback_query: callback_query.data.startswith('load_table'))
async def get_xl(message: Message, state: FSMContext):
    await state.set_state(FileBox.file)
    await message.answer(f'Перешлите боту таблицу для редактирования.')
    await bot.send_message(chat_id=message.from_user.id, text='Перешлите боту таблицу.')


@router.message(FileBox.file)
async def quantity_five(message: Message, state: FSMContext):
    await state.update_data(file=message.document)

    DB = sql.DBMagic(POL_MEL_DB)
    user_data = await DB.check_exist("Users", "tg_id", str(message.from_user.id))
    user_name = user_data[0][1]
    document_name = message.document.file_name
    logger.info(f"Пользователь {user_name} прикрепил таблицу {document_name}")
    DB = sql.DBMagic(POL_MEL_DB)
    if not await DB.check_exist("Tables", "table_name", document_name):
        await state.update_data(document_name=document_name)

        file_id = message.document.file_id
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        await state.update_data(file_path=file_path)

        file_path_to_tables = os.path.join("/pm_bot/tables/", document_name)
        await bot.download_file(file_path, file_path_to_tables)
        if message.from_user.id != 674796107:
            await message.bot.send_message(chat_id=message.chat.id, text='Выберите что делать с таблицей',
                                           reply_markup=kb.choice_action)
        else:
            await message.bot.send_message(chat_id=message.chat.id, text='Выберите что делать с таблицей',
                                           reply_markup=kb.admin_choice_action)
    else:
        await message.bot.send_message(chat_id=message.chat.id,
                                       text='Таблица с таким именем уже есть с системе. Переименуйте ее или '
                                            'обратитесь к администратору.', reply_markup=kb.menu)


@router.callback_query(FileBox.file, lambda callback_query: callback_query.data.startswith('add_br'))
async def add_br(message: Message, state: FSMContext):
    await state.set_state(FileBox.file)
    data = await state.get_data()
    file, document_name = data['file'], data['document_name']

    file_path = os.path.join('tables', document_name)
    errors_answer = await line_breaks(file_path)
    if errors_answer:
        await message.bot.send_message(chat_id=message.from_user.id, text=errors_answer)
        await message.bot.send_message(chat_id=message.from_user.id, text='Загрузите таблицу заново', reply_markup=kb.menu)
    else:
        await message.bot.send_document(chat_id=message.from_user.id, document=FSInputFile(path=file_path))
        await message.bot.send_message(chat_id=message.from_user.id, text='Выберите пункт', reply_markup=kb.choice_action)


@router.callback_query(FileBox.file, lambda callback_query: callback_query.data.startswith('name_update'))
async def update_product_name(message: Message, state: FSMContext):
    await state.set_state(FileBox.file)
    data = await state.get_data()
    file, document_name, file_path = data['file'], data['document_name'], data['file_path']
    await message.bot.send_message(chat_id=message.from_user.id, text="Обновление наименований займет время, подожди!")

    file_path = os.path.join('tables', document_name)
    answer = await name_update(file_path)
    if not answer:
        await message.bot.send_message(chat_id=message.from_user.id, text='Загрузите таблицу заново', reply_markup=kb.menu)
    else:
        await message.bot.send_document(chat_id=message.from_user.id, document=FSInputFile(path=file_path))
        await message.bot.send_message(chat_id=message.from_user.id, text=answer, reply_markup=kb.choice_action)


@router.callback_query(FileBox.file, lambda callback_query: callback_query.data.startswith('cost_update'))
async def update_costs(message: Message, state: FSMContext):
    await state.set_state(FileBox.file)
    data = await state.get_data()
    file, document_name, file_path = data['file'], data['document_name'], data['file_path']
    await message.bot.send_message(chat_id=message.from_user.id, text="Обновление поля цен займет время, подожди!")

    file_path = os.path.join('tables', document_name)

    answer = await price_update(file_path)
    if type(answer) is str:
        await message.bot.send_message(chat_id=message.from_user.id, text=answer, reply_markup=kb.menu)
    else:
        await message.bot.send_document(chat_id=message.from_user.id, document=FSInputFile(path=file_path))
        await message.bot.send_message(chat_id=message.from_user.id, text="Обновлено!", reply_markup=kb.choice_action)


@router.callback_query(FileBox.file, lambda callback_query: callback_query.data.startswith('cnt'))
async def cnt_cards(message: Message, state: FSMContext):
    await state.set_state(FileBox.file)
    data = await state.get_data()
    file, document_name, file_path = data['file'], data['document_name'], data['file_path']
    user_id = message.from_user.id
    cards_amount = await cards_count(document_name)
    if type(cards_amount) is str:
        await message.bot.send_message(chat_id=user_id, text='Загрузите таблицу заново', reply_markup=kb.menu)
    elif not os.path.exists(document_name):
        await message.bot.send_message(chat_id=user_id, text='Таблица с таким именем уже существует!',
                                       reply_markup=kb.menu)
    else:
        await message.bot.send_message(chat_id=user_id,
                                       text=f'Неполные карточки: {cards_amount[0]}\nПолные карточки: {cards_amount[1]}')
        await message.bot.send_message(chat_id=user_id, text='Загрузите еще таблицу', reply_markup=kb.choice_action)


@router.callback_query(FileBox.file, lambda callback_query: callback_query.data.startswith('upload'))
async def add_table(message: Message, state: FSMContext):
    logger.info('Заливаю таблицу в систему учета')
    await state.set_state(FileBox.file)
    await message.answer(text='Подождите, идет обработка запроса!')
    data = await state.get_data()
    document_name = data['document_name']
    logger.info(f'Получил document_name - {document_name}')
    file_path_to_tables = os.path.join("/pm_bot/tables/", document_name)
    cards_amount = await cards_count(file_path_to_tables)

    user_id = message.from_user.id

    DB = sql.DBMagic(POL_MEL_DB)
    try:
        logger.info('Добавляю таблицу в БД')
        await DB.add_data("Tables",
                              {
                                  "table_name": document_name,
                                  "reg_time": datetime.now(),
                                  "min_cost": cards_amount[0],
                                  "max_cost": cards_amount[1],
                                  "user_id": user_id
                                    })
    except InvalidTextRepresentation:
        await message.bot.send_message(chat_id=user_id, text='Ошибка. Загруженная таблица имеет неправильные поля.',
                                       reply_markup=kb.menu)
    else:
        await message.bot.send_message(chat_id=user_id,
                                       text='Таблица загружена в учетную систему!', reply_markup=kb.choice_action)
        logger.info(f'Таблица {document_name} загружена в учетную систему!')


@router.callback_query(FileBox.file, lambda callback_query: callback_query.data.startswith('admin_upload'))
async def choice_user(message: Message):
    if message.from_user.id == 674796107:
        DB = sql.DBMagic(POL_MEL_DB)
        user_list = await DB.check_exist("Users")
        logger.debug(f"user_list - {user_list}")
        await message.bot.send_message(chat_id=message.from_user.id,
                                       text='Выбери пользователя', reply_markup=await kb.user_list(user_list))
    else:
        await message.bot.send_message(chat_id=message.from_user.id,
                                       text='Не достаточно прав!', reply_markup=await kb.menu)


@router.callback_query(FileBox.file, lambda callback_query: callback_query.data.startswith('имя_'))
async def add_table(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FileBox.file)
    await callback.answer(text='Подождите, идет обработка запроса!')

    data = await state.get_data()
    document_name = data['document_name']
    file_path_to_tables = os.path.join("/pm_bot/tables/", document_name)
    cards_amount = await cards_count(file_path_to_tables)

    user_id = int(callback.data.replace('имя_', ''))
    DB = sql.DBMagic(POL_MEL_DB)
    await DB.add_data("Tables",
                      {
                          "table_name": document_name,
                          "reg_time": datetime.now(),
                          "min_cost": cards_amount[0],
                          "max_cost": cards_amount[1],
                          "user_id": user_id
                      })
    await callback.bot.send_message(chat_id=callback.from_user.id,
                                    text='Карточка загружена в учетную систему!', reply_markup=kb.choice_action)


class SBIS_ID(StatesGroup):
    sbis_id = State()


@router.callback_query(lambda callback_query: callback_query.data.startswith('add_product_to_vk'))
async def add_product(message: Message, state: FSMContext):
    if message.from_user.id not in (674796107, 6593479727):
        await message.bot.send_message(chat_id=message.from_user.id, text=f'Недостаточно прав!', reply_markup=kb.menu)
    else:
        await state.set_state(SBIS_ID.sbis_id)
        await bot.send_message(chat_id=message.from_user.id, text='Введите SBIS ID:')


@router.message(SBIS_ID.sbis_id)
async def save_user(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    sbis_id = message.text
    po = ProductIntegrations()
    sync_result = await po.sync_one_prod(sbis_id)
    if sync_result:
        await bot.send_message(chat_id=message.from_user.id, text=sync_result)
    else:
        await bot.send_message(chat_id=message.from_user.id, text='Товар добавлен в ВК!')
