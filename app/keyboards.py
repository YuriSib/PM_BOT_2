from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

start_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Авторизоваться', callback_data='sign_in')],
    [InlineKeyboardButton(text='Информация', callback_data='info')]])


menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Загрузить таблицу', callback_data='load_table'),
     InlineKeyboardButton(text='Информация', callback_data='info')],
    [InlineKeyboardButton(text='Добавить товар в ВК', callback_data='add_product_to_vk')]])

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Загрузить таблицу', callback_data='load_table')],
    [InlineKeyboardButton(text='Сделать подсчет работ', callback_data='work_count')],
    [InlineKeyboardButton(text='Добавить товар в ВК', callback_data='add_product_to_vk')],
    [InlineKeyboardButton(text='Информация', callback_data='info')]],)


choice_action = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Добавление переноса строк', callback_data='add_br'),
     InlineKeyboardButton(text='Подсчет работ', callback_data='cnt')],
    [InlineKeyboardButton(text='ОБНОВИТЬ НАИМЕНОВАНИЯ (для импорта в СБИС)', callback_data='name_update'),
     InlineKeyboardButton(text='ОБНОВИТЬ КОЛОНКУ ЦЕН (для обновления прайса)', callback_data='cost_update')],
    [InlineKeyboardButton(text='Залить таблицу в систему учета', callback_data='upload')],
    [InlineKeyboardButton(text='Назад в главное меню', callback_data='back_to_menu')]
])

admin_choice_action = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Добавление переноса строк', callback_data='add_br'),
     InlineKeyboardButton(text='Подсчет работ', callback_data='cnt')],
    [InlineKeyboardButton(text='ОБНОВИТЬ НАИМЕНОВАНИЯ (для импорта в СБИС)', callback_data='name_update'),
     InlineKeyboardButton(text='ОБНОВИТЬ КОЛОНКУ ЦЕН (для обновления прайса)', callback_data='cost_update')],
    [InlineKeyboardButton(text='Залить таблицу в систему учета', callback_data='upload')],
    [InlineKeyboardButton(text='Залить таблицу как другой пользователь', callback_data='admin_upload')],
    [InlineKeyboardButton(text='Назад в главное меню', callback_data='back_to_menu')],
])


async def user_list(users: list) -> InlineKeyboardMarkup:
    row = []
    for users in users:
        name, id_ = users[1], users[0]
        row.append([InlineKeyboardButton(text=name, callback_data=f'имя_{id_}')])
    row.append([InlineKeyboardButton(text='Назад в главное меню', callback_data='back_to_menu')])

    return InlineKeyboardMarkup(inline_keyboard=row)
