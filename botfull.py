import telebot
from telebot import types
import random
import datetime
import threading
import time
import json
import os
import requests
from telebot.types import BotCommand
from translations_data import translations
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from deep_translator import GoogleTranslator
from news_viewer import NewsViewer
from position_calculator import PositionSizeCalculator
from capital_manager import PositionCapitalManager

TOKEN = "7728811663:AAH9K5d2Y6zkOaQqLz5oZXvI3dXQO0Kp9PI"
ADMIN_CHAT_ID = 6547883364
API_KEY = "089wRXsDWUqMEP0jXUTUysIFMCtwHkak43WmMDZS"  # ← حط مفتاحك هنا

bot = telebot.TeleBot(TOKEN)

bot.set_my_commands([
    BotCommand("start", "ابدأ"),
])

user_data = {}
temp_signal = {}
analyst_data = {}         # لتخزين حسابات المحللين
analyst_state = {}        # لتتبع خطوات التسجيل
user_states = {}
withdraw_requests = []
admin_state = {}

# استرجاع البيانات من الملف عند بداية تشغيل البوت
def load_data():
    global user_data
    if os.path.exists("user_data.json"):
        with open("user_data.json", "r") as f:
            data = json.load(f)
            # نعيد تحويل التواريخ النصية إلى datetime
            for uid, info in data.items():
                if info.get("active_package") and info["active_package"].get("start_date"):
                    info["active_package"]["start_date"] = datetime.datetime.fromisoformat(info["active_package"]["start_date"])
                    info["active_package"]["last_profit_date"] = datetime.datetime.fromisoformat(info["active_package"]["last_profit_date"])
            user_data = {int(k): v for k, v in data.items()}

# حفظ البيانات في ملف
def save_data():
    with open("user_data.json", "w") as f:
        json.dump(user_data, f, default=str)

# دوال عامة للتحميل والحفظ لأي ملف JSON
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# تحميل الباقات من ملف
def load_packages():
    if os.path.exists("packages.json"):
        with open("packages.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# حفظ الباقات إلى الملف
def save_packages():
    with open("packages.json", "w", encoding="utf-8") as f:
        json.dump(packages, f, ensure_ascii=False, indent=4)

# متغير الباقات العالمي
packages = load_packages()

def load_signals():
    global live_signals
    try:
        with open("live_signals.json", "r", encoding="utf-8") as f:
            live_signals = json.load(f)
    except FileNotFoundError:
        live_signals = []
    except Exception as e:
        print(f"❌ فشل في تحميل التوصيات: {e}")
        live_signals = []

load_signals()

def save_signals():
    with open("live_signals.json", "w", encoding="utf-8") as f:
        json.dump(live_signals, f, ensure_ascii=False, indent=2)

def save_analysts():
    with open("analysts.json", "w", encoding="utf-8") as f:
        json.dump(analyst_data, f, ensure_ascii=False, indent=4)

def load_analysts():
    global analyst_data
    try:
        with open("analysts.json", "r", encoding="utf-8") as f:
            analyst_data = json.load(f)
    except FileNotFoundError:
        analyst_data = {}

save_analysts()

def send_welcome(user_id, first_name):
    lang = user_data[user_id].get("language", "ar")

    captions = {
        "ar": f"👑 *أهلاً {first_name} في Capital Vision*\n\n💼 استثمر بذكاء، واربح بعقلية النخبة.\n\n👇 اختر من القائمة للبدء:",
        "en": f"👑 *Welcome {first_name} to Capital Vision*\n\n💼 Invest smart, earn like the elite.\n\n👇 Select to begin:",
        "ru": f"👑 *Добро пожаловать, {first_name}, в Capital Vision*\n\n💼 Инвестируйте умно – зарабатывайте как элита.\n\n👇 Выберите из меню:"
    }

    # ارسال صورة الترحيب (ضع الصورة داخل مجلد البوت بإسم welcome.jpg أو اكتب رابط مباشر)
    photo_path = "welcome.jpg"  # أو رابط مباشر إذا تحب

    bot.send_photo(user_id, open(photo_path, "rb"), caption=captions[lang], parse_mode="Markdown")

    # اظهار القائمة
    send_main_menu(user_id)

def send_main_menu(user_id):
    lang = user_data.get(user_id, {}).get("language", "ar")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(t("trading_btn", lang), t("trading_assistant_btn", lang)) 
    markup.add(t("analysis_center_btn", lang), t("analyst_mode_btn", lang))
    markup.add(t("deposit_btn", lang), t("balance_btn", lang), t("withdraw_btn", lang))
    markup.add(t("package_status_btn", lang), t("referral_btn", lang), t("invest_btn", lang))
    markup.add(t("change_currency_btn", lang), t("change_lang_btn", lang))
    markup.add(t("support_btn", lang))  

    bot.send_message(user_id, t("main_menu_text", lang), reply_markup=markup)

load_data()
save_data()

# العملات المدعومة
currencies = ["USD", "EGP", "EUR", "SAR", "RUB", "USDT"]

# تحويل العملة إلى رمز
currency_symbols = {
    "USD": "$",
    "EGP": "ج.م",
    "EUR": "€",
    "SAR": "ر.س",
    "RUB": "₽",
    "USDT": "USDT"
}

# أسعار التحويل من الدولار إلى باقي العملات
currency_rates = {
    "USD": 1,
    "EGP": 49.8,
    "EUR": 0.91,
    "SAR": 3.75,
    "RUB": 81,
    "USDT": 1
}

# حد السحب الأدنى
MIN_WITHDRAW = 50

def translate_text(text, target="ar"):
    try:
        return GoogleTranslator(source="auto", target=target).translate(text)
    except:
        return text  # لو حصل خطأ، رجّع النص الأصلي

def get_user_lang(chat_id):
    """يرجع لغة المستخدم بأمان سواء كان مفتاحه str أو int"""
    uid_str = str(chat_id)
    return (
        user_data.get(uid_str, {}) or user_data.get(chat_id, {})
    ).get("language", "ar")

def get_user_doc(user_id):
    """يرجع مرجع دكشنري المستخدم بأمان للتعديل والحفظ"""
    uid_str = str(user_id)
    if uid_str in user_data:
        return user_data[uid_str], uid_str
    if user_id in user_data:
        return user_data[user_id], user_id
    # لو مستخدم جديد
    user_data[uid_str] = {"language": "ar", "balance": 0.0, "profits": 0.0}
    return user_data[uid_str], uid_str

# 📌 دالة مساعدة لإرسال رسالة مع زر /start
def send_with_cancel(user_id, text, markup=None):
    cancel_btn = types.KeyboardButton("/start")
    if markup:
        markup.add(cancel_btn)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(cancel_btn)
    bot.send_message(user_id, text, reply_markup=markup)

def show_analyst_dashboard(user_id):
    lang = user_data.get(user_id, {}).get("language", "ar")
    data = analyst_data.get(user_id, {})
    
    name = data.get("name", "غير معروف")
    followers = len(data.get("followers", []))
    views = data.get("views", 0)
    signals = len(data.get("signals", []))

    text = t("analyst_label", lang).format(name=name, signals=signals, views=views, followers=followers)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(t("publish_analysis_btn", lang))
    markup.add(t("my_analysis_btn", lang))
    markup.add(t("back_to_main_menu", lang))

    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

# دالة لتحويل من دولار إلى العملة المختارة
def convert_currency(amount_usd, target_currency):
    rate = currency_rates.get(target_currency, 1)
    return round(amount_usd * rate, 2)

def send_single_package(user_id, index):
    user = user_data.get(user_id, {})
    lang = user.get("language", "ar")
    currency = user.get("currency", "USD")
    symbol = currency_symbols.get(currency, "$")

    package_keys = list(packages.keys())
    if index < 0 or index >= len(package_keys):
        return

    package_name = package_keys[index]
    package = packages[package_name]
    amount = convert_currency(package["amount"], currency)
    profit = convert_currency(package["profit"], currency)
    daily = round(profit / 10, 2)

    text = f"""📦 *{package_name}*

💵 *قيمة الاستثمار:* {amount} {symbol}  
💰 *الأرباح المتوقعة:* {profit} {symbol}  
📈 *متوسط ربح يومي:* ~{daily} {symbol}  
📆 *المدة:* 10 أيام
"""

    markup = types.InlineKeyboardMarkup()
    buttons = []

    if index > 0:
        buttons.append(types.InlineKeyboardButton("⏮ السابق", callback_data=f"pkg_prev_{index}"))
    buttons.append(types.InlineKeyboardButton("✅ اختيار", callback_data=f"pkg_select_{index}"))
    if index < len(package_keys) - 1:
        buttons.append(types.InlineKeyboardButton("⏭ التالي", callback_data=f"pkg_next_{index}"))

    markup.add(*buttons)

    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=markup)

