import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import google.generativeai as genai
from aiohttp import web

# Берем токены из настроек Render
TELEGRAM_TOKEN = os.getenv("8511912777:AAHhUtLcjs8-6aW_ls81ONjXCKgYlVx8fcU")
GOOGLE_API_KEY = os.getenv("AIzaSyAoYb8sy7u8CGC1paTLGVNJ7XZRJka-a6g")

# Настройка Gemini
genai.configure(api_key=GOOGLE_API_KEY)
# Используем модель flash — она самая быстрая и бесплатная
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- Веб-сервер для "здоровья" Render ---
async def handle(request):
    return web.Response(text="Бот онлайн!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render сам подставит нужный порт
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- Логика ответов ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("✅ Бот готов к работе в РФ! Присылай текст или фото задачи. Я использую Google Gemini.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        prompt = f"Ты учитель. Реши задачу. Запрет на символы LaTeX ($, \\, {{}}). Пиши словами (угол, корень, вектор). Задача: {message.text}"
        response = model.generate_content(prompt)
        await message.answer(response.text)
    except Exception as e:
        await message.answer("Произошла ошибка. Попробуйте еще раз позже.")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        img_data = downloaded_file.read()

        # Формируем запрос
        contents = [
            "Ты учитель. Реши задачу на фото максимально подробно. Пиши только словами, без LaTeX символов.",
            {'mime_type': 'image/jpeg', 'data': img_data}
        ]
        
        response = model.generate_content(contents)
        await message.answer(response.text)
    except Exception as e:
        await message.answer("Не удалось распознать фото. Попробуйте сделать снимок четче.")

async def main():
    # Запуск сервера и бота параллельно
    asyncio.create_task(start_webserver())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
