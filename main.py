# СТАНДАРТНЫЕ БИБЛИОТЕКИ
import asyncio
import json
import os
from datetime import datetime, timedelta
from random import choice

# СТОРОННИЕ ПАКЕТЫ
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.types import WebAppInfo

# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
from dotenv import load_dotenv


# КОНФИГУРАЦИЯ
load_dotenv()                  # Загрузка переменных окружения из файла .env
TOKEN = os.getenv("BOT_TOKEN") # Токен бота (обязательно)

THEORY_FILE = "theory_.json"   # Теоретические материалы
TASKS_FILE = "tasks.json"      # Банк задач
TESTS_FILE = "tests.json"      # Тестовые вопросы


# ИНИЦИАЛИЗАЦИЯ
bot = Bot(token=TOKEN)    # Клиент API Telegram
dp = Dispatcher()         # Обработчик сообщений
router = Router()         # Маршрутизатор
dp.include_router(router) # Подключение маршрутов


# СЛОВАРИ ДЛЯ ХРАНЕНИЯ СОСТОЯНИЙ ПОЛЬЗОВАТЕЛЯ
# Временные данные пользователей (user_id: данные)
user_tests = {}         # Текущий тест пользователя (вопросы/ответы)
user_states = {}        # Текущее состояние (меню/тесты/задачи/напоминания)
user_reminders = {}     # Время напоминаний (user_id: datetime)
user_test_progress = {} # Прогресс тестирования (вопросы/правильные ответы)
user_tasks = {}         # Задачи пользователя + текущий индекс
user_stats = {}         # Статистика (решения/тесты/бейджи)
user_solved_items = {}  # ID решенных задач (для исключения повторов)


# КОНСТАНТЫ СОСТОЯНИЙ ПОЛЬЗОВАТЕЛЯ
STATE_TASKS = "tasks" # Режим решения задач
STATE_TESTS = "tests" # Режим прохождения тестов
STATE_NONE = "none"   # Режим ожидания


# ЗАГРУЗКА ДАННЫХ ИЗ JSON-ФАЙЛОВ
with open(THEORY_FILE, "r", encoding="utf-8") as f:
    theory_data = json.load(f)         # Теоретические материалы

with open(TASKS_FILE, "r", encoding="utf-8") as f:
    tasks_data = json.load(f)          # Банк задач

with open(TESTS_FILE, "r", encoding="utf-8") as f:
    tests_data = json.load(f)["tests"] # Тестовые вопросы (ключ "tests")