def t(key, lang):
    return translations.get(key, {}).get(lang, translations.get(key, {}).get("ar", key))

news = NewsViewer(bot, user_data, t)

psc = PositionSizeCalculator(bot, user_data, t)

pcm = PositionCapitalManager(bot, user_data, t)

payment_methods = {
    "فودافون كاش": "01006975034",
    "أورنج كاش": "01222142835",
    "انستا باي": "01018353314",
    "USDT TRC20": "TQzL9FyVxySe6d41ete7mifQuPRPhCDMy9"
}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    # إنشاء بيانات المستخدم لو مش موجود
    if user_id not in user_data:
        user_data[user_id] = {
            'balance': 0,
            'active_package': None,
            'profits': 0,
            'referrals': 0,
            'ref_code': f"ref{user_id}",
            'ref_by': referrer_id,
            'ref_bonus_claimed': False,
            'currency': 'USD',
            'language': None
        }
        save_data()

    # التحقق من اللغة
    lang = user_data[user_id].get("language")
    if not lang:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
            types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
        )
        bot.send_message(user_id, "🌐 Please choose your language / الرجاء اختيار اللغة:", reply_markup=markup)
        return  # إيقاف الكود هنا لحين اختيار اللغة

    # لو اللغة موجودة بالفعل، نرسل الترحيب
    send_welcome(user_id, message.from_user.first_name)
    
