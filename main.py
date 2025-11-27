import asyncio
import logging
import aiohttp
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

BOT_TOKEN = "8157782936:AAHhp9dImUyPG53oVqP1F56dOQ2GR1iDgt4"
FACT_API_URL = "https://uselessfacts.jsph.pl/random.json?language=en"
TRANSLATE_API_URL = "https://api.mymemory.translated.net/get"
DATA_FILE = "bot_data.json"
ADMIN_PASSWORD = "Muhammadamin"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Admin va foydalanuvchilar
admin_users = set()
users_data = {}



# Barcha uzbek faktlar (standart + foydalanuvchi qo'shgan)
uzbek_facts = [
     "Kamalakni faqat ertalab yoki kechqurun ko'rish mumkin. Bu faqat quyosh ufqdan 40 daraja yoki undan kam balandlikda bo'lganda yuzaga kelishi mumkin.",
    "O'zbekiston dunyodagi eng qadimiy shaharlardan biri bo'lgan Samarqandga ega.",
    "O'zbek tilida 100 dan ortiq turli xil salomlashish usullari mavjud.",
    "O'zbekistonning milliy taomi - palov, UNESCO nomzodlar ro'yxatiga kiritilgan.",
    "O'zbekistonda yiliga 300 dan ortiq quyoshli kun bo'ladi.",
    "Toshkent shahri Osiyodagi eng yirik shaharlardan biri hisoblanadi.",
    "O'zbekistonning qadimiy shaharlari Buyuk Ipak yo'li bo'ylab joylashgan.",
    "O'zbek tilida so'zlar asosan turkiy tillar oilasiga mansub.",
]

def load_data():
    """JSON fayldan barcha ma'lumotlarni yuklash"""
    global uzbek_facts, users_data
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                uzbek_facts = data.get('uzbek_facts', uzbek_facts.copy())
                users_data = data.get('users_data', {})
        else:
            save_data()
    except Exception as e:
        print(f"Ma'lumotlarni yuklashda xatolik: {e}")

