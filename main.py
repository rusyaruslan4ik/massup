import html
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from datetime import datetime

import matplotlib.pyplot as plt
from io import BytesIO

from dotenv import load_dotenv
import os
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Состояния регистрации
user_states = {}

# Путь к фото (одно и то же везде)
photo_url_start = "https://disk.yandex.ru/i/4nyQt-NqdqKY2Q" 
photo_url_menu = "https://disk.yandex.ru/i/c9YJqC96klJgNQ"
photo_url_profile = "https://disk.yandex.ru/i/OnjRWmXXxr4qOg"

# Создание таблицы
def create_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            gender TEXT,
            name TEXT,
            birth_date TEXT,
            height REAL,
            weight REAL,
            activity REAL DEFAULT 1.2
        )
    ''')
    conn.commit()
    conn.close()

create_table()

def create_goal_column():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN goal_weight REAL")
    except sqlite3.OperationalError:
        pass  # Уже добавлено
    conn.commit()
    conn.close()

create_goal_column()

def create_weight_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_history (
            user_id INTEGER,
            date TEXT,
            weight REAL
        )
    ''')
    conn.commit()
    conn.close()

create_weight_table()




def add_weight_entry(user_id, weight):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO weight_history (user_id, date, weight) VALUES (?, ?, ?)', 
                   (user_id, datetime.now().strftime("%d.%m.%Y"), weight))
    conn.commit()
    conn.close()

# Добавление пользователя
def add_user(user_id, username, gender, name, birth_date, height, weight, activity):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, username, gender, name, birth_date, height, weight, activity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                   (user_id, username, gender, name, birth_date, height, weight, activity))
    conn.commit()
    conn.close()

# Получение пользователя
def get_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# Главное меню 
def get_main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("👤 Посмотреть профиль", callback_data="view_profile"))
    kb.add(
        InlineKeyboardButton("➕ Изменить вес", callback_data="add_weight"),
        InlineKeyboardButton("📈 График веса", callback_data="weight_graph")
    )
    kb.add(
        InlineKeyboardButton("🎯 Установить цель", callback_data="set_goal"),
        InlineKeyboardButton("📊 Рассчитать ИМТ", callback_data="calculate_bmi")
    )
    kb.add(InlineKeyboardButton("💪 БЖУ для набора массы", callback_data="calories_info"))
    return kb

# Кнопки активности Имя
def get_activity_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("1.2 — сидячий образ жизни", callback_data="activity_1.2"),
        InlineKeyboardButton("1.375 — лёгкие тренировки", callback_data="activity_1.375"),
        InlineKeyboardButton("1.55 — умеренные тренировки", callback_data="activity_1.55"),
        InlineKeyboardButton("1.725 — интенсивные тренировки", callback_data="activity_1.725"),
        InlineKeyboardButton("1.9 — тяжёлый труд + тренировки", callback_data="activity_1.9"),
    )
    return kb



async def send_updated_profile(chat_id, user_id, update_text):
    user = get_user(user_id)
    if not user:
        await bot.send_message(chat_id, "Ошибка: пользователь не найден.")
        return

    try:
        birth_date = datetime.strptime(user[4], "%d.%m.%Y")
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        age_text = f"{user[4]} ({age})"
    except:
        age_text = user[4]

    activity = user[7] if len(user) > 7 and user[7] else 1.2

    goal_weight = user[8] if len(user) > 8 and user[8] else None
    goal_text = f"\n🎯 Цель: {goal_weight} кг" if goal_weight else ""

    profile_text = (
        f"{update_text}\n\n"
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🧑 Пол: {user[2]}\n"
        f"🗣 Имя: {user[3]}\n"
        f"🎂 Дата рождения: {age_text}\n"
        f"📏 Рост: {user[5]} см\n"
        f"⚖️ Вес: {user[6]} кг{goal_text}\n"
        f"💬 Username: @{user[1]}\n"
        f"⚡️ Активность: {activity}"
    )

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✏️ Изменить имя", callback_data="edit_name"),
        InlineKeyboardButton("📅 Изменить дату", callback_data="edit_birth"),
        InlineKeyboardButton("📏 Изменить рост", callback_data="edit_height"),
        InlineKeyboardButton("⚖️ Изменить вес", callback_data="edit_weight"),
        InlineKeyboardButton("⚡️ Изменить активность", callback_data="edit_activity"),
    )
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))

    await bot.send_photo(
        chat_id=chat_id,
        photo=photo_url_menu,
        caption=profile_text,
        reply_markup=kb,
        parse_mode='HTML'
    )