@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_language(call):
    user_id = call.message.chat.id
    lang = call.data.split("_")[1]

    if user_id in user_data:
        user_data[user_id]["language"] = lang
        save_data()
        
        # إرسال رسالة الترحيب بناءً على اللغة المختارة
        send_welcome(user_id, call.from_user.first_name)

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "plans_ready")
def show_first_package(call):
    user_id = call.message.chat.id
    send_single_package(user_id, 0)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 قائمة المستخدمين", callback_data="admin_users"),
        types.InlineKeyboardButton("➕ إضافة رصيد", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("➖ خصم رصيد", callback_data="admin_deduct_balance"),
        types.InlineKeyboardButton("📤 إرسال رسالة للعميل", callback_data="admin_send_user"),
        types.InlineKeyboardButton("📢 إرسال رسالة للجميع", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("➕ إضافة باقة جديدة", callback_data="admin_add_package"),
        types.InlineKeyboardButton("❌ حذف باقة", callback_data="admin_delete_package")
    )
    markup.add(types.InlineKeyboardButton("➕ إضافة توصية", callback_data="admin_add_live_signal"),
        types.InlineKeyboardButton("🗑️ حذف توصية", callback_data="admin_delete_signal")
    )
    
    bot.send_message(ADMIN_CHAT_ID, "⚙️ لوحة تحكم الإدارة:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [
    t("invest_btn", "ar"), t("invest_btn", "en"), t("invest_btn", "ru")
])
def investment_options(message):
    user_id = message.chat.id

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📦 خطط جاهزة", callback_data="plans_ready"),
        types.InlineKeyboardButton("✍️ استثمار مبلغ مخصص", callback_data="plans_custom")
    )

    bot.send_message(user_id, "💼 اختر نوع الاستثمار:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [
    t("deposit_btn", "ar"), t("deposit_btn", "en"), t("deposit_btn", "ru")
])
def ask_fund_amount(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    user_data[user_id]["awaiting_fund_amount"] = True
    save_data()
    bot.send_message(user_id, t("fund_enter_amount", lang))  # 💵 من فضلك أدخل المبلغ الذي تريد شحنه (بالدولار):

@bot.message_handler(func=lambda msg: msg.text == t("fund_btn", user_data.get(msg.chat.id, {}).get("language", "ar")))
def start_fund_process(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")
    user_data[user_id]["awaiting_custom_amount"] = True
    save_data()
    bot.send_message(user_id, t("fund_enter_amount", lang))

@bot.callback_query_handler(func=lambda call: call.data.startswith("pkg_select_"))
def handle_package_selection(call):
    user_id = call.message.chat.id
    index = int(call.data.split("_")[2])
    package_keys = list(packages.keys())

    if 0 <= index < len(package_keys):
        selected = package_keys[index]
        user_data[user_id]["selected_package"] = selected
        save_data()

        # ✅ نعرض الآن وسائل الدفع
        markup = types.InlineKeyboardMarkup()
        for method in payment_methods:
            markup.add(types.InlineKeyboardButton(method, callback_data=f"deposit_{method}"))

        bot.send_message(user_id, f"✅ تم اختيار الباقة: *{selected}*\n💳 اختر وسيلة الدفع:", parse_mode="Markdown", reply_markup=markup)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pkg_"))
def handle_package_navigation(call):
    user_id = call.message.chat.id
    data = call.data

    if data.startswith("pkg_next_"):
        index = int(data.split("_")[2]) + 1
        send_single_package(user_id, index)

    elif data.startswith("pkg_prev_"):
        index = int(data.split("_")[2]) - 1
        send_single_package(user_id, index)

    elif data.startswith("pkg_select_"):
        index = int(data.split("_")[2])
        package_keys = list(packages.keys())
        if 0 <= index < len(package_keys):
            selected = package_keys[index]
            user_data[user_id]["selected_package"] = selected
            save_data()
            bot.send_message(user_id, f"✅ تم اختيار الباقة: *{selected}*", parse_mode="Markdown")

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "plans_custom")
def ask_custom_amount(call):
    user_id = call.message.chat.id
    user = user_data.get(user_id, {})
    lang = user.get("language", "ar")
    
    bot.send_message(user_id, "💵 من فضلك أدخل المبلغ الذي تريد استثماره (بالدولار):")
    user_data[user_id]["awaiting_custom_amount"] = True
    save_data()
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_"))
def handle_package_selection(call):
    selected_package = call.data.replace("choose_", "").strip()

    user_id = call.message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["selected_package"] = selected_package

    # نعرض وسائل الدفع
    markup = types.InlineKeyboardMarkup()
    for method in payment_methods.keys():
        markup.add(types.InlineKeyboardButton(text=method, callback_data=f"deposit_{method}"))
    
    bot.send_message(user_id, f"💼 اختر وسيلة الدفع لباقتك: *{selected_package}*", parse_mode="Markdown", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_custom_investment", "cancel_custom_investment"])
def handle_custom_investment_action(call):
    user_id = call.message.chat.id
    action = call.data
    lang = user_data.get(user_id, {}).get("language", "ar")

    if action == "confirm_custom_investment":
        invest = user_data[user_id].get("pending_investment")
        if not invest:
            bot.send_message(user_id, "❌ لم يتم العثور على بيانات الاستثمار.")
            return

        # تأكد إن الرصيد كافي
        if user_data[user_id]["balance"] < invest["amount"]:
            bot.send_message(user_id, "❌ رصيدك غير كافٍ لتفعيل هذا الاستثمار. الرجاء شحن رصيدك أولاً.")
            return

        user_data[user_id]["balance"] -= invest["amount"]
        user_data[user_id]["profits"] = 0
        user_data[user_id]["active_package"] = {
            "amount": invest["amount"],
            "start_date": datetime.datetime.now(),
            "last_profit_date": datetime.datetime.now(),
            "days_passed": 0,
            "active": True
        }
        save_data()

        bot.send_message(user_id, "✅ تم تفعيل استثمارك بنجاح! ستبدأ الأرباح بالتجمع يوميًا.")
    else:
        bot.send_message(user_id, "❌ تم إلغاء العملية.")
        user_data[user_id].pop("pending_investment", None)
        save_data()

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("deposit_"))
def show_payment_details(call):
    method = call.data.split("_", 1)[1]
    number = payment_methods.get(method, "غير متوفر")
    user_id = call.message.chat.id
    user = user_data.get(user_id)

    # ✅ تأكد من وجود بيانات المستخدم
    if not user:
        user_data[user_id] = {
            'balance': 0,
            'active_package': None,
            'profits': 0,
            'referrals': 0,
            'ref_code': f"ref{user_id}",
            'ref_by': None,
            'ref_bonus_claimed': False
        }
        user = user_data[user_id]

    selected_package = user.get("selected_package", "باقة غير معروفة")
    lang = user.get("language", "ar")

    # ✅ تفعيل انتظار إثبات الدفع
    user["awaiting_payment"] = True
    save_data()

    msg = f"""💰 ادفع باستخدام *{method}*
📞 الرقم: `{number}`

📦 الباقة المختارة: *{selected_package}*

📤 بعد الدفع ابعت صورة إثبات أو رقم العملية هنا في الشات.
"""
    bot.send_message(user_id, msg, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("custompay_"))
def handle_custom_payment(call):
    method = call.data.replace("custompay_", "")
    user_id = call.message.chat.id
    user = user_data.get(user_id)

    if not user or "custom_investment" not in user:
        bot.send_message(user_id, "❌ لا يوجد مبلغ محدد.")
        return

    amount = user["custom_investment"]["amount"]
    number = payment_methods.get(method, "غير متوفر")
    user["awaiting_payment"] = True
    user["custom_payment_method"] = method
    save_data()

    text = f"""💳 وسيلة الدفع: *{method}*
📞 الرقم: `{number}`

💰 المبلغ المطلوب دفعه: *{amount}$*

📤 بعد الدفع، أرسل إثبات التحويل أو رقم العملية هنا."""

    bot.send_message(user_id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("addfunds_"))
def handle_fund_deposit(call):
    method = call.data.split("_", 1)[1]
    number = payment_methods.get(method, "غير متوفر")
    user_id = call.message.chat.id
    user = user_data.get(user_id)

    lang = user.get("language", "ar")

    # ✅ جلب المبلغ المسجّل من المستخدم
    amount = user.get("fund_amount", 0)

    msg = f"💰 وسيلة الدفع: *{method}*\n📞 الرقم: `{number}`\n\n💵 المبلغ المطلوب دفعه: *{amount}$*\n\n📤 بعد الدفع، ابعت صورة أو رسالة نصية تحتوي على إثبات الدفع هنا."
    bot.send_message(user_id, msg, parse_mode="Markdown")

    user["awaiting_fund_payment"] = True
    save_data()

    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_live_signal")
def start_add_signal(call):
    admin_state[call.message.chat.id] = "awaiting_pair"
    temp_signal[call.message.chat.id] = {}
    bot.send_message(call.message.chat.id, "📌 أرسل اسم الزوج (مثل: XAU/USD):")

@bot.message_handler(func=lambda m: m.chat.id in admin_state and admin_state[m.chat.id].startswith("awaiting_"))
def handle_signal_steps(message):
    user_id = message.chat.id
    step = admin_state[user_id]
    text = message.text.strip()
    
    temp = temp_signal.get(user_id, {})

    if step == "awaiting_pair":
        temp["pair"] = text
        admin_state[user_id] = "awaiting_type"
        bot.send_message(user_id, "✍️ نوع الصفقة (شراء/بيع):")
    
    elif step == "awaiting_type":
        temp["type"] = text
        admin_state[user_id] = "awaiting_entry"
        bot.send_message(user_id, "💵 سعر الدخول:")
    
    elif step == "awaiting_entry":
        temp["entry"] = text
        admin_state[user_id] = "awaiting_target"
        bot.send_message(user_id, "🎯 الهدف:")
    
    elif step == "awaiting_target":
        temp["target"] = text
        admin_state[user_id] = "awaiting_stop"
        bot.send_message(user_id, "🛡️ وقف الخسارة:")
    
    elif step == "awaiting_stop":
        temp["stoploss"] = text
        admin_state[user_id] = "awaiting_status"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("⏳ قيد التنفيذ", callback_data="signal_status_active"),
            types.InlineKeyboardButton("✅ منتهية", callback_data="signal_status_closed")
        )
        bot.send_message(user_id, "⏱️ اختر الحالة:", reply_markup=markup)

    temp_signal[user_id] = temp