STICKERS = {
    "welcome": "CAACAgIAAxkBAAEBL-Nn6lkZ7MFhFH7SsrWG0-RepGg9iQAC1AwAAnqLoEieLyIklDO8mzYE",

    "recommend": [
        "CAACAgIAAxkBAAEBL-Vn6lluax4ZbJbK-WtvoYcrpp4C9QACYw4AAgtaoEg7Cb-9icYZzTYE",
        "CAACAgIAAxkBAAEBL-Fn6lkQPCM5BJxta5iUILFblCL_pgACZg8AAlGwsEiUHH3OCPuZqTYE",
        "CAACAgIAAxkBAAEBL-dn6lmHFcSeAneJnnlze5VmVyRg6QACYQ8AAp5wmEhb4tJtlpFD-TYE"
    ],

    "progress": [
        "CAACAgIAAxkBAAEBL-9n6lmv8bgTjgAB28BYiMBoYp3Re0kAAmgNAAK0oaFIHliZ98qHA0E2BA",
        "CAACAgIAAxkBAAEBL-1n6lmoCFPLVdwdJESnIDEE9Rz__AACrQ4AAuR6QUt_BjUr8hmSxjYE",
        "CAACAgIAAxkBAAEBL-Nn6lkZ7MFhFH7SsrWG0-RepGg9iQAC1AwAAnqLoEieLyIklDO8mzYE"
    ],

    "correct": [
        "CAACAgIAAxkBAAEBL-9n6lmv8bgTjgAB28BYiMBoYp3Re0kAAmgNAAK0oaFIHliZ98qHA0E2BA",
        "CAACAgIAAxkBAAEBL_Fn6lolRAuML3PfPhztO9MfdiGA6wAC3w4AAuuRQEvxUkpRRrID-TYE",
        "CAACAgIAAxkBAAEBL99n6lkBOEfehT01DDi-_qOVQT5KfwACGxMAAlqS2EhjB6Z1XtCrlzYE",
        "CAACAgIAAxkBAAEBL-Nn6lkZ7MFhFH7SsrWG0-RepGg9iQAC1AwAAnqLoEieLyIklDO8mzYE",
        "CAACAgIAAxkBAAEBL-1n6lmoCFPLVdwdJESnIDEE9Rz__AACrQ4AAuR6QUt_BjUr8hmSxjYE"
    ],

    "errors": [
        "CAACAgIAAxkBAAEBL-Fn6lkQPCM5BJxta5iUILFblCL_pgACZg8AAlGwsEiUHH3OCPuZqTYE",
        "CAACAgIAAxkBAAEBL-Vn6lluax4ZbJbK-WtvoYcrpp4C9QACYw4AAgtaoEg7Cb-9icYZzTYE",
        "CAACAgIAAxkBAAEBL-dn6lmHFcSeAneJnnlze5VmVyRg6QACYQ8AAp5wmEhb4tJtlpFD-TYE"
    ],

    "experiments": "CAACAgIAAxkBAAEBL-ln6lmTrqWYAbh8UyUmAAEdBdFmXI8AAnIPAAIkWqBIiNZAMrUUvc42BA",

    "reminders": [
        "CAACAgIAAxkBAAEBL99n6lkBOEfehT01DDi-_qOVQT5KfwACGxMAAlqS2EhjB6Z1XtCrlzYE",
        "CAACAgIAAxkBAAEBL-Nn6lkZ7MFhFH7SsrWG0-RepGg9iQAC1AwAAnqLoEieLyIklDO8mzYE"
    ]
}


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ

# Возвращает список всех доступных тем для тестов из загруженных данных
def get_topics():
    return [test["topic"] for test in tests_data]


def get_tests_by_topic(topic):
    for test in tests_data:
        if test["topic"] == topic: # Находит вопросы для указанной темы
            return test["questions"]
    return []                      # Возвращает: list вопросов или пустой список


# Создает клавиатуру основного меню с 6 кнопками в 3 ряда
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📘 Теория"), KeyboardButton(text="📚 Задачи")],
            [KeyboardButton(text="📊 Тесты"), KeyboardButton(text="🔗 Ссылки")],
            [KeyboardButton(text="⏰ Напоминания"), KeyboardButton(text="📈 Прогресс")],
            [KeyboardButton(text="💡 Рекомендации"), KeyboardButton(text="🔬 3D-Эксперименты")]
        ],
        resize_keyboard=True
    )

# Генерирует цветной текстовый прогресс-бар
def create_progress_bar(current, total, width=20):
    percent = (current / total) * 100   # Вычисляет процент выполнения (0-100%)

    # Считает сколько символов █ нужно отобразить
    filled = int(round(width * current / total)) if total > 0 else 0  # Защита от деления на 0

    if percent < 30:
        bar_color = "🔴"
    elif percent < 70:
        bar_color = "🟡"
    else:
        bar_color = "🟢"

    bar = f"{bar_color} [{'█' * filled}{'░' * (width - filled)}] {current}/{total} ({round(percent)}%)"
    return bar        # Формат: "🟡 [████░░░░] 5/10 (50%)"



def init_user_data(user_id):

    # Создает записи для нового пользователя в:
    #    - user_stats: хранит прогресс и статистику
    #    - user_solved_items: предотвращает дублирование решений

    if user_id not in user_stats:
        user_stats[user_id] = {
            "solved_tasks": 0,                       # Кол-во решенных задач
            "total_tasks": len(tasks_data["tasks"]), # Всего задач доступно
            "correct_tests": 0,                      # Правильные ответы в тестах
            "total_questions": sum(len(t["questions"]) for t in tests_data), # Всего вопросов
            "tests_taken": 0,                        # Пройденные тесты
            "badges": ["Новичок"],                   # Доступные бейджи
            "weak_topics": {}                        # Пустой словарь для хранения ошибок
        }

    if user_id not in user_solved_items:
        user_solved_items[user_id] = {
            "solved_tasks": set(),                   # Пустое множество для ID решенных задач
            "correct_questions": set()               # Пустое множество для ID правильных ответов
        }