@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user = get_user(message.from_user.id)

    if user:
        try:
            birth_date = datetime.strptime(user[4], "%d.%m.%Y")
            today = datetime.now()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            age_text = f"{user[4]} ({age} лет)"
        except:
            age_text = user[4]

        text = (
            f"✅ Вы уже зарегистрированы!\n\n"
            f"👤 Имя: {user[3]}\n"
            f"🧑 Пол: {user[2]}\n"
            f"🎂 Дата рождения: {age_text}\n"
            f"📏 Рост: {user[5]} см\n"
            f"⚖️ Вес: {user[6]} кг\n"
            f"💬 Username: @{user[1]}"
        )

        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo_url_menu,
            caption=text,
            reply_markup=get_main_menu(),
            parse_mode='HTML'
        )
    else:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Начать регистрацию", callback_data="start_registration"))
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo_url_start,
            caption="Спасибо, что используете нас! Я бот-ассистент для набора массы 💪\n\nНажмите кнопку ниже, чтобы начать регистрацию:",
            reply_markup=kb
        )

@dp.callback_query_handler(lambda c: c.data == 'start_registration')
async def start_registration(callback_query: types.CallbackQuery):
    user_states[callback_query.from_user.id] = {'step': 'gender'}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Мужской", callback_data="gender_male"))
    kb.add(InlineKeyboardButton("Женский", callback_data="gender_female"))
    await callback_query.message.edit_caption("Выберите ваш пол:", reply_markup=kb)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('gender_'))
async def process_gender(callback_query: types.CallbackQuery):
    gender = "Мужской" if callback_query.data == "gender_male" else "Женский"
    user_states[callback_query.from_user.id]['gender'] = gender
    user_states[callback_query.from_user.id]['step'] = 'name'
    await callback_query.message.answer("👤 Введите ваше имя:")

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'name')
async def process_name(message: types.Message):
    user_states[message.from_user.id]['name'] = message.text
    user_states[message.from_user.id]['step'] = 'birth_date'
    await message.answer("📅 Введите дату рождения в формате дд.мм.гггг:")

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'birth_date')
async def process_birth_date(message: types.Message):
    try:
        birth_date = datetime.strptime(message.text, "%d.%m.%Y")
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 5 or age > 120:
            await message.answer("Возраст должен быть от 5 до 120 лет. Введите корректную дату:")
            return
        user_states[message.from_user.id]['birth_date'] = message.text
        user_states[message.from_user.id]['step'] = 'height'
        await message.answer("📏 Введите ваш рост в см (например, 178.5):")
    except ValueError:
        await message.answer("📅 Неверный формат! Введите дату в формате дд.мм.гггг:")

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'height')
async def process_height(message: types.Message):
    try:
        height = float(message.text.replace(',', '.'))
        if height < 50 or height > 300:
            await message.answer("Рост должен быть от 50 до 300 см. Введите корректное значение:")
            return
        user_states[message.from_user.id]['height'] = height
        user_states[message.from_user.id]['step'] = 'weight'
        await message.answer("⚖️ Введите ваш вес в кг (например, 65.5):")
    except ValueError:
        await message.answer("📏Неверный формат! Введите рост в см (например, 178.5):")

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'weight')
async def process_weight(message: types.Message):
    try:
        weight = float(message.text.replace(',', '.'))
        if weight < 20 or weight > 500:
            await message.answer("Вес должен быть от 20 до 500 кг. Введите корректное значение:")
            return
        user_states[message.from_user.id]['weight'] = weight
        user_states[message.from_user.id]['step'] = 'activity'
        await message.answer("ℹ️ Выберите ваш коэффициент активности:", reply_markup=get_activity_kb())
    except ValueError:
        await message.answer("⚖️ Неверный формат! Введите вес в кг (например, 65.5):")
        