@bot.callback_query_handler(func=lambda call: call.data.startswith("signal_status_"))
def finish_add_signal(call):
    user_id = call.message.chat.id
    status = "قيد التنفيذ" if call.data.endswith("active") else "منتهية"

    temp = temp_signal.get(user_id)
    if not temp:
        bot.send_message(user_id, "❌ خطأ في البيانات.")
        return

    temp["status"] = status
    temp["date"] = datetime.datetime.now().strftime("%Y-%m-%d")

    # توليد ID جديد
    new_id = max([s["id"] for s in live_signals], default=0) + 1
    temp["id"] = new_id

    # إضافة للتوصيات الحية
    live_signals.append(temp)
    save_signals()

    bot.send_message(user_id, f"✅ تم حفظ التوصية #{new_id} بنجاح.")
    
    # حذف الحالة المؤقتة
    admin_state.pop(user_id, None)
    temp_signal.pop(user_id, None)

    # إرسال إشعار للمستخدمين اللي فعلوا التنبيه
    for uid, data in user_data.items():
        if data.get("alerts_enabled"):
            msg = f"""🔔 توصية جديدة متاحة الآن!

📊 {temp['pair']} - {temp['type']}
💵 دخول: {temp['entry']}
🎯 هدف: {temp['target']}
🛡️ وقف خسارة: {temp['stoploss']}

📍 الحالة: {temp['status']}
📆 التاريخ: {temp['date']}

📌 اضغط على "صفقات جارية" لمشاهدتها.
"""
            try:
                bot.send_message(uid, msg)
            except:
                continue

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_signal")
def admin_delete_signal_callback(call):
    user_id = call.message.chat.id

    if not live_signals:
        bot.send_message(user_id, "❌ لا توجد توصيات لحذفها.")
        return

    markup = types.InlineKeyboardMarkup()
    for signal in live_signals:
            btn_text = f"{signal['id']} - {signal['pair']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"delete_signal_{signal['id']}"))

    bot.send_message(user_id, "🗑️ اختر التوصية التي تريد حذفها:", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_signal_"))
def confirm_delete_signal(call):
    user_id = call.message.chat.id

    try:
        signal_id = int(call.data.split("_")[-1])
        signal_to_delete = next((s for s in live_signals if s["id"] == signal_id), None)

        if not signal_to_delete:
            bot.answer_callback_query(call.id, text="❌ لم يتم العثور على التوصية.")
            return

        live_signals.remove(signal_to_delete)
        save_signals()  # تأكد إن عندك الدالة دي شغالة

        bot.edit_message_text(
            f"✅ تم حذف التوصية رقم #{signal_id} بنجاح.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

    except Exception as e:
        print(f"❌ خطأ أثناء حذف التوصية: {e}")
        bot.answer_callback_query(call.id, text="❌ حدث خطأ أثناء الحذف.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_") or call.data.startswith("reject_"))
def handle_admin_confirmation(call):
    parts = call.data.split("_")
    action = parts[0]  # "confirm" أو "reject"
    user_id = int(parts[1])
    payment_type = parts[2] if len(parts) > 2 else "normal"

    if user_id not in user_data:
        return

    lang = user_data[user_id].get("language", "ar")

    if action == "confirm":
        if payment_type == "fund":
            amount = user_data[user_id].get("fund_amount", 0)
            user_data[user_id]["balance"] += amount
            user_data[user_id].pop("awaiting_fund_payment", None)
            user_data[user_id].pop("fund_amount", None)
            save_data()

            bot.send_message(user_id, f"✅ تم تأكيد الإيداع! تم إضافة *{amount}$* إلى رصيدك.", parse_mode="Markdown")

        elif payment_type == "custom":
            investment = user_data[user_id].get("custom_investment")
            if not investment:
                bot.send_message(user_id, "❌ لا يوجد مبلغ استثمار مخصص.")
                return

            amount = investment.get("amount", 0)
            user_data[user_id]["balance"] += amount
            user_data[user_id]["active_package"] = {
                "amount": amount,
                "start_date": datetime.datetime.now(),
                "last_profit_date": datetime.datetime.now(),
                "days_passed": 0,
                "active": True
            }
            user_data[user_id]["profits"] = 0
            investment["confirmed"] = True

            # حذف أي باقة مختارة قديمة
            user_data[user_id].pop("selected_package", None)
            save_data()

            bot.send_message(user_id, f"✅ تم تأكيد الدفع وتفعيل باقتك الاستثمارية بمبلغ *{amount}$*!\n💰 أرباحك هتبدأ تتجمع يوميًا، والسحب متاح بعد 7 أيام.", parse_mode="Markdown")

        else:  # normal
            selected_package = user_data[user_id].get("selected_package")
            if not selected_package or selected_package not in packages:
                bot.send_message(user_id, t("no_package_selected", lang))
                return

            amount = packages[selected_package]["amount"]
            user_data[user_id]["balance"] += amount
            user_data[user_id]["active_package"] = {
                "amount": amount,
                "start_date": datetime.datetime.now(),
                "last_profit_date": datetime.datetime.now(),
                "days_passed": 0,
                "active": True
            }
            user_data[user_id]["profits"] = 0
            save_data()

            referrer_id = user_data[user_id].get("ref_by")
            if referrer_id and not user_data[user_id].get("ref_bonus_claimed", False):
                user_data[referrer_id]["balance"] += 5
                user_data[user_id]["ref_bonus_claimed"] = True
                bot.send_message(referrer_id, t("referral_activated", lang))

            bot.send_message(user_id, f"✅ تم تفعيل باقتك الاستثمارية: *{selected_package}*!\n💰 أرباحك هتبدأ تتجمع يوميًا، والسحب متاح بعد 7 أيام.", parse_mode="Markdown")

    else:  # رفض العملية
        if payment_type == "fund":
            bot.send_message(user_id, "❌ تم رفض عملية الشحن.")
            user_data[user_id].pop("awaiting_fund_payment", None)
            user_data[user_id].pop("fund_amount", None)

        elif payment_type == "custom":
            bot.send_message(user_id, "❌ تم رفض الاستثمار المخصص.")
            user_data[user_id].pop("custom_investment", None)
            user_data[user_id]["awaiting_custom_amount"] = False

        else:  # normal
            bot.send_message(user_id, t("payment_rejected", lang))
            user_data[user_id].pop("awaiting_payment", None)

        save_data()

    bot.answer_callback_query(call.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.message_handler(func=lambda message: message.text in [
    t("balance_btn", "ar"), t("balance_btn", "en"), t("balance_btn", "ru")
])
def my_balance(message):
    user_id = message.chat.id
    user = user_data.get(user_id)

    if not user:
        lang = user.get("language", "ar")
        bot.send_message(user_id, t("data_not_found", lang))
        return

    curr = user.get("currency", "USD")
    symbol = currency_symbols.get(curr, "$")
    
    # الرصيد والأرباح بالدولار
    usd_balance = user.get("balance", 0)
    usd_profits = user.get("profits", 0)

    # نحولهم للعملة المختارة
    balance = convert_currency(usd_balance, curr)
    profits = convert_currency(usd_profits, curr)

    ref_code = user.get("ref_code", f"ref{user_id}")

    text = f"""👤 اسمك: {message.from_user.first_name}
💰 رصيدك الحالي: {balance} {symbol}
📦 أرباحك الحالية: {profits} {symbol}
🔗 رابط الإحالة:
https://t.me/{bot.get_me().username}?start={ref_code}"""

    bot.send_message(user_id, text)

@bot.message_handler(func=lambda message: message.text in [
    t("analysis_center_btn", "ar"),
    t("analysis_center_btn", "en"),
    t("analysis_center_btn", "ru")
])
def analysis_center_menu(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(t("latest_analyses_btn", lang), t("my_favorites_btn", lang))
    markup.add(t("my_following_btn", lang), t("analysis_explain_btn", lang))
    markup.add(t("back_to_main_menu", lang))

    bot.send_message(user_id, t("analysis_section_welcome", lang), parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == t("analyst_mode_btn", user_data.get(message.chat.id, {}).get("language", "ar")))
def enter_analyst_mode(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    analyst = analyst_data.get(user_id)
    if analyst:
        show_analyst_dashboard(user_id)
    else:
        bot.send_message(user_id, t("analyst_intro", lang), parse_mode="Markdown")
        analyst_state[user_id] = "awaiting_name"

@bot.message_handler(func=lambda message: analyst_state.get(message.chat.id) == "awaiting_name")
def handle_analyst_name(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")
    display_name = message.text.strip()

    if len(display_name) < 2:
        bot.send_message(user_id, t("analyst_name_short", lang))
        return

    analyst_data[user_id] = {
        "name": display_name,
        "followers": [],
        "views": 0,
        "signals": []
    }
    analyst_state.pop(user_id, None)

    bot.send_message(user_id, t("analyst_created", lang).format(name=display_name), parse_mode="Markdown")
    show_analyst_dashboard(user_id)

@bot.message_handler(func=lambda message: message.text == t("invest_btn", user_data.get(message.chat.id, {}).get("language", "ar")))
def invest_options(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🧮 اختيار من الخطط الجاهزة", callback_data="plans_ready"),
        types.InlineKeyboardButton("✍️ استثمار مبلغ مخصص", callback_data="plans_custom")
    )
    bot.send_message(user_id, t("choose_invest_type", lang), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [
    t("package_status_btn", "ar"), t("package_status_btn", "en"), t("package_status_btn", "ru")
])
def package_status(message):
    user_id = message.chat.id
    user = user_data.get(user_id)

    if not user or not user.get("active_package"):
        lang = user.get("language", "ar")
        bot.send_message(user_id, t("no_active_package", lang))
        return

    package = user["active_package"]
    package_name = user.get("selected_package", "غير معروف")
    start_date = package.get("start_date")
    days_passed = package.get("days_passed", 0)
    max_days = 15
    days_remaining = max(0, max_days - days_passed)
    curr = user.get("currency", "USD")
    symbol = currency_symbols.get(curr, "$")

    # تحويل القيم من USD للعملة المختارة
    current_profit_usd = user.get("profits", 0)
    profit_limit_usd = package["amount"] * 5

    current_profit = convert_currency(current_profit_usd, curr)
    profit_limit = convert_currency(profit_limit_usd, curr)

    status = "✅ نشطة" if package.get("active", False) else "⛔ منتهية"

    text = f"""📊 *تفاصيل الباقة الحالية:*

💼 *الباقة:* {package_name}
📆 *بدأت في:* {start_date.strftime("%Y-%m-%d")}
⏳ *مرّ عليها:* {days_passed} يوم  
⏱ *متبقي:* {days_remaining} يوم  
💵 *الأرباح الحالية:* {current_profit} {symbol}
🎯 *الحد الأقصى للأرباح:* {profit_limit} {symbol}
📍 *الحالة:* {status}
"""
    bot.send_message(user_id, text, parse_mode="Markdown")

from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import time

# =====  بدء السحب  =====
@bot.message_handler(func=lambda m: m.text in [
    t("withdraw_btn", "ar"), t("withdraw_btn", "en"), t("withdraw_btn", "ru")
])
def withdraw(message):
    user_id = message.chat.id
    lang = get_user_lang(user_id)

    # أزرار المصدر
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_bal = "💰 " + t("withdraw_from_balance_btn", lang)
    btn_pro = "📦 " + t("withdraw_from_packages_btn", lang)
    btn_cancel = t("back_to_main_menu", lang)
    kb.add(btn_bal, btn_pro)
    kb.add(btn_cancel)

    bot.send_message(user_id, t("choose_withdraw_source", lang), reply_markup=kb)
    user_states[str(user_id)] = {"action": "choose_source", "btn_bal": btn_bal, "btn_pro": btn_pro, "btn_cancel": btn_cancel}


# =====  اختيار المصدر  =====
@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id), {}).get("action") == "choose_source")
def process_withdraw_source(message):
    user_id = message.chat.id
    sid = str(user_id)
    lang = get_user_lang(user_id)
    state = user_states.get(sid, {})
    text = (message.text or "").strip()

    if text == state.get("btn_cancel", t("cancel", lang)):
        try:
            bot.send_message(user_id, t("withdraw_cancelled", lang), reply_markup=main_menu(lang))
        except:
            bot.send_message(user_id, t("withdraw_cancelled", lang))
        user_states.pop(sid, None)
        return

    # تحديد المصدر
    if text == state.get("btn_bal"):
        source_key = "balance"
    elif text == state.get("btn_pro"):
        source_key = "profits"
    else:
        bot.send_message(user_id, t("invalid_option", lang))
        return

    user_doc, key = get_user_doc(user_id)
    available = float(user_doc.get(source_key, 0.0))

    if available < MIN_WITHDRAW:
        bot.send_message(user_id, t("withdraw_minimum", lang).format(MIN_WITHDRAW))
        user_states.pop(sid, None)
        return

    user_states[sid] = {"action": "enter_amount", "source": source_key, "available": available}
    bot.send_message(
        user_id,
        t("enter_withdraw_amount", lang).format(available=available)
    )


# =====  إدخال المبلغ  =====
@bot.message_handler(func=lambda m: user_states.get(str(m.chat.id), {}).get("action") == "enter_amount")
def process_withdraw_amount(message):
    user_id = message.chat.id
    sid = str(user_id)
    lang = get_user_lang(user_id)
    state = user_states.get(sid, {})

    # تحقق من المبلغ
    try:
        amount = float((message.text or "").strip())
    except ValueError:
        bot.send_message(user_id, t("invalid_amount", lang))
        return

    if amount < MIN_WITHDRAW:
        bot.send_message(user_id, t("withdraw_minimum", lang).format(MIN_WITHDRAW))
        return

    available = float(state.get("available", 0.0))
    if amount > available:
        bot.send_message(user_id, t("amount_out_of_range", lang).format(min=MIN_WITHDRAW, max=available))
        return

    # إنشاء طلب بدون خصم الآن (الخصم يتم عند الموافقة فقط)
    requests = load_json("withdraw_requests.json")
    if not isinstance(requests, dict):
        requests = {}
    req_id = f"{sid}_{int(time.time())}"

    requests[req_id] = {
        "user_id": sid,
        "amount": amount,
        "source": state.get("source", "balance"),
        "status": "pending",
        "created_at": int(time.time())
    }
    save_json("withdraw_requests.json", requests)

    # إشعار المستخدم
    try:
        bot.send_message(user_id, t("withdraw_under_review", lang), reply_markup=main_menu(lang))
    except:
        bot.send_message(user_id, t("withdraw_under_review", lang))

    # إشعار للإدمن مع أزرار قبول/رفض
    mk = InlineKeyboardMarkup()
    mk.add(
        InlineKeyboardButton("✅ قبول", callback_data=f"wd:approve:{req_id}"),
        InlineKeyboardButton("❌ رفض", callback_data=f"wd:decline:{req_id}")
    )
    # لو ADMIN_CHAT_ID قناة/جروب تأكد إن البوت Admin هناك وأنه يعرف يرسل
    bot.send_message(
        ADMIN_CHAT_ID,
        f"💸 طلب سحب جديد\n"
        f"👤 ID: {sid}\n"
        f"💵 Amount: {amount}$\n"
        f"📂 Source: {state.get('source')}",
        reply_markup=mk
    )

    # تنظيف الحالة
    user_states.pop(sid, None)


# =====  موافقة/رفض الإدارة  =====
@bot.callback_query_handler(func=lambda c: c.data.startswith("wd:"))
def handle_withdraw_admin(call):
    try:
        _, action, req_id = call.data.split(":", 2)
    except Exception:
        bot.answer_callback_query(call.id, "Bad data")
        return

    requests = load_json("withdraw_requests.json")
    if not isinstance(requests, dict):
        requests = {}

    if req_id not in requests:
        bot.answer_callback_query(call.id, "❌ الطلب غير موجود")
        return

    req = requests[req_id]
    user_id = req["user_id"]
    amount = float(req["amount"])
    source = req["source"]
    lang = get_user_lang(user_id)

    if action == "approve":
        # خصم فعلي الآن
        user_doc, key = get_user_doc(user_id)
        current_val = float(user_doc.get(source, 0.0))
        # ضمان عدم السالب
        if amount > current_val:
            # لو رصيده اتغير من وقت الطلب
            bot.answer_callback_query(call.id, "⚠️ رصيد المستخدم لا يكفي الآن")
            return

        user_doc[source] = round(current_val - amount, 2)
        save_json("user_data.json", user_data)

        req["status"] = "approved"
        save_json("withdraw_requests.json", requests)

        bot.send_message(user_id, t("withdraw_approved", lang).format(amount=amount))
        try:
            bot.edit_message_text(
                f"✅Approved: {req_id}\nUser: {user_id}\nAmount: {amount}$\nSource: {source}",
                chat_id=call.message.chat.id, message_id=call.message.message_id
            )
        except:
            pass
        bot.answer_callback_query(call.id, "✅ Done")

    elif action == "decline":
        req["status"] = "declined"
        save_json("withdraw_requests.json", requests)

        # رسالة للمستخدم مع زر تواصل
        contact_btn = InlineKeyboardMarkup()
        contact_btn.add(InlineKeyboardButton(t("contact_admin_btn", lang), url="https://t.me/ahmed_afifi_trader"))

        bot.send_message(
            user_id,
            t("withdraw_declined", lang).format(amount=amount, source=source),
            reply_markup=contact_btn
        )
        try:
            bot.edit_message_text(
                f"❌Declined: {req_id}\nUser: {user_id}\nAmount: {amount}$\nSource: {source}",
                chat_id=call.message.chat.id, message_id=call.message.message_id
            )
        except:
            pass
        bot.answer_callback_query(call.id, "❌ Declined")

@bot.message_handler(func=lambda message: message.text == t("deposit_btn", user_data.get(message.chat.id, {}).get("language", "ar")))
def ask_fund_amount(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    user_data[user_id]["awaiting_fund_amount"] = True
    save_data()
    bot.send_message(user_id, "💰 من فضلك اكتب المبلغ اللي حابب تشحنه (بالدولار):")

@bot.message_handler(func=lambda message: message.text in [
    t("referral_btn", "ar"), t("referral_btn", "en"), t("referral_btn", "ru")
])
def referral(message):
    user_id = message.chat.id
    user = user_data.get(user_id)
    lang = user.get("language", "ar")
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(user_id, t("send_referral_link", lang).format(link=link))

@bot.message_handler(func=lambda message: message.text in [
    t("trading_assistant_btn", "ar"), t("trading_assistant_btn", "en"), t("trading_assistant_btn", "ru")
])
def open_trading_assistant(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # الصف الأول
    markup.add("📐 " + t("tool_position_size", lang), "📏 " + t("tool_risk_reward", lang))
    # الصف الثالث
    markup.add("📅 " + t("tool_days_to_target", lang))
    # الصف الرابع
    markup.add("🛡️ " + t("tool_capital_management", lang))
    # الصف الخامس
    markup.add("🕒 " + t("tool_market_hours", lang), "🌐 " + t("tool_market_news", lang))
    # زر الرجوع
    markup.add(t("back_to_main_menu", lang))

    bot.send_message(user_id, t("choose_trading_tool", lang), reply_markup=markup)

@bot.message_handler(func=lambda m: m.text and "🕒" in m.text)
def market_hours(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    if lang == "ar":
        hours_text = (
            "⏰ *أوقات عمل الأسواق:*\n\n"
            "🇺🇸 السوق الأمريكي (NYSE & NASDAQ):\n"
            "🕒 يفتح: 4:30 م بتوقيت مصر\n"
            "🕘 يغلق: 11:00 م بتوقيت مصر\n\n"
            "🇪🇬 البورصة المصرية (EGX):\n"
            "🕒 يفتح: 10:00 ص\n"
            "🕘 يغلق: 2:30 م\n\n"
            "🌍 أسواق الفوركس (24 ساعة):\n"
            "🔹 سيدني: 12:00 ص - 9:00 ص\n"
            "🔹 طوكيو: 2:00 ص - 11:00 ص\n"
            "🔹 لندن: 10:00 ص - 7:00 م\n"
            "🔹 نيويورك: 3:00 م - 12:00 ص\n\n"
            "⚡️ مواعيد قد تتغير في العطلات الرسمية."
        )
    elif lang == "en":
        hours_text = (
            "⏰ *Market Hours:*\n\n"
            "🇺🇸 US Market (NYSE & NASDAQ):\n"
            "🕒 Opens: 4:30 PM Cairo Time\n"
            "🕘 Closes: 11:00 PM Cairo Time\n\n"
            "🇪🇬 Egyptian Exchange (EGX):\n"
            "🕒 Opens: 10:00 AM\n"
            "🕘 Closes: 2:30 PM\n\n"
            "🌍 Forex Markets (24 Hours):\n"
            "🔹 Sydney: 12:00 AM - 9:00 AM\n"
            "🔹 Tokyo: 2:00 AM - 11:00 AM\n"
            "🔹 London: 10:00 AM - 7:00 PM\n"
            "🔹 New York: 3:00 PM - 12:00 AM\n\n"
            "⚡️ Hours may vary on official holidays."
        )
    elif lang == "ru":
        hours_text = (
            "⏰ *Время работы рынков:*\n\n"
            "🇺🇸 Американский рынок (NYSE & NASDAQ):\n"
            "🕒 Открывается: 16:30 по Каирскому времени\n"
            "🕘 Закрывается: 23:00 по Каирскому времени\n\n"
            "🇪🇬 Египетская биржа (EGX):\n"
            "🕒 Открывается: 10:00\n"
            "🕘 Закрывается: 14:30\n\n"
            "🌍 Валютный рынок (24 часа):\n"
            "🔹 Сидней: 00:00 - 09:00\n"
            "🔹 Токио: 02:00 - 11:00\n"
            "🔹 Лондон: 10:00 - 19:00\n"
            "🔹 Нью-Йорк: 15:00 - 00:00\n\n"
            "⚡️ В праздничные дни время работы может меняться."
        )
    else:
        hours_text = "⚠️ Language not supported yet."

    bot.send_message(user_id, hours_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and "🌐" in m.text)
def open_news(message):
    news.open_menu(message)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("news_", "next", "prev", "tr_", "back_trading_menu")))
def news_callbacks(call):
    data = call.data
    if data.startswith("news_"):
        code = data.split("_")[1]
        news.handle_region(call, code)
    elif data == "back_trading_menu":
        open_trading_assistant(call.message)
        bot.answer_callback_query(call.id)
    else:
        news.handle_callback(call)

@bot.message_handler(func=lambda m: m.text and "📐" in m.text)
def open_tool_ps(message):
    psc.open_market_menu(message)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("ps_",)))
def handle_ps_callbacks(call):
    data = call.data

    # اختيار السوق
    if data.startswith("ps_m_"):
        market = data.replace("ps_m_", "")
        psc.open_form(call, market)

    # اختيار الحقول
    elif data == "ps_f_balance":
        psc.ask_for_input(call, "balance")
    elif data == "ps_f_risk":
        psc.ask_for_input(call, "risk")
    elif data == "ps_f_entry":
        psc.ask_for_input(call, "entry")
    elif data == "ps_f_sl":
        psc.ask_for_input(call, "sl")

    # الحساب
    elif data == "ps_calc":
        psc.calculate(call)

    # المثال
    elif data == "ps_example":
        psc.send_example(call)

@bot.message_handler(func=lambda m: m.text and "🛡️" in m.text)
def open_capital_mng(message):
    pcm.open_menu(message)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("cm_",)))