def get_random_sticker(sticker_type):
    try:
        if sticker_type not in STICKERS:
            return None

        sticker = STICKERS[sticker_type]
        if isinstance(sticker, list):
            return choice(sticker)
        return sticker
    except Exception as e:
        print(f"Error getting sticker: {e}")
        return None


# Хендлеры
@router.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id # Получаем ID пользователя

    # Если пользователь новый, инициализируем для него данные
    if user_id not in user_stats:
        init_user_data(user_id)    # Создаем записи в user_stats и user_solved_items

    await message.answer(
        "Привет! Я помогу тебе подготовиться к ЕГЭ по физике. Выбери действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await message.answer_sticker(sticker=STICKERS["welcome"])


@router.message(lambda message: message.text == "📘 Теория")
async def send_theory_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])    # Создаем пустую клавиатуру

    # Генерируем кнопки для каждой темы
    for topic in theory_data["темы"]:
        button = InlineKeyboardButton(
            text=f"{topic['номер']}. {topic['название']}", # Текст кнопки
            callback_data=f"topic_{topic['номер']}"        # Данные для callback
        )
        keyboard.inline_keyboard.append([button])          # Добавляем кнопку в клавиатуру
    await message.answer("Выбери тему:", reply_markup=keyboard)


@router.callback_query(lambda callback: callback.data.startswith("topic_"))
async def handle_topic_selection(callback: CallbackQuery):

    # Извлекаем номер темы из callback_data (формат "topic_<номер>")
    topic_number = int(callback.data.split("_")[1])

    # Ищем тему в theory_data по номеру
    selected_topic = next((t for t in theory_data["темы"] if t["номер"] == topic_number), None)

    # Формируем ответ с названием и содержимым темы (HTML форматирование)
    if selected_topic:
        response = f"📘 <b>{selected_topic['название']}</b>\n\n{selected_topic['содержимое']}"
        await callback.message.answer(response, parse_mode="HTML")
    else:
        await callback.message.answer("Тема не найдена.")

    # Подтверждаем обработку callback (убирает "часики" в интерфейсе и "зависания")
    await callback.answer()