@dp.callback_query_handler(lambda c: c.data.startswith('activity_'))
async def handle_activity(callback_query: types.CallbackQuery):
    activity_value = float(callback_query.data.split('_')[1])
    step = user_states.get(callback_query.from_user.id, {}).get('step')

    if step == 'activity':
        # Регистрация
        user_states[callback_query.from_user.id]['activity'] = activity_value
        data = user_states[callback_query.from_user.id]

        add_user(
            callback_query.from_user.id,
            callback_query.from_user.username,
            data['gender'],
            data['name'],
            data['birth_date'],
            data['height'],
            data['weight'],
            data['activity']
        )
        add_weight_entry(callback_query.from_user.id, data['weight'])
        await callback_query.message.edit_text("🎉 Поздравляем! \n✅ Регистрация завершена!")
        await bot.send_photo(
            chat_id=callback_query.from_user.id,
            photo=photo_url_menu,
            caption="Меню",
            reply_markup=get_main_menu()
        )
        

        # Лог админу
        text = (
            f"📝 <b>Новая регистрация</b>\n\n"
            f"ID: <code>{callback_query.from_user.id}</code>\n"
            f"Username: @{callback_query.from_user.username}\n"
            f"Имя: {data['name']}\n"
            f"Пол: {data['gender']}\n"
            f"Дата рождения: {data['birth_date']}\n"
            f"Рост: {data['height']} см\n"
            f"Вес: {data['weight']} кг\n"
            f"Активность: {data['activity']}"
        )
        await bot.send_message(chat_id=1080763483, text=text, parse_mode='HTML')
    elif step == 'edit_activity':
        # Редактирование активности
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET activity = ? WHERE user_id = ?", (activity_value, callback_query.from_user.id))
        conn.commit()
        conn.close()

        user_states.pop(callback_query.from_user.id, None)

        # Отправляем обновлённый профиль 
        message = types.Message(chat=callback_query.message.chat, message_id=callback_query.message.message_id, from_user=callback_query.from_user)
        await send_updated_profile(callback_query.from_user.id, callback_query.from_user.id, "✅ Активность успешно изменена!")
    else:
        await callback_query.message.answer("⚠️ Ошибка. Попробуйте снова.")

    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'view_profile')
async def view_profile(callback_query: types.CallbackQuery):
    user = get_user(callback_query.from_user.id)
    if not user:
        await callback_query.message.answer("Вы не зарегистрированы.")
        return

    try:
        birth_date = datetime.strptime(user[4], "%d.%m.%Y")
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        age_text = f"{user[4]} ({age})"
    except:
        age_text = user[4]

    activity = user[7] if len(user) > 7 and user[7] else 1.2

    goal_weight = user[8] if len(user) > 8 and user[8] else None
    goal_text = f"\n🎯 Цель: {goal_weight} кг" if goal_weight else ""

    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🧑 Пол: {user[2]}\n"
        f"🗣 Имя: {user[3]}\n"
        f"🎂 Дата рождения: {age_text}\n"
        f"📏 Рост: {user[5]} см\n"
        f"⚖️ Вес: {user[6]} кг{goal_text}\n"
        f"💬 Username: @{user[1]}\n"
        f"⚡ Активность: {activity}"
    )

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✏️ Изменить имя", callback_data="edit_name"),
        InlineKeyboardButton("📅 Изменить дату", callback_data="edit_birth"),
        InlineKeyboardButton("📏 Изменить рост", callback_data="edit_height"),
        InlineKeyboardButton("⚖️ Изменить вес", callback_data="edit_weight"),
        InlineKeyboardButton("⚡ Изменить активность", callback_data="edit_activity"),
    )
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))


    await callback_query.message.delete()

    await bot.send_photo(
        chat_id=callback_query.from_user.id,
        photo=photo_url_profile,
        caption=text,
        reply_markup=kb,
        parse_mode='HTML'
    )
    await callback_query.answer()

# ----- Здесь аналогично все edit_caption при редактировании -----
# (оставим коротко, чтобы не повторяться, но все edit_text -> edit_caption)