def handle_cm_callbacks(call):
    data = call.data

    if data == "cm_conservative":
        pcm.choose_plan(call, "conservative")
    elif data == "cm_balanced":
        pcm.choose_plan(call, "balanced")
    elif data == "cm_aggressive":
        pcm.choose_plan(call, "aggressive")
    elif data == "cm_info":
        pcm.send_info(call)

@bot.message_handler(func=lambda message: message.text in [
    t("support_btn", "ar"), t("support_btn", "en"), t("support_btn", "ru")
])
def support(message):
    user = user_data.get(message.chat.id)
    lang = user.get("language", "ar") if user else "ar"
    bot.send_message(message.chat.id, t("support_text", lang))


# ✅ نظام الأرباح اليومية العشوائية
def daily_profit_loop():
    while True:
        updated = False

        for user_id, data in user_data.items():
            package = data.get("active_package")
            if package and package["active"]:
                amount = package["amount"]
                total_profit_limit = amount * 5  # 500%
                current_profit = data.get("profits", 0)

                if current_profit < total_profit_limit:
                    daily_percent = random.uniform(0.04, 0.10)
                    daily_profit = int(amount * daily_percent)
                    new_profit = min(current_profit + daily_profit, total_profit_limit)
                    data["profits"] = new_profit
                    updated = True

        if updated:        
            save_data()

        time.sleep(86400)  # كل 60 ثانية مؤقتاً (خليها 86400 للـ 24 ساعة)