@router.message(lambda message: message.text == "📚 Задачи")
async def send_task_topics(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = STATE_TASKS

    topics = set(task["topic"] for task in tasks_data["tasks"])
    keyboard = InlineKeyboardBuilder()
    for topic in topics:
        keyboard.button(text=topic, callback_data=f"task_topic_{topic}")
    keyboard.adjust(1)
    await message.answer("Выбери тему задач:", reply_markup=keyboard.as_markup())


@router.callback_query(lambda callback: callback.data.startswith("task_topic_"))
async def handle_task_topic_selection(callback: CallbackQuery):
    topic = callback.data.replace("task_topic_", "")
    user_id = callback.from_user.id
    init_user_data(user_id)
    tasks = [task for task in tasks_data["tasks"] if task["topic"] == topic]

    if not tasks:
        await callback.message.answer("❌ Задачи не найдены.")
        return

    user_tasks[user_id] = {"tasks": tasks, "current_task_index": 0}
    user_states[user_id] = STATE_TASKS
    await send_next_task(callback.message, user_id)
    await callback.answer()


async def send_next_task(message: types.Message, user_id: int):
    if user_id not in user_tasks:
        await message.answer("❌ Ошибка: задачи не найдены.")
        return

    user_state = user_tasks[user_id]
    task = user_state["tasks"][user_state["current_task_index"]]

    await message.answer(f"📚 <b>Задача:</b>\n{task['question']}", parse_mode="HTML")


async def handle_task_answer(message: types.Message):
    user_id = message.from_user.id
    init_user_data(user_id)

    if user_id not in user_tasks:
        await message.answer("❌ Ты не решаешь задачи сейчас.")
        return

    user_state = user_tasks[user_id]
    task = user_state["tasks"][user_state["current_task_index"]]
    task_id = f"{task['topic']}_{task['question'][:50]}"

    try:
        user_answer = float(message.text.strip())
        is_correct = abs(user_answer - task["answer"]) < 0.001

        if is_correct and task_id not in user_solved_items[user_id]["solved_tasks"]:
            user_stats[user_id]["solved_tasks"] += 1
            user_solved_items[user_id]["solved_tasks"].add(task_id)
            await check_and_award_badges(message, user_id)
        else:
            if not is_correct:
                update_weak_topics(user_id, task["topic"])

        response = (
            f"✅ Правильный ответ!\n\n<b>Решение:</b> {task['solution']}" if is_correct
            else f"❌ Неправильно. Правильный ответ: {task['answer']}\n\n<b>Решение:</b> {task['solution']}"
        )

        # Отправляем результат текущей задачи
        await message.answer(response, parse_mode="HTML")

        # Увеличиваем счетчик задач
        user_state["current_task_index"] += 1

        # Проверяем, есть ли еще задачи
        if user_state["current_task_index"] < len(user_state["tasks"]):
            # Если задачи еще есть, отправляем следующую
            await send_next_task(message, user_id)
        else:
            # Если задачи закончились - сообщаем об этом
            await message.answer("🎉 Ты решил все задачи!", reply_markup=get_main_menu_keyboard())
            del user_tasks[user_id]

    except ValueError:
        await message.answer("❌ Введи числовой ответ.")


@router.message(lambda message: message.text == "📊 Тесты")
async def send_test_topics(message: types.Message):
    user_id = message.from_user.id
    init_user_data(user_id)
    user_states[user_id] = STATE_TESTS  # Устанавливаем состояние тестов

    topics = get_topics()
    if not topics:
        await message.answer("Тесты пока не загружены.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for index, topic in enumerate(topics):
        button = InlineKeyboardButton(text=topic, callback_data=f"test_topic_{index}")
        keyboard.inline_keyboard.append([button])

    await message.answer("Выбери тему теста:", reply_markup=keyboard)


@router.callback_query(lambda callback: callback.data.startswith("test_topic_"))
async def handle_test_topic_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    init_user_data(user_id)  # Инициализируем данные

    topic_index = int(callback.data.replace("test_topic_", ""))
    topics = get_topics()

    if topic_index < 0 or topic_index >= len(topics):
        await callback.message.answer("❌ Ошибка: тема не найдена.")
        return

    topic = topics[topic_index]
    tests = get_tests_by_topic(topic)

    if not tests:
        await callback.message.answer("❌ В этой теме пока нет тестов.")
        return

    # Инициализируем прогресс теста
    user_test_progress[user_id] = {
        "topic": topic,
        "tests": tests,
        "current_question_index": 0,
        "correct_answers": 0
    }
    user_states[user_id] = STATE_TESTS

    await send_next_test_question(callback.message, user_id)
    await callback.answer()


async def send_next_test_question(message: types.Message, user_id: int):
    if user_id not in user_test_progress:
        await message.answer("❌ Начните тест заново, выбрав тему из меню.")
        return

    progress = user_test_progress[user_id]
    tests = progress["tests"]
    current_index = progress["current_question_index"]

    if current_index >= len(tests):
        # Завершение теста
        correct = progress["correct_answers"]
        total = len(tests)
        percentage = round(100 * correct / total) if total > 0 else 0

        user_stats[user_id]["tests_taken"] = user_stats[user_id].get("tests_taken", 0) + 1
        await check_and_award_badges(message, user_id)

        response = (
            f"🎉 Тест завершен!\n"
            f"Правильных ответов: {correct}/{total} ({percentage}%)\n\n"
            "Выбери следующее действие:" if percentage > 0.5 else
            f"Тест завершен.\n"
            f"Правильных ответов: {correct}/{total} ({percentage}%)\n"
            "Нужно повторить материал!\n\n"
            "Выбери следующее действие:"
        )

        await message.answer(response, reply_markup=get_main_menu_keyboard())
        del user_test_progress[user_id]
        return

    # Продолжение теста
    test = tests[current_index]
    user_tests[user_id] = test

    question_text = f"📊 <b>Вопрос {current_index + 1}:</b>\n{test['question']}"
    await message.answer(question_text, parse_mode="HTML")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=option, callback_data=f"answer_{i}")]
        for i, option in enumerate(test["options"])
    ])
    await message.answer("Выбери вариант ответа:", reply_markup=keyboard)


