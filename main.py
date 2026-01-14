import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import google.generativeai as genai
from aiohttp import web

# Включаем логирование, чтобы видеть ошибки в панели Render
logging.basicConfig(level=logging.INFO)

# ПОЛУЧАЕМ ТОКЕНЫ
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ПРОВЕРКА НАЛИЧИЯ КЛЮЧЕЙ
if not TELEGRAM_TOKEN or not GOOGLE_API_KEY:
    print("❌ ОШИБКА: Переменные TELEGRAM_TOKEN или GOOGLE_API_KEY не заданы в настройках Render!")

# Настройка Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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
    print(f"✅ Веб-сервер запущен на порту {port}")

# --- Логика ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🤖 Бот на Gemini запущен! Присылай задачу.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    try:
        response = model.generate_content(f"Реши задачу (без LaTeX): {message.text}")
        await message.answer(response.text)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        img_data = downloaded_file.read()
        
        response = model.generate_content(["Реши задачу на фото (без LaTeX)", {'mime_type': 'image/jpeg', 'data': img_data}])
        await message.answer(response.text)
    except Exception as e:
        await message.answer(f"Ошибка фото: {e}")

async def main():
    asyncio.create_task(start_webserver())
    print("🚀 Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