# تشغيل النظام في الخلفية
threading.Thread(target=daily_profit_loop, daemon=True).start()

@bot.message_handler(func=lambda message: message.text in [
    t("change_currency_btn", "ar"), t("change_currency_btn", "en"), t("change_currency_btn", "ru")
])
def change_currency(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(curr, callback_data=f"set_curr_{curr}") for curr in currencies]
    markup.add(*buttons)
    user = user_data.get(message.chat.id)
    lang = user.get("language", "ar") if user else "ar"
    bot.send_message(message.chat.id, t("choose_currency", lang), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [
    t("change_lang_btn", "ar"), t("change_lang_btn", "en"), t("change_lang_btn", "ru")
])
def show_language_options(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
    )
    user = user_data.get(message.chat.id)
    lang = user.get("language", "ar") if user else "ar"
    bot.send_message(message.chat.id, t("choose_language", lang), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [
    "📊 قسم التداول", "📊 Trading Section", "📊 Раздел трейдинга"
])
def trading_section(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        t("trading_active_signals_btn", lang),
    )
    markup.add(
        t("trading_stats_btn", lang),
        t("trading_channel_btn", lang)
    )
    markup.add(
        t("trading_contact_btn", lang),
        t("trading_help_btn", lang)  # ← زر الشرح الجديد
    )
    markup.add(t("back_to_main_menu", lang))

    bot.send_message(user_id, t("trading_section_welcome", lang), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["🔙 رجوع للقائمة الرئيسية", "🔙 Back to Main Menu", "🔙 Назад в главное меню"])