@router.callback_query(lambda callback: callback.data.startswith("answer_"))
async def handle_answer_selection(callback: CallbackQuery):
    user_id = callback.from_user.id

    # Проверяем активность теста
    if user_id not in user_tests or user_id not in user_test_progress:
        await callback.answer("Ошибка! Вопрос не найден.", show_alert=True)
        return

    test = user_tests[user_id]
    progress = user_test_progress[user_id]
    user_answer_index = int(callback.data.split("_")[1])
    question_id = f"{test['question'][:50]}"

    # Проверяем правильность ответа
    is_correct = user_answer_index in test["answer"]

    # Обработка ответа
    if is_correct:
        if question_id not in user_solved_items[user_id]["correct_questions"]:
            progress["correct_answers"] += 1
            user_stats[user_id]["correct_tests"] += 1
            user_solved_items[user_id]["correct_questions"].add(question_id)
            await check_and_award_badges(callback.message, user_id)
        response = "✅ Правильно!"
    else:
        update_weak_topics(user_id, progress["topic"])
        correct_answers = ", ".join([test["options"][i] for i in test["answer"]])
        response = f"❌ Неправильно. Правильный ответ: <b>{correct_answers}</b>"

    # Отправляем результат
    await callback.message.answer(response, parse_mode="HTML")

    # Удаляем текущий вопрос
    del user_tests[user_id]

    # Переход к следующему вопросу
    if user_id in user_test_progress:
        user_test_progress[user_id]["current_question_index"] += 1
        await send_next_test_question(callback.message, user_id)

    await callback.answer()


@router.callback_query(lambda callback: callback.data == "next_question")
async def handle_next_question(callback: CallbackQuery):
    user_id = callback.from_user.id

    if user_id not in user_test_progress:
        await callback.answer("Тест не найден.", show_alert=True)
        return

    progress = user_test_progress[user_id]
    progress["current_question_index"] += 1

    if progress["current_question_index"] < len(progress["tests"]):
        await send_next_test_question(callback.message, user_id)
    else:
        # Завершение теста
        correct = progress["correct_answers"]
        total = len(progress["tests"])
        percentage = round(100 * correct / total) if total > 0 else 0

        user_stats[user_id]["tests_taken"] += 1
        await callback.message.answer(
            f"🎉 Тест завершен!\n"
            f"Правильных ответов: {correct}/{total} ({percentage}%)\n\n"
            "Выбери следующее действие:",
            reply_markup=get_main_menu_keyboard()
        )
        del user_test_progress[user_id]

    await callback.answer()


async def check_and_award_badges(message: types.Message, user_id: int):
    if user_id not in user_stats:
        return

    stats = user_stats[user_id]
    badges = stats["badges"]

    # Бейдж за решение 10 тестов
    if stats["correct_tests"] >= 10 and "Решил 10 тестов" not in badges:
        badges.append("Решил 10 тестов")
        await message.answer("🎉 Ты получил бейдж «Решил 10 тестов»!")

    # Бейдж за решение 50 тестов
    if stats["correct_tests"] >= 50 and "Решил 50 тестов" not in badges:
        badges.append("Решил 50 тестов")
        await message.answer("🎉 Ты получил бейдж «Решил 50 тестов»!")

    # Бейдж за 100% в тесте
    if user_id in user_test_progress:
        progress = user_test_progress[user_id]
        correct = progress["correct_answers"]
        total = len(progress["tests"])
        if correct == total and "Тест на 100%" not in badges:
            badges.append("Тест на 100%")
            await message.answer("🎉 Ты получил бейдж «Тест на 100%»!")

    # Бейдж за 2 решенные задачи
    if stats.get("solved_tasks", 0) >= 2 and "2 задачи" not in badges:
        badges.append("2 задачи")
        await message.answer("🎉 Ты получил бейдж «2 задачи»!")


