import json
import sqlite3
import datetime
import pandas as pd


async def result_counter(result_data):
    result_string = ""
    for i, option in enumerate(result_data):
        result_string += f"{i + 1}) '{option['text']}'\n"
        result_string += f"Количество выборов: '{option['voter_count']}'\n"
    return result_string


async def load_statistics_information():
    arr_title_poll = []
    arr_answer = []
    arr_date_start_poll = []
    arr_group_published_poll = []
    arr_status_poll = []
    arr_date_end_poll = []
    arr_member_poll = []
    arr_result_poll = []
    arr_anon_poll = []
    arr_multi_pool = []

    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT p.poll_id, p.question, p.chat_id, g.chat_title, p.datetime, p.status, p.message_id, p.options, p.poll_removed, p.poll_data '
        'FROM poll_direct p JOIN groups g ON p.chat_id = g.chat_id')
    raw_data = cursor.fetchall()
    for data in raw_data:
        question = data[1]
        chat_title = data[3]
        date_create_poll = (datetime.datetime.strptime(data[4], '%Y-%m-%d %H:%M:%S.%f')).strftime('%H:%M %d.%m.%Y')
        status_poll = data[5]
        option_poll = data[7]
        date_end_poll = data[8]
        try:
            poll_data = json.loads(data[9])
        except TypeError as e:
            poll_data = None
        except json.decoder.JSONDecodeError as jde:
            poll_data = "Опрос завершён с ошибкой"

        arr_title_poll.append(question)
        arr_answer.append(str(option_poll)[1:-1])
        arr_date_start_poll.append(date_create_poll)
        arr_group_published_poll.append(chat_title)
        arr_status_poll.append("Действующий" if status_poll == 1 else "Окончен")
        arr_date_end_poll.append(date_end_poll)
        try:
            arr_member_poll.append(poll_data["total_voter_count"])
            arr_result_poll.append(await result_counter(poll_data["options"]))
            arr_anon_poll.append("Да" if poll_data["is_anonymous"] else "Нет")
            arr_multi_pool.append("Да" if poll_data["allows_multiple_answers"] else "Нет")
        except TypeError:
            arr_member_poll.append(None)
            arr_result_poll.append(None)
            arr_anon_poll.append(None)
            arr_multi_pool.append(None)

    df = pd.DataFrame({
        'Тема опроса': arr_title_poll,
        'Варианты ответов': arr_answer,
        'Дата публикации': arr_date_start_poll,
        'Группа в которой опубликован': arr_group_published_poll,
        'Статус опроса': arr_status_poll,
        'Дата окончания': arr_date_end_poll,
        'Количество пользователей участвовавших в опросе': arr_member_poll,
        'Результаты опроса': arr_result_poll,
        'Опрос анонимный': arr_anon_poll,
        'Возможность выбора нескольких ответов': arr_multi_pool
    })

    return df


async def create_file(data_frame):
    dt_obj = datetime.datetime.now()
    dt_string = dt_obj.strftime("%Y-%m-%d_%H:%M")
    path_str = f'./poll_statistics_{dt_string}.xlsx'
    data_frame.to_excel(path_str, index=False, na_rep='NaN')
    return path_str


async def get_statistics():
    return await create_file(await load_statistics_information())