def back_to_main_menu(message):
    user_id = message.chat.id
    send_main_menu(user_id)

@bot.message_handler(func=lambda message: message.text in [
    "🟢 صفقات جارية", "🟢 Active Trades", "🟢 Активные сделки"
])
def show_live_signals(message):
    user_id = message.chat.id
    lang = user_data.get(user_id, {}).get("language", "ar")

    if not live_signals:
        bot.send_message(user_id, t("no_active_signals", lang))
        return

    markup = types.InlineKeyboardMarkup()
    for signal in live_signals:
        label = f"{signal['pair']} ({signal['type']})"
        markup.add(types.InlineKeyboardButton(label, callback_data=f"signal_{signal['id']}"))

    bot.send_message(user_id, t("choose_live_signal", lang), reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in [
    "📢 قناة التوصيات", "📢 Signals Channel", "📢 Канал сигналов"
])
def trading_channel(message):
    bot.send_message(message.chat.id, "تابعنا على قناة التوصيات: https://t.me/Capital_Vision_PRO_Forex")

@bot.message_handler(func=lambda message: message.text in [
    "📨 مراسلة المنسق", "📨 Contact Support", "📨 Связаться с поддержкой"
])
def trading_contact(message):
    bot.send_message(message.chat.id, "للتواصل معنا مباشرة: https://t.me/Ahmed_afifi_trader")

@bot.callback_query_handler(func=lambda call: call.data.startswith("signal_"))
def show_signal_detail(call):
    user_id = call.message.chat.id
    signal_id = int(call.data.split("_")[1])
    lang = user_data.get(user_id, {}).get("language", "ar")

    signal = next((s for s in live_signals if s["id"] == signal_id), None)
    if not signal:
        bot.send_message(user_id, t("signal_not_found", lang))
        return

    text = f"""📊 *توصية مباشرة (ID: #{signal['id']})*

🔹 *الزوج:* {signal['pair']}
🔹 *النوع:* {signal['type']}
🔹 *الدخول:* {signal['entry']}
🎯 *الهدف:* {signal['target']}
🛡️ *وقف الخسارة:* {signal['stoploss']}

📅 *التاريخ:* {signal['date']}
⏱️ *الحالة:* {signal['status']}"""

    bot.send_message(user_id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_curr_"))
def set_currency(call):
    user_id = call.message.chat.id
    selected_currency = call.data.split("_")[2]

    if user_id in user_data:
        user_data[user_id]["currency"] = selected_currency
        save_data()
        symbol = currency_symbols.get(selected_currency, selected_currency)
        bot.send_message(user_id, f"✅ تم تعيين عملتك المفضلة: {selected_currency} ({symbol})")
    else:
        bot.send_message(user_id, "❌ لم يتم العثور على بياناتك.")

    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_CHAT_ID and ADMIN_CHAT_ID in admin_state)
def handle_admin_inputs(message):
    state = admin_state.get(ADMIN_CHAT_ID)
    text = message.text.strip()

    if state == "awaiting_add_balance":
        try:
            uid, amount = text.split()
            uid = int(uid)
            amount = float(amount)
            user_data[uid]["balance"] += amount
            bot.send_message(ADMIN_CHAT_ID, f"✅ تم إضافة {amount}$ إلى حساب {uid}.")
            bot.send_message(uid, f"💰 تم إضافة {amount}$ إلى رصيدك من قبل الإدارة.")
            save_data()
        except:
            bot.send_message(ADMIN_CHAT_ID, "❌ تنسيق غير صحيح.")

    elif state == "awaiting_deduct_balance":
        try:
            uid, amount = text.split()
            uid = int(uid)
            amount = float(amount)
            user_data[uid]["balance"] -= amount
            bot.send_message(ADMIN_CHAT_ID, f"✅ تم خصم {amount}$ من حساب {uid}.")
            bot.send_message(uid, f"💰 تم خصم {amount}$ من رصيدك من قبل الإدارة.")
            save_data()
        except:
            bot.send_message(ADMIN_CHAT_ID, "❌ تنسيق غير صحيح.")

    elif state == "awaiting_send_user":
        try:
            uid, msg = text.split(" ", 1)
            uid = int(uid)
            bot.send_message(uid, f"📬 رسالة من الإدارة:\n{msg}")
            bot.send_message(ADMIN_CHAT_ID, "✅ تم إرسال الرسالة.")
            save_data()
        except:
            bot.send_message(ADMIN_CHAT_ID, "❌ تنسيق غير صحيح.")

    elif state == "awaiting_broadcast":
        count = 0
        for uid in user_data.keys():
            try:
                bot.send_message(uid, f"📢 إعلان إداري:\n{text}")
                count += 1
            except:
                continue
        bot.send_message(ADMIN_CHAT_ID, f"✅ تم إرسال الرسالة إلى {count} مستخدم.")

    elif state == "awaiting_add_package":
        try:
            name, amount, profit = text.split()
            amount = int(amount)
            profit = int(profit)
            packages[name] = {"amount": amount, "profit": profit}
            save_packages()
            bot.send_message(ADMIN_CHAT_ID, f"✅ تم إضافة الباقة: {name}")
            save_data()
        except:
            bot.send_message(ADMIN_CHAT_ID, "❌ تنسيق غير صحيح.")

    elif state == "awaiting_delete_package":
        if text in packages:
            del packages[text]
            save_packages()
            bot.send_message(ADMIN_CHAT_ID, f"✅ تم حذف الباقة: {text}")
        else:
            bot.send_message(ADMIN_CHAT_ID, "❌ لم يتم العثور على باقة بهذا الاسم.")

    admin_state.pop(ADMIN_CHAT_ID, None)