@dp.callback_query_handler(lambda c: c.data == 'calories_info')
async def calories_info(callback_query: types.CallbackQuery):
    user = get_user(callback_query.from_user.id)
    if not user:
        await callback_query.message.answer("Вы не зарегистрированы.")
        return

    try:
        birth_date = datetime.strptime(user[4], "%d.%m.%Y")
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        age = 25

    weight = user[6]
    height = user[5]
    gender = user[2]
    activity = user[7] if len(user) > 7 and user[7] else 1.2

    if gender == "Мужской":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

    daily_calories = bmr * activity
    gain_calories = daily_calories * 1.2

    B = round(weight * 1.8)
    F = round(weight * 1.3)
    U = round((gain_calories - B*4 - F*9)//4)


    text = (
        f"💪 <b>БЖУ для массы</b>\n\n"
        f"🟰 Для поддержания веса нужно: <b>{daily_calories:.0f} ккал</b>\n"
        f"🔺 Для набора массы: <b>{gain_calories:.0f} ккал</b>\n\n"
        f"🥚 <b>Белки:</b>         {B} г — {B*4} ккал\n"
        f"🥩 <b>Жиры:</b>         {F} г — {F*9} ккал\n"
        f"🥦 <b>Углеводы:</b>  {U} г — {U*4} ккал\n\n"
        f"⚡ Ваш коэффициент активности: {activity}"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))
    await callback_query.message.edit_caption(caption=text, reply_markup=kb, parse_mode='HTML')
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_menu')
async def back_to_menu(callback_query: types.CallbackQuery):
    await callback_query.message.delete()

    await bot.send_photo(
        chat_id=callback_query.from_user.id,
        photo=photo_url_menu,
        caption="📋 Главное меню:",
        reply_markup=get_main_menu(),
        parse_mode='HTML'
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == 'calculate_bmi')
async def calculate_bmi(callback_query: types.CallbackQuery):
    user = get_user(callback_query.from_user.id)
    if not user:
        await callback_query.message.answer("Вы не зарегистрированы.")
        return

    weight = user[6]
    height = user[5]

    if not weight or not height:
        await callback_query.message.answer("Не хватает данных для расчёта ИМТ.")
        return

    height_m = height / 100
    bmi = weight / (height_m ** 2)
    bmi = round(bmi, 1)

    text = f"💡 Ваш ИМТ: <b>{bmi}</b>\n\n"
    if bmi < 18.5:
        text += "Вы находитесь в дефиците массы тела."
    elif bmi < 25:
        text += "Ваш вес в норме."
    elif bmi < 30:
        text += "Есть небольшой избыток массы тела."
    else:
        text += "Ожирение."

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))

    await callback_query.message.delete()

    await bot.send_photo(
        chat_id=callback_query.from_user.id,
        photo=photo_url_menu,
        caption=text,
        reply_markup=kb,
        parse_mode='HTML'
    )
    await callback_query.answer()



@dp.callback_query_handler(lambda c: c.data == 'edit_name')
async def edit_name(callback_query: types.CallbackQuery):
    user_states[callback_query.from_user.id] = {'step': 'edit_name'}
    await callback_query.message.answer("✏️ Введите новое имя:")
    await callback_query.answer()

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'edit_name')
async def process_edit_name(message: types.Message):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    conn.close()
    user_states.pop(message.from_user.id, None)

    await send_updated_profile(message.chat.id, message.from_user.id, "✅ Имя успешно изменено!")



@dp.callback_query_handler(lambda c: c.data == 'edit_birth')
async def edit_birth(callback_query: types.CallbackQuery):
    user_states[callback_query.from_user.id] = {'step': 'edit_birth'}
    await callback_query.message.answer("📅 Введите новую дату рождения в формате дд.мм.гггг:")
    await callback_query.answer()

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'edit_birth')
async def process_edit_birth(message: types.Message):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Неверный формат! Введите дату в формате дд.мм.гггг:")
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET birth_date = ? WHERE user_id = ?", (message.text, message.from_user.id))
    conn.commit()
    conn.close()
    user_states.pop(message.from_user.id, None)

    await send_updated_profile(message.chat.id, message.from_user.id, "✅ Дата рождения успешно изменена!")




@dp.callback_query_handler(lambda c: c.data == 'edit_height')
async def edit_height(callback_query: types.CallbackQuery):
    user_states[callback_query.from_user.id] = {'step': 'edit_height'}
    await callback_query.message.answer("📏 Введите новый рост в см (например, 178.5):")
    await callback_query.answer()

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'edit_height')
async def process_edit_height(message: types.Message):
    try:
        height = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer("❌ Неверный формат! Введите число, например, 178.5:")
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET height = ? WHERE user_id = ?", (height, message.from_user.id))
    conn.commit()
    conn.close()
    user_states.pop(message.from_user.id, None)

    await send_updated_profile(message.chat.id, message.from_user.id, "✅ Рост успешно изменен!")



@dp.callback_query_handler(lambda c: c.data == 'edit_weight')
async def edit_weight(callback_query: types.CallbackQuery):
    user_states[callback_query.from_user.id] = {'step': 'edit_weight'}
    await callback_query.message.answer("⚖️ Введите новый вес в кг (например, 65.5):")
    await callback_query.answer()

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'edit_weight')
async def process_edit_weight(message: types.Message):
    try:
        weight = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer("❌ Неверный формат! Введите число, например, 65.5:")
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET weight = ? WHERE user_id = ?", (weight, message.from_user.id))
    conn.commit()
    conn.close()
    user_states.pop(message.from_user.id, None)

    add_weight_entry(message.from_user.id, weight)
    await send_updated_profile(message.chat.id, message.from_user.id, "✅ Вес успешно изменен!")


