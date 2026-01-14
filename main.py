import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import google.generativeai as genai
from aiohttp import web

# Логирование
logging.basicConfig(level=logging.INFO)

# ПОЛУЧАЕМ ТОКЕНЫ
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Настройка Gemini
genai.configure(api_key=GOOGLE_API_KEY)

def get_available_model():
    """Автоматический подбор рабочей модели"""
    # Сначала пробуем самые стабильные варианты имен
    models_to_try = [
        'gemini-1.5-flash',
        'models/gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro'
    ]
    
    for m_name in models_to_try:
        try:
            m = genai.GenerativeModel(m_name)
            # Тестовый микро-запрос для проверки доступности
            m.generate_content("test", generation_config={"max_output_tokens": 1})
            logging.info(f"✅ Успешно подключена модель: {m_name}")
            return m
        except Exception as e:
            logging.warning(f"⚠️ Модель {m_name} недоступна: {e}")
            continue
    return None

# Инициализация модели
model = get_available_model()

if model is None:
    logging.error("❌ КРИТИЧЕСКАЯ ОШИБКА: Ни одна модель Gemini не ответила. Проверьте API ключ!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- Веб-сервер для Render ---
async def handle(request):
    return web.Response(text="Бот работает!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"✅ Веб-сервер на порту {port}")

# --- Логика бота ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🤖 Бот на Google Gemini запущен и готов решать задачи по фото и тексту!")

@dp.message(F.text)
async def handle_text(message: types.Message):
    if model is None:
        await message.answer("Ошибка: Модель ИИ не настроена. Проверьте логи сервера.")
        return
    
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        # Улучшенный промпт для математики
        prompt = f"Ты учитель. Реши задачу подробно. НЕ ИСПОЛЬЗУЙ LaTeX (символы $, \, {{}}). Пиши словами: корень, степень, угол. Задача: {message.text}"
        response = model.generate_content(prompt)
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Ошибка текста: {e}")
        await message.answer(f"Произошла ошибка: {str(e)}")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if model is None:
        await message.answer("Ошибка: Модель ИИ не настроена.")
        return

    await bot.send_chat_action(message.chat.id, "typing")
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        img_data = downloaded_file.read()
        
        # Передаем картинку правильно
        img_part = {'mime_type': 'image/jpeg', 'data': img_data}
        prompt = "Ты учитель. Реши задачу на фото максимально подробно. Пиши только словами, БЕЗ LaTeX символов."
        
        response = model.generate_content([prompt, img_part])
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Ошибка фото: {e}")
        await message.answer("Не удалось обработать фото. Попробуйте отправить текст или другое фото.")

async def main():
    # Запускаем сервер и бота
    asyncio.create_task(start_webserver())
    logging.info("🚀 Запуск Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
