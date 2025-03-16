import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv("config.env")

# Настройка логирования с датой и временем
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",  # Добавляем дату и время
    datefmt="%Y-%m-%d %H:%M:%S"  # Формат даты и времени
)
logger = logging.getLogger(__name__)

# ___________________________________________ Основные переменные ______________________________________________________
token = os.getenv("TOKEN")
doctor_name = os.getenv("DOCTOR_NAME")
doctor_id = os.getenv("DOCTOR_ID")
delay = int(os.getenv("DELAY"))  # Интервал в секундах
# ______________________________________________________________________________________________________________________

url = f'https://telemed-patient-bff.sberhealth.ru/api/showcase/web/v1/providers/62/doctors/{doctor_id}/specialties/psychologist/slots'


# Функция для проверки слотов
async def check_slots(context: ContextTypes.DEFAULT_TYPE, chat_id: int = None):
    if chat_id is None:
        chat_id = context.job.chat_id

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            slots = data['slots']
            if len(slots) > 0:
                await context.bot.send_message(chat_id=chat_id, text="Слоты есть!")
            else:
                if hasattr(context, 'manual_check') and context.manual_check:
                    await context.bot.send_message(chat_id=chat_id, text="Свободных слотов пока нет.")
        else:
            await context.bot.send_message(chat_id=chat_id,
                                           text=f'Ошибка при получении данных. Код статуса: {response.status_code}')
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Ошибка при обработке данных.")


# Команда для запуска проверки слотов
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if jobs:
        await update.message.reply_text("Проверка уже запущена.")
        return

    delay_minutes = delay / 60  # Переводим в минуты
    if delay_minutes < 1:
        text = f"Доктор {doctor_name}. Запущена проверка слотов каждые {delay} секунд."
    else:
        text = f"Доктор {doctor_name}. Запущена проверка слотов каждые {delay_minutes:.1f} минут."

    # Передаем chat_id в задачу
    context.job_queue.run_repeating(
        check_slots,  # Используем функцию напрямую
        interval=delay,
        first=0,
        chat_id=chat_id,
        name=str(chat_id)
    )
    await update.message.reply_text(text)


# Команда для остановки проверки слотов
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    jobs = context.job_queue.get_jobs_by_name(chat_id)

    if jobs:
        for job in jobs:
            job.schedule_removal()
        await update.message.reply_text("Проверка остановлена.")
    else:
        await update.message.reply_text("Проверка не была запущена.")


# Команда для проверки статуса проверки слотов
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    jobs = context.job_queue.get_jobs_by_name(chat_id)

    if jobs:
        await update.message.reply_text(f"Доктор {doctor_name}. Проверка активна.")
    else:
        await update.message.reply_text("Проверка не активна.")


async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        context.manual_check = True
        await check_slots(context, chat_id)
        await update.message.reply_text(f"Доктор {doctor_name}. Ручная проверка выполнена.")
    except Exception as e:
        logger.error(f"Ошибка при ручной проверке: {e}")
        await update.message.reply_text("Произошла ошибка при ручной проверке.")


async def send_startup_message(application: Application):
    chat_id = os.getenv("CHAT_ID")
    await application.bot.send_message(chat_id, text="Бот запущен!")


if __name__ == '__main__':
    application = Application.builder().token(token).post_init(send_startup_message).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler('check', check))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('manual_check', manual_check))

    # Запускаем бота
    application.run_polling()