@router.message(Command("progress"))
@router.message(lambda m: m.text == "📈 Прогресс")
async def show_progress(message: types.Message):
    user_id = message.from_user.id
    init_user_data(user_id)

    if user_id not in user_stats:
        await message.answer("📊 Вы ещё не начали решать задачи или тесты.")
        return

    stats = user_stats[user_id]

    # Рассчитываем прогресс
    tasks_progress = create_progress_bar(stats["solved_tasks"], stats["total_tasks"])
    tests_progress = create_progress_bar(stats["correct_tests"], stats["total_questions"])

    # Рассчитываем процент выполнения
    if stats["total_tasks"] > 0:
        tasks_percent = round(100 * stats["solved_tasks"] / stats["total_tasks"])
    else:
        tasks_percent = 0

    if stats["total_questions"] > 0:
        tests_percent = round(100 * stats["correct_tests"] / stats["total_questions"])
    else:
        tests_percent = 0

    # Формируем список бейджей
    badges_text = "\n\n🏅 <b>Ваши бейджи:</b>\n" + ", ".join(stats.get("badges", ["Пока нет"])) if stats.get("badges") else ""

    response = (
        "📊 <b>Ваш прогресс:</b>\n\n"
        f"<b>Задачи:</b>\n{tasks_progress}\n"
        f"Решено: {stats['solved_tasks']}/{stats['total_tasks']} ({tasks_percent}%)\n\n"
        f"<b>Тесты:</b>\n{tests_progress}\n"
        f"Правильных ответов: {stats['correct_tests']}/{stats['total_questions']} ({tests_percent}%)\n\n"
        f"<b>Пройдено тестов:</b> {stats.get('tests_taken', 0)}"
        f"{badges_text}"
    )

    await message.answer(response, parse_mode="HTML")

    await message.answer_sticker(sticker=get_random_sticker("progress"))


@router.message(Command("recommend"))
@router.message(lambda message: message.text == "💡 Рекомендации")
async def handle_recommend_button(message: types.Message):
    # Создаем клавиатуру с кнопкой удаления истории
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Удалить историю рекомендаций", callback_data="delete_recommend_history")]
    ])

    # Вызываем функцию рекомендаций с возможностью удаления истории
    await give_recommendation(message, keyboard)


async def give_recommendation(message: types.Message, keyboard=None):
    user_id = message.from_user.id
    init_user_data(user_id)

    if not user_stats[user_id]["weak_topics"]:
        await message.answer(
            "📊 Вы пока не делали ошибок или статистика не собрана.\n"
            "Начните решать задачи или тесты, чтобы получить персональные рекомендации!",
            reply_markup=keyboard
        )
        return

    # Получаем словарь тем и количества ошибок
    topic_errors = user_stats[user_id]["weak_topics"]

    # Сортируем темы по количеству ошибок (от большего к меньшему)
    sorted_topics = sorted(topic_errors.items(), key=lambda x: x[1], reverse=True)

    # Формируем сообщение
    response = "📊 <b>Ваши слабые темы:</b>\n"
    for topic, errors in sorted_topics[:3]:  # Показываем топ-3
        response += f"\n• <u>{topic}</u>: {errors} ошибок"

    # Добавляем общий совет
    response += "\n\n💡 Совет: сосредоточьтесь на повторении этих тем!"

    await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
    await message.answer_sticker(sticker=get_random_sticker("recommend"))


@router.callback_query(lambda callback: callback.data == "delete_recommend_history")
async def delete_recommend_history(callback: CallbackQuery):
    user_id = callback.from_user.id
    init_user_data(user_id)

    # Очищаем историю рекомендаций
    user_stats[user_id]["weak_topics"] = []

    # Создаем новую клавиатуру (можно убрать после удаления)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Удалить историю рекомендаций", callback_data="delete_recommend_history")]
    ])

    await callback.message.answer(
        "✅ История рекомендаций очищена. Теперь статистика будет собираться заново."
    )
    await callback.answer()


def update_weak_topics(user_id, topic):
    if not topic:
        return

    # Инициализация данных пользователя (если ещё нет)
    if user_id not in user_stats:
        init_user_data(user_id)

    # Инициализация weak_topics (если ещё нет)
    if "weak_topics" not in user_stats[user_id]:
        user_stats[user_id]["weak_topics"] = {}

    # Увеличиваем счётчик ошибок для темы
    if topic in user_stats[user_id]["weak_topics"]:
        user_stats[user_id]["weak_topics"][topic] += 1
    else:
        user_stats[user_id]["weak_topics"][topic] = 1


