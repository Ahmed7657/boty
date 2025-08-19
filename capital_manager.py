# capital_manager.py

from telebot import types

class PositionCapitalManager:
    def __init__(self, bot, user_data, t):
        self.bot = bot
        self.user_data = user_data
        self.t = t
        self.states = {}

    #-------------------------------------------------
    def open_menu(self, message):
        """مقدمة الأداة واختيار الخطة"""
        uid = message.chat.id
        lang = self.user_data.get(uid, {}).get("language", "ar")

        text = self.t("capital_intro", lang)

        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🟢 المحافظة", callback_data="cm_conservative"),
            types.InlineKeyboardButton("⚪ المتوازنة", callback_data="cm_balanced"),
            types.InlineKeyboardButton("🔴 الهجومية", callback_data="cm_aggressive"),
        )
        kb.add(types.InlineKeyboardButton("📘 شرح الخطط", callback_data="cm_info"))
        kb.add(types.InlineKeyboardButton("🔙", callback_data="back_trading_menu"))

        self.bot.send_message(uid, text, reply_markup=kb)

    #-------------------------------------------------
    def choose_plan(self, call, plan):
        """بعد اختيار خطة ➝ طلب رأس المال"""
        uid = call.message.chat.id
        lang = self.user_data.get(uid, {}).get("language", "ar")
        self.states[uid] = plan
        self.bot.answer_callback_query(call.id)
        self.bot.send_message(uid, "💰 اكتب رأس مال حسابك:")
        self.bot.register_next_step_handler(call.message, lambda m: self.process_capital(m, plan))

    #-------------------------------------------------
    def process_capital(self, message, plan):
        """الحساب بناءً على رأس المال والخطة المختارة"""
        uid = message.chat.id
        lang = self.user_data.get(uid, {}).get("language", "ar")
        try:
            capital = float(message.text.strip())
        except:
            self.bot.send_message(uid, "❗ يرجى إدخال رقم صحيح.")
            return

        if plan == "conservative":
            risk = "0.5% - 1%"
            use = "30% - 40%"
            trades = "1 - 2"
        elif plan == "balanced":
            risk = "1% - 2%"
            use = "حتى 60%"
            trades = "2 - 4"
        else:
            risk = "3% - 5%"
            use = "حتى 80%"
            trades = "حتى 5"

        msg = (
            f"✅ *الخطة المختارة:* {plan}\n\n"
            f"📊 المخاطرة لكل صفقة: {risk}\n"
            f"💼 استخدام من رأس المال: {use}\n"
            f"🔄 عدد الصفقات المفتوحة: {trades}"
        )

        self.bot.send_message(uid, msg, parse_mode="Markdown")

    #-------------------------------------------------
    def send_info(self, call):
        """زر شرح الخطط"""
        uid = call.message.chat.id
        text = (
            "🟢 *المحافظة*: أقل مخاطرة وأمان كبير.\n"
            "⚪ *المتوازنة*: توازن بين الأمان والنمو.\n"
            "🔴 *الهجومية*: عائد سريع لكن بخطر أكبر."
        )
        self.bot.answer_callback_query(call.id)
        self.bot.send_message(uid, text, parse_mode="Markdown")