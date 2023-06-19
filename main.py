import sqlite3
import datetime
from aiogram import executor
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.storage import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from statistics import get_statistics
import configparser

config = configparser.ConfigParser()
config.read("config.ini")
TOKEN = config['Telegram']['token']
USER_ID = config['Telegram']['user_id']
print(USER_ID)
storage = MemoryStorage()
bot = Bot(token=f'{TOKEN}')
dp = Dispatcher(bot, storage=storage)


# Класс состояния для отслеживания состояний пользователей
class YourState(StatesGroup):
    wait_question = State()
    wait_anonymity = State()
    wait_multiple_answers = State()
    wait_answers = State()

def is_user_allowed(user_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM allowed_users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if bool(user) or USER_ID != "":
        return 1
    else:
        return 0

    conn.close()

    return bool(user)

# Создание таблицы для хранения информации о группе
def create_groups_table():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            members_count INTEGER,
            date_added TEXT,
            status INTEGER,
            date_removed TEXT,
            last_modified TEXT
        )
    ''')

    conn.commit()
    conn.close()


def create_poll_direct_table():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poll_direct (
            poll_id INTEGER PRIMARY KEY,
            question TEXT,
            chat_id INTEGER,
            datetime DATETIME,
            status INTEGER,
            message_id INTEGER,
            options BLOB,
            poll_removed DATETIME,
            poll_data BLOB
        )
    ''')

    conn.commit()
    conn.close()