@router.message(lambda message: message.text == "🔬 3D-Эксперименты")
async def handle_3d_experiments(message: types.Message):
    await message.answer(
        "Лаборатория 3D-экспериментов:\n\n"
        "Здесь вы можете взаимодействовать с интерактивными моделями",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔬 Открыть лабораторию", web_app=WebAppInfo(url="https://marisamak.github.io/menu.html"))],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    )

    await message.answer_sticker(sticker=STICKERS["experiments"])


@router.message(lambda message: message.text == "⬅️ Назад")
async def handle_back(message: types.Message):
    await message.answer(
        "Возвращаемся...",
        reply_markup=get_main_menu_keyboard()
    )


@router.message(lambda message: message.text == "⏰ Напоминания")
async def set_reminder(message: types.Message):
    # Переход в режим установки напоминания.
    user_states[message.from_user.id] = "setting_reminder"  # Устанавливаем состояние пользователя
    await message.answer("⏰ Введи время, когда ты хочешь получить напоминание, в формате ЧЧ:ММ. Например: 14:30")


async def schedule_reminder(user_id, remind_time):
    now = datetime.now()
    delay = (remind_time - now).total_seconds()
    await asyncio.sleep(delay)
    if user_id in user_reminders and user_reminders[user_id] == remind_time:
        del user_reminders[user_id]
        await bot.send_message(user_id, "⏰ Напоминание! Время продолжить подготовку! 🚀")


async def handle_reminder_time(message: types.Message):
    user_id = message.from_user.id
    try:
        remind_time = datetime.strptime(message.text.strip(), "%H:%M").time()
        now = datetime.now()
        remind_datetime = datetime.combine(now.date(), remind_time)

        if remind_datetime < now:
            remind_datetime += timedelta(days=1)

        user_reminders[user_id] = remind_datetime
        await message.answer(f"✅ Напоминание установлено на {remind_datetime.strftime('%H:%M')}.")
        asyncio.create_task(schedule_reminder(user_id, remind_datetime))

        # Сбрасываем состояние пользователя
        del user_states[user_id]
    except ValueError:
        await message.answer("❌ Неправильный формат времени. Введи в формате ЧЧ:ММ (например, 14:30).")

    await message.answer_sticker(sticker=get_random_sticker("reminders"))

    # Главное меню, если команда не распознана
    await message.answer("ℹ️ Выбери действие через меню.",reply_markup=get_main_menu_keyboard())


@router.message(lambda message: message.text == "🔗 Ссылки")
async def send_links(message: types.Message):
    links = [
        "https://fipi.ru/ege",
        "https://ege.sdamgia.ru/",
        "https://neznaika.info/",
        "https://neofamily.ru/fizika/smart-directory",
        "https://mizenko23.ru/wp-content/uploads/2019/04/jakovlev_fizika-polnyj_kurs_podgotovki_k_egeh.pdf",
        "https://thenewschool.ru/trainer/physics",
        "https://3.shkolkovo.online/catalog?SubjectId=4",
    ]

    links_text = "\n".join([f"🔗 <a href=\"{link}\">{link}</a>" for link in links])
    await message.answer(f"Вот полезные ресурсы:\n{links_text}", parse_mode="HTML")


@router.message()
async def process_user_message(message: types.Message):
    user_id = message.from_user.id
    user_state = user_states.get(user_id, STATE_NONE)

    if user_state == STATE_TASKS:
        await handle_task_answer(message)
    elif user_state == STATE_TESTS:
        # Если пользователь в режиме тестов, но пишет текст вместо выбора варианта
        await message.answer(
            "ℹ️ Пожалуйста, выберите тему теста через меню или используйте кнопки для ответа на вопросы теста.")
    elif user_state == "setting_reminder":
        await handle_reminder_time(message)
    else:
        await message.answer("ℹ️ Я не понимаю эту команду. Пожалуйста, выбери действие из меню ниже:",
                             reply_markup=get_main_menu_keyboard())


# Главный блок
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())