@dp.callback_query_handler(lambda c: c.data == 'edit_activity')
async def edit_activity(callback_query: types.CallbackQuery):
    await callback_query.message.answer("⚡ Выберите новый коэффициент активности:", reply_markup=get_activity_kb())
    user_states[callback_query.from_user.id] = {'step': 'edit_activity'}
    await callback_query.answer()






def get_weight_history(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT date, weight FROM weight_history WHERE user_id = ? ORDER BY date', (user_id,))
    data = cursor.fetchall()
    conn.close()
    return data

@dp.callback_query_handler(lambda c: c.data == 'add_weight')
async def add_weight_start(callback_query: types.CallbackQuery):
    user_states[callback_query.from_user.id] = {'step': 'add_weight'}
    await callback_query.message.answer("Введите новый вес в кг (например, 70.5):")
    await callback_query.answer()

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'add_weight')
async def process_add_weight(message: types.Message):
    try:
        weight = float(message.text.replace(",", "."))
        if weight < 20 or weight > 500:
            await message.answer("Вес должен быть от 20 до 500 кг.")
            return

        # Обновляем основной вес
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET weight = ? WHERE user_id = ?", (weight, message.from_user.id))
        conn.commit()
        conn.close()

        # Добавляем запись в историю
        add_weight_entry(message.from_user.id, weight)

        user_states.pop(message.from_user.id, None)
        await message.answer(f"✅ Вес обновлён и добавлен в историю: {weight} кг.")
    except:
        await message.answer("❌ Неверный формат! Введите число, например, 70.5.")

@dp.callback_query_handler(lambda c: c.data == 'weight_graph')
async def show_weight_graph(callback_query: types.CallbackQuery):
    data = get_weight_history(callback_query.from_user.id)
    if not data or len(data) < 2:
        await callback_query.message.answer("Недостаточно данных для графика. Нужно хотя бы 2 записи.")
        await callback_query.answer()
        return

    await callback_query.message.answer("<b>Загружаем ваш график...</b>", parse_mode='HTML')

    dates = [x[0] for x in data]
    weights = [x[1] for x in data]

    plt.figure(figsize=(8, 5))
    plt.plot(dates, weights, marker='o', linestyle='-', color='blue')
    plt.xticks(rotation=45)
    plt.xlabel("Дата")
    plt.ylabel("Вес (кг)")
    plt.title("История веса")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    await bot.send_photo(callback_query.from_user.id, photo=buf, caption="📈 Ваш график веса.")
    await callback_query.answer()



@dp.callback_query_handler(lambda c: c.data == 'set_goal')
async def set_goal(callback_query: types.CallbackQuery):
    user_states[callback_query.from_user.id] = {'step': 'set_goal'}
    await callback_query.message.answer("🎯 Введите вашу цель по весу в кг (например, 80):")
    await callback_query.answer()

def parse_weight(text: str) -> float | None:
    try:
        weight = float(text.replace(',', '.'))
        return weight
    except ValueError:
        return None

@dp.message_handler(lambda message: user_states.get(message.from_user.id, {}).get('step') == 'set_goal')
async def process_set_goal(message: types.Message):
    goal_weight = parse_weight(message.text)
    if goal_weight is None:
        await message.answer("❌ Неверный формат! Введите число, например, 80.")
        return

    if goal_weight < 20 or goal_weight > 500:
        await message.answer("Вес должен быть от 20 до 500 кг. Введите корректное значение:")
        return

    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET goal_weight = ? WHERE user_id = ?", (goal_weight, message.from_user.id))
        conn.commit()
        conn.close()

        # Получаем текущий вес
        user = get_user(message.from_user.id)
        current_weight = user[6] if user else None

        if current_weight is not None and abs(current_weight - goal_weight) < 0.01:
            extra_note = "\n🎉 Вы уже достигли этой цели!"
        else:
            extra_note = ""

        user_states.pop(message.from_user.id, None)

        await send_updated_profile(
            message.chat.id,
            message.from_user.id,
            f"✅ Цель по весу успешно установлена!{extra_note}"
        )

        print(f"[LOG] User {message.from_user.id} set goal_weight: {goal_weight}")

    except Exception as e:
        print(f"[ERROR] Ошибка при обновлении цели: {e}")
        await message.answer("❌ Произошла ошибка при установке цели. Попробуйте позже.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

    # view_profile()