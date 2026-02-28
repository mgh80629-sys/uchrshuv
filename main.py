import asyncio
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from database import (
    init_db,
    insert_service,
    get_services,
    get_masters,
    get_booked_slots,
    add_appointment,
    insert_master,
    delete_master
)

# ================= CONFIG =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

WORK_START = 9
WORK_END = 18
SLOT_INTERVAL = 30

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

user_data = {}

# ================= FSM =================
class AddServiceState(StatesGroup):
    name = State()
    price = State()
    duration = State()


class AddMasterState(StatesGroup):
    name = State()


# ================= UTIL =================
def generate_slots():
    slots = []
    start = datetime.now().replace(hour=WORK_START, minute=0, second=0)
    end = datetime.now().replace(hour=WORK_END, minute=0)

    while start < end:
        slots.append(start.strftime("%H:%M"))
        start += timedelta(minutes=SLOT_INTERVAL)

    return slots


# ================= KEYBOARDS =================
def services_keyboard(services):
    kb = []
    for s in services:
        kb.append([
            InlineKeyboardButton(
                text=f"{s[1]} - {s[2]} so'm",
                callback_data=f"service_{s[0]}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def masters_keyboard(masters):
    kb = []
    for m in masters:
        kb.append([
            InlineKeyboardButton(
                text=m[1],
                callback_data=f"master_{m[0]}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def masters_admin_keyboard(masters):
    kb = []
    for m in masters:
        kb.append([
            InlineKeyboardButton(
                text=f"❌ {m[1]}",
                callback_data=f"delete_master_{m[0]}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def days_keyboard():
    kb = []
    today = datetime.now()
    for i in range(7):
        day = today + timedelta(days=i)
        kb.append([
            InlineKeyboardButton(
                text=day.strftime("%d-%m"),
                callback_data=f"day_{day.strftime('%Y-%m-%d')}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def slots_keyboard(slots):
    kb = []
    for s in slots:
        kb.append([
            InlineKeyboardButton(
                text=s,
                callback_data=f"time_{s}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ================= REMINDER =================
async def send_reminder(user_id, date, time):
    await bot.send_message(
        user_id,
        f"⏰ Eslatma!\n\n1 soatdan keyin navbatingiz bor.\n{date} {time}"
    )


# ================= START =================
@dp.message(CommandStart())
async def start(message: Message):
    services = await get_services()
    if not services:
        await message.answer("Admin hali xizmat qo‘shmagan.")
        return
    await callback.answer()    
    await message.answer("Xizmatni tanlang:", reply_markup=services_keyboard(services))


# ================= ADMIN SERVICE =================
@dp.message(Command("admin1"))
async def add_service_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Yangi xizmat nomini kiriting:")
    await state.set_state(AddServiceState.name)


@dp.message(AddServiceState.name)
async def add_service_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Narxini kiriting (faqat raqam):")
    await state.set_state(AddServiceState.price)


@dp.message(AddServiceState.price)
async def add_service_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting!")
        return

    await state.update_data(price=int(message.text))
    await message.answer("Davomiyligini kiriting (minut):")
    await state.set_state(AddServiceState.duration)


@dp.message(AddServiceState.duration)
async def add_service_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting!")
        return

    data = await state.get_data()

    await insert_service(
        data["name"],
        data["price"],
        int(message.text)
    )

    await message.answer("✅ Xizmat qo‘shildi!")
    await state.clear()


# ================= ADMIN MASTER =================
@dp.message(Command("admin2"))
async def add_master_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer("Yangi usta ismini kiriting:")
    await state.set_state(AddMasterState.name)


@dp.message(AddMasterState.name)
async def add_master_name(message: Message, state: FSMContext):
    await insert_master(message.text)
    await message.answer("✅ Usta muvaffaqiyatli qo‘shildi!")
    await state.clear()


@dp.message(Command("daletmas"))
async def admin_masters_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    masters = await get_masters()

    if not masters:
        await message.answer("Hozircha ustalar yo‘q.")
        return

    await message.answer(
        "🛠 Ustalar ro‘yxati:\n(O‘chirish uchun bosing)",
        reply_markup=masters_admin_keyboard(masters)
    )


@dp.callback_query(F.data.startswith("daletmas"))
async def delete_master_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    master_id = int(callback.data.split("_")[2])
    await delete_master(master_id)

    masters = await get_masters()

    if masters:
        await callback.message.edit_text(
            "🛠 Ustalar ro‘yxati:\n(O‘chirish uchun bosing)",
            reply_markup=masters_admin_keyboard(masters)
        )
    else:
        await callback.message.edit_text("Hozircha ustalar yo‘q.")

    await callback.answer("Usta o‘chirildi ✅")


# ================= CLIENT FLOW =================
@dp.callback_query(F.data.startswith("service_"))
async def service_selected(callback: CallbackQuery):
    user_data[callback.from_user.id] = {
        "service_id": int(callback.data.split("_")[1])
    }

    masters = await get_masters()
    await callback.message.answer("Ustani tanlang:", reply_markup=masters_keyboard(masters))


@dp.callback_query(F.data.startswith("master_"))
async def master_selected(callback: CallbackQuery):
    user_data[callback.from_user.id]["master_id"] = int(callback.data.split("_")[1])
    await callback.message.answer("Kunni tanlang:", reply_markup=days_keyboard())


@dp.callback_query(F.data.startswith("day_"))
async def day_selected(callback: CallbackQuery):
    date = callback.data.split("_")[1]
    user_data[callback.from_user.id]["date"] = date

    master_id = user_data[callback.from_user.id]["master_id"]
    booked = await get_booked_slots(date, master_id)
    all_slots = generate_slots()
    free = [s for s in all_slots if s not in booked]

    if not free:
        await callback.message.answer("Bo‘sh vaqt yo‘q ❌")
        return

    await callback.message.answer("Vaqtni tanlang:", reply_markup=slots_keyboard(free))


@dp.callback_query(F.data.startswith("time_"))
async def time_selected(callback: CallbackQuery):
    time = callback.data.split("_")[1]
    data = user_data[callback.from_user.id]

    await add_appointment(
        callback.from_user.id,
        data["service_id"],
        data["master_id"],
        data["date"],
        time
    )

    appointment_dt = datetime.strptime(
        f"{data['date']} {time}",
        "%Y-%m-%d %H:%M"
    )
    reminder_time = appointment_dt - timedelta(hours=1)

    if reminder_time > datetime.now():
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=reminder_time,
            args=[callback.from_user.id, data["date"], time]
        )

    await callback.message.answer(f"✅ Uchrashuv belgilandi!\n{data['date']} {time}")


# ================= MAIN =================
async def main():
    await init_db()
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