def create_allowed_users_table():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS allowed_users (
            user_id INTEGER PRIMARY KEY
        )
    ''')

    conn.commit()
    conn.close()

# Удаление опубликованного опроса
async def delete_poll(poll_id):
    # Вызов метода stop_poll с указанием идентификатора чата и идентификатора опроса
    await bot.stop_poll(chat_id='GROUP_CHAT_ID', message_id=poll_id)

@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def on_new_chat_members(message: types.Message):
    # Получение информации о группе
    chat_id = message.chat.id
    chat_title = message.chat.title

    # Получение количества участников группы
    members_count = await bot.get_chat_members_count(chat_id)

    # Дата и время добавления
    date_added = datetime.datetime.now()

    # Статус
    status = 1

    # Создание соединения с базой данных
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # Проверка, существует ли таблица groups
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
    table_exists = cursor.fetchone()

    if not table_exists:
        # Таблица groups не существует, создаем ее
        create_groups_table()

    # Проверка, существует ли уже запись для этой группы
    cursor.execute('SELECT * FROM groups WHERE chat_id = ?', (chat_id,))
    existing_group = cursor.fetchone()

    if existing_group:
        # Группа уже существует в базе данных, обновляем значения
        cursor.execute('UPDATE groups SET status = ?, date_removed = NULL, last_modified = ? WHERE chat_id = ?', (status, date_added, chat_id))
    else:
        # Вставка информации о новой группе в таблицу
        cursor.execute('INSERT INTO groups (chat_id, chat_title, members_count, date_added, status, last_modified) VALUES (?, ?, ?, ?, ?, ?)',
                       (chat_id, chat_title, members_count, date_added, status, date_added))

    # Сохранение изменений и закрытие соединения
    conn.commit()
    conn.close()

@dp.message_handler(content_types=types.ContentType.LEFT_CHAT_MEMBER)
async def on_left_chat_member(message: types.Message):
    # Получение информации о группе
    chat_id = message.chat.id

    # Дата и время удаления
    date_removed = datetime.datetime.now()

    # Создание соединения с базой данных
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    try:
        # Обновление информации о группе в таблице
        cursor.execute('UPDATE groups SET status = 0, date_removed = ?, last_modified = ? WHERE chat_id = ?', (date_removed, date_removed, chat_id))

        # Сохранение изменений и закрытие соединения
        conn.commit()
        conn.close()
    except sqlite3.OperationalError:
        # Обработка ошибки при отсутствии таблицы
        create_groups_table()

        # Повторная попытка обновления информации о группе в таблице
        cursor.execute('UPDATE groups SET status = 0, date_removed = ?, last_modified = ? WHERE chat_id = ?', (date_removed, date_removed, chat_id))

        # Сохранение изменений и закрытие соединения
        conn.commit()
        conn.close()

@dp.message_handler(commands=['start'])
async def start_question(message: types.Message):
    user_id = message.from_user.id
    if is_user_allowed(user_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Создать опрос", "Опросы", "Группы", "Статистика", "Вернуться в главное меню"]
        keyboard.add(*buttons)
        await message.answer("Приветствую! Выбери интересующий пункт", reply_markup=keyboard)
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.") # тут можно дописать текст

@dp.message_handler(lambda message: message.text == "Вернуться в главное меню")
async def return_start(message: types.Message):
    user_id = message.from_user.id
    if is_user_allowed(user_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Создать опрос", "Опросы", "Группы", "Статистика", "Вернуться в главное меню"]
        keyboard.add(*buttons)
        await message.answer("Приветствую! Выбери интересующий пункт", reply_markup=keyboard)
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")


@dp.message_handler(lambda message: message.text == "Статистика")
async def question_fork(message: types.Message):
    user_id = message.from_user.id
    # Получение обновлений (сообщений) из API бота
    updates = await bot.get_updates()
    # Обработка каждого обновления (сообщения)
    if is_user_allowed(user_id):
        file_name = await get_statistics()
        doc_file = open(file_name, "rb")
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Вернуться в главное меню"]
        keyboard.add(*buttons)
        await message.answer("Ожидайте. Файл с информацией будет направлен в диалог.", reply_markup=keyboard)
        await message.answer_document(document=doc_file)
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")



@dp.message_handler(lambda message: message.text == "Опросы")
async def question_fork(message: types.Message):
    user_id = message.from_user.id
    # Получение обновлений (сообщений) из API бота
    updates = await bot.get_updates()
    # Обработка каждого обновления (сообщения)
    if is_user_allowed(user_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Активные опросы", "Результаты опросов", "Вернуться в главное меню"]
        keyboard.add(*buttons)
        await message.answer("Приветствую! Выбери интересующий пункт", reply_markup=keyboard)
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")


@dp.message_handler(lambda message: message.text == "Активные опросы")
async def active_question(message: types.Message):
    user_id = message.from_user.id
    # Получение списка активных опросов из базы данных
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT  p.question, g.chat_title, p.datetime, p.status FROM poll_direct p JOIN groups g ON p.chat_id = g.chat_id '
                   'WHERE p.status = 1')
    activate_polls = cursor.fetchall()
    conn.close()

    if is_user_allowed(message.from_user.id):
        if activate_polls:
            for poll in activate_polls:
                question_data = poll[0]
                group_data = poll[1]
                date_time_data = datetime.datetime.strptime(poll[2], '%Y-%m-%d %H:%M:%S.%f')
                date_time_data = date_time_data.strftime('%H:%M %d.%m.%Y')
                # Формирование информации об опросе для вывода
                response = f"Активный опрос c вопросом: {question_data}\nразмещён в группе: {group_data}\nв {date_time_data}"
                await message.answer(response)
        else:
            response = f"Все опросы завершены"
            await message.answer(response)
    else:
        await message.answer("Доступ закрыт.")


@dp.message_handler(lambda message: message.text == "Результаты опросов")
async def result_question(message: types.Message):
    user_id = message.from_user.id
    # Получение обновлений (сообщений) из API бота
    updates = await bot.get_updates()
    # Обработка каждого обновления (сообщения)
    if is_user_allowed(user_id):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Завершить конкретный опрос", "Завершить все активные опросы",  "Вернуться в главное меню"]
        keyboard.add(*buttons)
        await message.answer("Получение результатов опроса возможно только после его завершения.\n", reply_markup=keyboard)
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")

@dp.message_handler(lambda message: message.text == "Завершить конкретный опрос")
async def result_question(message: types.Message):
    buttons_poll.clear()
    user_id = message.from_user.id
    # Получение обновлений (сообщений) из API бота
    updates = await bot.get_updates()
    # Обработка каждого обновления (сообщения)
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT  p.question, g.chat_title, p.datetime, p.status, p.poll_id FROM poll_direct p JOIN groups g ON p.chat_id = g.chat_id '
        'WHERE p.status = 1')
    activate_polls = cursor.fetchall()
    conn.close()
    if is_user_allowed(user_id):
        for index, poll in enumerate(activate_polls):
            question_data = poll[0]
            group_data = poll[1]
            date_time_data = datetime.datetime.strptime(poll[2], '%Y-%m-%d %H:%M:%S.%f')
            date_time_data = date_time_data.strftime('%H:%M %d.%m.%Y')
            # Формирование информации об опросе для вывода
            await message.answer(f"{index+1}). Опрос с вопросом: '{question_data}'\nразмещённый в группе: '{group_data}'\nв {date_time_data}\nИдентификатор: {poll[4]}")
            buttons_poll.append(f"{index+1}): {poll[4]}")
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons_poll.append("Вернуться в главное меню")
        keyboard.add(*buttons_poll)
        await message.answer("Выберите нужный номер для завершения соответствующего опроса и получения его результатов:", reply_markup=keyboard)
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")

@dp.message_handler(lambda message: message.text in buttons_poll)
async def result_question(message: types.Message):
    poll_id_data = message.text.split(': ')
    poll_id_data = poll_id_data[1]
    user_id = message.from_user.id
    # Получение обновлений (сообщений) из API бота
    updates = await bot.get_updates()
    # Обработка каждого обновления (сообщения)
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT p.poll_id, p.question, p.chat_id, p.message_id, p.datetime, g.chat_title, p.status '
                   f'FROM poll_direct p JOIN groups g ON p.chat_id = g.chat_id WHERE p.status = 1 AND p.poll_id = {poll_id_data}')
    activate_polls = cursor.fetchall()

    if is_user_allowed(user_id):
        for poll in activate_polls:
            poll_id = poll[0]
            question = poll[1]
            chat_id = poll[2]
            message_id = poll[3]
            date_time_data = datetime.datetime.strptime(poll[4], '%Y-%m-%d %H:%M:%S.%f')
            date_time_data = date_time_data.strftime('%H:%M %d.%m.%Y')
            group_title = poll[5]
            try:
                # Получение результатов опроса
                result = await bot.stop_poll(chat_id, message_id)
                if result:
                    poll_question = result.question
                    options = result.options
                    total_voters = result.total_voter_count

                    response = f"Результаты опроса '{poll_question}'\nв группе {group_title}\nот {date_time_data}:\n\n"
                    response += f"Всего проголосовало: {total_voters}\n"
                    for i, option in enumerate(options):
                        response += f"{i + 1}) '{option.text}'\n"
                        response += f"Количество выборов: {option.voter_count}\n"
                    await message.answer(response)

                # Обновление статуса опроса в базе данных
                cursor.execute('UPDATE poll_direct SET status = 0, date_removed = ?, poll_data = ? WHERE poll_id = ?',
                               (datetime.datetime.now(), str(result), poll_id))
                conn.commit()

            except Exception as e:
                await message.answer(f"Произошла ошибка при получении результатов опроса ID: {poll_id}")
                print(e)



        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Вернуться в главное меню"]
        keyboard.add(*buttons)
        await message.answer("Опросы завершен.\n", reply_markup=keyboard)
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")
    conn.close()

@dp.message_handler(lambda message: message.text == "Завершить все активные опросы")
async def result_question(message: types.Message):
    user_id = message.from_user.id
    # Получение обновлений (сообщений) из API бота
    updates = await bot.get_updates()
    # Обработка каждого обновления (сообщения)

    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT p.poll_id, p.question, p.chat_id, p.message_id, p.datetime, g.chat_title, p.status '
                   'FROM poll_direct p JOIN groups g ON p.chat_id = g.chat_id WHERE p.status = 1')
    activate_polls = cursor.fetchall()

    if is_user_allowed(user_id):
        for poll in activate_polls:
            poll_id = poll[0]
            question = poll[1]
            chat_id = poll[2]
            message_id = poll[3]
            date_time_data = datetime.datetime.strptime(poll[4], '%Y-%m-%d %H:%M:%S.%f')
            date_time_data = date_time_data.strftime('%H:%M %d.%m.%Y')
            group_title = poll[5]
            try:
                # Получение результатов опроса
                result = await bot.stop_poll(chat_id, message_id)
                if result:
                    poll_question = result.question
                    options = result.options
                    total_voters = result.total_voter_count

                    response = f"Результаты опроса '{poll_question}'\nв группе {group_title}\nот {date_time_data}:\n\n"
                    response += f"Всего проголосовало: {total_voters}\n"
                    for i, option in enumerate(options):
                        response += f"{i + 1}) '{option.text}'\n"
                        response += f"Количество выборов: {option.voter_count}\n"
                    await message.answer(response)

                # Обновление статуса опроса в базе данных
                cursor.execute('UPDATE poll_direct SET status = 0, date_removed = ?, poll_data = ? WHERE poll_id = ?',
                               (datetime.datetime.now(), str(result), poll_id))
                conn.commit()

            except Exception as e:
                await message.answer(f"Произошла ошибка при получении результатов опроса ID: {poll_id}")
                print(e)



        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Вернуться в главное меню"]
        keyboard.add(*buttons)
        await message.answer("Все опросы завершены.\n", reply_markup=keyboard)
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")
    conn.close()

@dp.message_handler(lambda message: message.text == "Группы")
async def group_question(message: types.Message):
    user_id = message.from_user.id
    # Создание соединения с базой данных
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    # Получение списка групп, в которых бот состоит
    cursor.execute('SELECT chat_id, chat_title, members_count FROM groups WHERE status = 1')
    groups = cursor.fetchall()
    # Сохранение изменений и закрытие соединения
    conn.commit()
    conn.close()
    if is_user_allowed(user_id):
        await message.answer("Привет! Вот список групп в которых я состою:\n(Идентификатор, название, колличество участников)")
        for i, group in enumerate(groups):
            await message.answer(f"{i+1}) {group}")
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")

@dp.message_handler(lambda message: message.text == "Создать опрос")
async def create_question(message: types.Message):
    user_id = message.from_user.id

    if is_user_allowed(user_id):
        # Запуск состояния ожидания вопроса
        await YourState.wait_question.set()
        await message.answer("Привет! Я помогу тебе создать опрос. Напиши свой вопрос:")
    else:
        # Сообщение о закрытом доступе
        await message.answer("Доступ закрыт.")

@dp.message_handler(state=YourState.wait_question)
async def process_question(message: types.Message, state: FSMContext):
    # Получение вопроса от пользователя
    question = message.text

    # Сохранение вопроса в состоянии
    await state.update_data(question=question)

    # Переход к ожиданию анонимности
    await YourState.wait_anonymity.set()
    await message.answer("Отлично! Теперь укажи, будет ли опрос анонимным (Да/Нет)")

@dp.message_handler(state=YourState.wait_anonymity)
async def process_anonymity(message: types.Message, state: FSMContext):
    # Получение выбранной анонимности от пользователя
    anonymity = message.text.lower()

    if anonymity not in ['да', 'нет']:
        await message.answer("Некорректный ответ. Пожалуйста, укажи, будет ли опрос анонимным (Да/Нет)")
        return

    # Сохранение анонимности в состоянии
    await state.update_data(anonymity=anonymity)

    # Переход к ожиданию нескольких ответов
    await YourState.wait_multiple_answers.set()
    await message.answer("Отлично! Теперь укажи, можно ли выбрать несколько вариантов ответа (Да/Нет)")

@dp.message_handler(state=YourState.wait_multiple_answers)
async def process_multiple_answers(message: types.Message, state: FSMContext):
    # Получение выбора нескольких ответов от пользователя
    multiple_answers = message.text.lower()

    if multiple_answers not in ['да', 'нет']:
        await message.answer("Некорректный ответ. Пожалуйста, укажи, можно ли выбрать несколько вариантов ответа (Да/Нет)")
        return

    # Сохранение выбора нескольких ответов в состоянии
    await state.update_data(multiple_answers=multiple_answers)

    # Переход к ожиданию вариантов ответов
    await YourState.wait_answers.set()
    await message.answer("Отлично! Теперь напиши варианты ответов, каждый с новой строки \nПри наличии одного правильного ответа, он должен находится в первой строке.")

@dp.message_handler(state=YourState.wait_answers)
async def process_answers(message: types.Message, state: FSMContext):
    # Разделение текста на строки
    answers = message.text.split('\n')
    answers = [answer for answer in answers if answer.strip()]  # Удаление пустых строк

    if len(answers) <= 1:
        await message.answer("Необходимо ввести хотя бы два варианта ответа.")
        return

    # Получение данных из состояния
    data = await state.get_data()
    question = data.get('question')
    anonymity = data.get('anonymity')
    multiple_answers = data.get('multiple_answers')

    # Формирование списка вариантов ответов в формате PollOption
    options = [str(answer) for answer in answers]

    # Определение типа опроса на основе выбора нескольких ответов
    if multiple_answers == 'да':
        poll_type = types.PollType.REGULAR
    else:
        poll_type = types.PollType.QUIZ

    # Создание соединения с базой данных
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()

    # Получение списка групп, в которых бот состоит
    cursor.execute('SELECT chat_id FROM groups WHERE status = 1')
    groups = cursor.fetchall()

    # Отправка опроса в каждую группу
    for group in groups:
        chat_id = group[0]
        if multiple_answers == 'да':
            sent_message = await bot.send_poll(chat_id, question, options, type=poll_type,
                                allows_multiple_answers=(multiple_answers == 'да'), is_anonymous=(anonymity == 'да'))
        else:
            sent_message = await bot.send_poll(chat_id, question, options, type=poll_type, correct_option_id=0,
                                allows_multiple_answers=(multiple_answers == 'да'), is_anonymous=(anonymity == 'да'))

        # Получение poll_id размещенного опроса
        if sent_message.poll:
            poll_id = sent_message.poll.id
            message_id = sent_message.message_id
        else:
            # Обработка случая, когда опрос отсутствует
            # Можно сгенерировать ошибку, вывести сообщение об ошибке или выполнить другое действие
            poll_id = None
            message_id = None

        # Получение текущей даты и времени
        current_datetime = datetime.datetime.now()
        status_poll = 1
        # Сохранение информации в базе данных

        cursor.execute(
            'INSERT INTO poll_direct (poll_id, question, chat_id, datetime, status, message_id, options) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (poll_id, question, chat_id, current_datetime, status_poll, message_id, str(options)))

    # Сохранение изменений и закрытие соединения
    conn.commit()
    conn.close()

    # Сброс состояния
    await state.finish()

if __name__ == '__main__':
    buttons_poll = []
    create_allowed_users_table()
    create_poll_direct_table()
    executor.start_polling(dp, skip_updates=True)