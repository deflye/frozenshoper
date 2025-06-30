import logging
import asyncio
import aiohttp
import aiosqlite
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router
from aiogram.filters import Command
import uuid
from aiogram.client.default import DefaultBotProperties

# === НАСТРОЙКИ ===
BOT_TOKEN = "7782237361:AAHkPxLuwyxMujNNXCVoaI4LUIBWAuVuC98"
CRYPTO_PAY_TOKEN = "422558:AAGn5BqvTaiWcl9dVI698fq5pM1lnc3vmue"
CRYPTO_API_URL = "https://pay.crypt.bot/api"
DB_PATH = os.getenv("DB_PATH", "/tmp/users.db")  # путь для Scalingo

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)
logging.basicConfig(level=logging.INFO)

# === ИНИЦИАЛИЗАЦИЯ БД ===
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product TEXT,
                price REAL,
                quantity INTEGER
            )
        """)
        await db.commit()

# === ГЛАВНОЕ МЕНЮ ===
def get_main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Все категории", callback_data="all_categories")
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.button(text="ℹ️ Информация", callback_data="info")
    return kb.as_markup()

# === КАТЕГОРИИ ===
@router.callback_query(F.data == "all_categories")
async def categories(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Kleinanzeigen", callback_data="kleinanzeigen")
    kb.button(text="Мануалы", callback_data="manuals")
    kb.button(text="🔙 Назад", callback_data="back_to_main")
    await call.message.edit_text("Выберите категорию:", reply_markup=kb.as_markup())

# === ТОВАРЫ В Kleinanzeigen ===
@router.callback_query(F.data == "kleinanzeigen")
async def show_item(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Саморег Germany номер 7$", callback_data="buy_germany")
    kb.button(text="🔙 Назад", callback_data="all_categories")
    await call.message.edit_text("Доступные товары:", reply_markup=kb.as_markup())

# === ТОВАРЫ В МАНУАЛАХ ===
@router.callback_query(F.data == "manuals")
async def show_manual(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Купить за 200$", callback_data="buy_manual")
    kb.button(text="🔙 Назад", callback_data="all_categories")
    await call.message.edit_text(
        "📃 Товар: Обход фрода Kleinanzeigen\n"
        "💰 Цена: 200$\n"
        "📄 Описание: Подробный мануал по обходу антифрода Kleinanzeigen.",
        reply_markup=kb.as_markup()
    )

# === ВЫБОР КОЛ-ВА ДЛЯ GERMANY ===
@router.callback_query(F.data == "buy_germany")
async def quantity_select(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for qty in [3, 4, 5, 10]:
        kb.button(text=str(qty), callback_data=f"pay_germany_{qty}")
    kb.button(text="🔙 Назад", callback_data="kleinanzeigen")
    await call.message.edit_text(
        "📃 Товар: Саморег Germany номер\n"
        "💰 Цена: 7$ \n"
        "📃 Описание: Саморег с германским номером. cookie в формате .json\n\n"
        "Выберите количество товара, которое хотите купить:",
        reply_markup=kb.as_markup()
    )

# === ОПЛАТА GERMANY ===
@router.callback_query(F.data.startswith("pay_germany_"))
async def pay_crypto(call: types.CallbackQuery):
    qty = int(call.data.split("_")[-1])
    amount = 7 * qty
    unique_id = str(uuid.uuid4())[:7]
    payload = f"{call.from_user.id}:germany:{unique_id}"

    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        json_data = {
            "asset": "USDT",
            "amount": str(amount),
            "description": f"Покупка: Germany Number x{qty} (ID: {unique_id})",
            "hidden_message": "Спасибо за покупку!",
            "payload": payload
        }
        async with session.post(f"{CRYPTO_API_URL}/createInvoice", headers=headers, json=json_data) as resp:
            result = await resp.json()
            if "result" not in result:
                await call.message.answer("❌ Ошибка при создании счёта.")
                return

            invoice = result['result']
            kb = InlineKeyboardBuilder()
            kb.button(text="💳 ОПЛАТИТЬ", url=invoice['pay_url'])
            kb.button(text="🔙 Назад", callback_data="kleinanzeigen")
            await call.message.answer(
                f"💰 Покупка Germany x{qty}\n"
                f"💵 Сумма: {amount}$\n"
                f"🧾 Комментарий к оплате: {unique_id}",
                reply_markup=kb.as_markup()
            )
            asyncio.create_task(wait_and_check_payment(invoice['invoice_id'], call.from_user.id, "Саморег Germany Number", 7, qty))

# === ОПЛАТА MANUAL ===
@router.callback_query(F.data == "buy_manual")
async def pay_manual(call: types.CallbackQuery):
    amount = 200
    unique_id = str(uuid.uuid4())[:7]
    payload = f"{call.from_user.id}:manual:{unique_id}"

    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        json_data = {
            "asset": "USDT",
            "amount": str(amount),
            "description": f"Покупка: Обход фрода (ID: {unique_id})",
            "hidden_message": "Спасибо за покупку!",
            "payload": payload
        }
        async with session.post(f"{CRYPTO_API_URL}/createInvoice", headers=headers, json=json_data) as resp:
            result = await resp.json()
            if "result" not in result:
                await call.message.answer("❌ Ошибка при создании счёта.")
                return

            invoice = result['result']
            kb = InlineKeyboardBuilder()
            kb.button(text="💳 ОПЛАТИТЬ", url=invoice['pay_url'])
            kb.button(text="🔙 Назад", callback_data="manuals")
            await call.message.answer(
                f"💰 Покупка: Обход фрода Kleinanzeigen\n"
                f"💵 Сумма: 200$\n"
                f"🧾 Комментарий к оплате: {unique_id}",
                reply_markup=kb.as_markup()
            )
            asyncio.create_task(wait_and_check_payment(invoice['invoice_id'], call.from_user.id, "Обход фрода Kleinanzeigen", 200, 1))

# === ПРОВЕРКА ОПЛАТЫ ===
async def wait_and_check_payment(invoice_id, user_id, product_name, price, quantity):
    await asyncio.sleep(120)
    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        async with session.post(f"{CRYPTO_API_URL}/getInvoice", headers=headers, json={"invoice_ids": [invoice_id]}) as resp:
            result = await resp.json()
            if result.get("result"):
                invoice = result["result"][0]
                if invoice.get("status") == "paid":
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("""
                            INSERT INTO purchases (user_id, product, price, quantity)
                            VALUES (?, ?, ?, ?)
                        """, (user_id, product_name, price, quantity))
                        await db.commit()

# === ПРОФИЛЬ ===
@router.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT product, price, quantity FROM purchases WHERE user_id = ?", (call.from_user.id,))
        rows = await cursor.fetchall()

    if not rows:
        text = "У вас пока нет покупок."
    else:
        total = sum(price * qty for _, price, qty in rows)
        purchases = "\n".join([f"🔹 {prod} x{qty} — {price * qty}$" for prod, price, qty in rows])
        text = f"<b>👤 Ваш профиль:</b>\nИмя: {call.from_user.first_name}\n\n<b>🛒 Покупки:</b>\n{purchases}\n\n💰 Всего пополнений: {total}$"

    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data="back_to_main")
    await call.message.edit_text(text, reply_markup=kb.as_markup())

# === ИНФО ===
@router.callback_query(F.data == "info")
async def info(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data="back_to_main")
    await call.message.edit_text("Поддержка бота — @dmitriyutkjn", reply_markup=kb.as_markup())

# === НАЗАД ===
@router.callback_query(F.data == "back_to_main")
async def back(call: types.CallbackQuery):
    await call.message.edit_text("🔘 Главное меню:", reply_markup=get_main_menu())

# === START ===
@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🔘 Главное меню:", reply_markup=get_main_menu())

# === RUN ===
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