def save_data():
    """Barcha ma'lumotlarni JSON faylga saqlash"""
    try:
        data = {
            'uzbek_facts': uzbek_facts,
            'users_data': users_data,
            'total_facts': len(uzbek_facts),
            'total_users': len(users_data),
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ma'lumotlarni saqlashda xatolik: {e}")

def update_user_data(user_id, username, first_name):
    """Foydalanuvchi ma'lumotlarini yangilash"""
    user_key = str(user_id)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if user_key not in users_data:
        users_data[user_key] = {
            'user_id': user_id,
            'username': username or "Yo'q",
            'first_name': first_name or "Noma'lum",
            'first_seen': current_time,
            'last_activity': current_time,
            'message_count': 1
        }
    else:
        users_data[user_key]['last_activity'] = current_time
        users_data[user_key]['message_count'] += 1
        users_data[user_key]['username'] = username or users_data[user_key]['username']
        users_data[user_key]['first_name'] = first_name or users_data[user_key]['first_name']
    
    save_data()

def get_main_menu():
    """Asosiy menyu yaratish"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌍 Aralash faktlar"), KeyboardButton(text="🇺🇿 Uzbek faktlar")],
            [KeyboardButton(text="✨ Qiziqarli fakt qo'shish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_admin_menu():
    """Admin menyu yaratish"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="📚 Faktlar boshqaruvi")],
            [KeyboardButton(text="🌍 Aralash faktlar"), KeyboardButton(text="🇺🇿 Uzbek faktlar")],
            [KeyboardButton(text="✨ Qiziqarli fakt qo'shish")],
            [KeyboardButton(text="👤 Oddiy menyu")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_fact_management_menu():
    """Faktlarni boshqarish menyusi"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi fakt qo'shish", callback_data="add_fact")],
            [InlineKeyboardButton(text="📋 Barcha faktlarni ko'rish", callback_data="list_facts")],
            [InlineKeyboardButton(text="🗑️ Fakt o'chirish", callback_data="delete_fact")],
            [InlineKeyboardButton(text="✏️ Fakt tahrirlash", callback_data="edit_fact")],
            [InlineKeyboardButton(text="📊 Faktlar statistikasi", callback_data="fact_stats")]
        ]
    )
    return keyboard

async def translate_to_uzbek(text: str) -> str:
    """Matnni o'zbekchaga tarjima qilish"""
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                'q': text,
                'langpair': 'en|uz'
            }
            async with session.get(TRANSLATE_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    translated = data.get('responseData', {}).get('translatedText', text)
                    return translated
                else:
                    return text
    except Exception as e:
        print(f"Tarjima xatosi: {str(e)}")
        return text

async def get_random_fact():
    """Tasodifiy fakt olish va tarjima qilish funksiyasi"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(FACT_API_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    fact_en = data.get('text', 'Fakt topilmadi')
                    # Ingliz tilidagi faktni o'zbekchaga tarjima qilish
                    fact_uz = await translate_to_uzbek(fact_en)
                    return fact_uz
                else:
                    return "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
    except Exception as e:
        return f"Xatolik: {str(e)}"

def get_random_uzbek_fact():
    """Tasodifiy o'zbek faktini olish"""
    import random
    if uzbek_facts:
        return random.choice(uzbek_facts)
    return "Hozircha faktlar mavjud emas."

@dp.message(Command("login"))
async def cmd_login(message: Message):
    """Admin login"""
    await message.answer("🔐 Admin parolini kiriting:")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Start komandasi"""
    # Foydalanuvchi ma'lumotlarini yangilash
    update_user_data(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    if message.from_user.id in admin_users:
        await message.answer(
            "🔥 <b>Salom Admin!</b> 🔥\n\n"
            "🎛️ <b>Admin paneliga xush kelibsiz!</b>\n"
            "🚀 Barcha funksiyalar sizning ixtiyoringizda!\n\n"
            "👇 <b>Quyidagi tugmalardan foydalaning:</b>",
            parse_mode="HTML",
            reply_markup=get_admin_menu()
        )
    else:
        await message.answer(
            "🎉 <b>Salom! Men RandomFactBot!</b> 🤖\n\n"
            "💡 Men sizga <b>qiziqarli tasodifiy faktlar</b> yuboraman!\n"
            "🌟 Har kuni yangi bilimlar oling!\n\n"
            "👇 <b>Quyidagi menyudan tanlang:</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Help komandasi"""
    menu = get_admin_menu() if message.from_user.id in admin_users else get_main_menu()
    await message.answer(
        "🆘 <b>RandomFactBot Yordami</b> 🆘\n\n"
        "🔧 <b>Komandalar:</b>\n"
        "• /start - Botni qayta ishga tushirish\n"
        "• /help - Bu yordam xabari\n"
        "• /login - Admin paneli (maxsus)\n\n"
        "🎯 <b>Menyu tugmalari:</b>\n"
        "🌍 <b>Aralash faktlar</b> - Dunyodagi qiziq faktlar\n"
        "🇺🇿 <b>Uzbek faktlar</b> - O'zbekistonga oid faktlar\n"
        "✨ <b>Fakt qo'shish</b> - O'z faktingizni ulashing\n\n"
        "💬 <b>Maslahat:</b> Har qanday savollar uchun menyudan foydalaning!",
        parse_mode="HTML",
        reply_markup=menu
    )

@dp.message(Command("fact"))
async def cmd_fact(message: Message):
    """Tasodifiy fakt yuborish"""
    await message.answer("⏳ Fakt qidirilmoqda...", reply_markup=get_main_menu())
    fact = await get_random_fact()
    await message.answer(f"💡 <b>Qiziqarli fakt:</b>\n\n{fact}", parse_mode="HTML", reply_markup=get_main_menu())

@dp.message(lambda message: message.text in ["👥 Foydalanuvchilar", "📊 Foydalanuvchilar"])
async def handle_users_stats(message: Message):
    """Foydalanuvchilar statistikasi"""
    if message.from_user.id not in admin_users:
        await message.answer("❌ Sizda admin huquqi yo'q!")
        return
    
    if not users_data:
        await message.answer("📊 Hozircha foydalanuvchilar yo'q.", reply_markup=get_admin_menu())
        return
    
    stats_text = "📊 <b>Foydalanuvchilar statistikasi:</b>\n\n"
    for i, (user_id, data) in enumerate(users_data.items(), 1):
        stats_text += (
            f"{i}. <b>ID:</b> {data['user_id']}\n"
            f"   <b>Ism:</b> {data['first_name']}\n"
            f"   <b>Username:</b> @{data['username']}\n"
            f"   <b>Birinchi kirgan:</b> {data['first_seen']}\n"
            f"   <b>Oxirgi faollik:</b> {data['last_activity']}\n"
            f"   <b>Xabarlar soni:</b> {data['message_count']}\n\n"
        )
    
    await message.answer(stats_text, parse_mode="HTML", reply_markup=get_admin_menu())

@dp.message(lambda message: message.text in ["📚 Faktlar boshqaruvi", "📝 Faktlarni boshqarish"])
async def handle_fact_management(message: Message):
    """Faktlarni boshqarish"""
    if message.from_user.id not in admin_users:
        await message.answer("❌ Sizda admin huquqi yo'q!")
        return
    
    await message.answer(
        "📝 <b>Faktlarni boshqarish</b>\n\n"
        f"Jami faktlar: {len(uzbek_facts)}\n\n"
        "Quyidagi amallardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=get_fact_management_menu()
    )

@dp.message(lambda message: message.text in ["👤 Oddiy menyu", "🔙 Oddiy menyu"])
async def handle_back_to_user(message: Message):
    """Oddiy menyuga qaytish"""
    if message.from_user.id in admin_users:
        admin_users.remove(message.from_user.id)
    
    await message.answer(
        "🔙 Oddiy foydalanuvchi menyusiga qaytdingiz:",
        reply_markup=get_main_menu()
    )

@dp.message(lambda message: message.text in ["🌍 Aralash faktlar", "Aralash faktlar"])
async def handle_mixed_facts(message: Message):
    """Aralash faktlar"""
    update_user_data(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    menu = get_admin_menu() if message.from_user.id in admin_users else get_main_menu()
    await message.answer("⏳ Fakt qidirilmoqda...", reply_markup=menu)
    fact = await get_random_fact()
    await message.answer(f"💡 <b>Aralash fakt:</b>\n\n{fact}", parse_mode="HTML", reply_markup=menu)

@dp.message(lambda message: message.text in ["🇺🇿 Uzbek faktlar", "Uzbek faktlar"])
async def handle_uzbek_facts(message: Message):
    """Uzbek faktlar"""
    update_user_data(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    fact = get_random_uzbek_fact()
    menu = get_admin_menu() if message.from_user.id in admin_users else get_main_menu()
    await message.answer(f"🇺🇿 <b>O'zbek fakt:</b>\n\n{fact}", parse_mode="HTML", reply_markup=menu)

@dp.message(lambda message: message.text in ["✨ Qiziqarli fakt qo'shish", "Qiziqarli fakt qo'shish"])
async def handle_add_fact(message: Message):
    """Fakt qo'shish so'rovi"""
    update_user_data(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    menu = get_admin_menu() if message.from_user.id in admin_users else get_main_menu()
    await message.answer(
        "✍️ Qiziqarli faktingizni yuboring!\n\n"
        "Masalan: 'O'zbekistonda 12 ta viloyat mavjud.'\n\n"
        "Yoki /start tugmasini bosing va menyudan tanlang.",
        reply_markup=menu
    )

@dp.message()
async def echo_message(message: Message):
    """Barcha xabarlarni qayta ishlash"""
    text = message.text.lower()
    
    # Admin login tekshirish
    if message.text == ADMIN_PASSWORD:
        admin_users.add(message.from_user.id)
        await message.answer(
            "✅ Admin sifatida kirdingiz!\n\n"
            "🔧 Admin paneliga xush kelibsiz:",
            reply_markup=get_admin_menu()
        )
        return
    
    # Foydalanuvchi ma'lumotlarini yangilash
    update_user_data(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    menu = get_admin_menu() if message.from_user.id in admin_users else get_main_menu()
    
    # Agar foydalanuvchi fakt qo'shish jarayonida bo'lsa
    if len(text) > 10 and not text.startswith('/'):
        # Faktni uzbek_facts ro'yxatiga qo'shish
        uzbek_facts.append(message.text)
        # JSON faylga saqlash
        save_data()
        
        fact_number = len(uzbek_facts)
        await message.answer(
            "✅ Fakt muvaffaqiyatli qo'shildi!\n"
            "🇺🇿 Bu fakt endi 'Uzbek faktlar' bo'limida ko'rinadi.",
            reply_markup=menu
        )
    elif 'fakt' in text or 'fact' in text:
        await message.answer("⏳ Fakt qidirilmoqda...", reply_markup=menu)
        fact = await get_random_fact()
        await message.answer(f"💡 <b>Qiziqarli fakt:</b>\n\n{fact}", parse_mode="HTML", reply_markup=menu)
    else:
        await message.answer(
            "Menyudan tanlang yoki /start tugmasini bosing!",
            reply_markup=menu
        )

# Callback handlerlar
@dp.callback_query(lambda c: c.data == "list_facts")
async def show_all_facts(callback: CallbackQuery):
    """Barcha faktlarni ko'rsatish"""
    if callback.from_user.id not in admin_users:
        await callback.answer("❌ Sizda admin huquqi yo'q!")
        return
    
    if not uzbek_facts:
        await callback.message.answer("📋 Hozircha faktlar yo'q.")
        return
    
    facts_text = "📋 <b>Barcha faktlar:</b>\n\n"
    for i, fact in enumerate(uzbek_facts, 1):
        facts_text += f"{i}. {fact}\n\n"
        if len(facts_text) > 3500:  # Telegram limit
            await callback.message.answer(facts_text, parse_mode="HTML")
            facts_text = ""
    
    if facts_text:
        await callback.message.answer(facts_text, parse_mode="HTML")
    
    await callback.answer()

@dp.callback_query(lambda c: c.data == "add_fact")
async def add_fact_prompt(callback: CallbackQuery):
    """Admin fakt qo'shish"""
    if callback.from_user.id not in admin_users:
        await callback.answer("❌ Sizda admin huquqi yo'q!")
        return
    
    await callback.message.answer(
        "➕ <b>Yangi fakt qo'shish</b>\n\n"
        "Faktni yuboring:",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "delete_fact")
async def delete_fact_prompt(callback: CallbackQuery):
    """Fakt o'chirish"""
    if callback.from_user.id not in admin_users:
        await callback.answer("❌ Sizda admin huquqi yo'q!")
        return
    
    if not uzbek_facts:
        await callback.message.answer("📋 O'chiriladigan faktlar yo'q.")
        await callback.answer()
        return
    
    facts_text = "🗑 <b>O'chirish uchun fakt raqamini yuboring:</b>\n\n"
    for i, fact in enumerate(uzbek_facts, 1):
        facts_text += f"{i}. {fact[:50]}...\n"
        if i >= 10:  # Faqat 10 ta ko'rsatish
            facts_text += f"\n... va yana {len(uzbek_facts) - 10} ta fakt"
            break
    
    await callback.message.answer(facts_text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "edit_fact")
async def edit_fact_prompt(callback: CallbackQuery):
    """Fakt o'zgartirish"""
    if callback.from_user.id not in admin_users:
        await callback.answer("❌ Sizda admin huquqi yo'q!")
        return
    
    if not uzbek_facts:
        await callback.message.answer("📋 O'zgartiriladigan faktlar yo'q.")
        await callback.answer()
        return
    
    facts_text = "✏️ <b>O'zgartirish uchun fakt raqamini yuboring:</b>\n\n"
    for i, fact in enumerate(uzbek_facts, 1):
        facts_text += f"{i}. {fact[:50]}...\n"
        if i >= 10:
            facts_text += f"\n... va yana {len(uzbek_facts) - 10} ta fakt"
            break
    
    await callback.message.answer(facts_text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "fact_stats")
async def show_fact_stats(callback: CallbackQuery):
    """Faktlar statistikasi"""
    if callback.from_user.id not in admin_users:
        await callback.answer("❌ Sizda admin huquqi yo'q!")
        return
    
    stats_text = (
        "📊 <b>Faktlar Statistikasi</b>\n\n"
        f"📚 <b>Jami faktlar:</b> {len(uzbek_facts)}\n"
        f"📝 <b>O'rtacha uzunlik:</b> {sum(len(fact) for fact in uzbek_facts) // len(uzbek_facts) if uzbek_facts else 0} belgi\n"
        f"📏 <b>Eng uzun fakt:</b> {max(len(fact) for fact in uzbek_facts) if uzbek_facts else 0} belgi\n"
        f"📐 <b>Eng qisqa fakt:</b> {min(len(fact) for fact in uzbek_facts) if uzbek_facts else 0} belgi\n\n"
        f"💾 <b>Fayl hajmi:</b> {os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0} bayt"
    )
    
    await callback.message.answer(stats_text, parse_mode="HTML")
    await callback.answer()

async def main():
    """Botni ishga tushirish"""
    # Barcha ma'lumotlarni yuklash
    load_data()
    print(f"Bot ishga tushdi... Jami {len(uzbek_facts)} ta fakt va {len(users_data)} ta foydalanuvchi yuklandi.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())