@bot.message_handler(content_types=['photo'])
def handle_payment_photo(message):
    user_id = message.chat.id
    user = user_data.get(user_id)

    if not user:
        return

    lang = user.get("language", "ar")

    # 🟢 إثبات دفع لباقات جاهزة أو استثمار
    if user.get("awaiting_payment", False):
        user["awaiting_payment"] = False
        save_data()

        bot.send_message(user_id, t("payment_received_text", lang))

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تأكيد الدفع", callback_data=f"confirm_{user_id}_normal"),
            types.InlineKeyboardButton("❌ رفض الدفع", callback_data=f"reject_{user_id}_normal")
        )

        bot.send_message(ADMIN_CHAT_ID, t("payment_from_user", lang).format(user_id=user_id), parse_mode="Markdown", reply_markup=markup)
        bot.forward_message(ADMIN_CHAT_ID, user_id, message.message_id)
        return

    # 🟢 إثبات دفع لشحن رصيد (إيداع مخصص)
    if user.get("awaiting_fund_payment", False):
        user["awaiting_fund_payment"] = False
        amount = user.get("fund_amount", 0)
        save_data()

        bot.send_message(user_id, t("payment_received_text", lang))

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تأكيد الإيداع", callback_data=f"confirm_{user_id}_fund"),
            types.InlineKeyboardButton("❌ رفض الإيداع", callback_data=f"reject_{user_id}_fund")
        )

        bot.send_message(ADMIN_CHAT_ID, f"📥 إثبات دفع (صورة) لشحن رصيد من ID: `{user_id}` بمبلغ: {amount}$", parse_mode="Markdown", reply_markup=markup)
        bot.forward_message(ADMIN_CHAT_ID, user_id, message.message_id)

@bot.message_handler(content_types=['text'])
def handle_payment_text(message):
    user_id = message.chat.id
    text = message.text.strip()
    user = user_data.get(user_id)

    if not user:
        return

    lang = user.get("language", "ar")

    # تجاهل أزرار القائمة الرئيسية
    if text in [
        t("packages_btn", lang), t("deposit_btn", lang), t("withdraw_btn", lang),
        t("balance_btn", lang), t("package_status_btn", lang), t("referral_btn", lang),
        t("support_btn", lang), t("trial_btn", lang), t("change_currency_btn", lang),
        t("change_lang_btn", lang)
    ]:
        return

    # ✅ إدخال مبلغ شحن الرصيد
    if user.get("awaiting_fund_amount", False):
        try:
            amount = float(text)
            if amount < 10:
                bot.send_message(user_id, "❌ الحد الأدنى للشحن هو 10$.")
                return

            user["awaiting_fund_amount"] = False
            user["fund_amount"] = amount
            save_data()

            markup = types.InlineKeyboardMarkup()
            for method in payment_methods:
                markup.add(types.InlineKeyboardButton(method, callback_data=f"addfunds_{method}"))

            bot.send_message(user_id, f"✅ تم تسجيل المبلغ: *{amount}$*\n💳 اختر وسيلة الدفع:", parse_mode="Markdown", reply_markup=markup)
        except ValueError:
            bot.send_message(user_id, "❌ من فضلك أدخل رقم صحيح.")
        return

    # ✅ إثبات دفع لباقات جاهزة
    if user.get("awaiting_payment", False):
        user["awaiting_payment"] = False
        save_data()

        bot.send_message(user_id, t("payment_received_text", lang))

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تأكيد الدفع", callback_data=f"confirm_{user_id}_normal"),
            types.InlineKeyboardButton("❌ رفض الدفع", callback_data=f"reject_{user_id}_normal")
        )

        bot.send_message(ADMIN_CHAT_ID, t("payment_from_user", lang).format(user_id=user_id), parse_mode="Markdown", reply_markup=markup)
        bot.send_message(ADMIN_CHAT_ID, f"💬 رسالة العميل: {text}")
        return

    # ✅ إثبات دفع لشحن رصيد
    if user.get("awaiting_fund_payment", False):
        user["awaiting_fund_payment"] = False
        amount = user.get("fund_amount", 0)
        save_data()

        bot.send_message(user_id, t("payment_received_text", lang))

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تأكيد الإيداع", callback_data=f"confirm_{user_id}_fund"),
            types.InlineKeyboardButton("❌ رفض الإيداع", callback_data=f"reject_{user_id}_fund")
        )

        bot.send_message(ADMIN_CHAT_ID, f"📥 إثبات دفع (نصي) لشحن رصيد من ID: `{user_id}` بمبلغ: {amount}$", parse_mode="Markdown", reply_markup=markup)
        bot.send_message(ADMIN_CHAT_ID, f"💬 رسالة العميل: {text}")
        return

    # ✅ إدخال مبلغ استثمار مخصص
    if user.get("awaiting_custom_amount", False):
        try:
            amount = float(text)
            if amount < 50:
                bot.send_message(user_id, "❌ الحد الأدنى للاستثمار هو 50$.")
                return

            user["custom_investment"] = {
                "amount": amount,
                "confirmed": False
            }
            user["awaiting_custom_amount"] = False
            save_data()

            markup = types.InlineKeyboardMarkup()
            for method in payment_methods:
                markup.add(types.InlineKeyboardButton(method, callback_data=f"custompay_{method}"))

            bot.send_message(user_id, f"✅ تم تسجيل المبلغ: *{amount}$*\n💳 اختر وسيلة الدفع:", parse_mode="Markdown", reply_markup=markup)
        except ValueError:
            bot.send_message(user_id, "❌ من فضلك أدخل رقم صحيح.")
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    action = call.data
    user_id = call.message.chat.id

    lang = user_data.get(user_id, {}).get("language", "ar")

    if action == "admin_users":
        text = t("admin_users_list", lang) + "\n"
        for uid, data in user_data.items():
            text += f"\nID: {uid} | {t('balance_btn', lang)}: {data['balance']}$ | {t('package_status_btn', lang)}: {data.get('profits', 0)}$"
        bot.send_message(user_id, text)

    elif action == "admin_add_balance":
        admin_state[user_id] = "awaiting_add_balance"
        time.sleep(0.5)
        bot.send_message(user_id, "📥 أرسل ID المستخدم وقيمة الرصيد المطلوب إضافته، مثال: 123456789 10")

    elif action == "admin_deduct_balance":
        admin_state[user_id] = "awaiting_deduct_balance"
        time.sleep(0.5)
        bot.send_message(user_id, "📤 أرسل ID المستخدم وقيمة الرصيد المطلوب خصمها، مثال: 123456789 5")

    elif action == "admin_send_user":
        admin_state[user_id] = "awaiting_send_user"
        time.sleep(0.5)
        bot.send_message(user_id, "✉️ أرسل ID المستخدم ثم الرسالة، مثال:\n123456789 مرحبًا بك!")

    elif action == "admin_broadcast":
        admin_state[user_id] = "awaiting_broadcast"
        time.sleep(0.5)
        bot.send_message(user_id, "📢 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين:")

    elif action == "admin_add_package":
        admin_state[user_id] = "awaiting_add_package"
        time.sleep(0.5)
        bot.send_message(user_id, "📦 أرسل اسم الباقة والمبلغ والأرباح، مثال:\nباقة 1500$ 1500 7500")

    elif action == "admin_delete_package":
        admin_state[user_id] = "awaiting_delete_package"
        time.sleep(0.5)
        bot.send_message(user_id, "❌ أرسل اسم الباقة التي تريد حذفها بالضبط:")

    else:
        bot.send_message(user_id, t("admin_invalid_format", lang))

    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.text not in [
    *[t(key, lang) for key in [
        "packages_btn", "deposit_btn", "withdraw_btn", "balance_btn", 
        "package_status_btn", "referral_btn", "support_btn", 
        "trial_btn", "change_currency_btn", "change_lang_btn"
    ] for lang in ["ar", "en", "ru"]]
])
def debug_all_messages(message):
    user = user_data.get(message.chat.id)
    lang = user.get("language", "ar") if user else "ar"
    bot.send_message(message.chat.id, t("unknown_message", lang))

bot.polling(none_stop=True)
