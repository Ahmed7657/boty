# position_calculator.py

from telebot import types

class PositionSizeCalculator:
    def __init__(self, bot, user_data, t):
        self.bot = bot
        self.user_data = user_data
        self.t = t
        # بيانات المستخدمين وحفظ حالة كل خطوة
        self.states = {}     # user_id: {"market": "", ...}
        self.last_inputs = {}  # user_id: {"balance": X, "risk":Y}

    # ----------------------------------------------------
    def open_market_menu(self, message):
        """فتح قائمة الأسواق"""
        user_id = message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")

        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(types.InlineKeyboardButton("📈 Forex", callback_data="ps_m_fx"),
              types.InlineKeyboardButton("📊 Stocks", callback_data="ps_m_stocks"),
              types.InlineKeyboardButton("💰 Crypto", callback_data="ps_m_crypto"),
              types.InlineKeyboardButton("⚒️ Commodities", callback_data="ps_m_commodities"),
              types.InlineKeyboardButton("🟨 Gold", callback_data="ps_m_gold"),
              types.InlineKeyboardButton("🛢 Oil", callback_data="ps_m_oil"),
              types.InlineKeyboardButton("📉 Indices", callback_data="ps_m_indices"))
        m.add(types.InlineKeyboardButton("🔙", callback_data="back_trading_menu"))

        self.bot.send_message(user_id, self.t("tool_position_size", lang), reply_markup=m)

    # ----------------------------------------------------
    def open_form(self, call, market):
        """فتح النموذج بعد اختيار السوق"""
        uid = call.message.chat.id
        self.states[uid] = {"market": market, "balance": None, "risk": None, "entry": None, "sl": None}
        lang = self.user_data.get(uid, {}).get("language", "ar")
        self.edit_form(call.message, lang)

    # ----------------------------------------------------
    def edit_form(self, msg, lang):
        """تعديل الرسالة لتظهر القيم التي أدخلها المستخدم"""
        uid = msg.chat.id
        st = self.states.get(uid, {})
        bal = st.get("balance", "—")
        risk = st.get("risk", "—")
        entry = st.get("entry", "—")
        sl = st.get("sl", "—")

        text = (
            f"💰 {self.t('account_balance', lang)}: {bal}\n"
            f"⚠️ {self.t('risk_percent', lang)} (%): {risk}\n"
            f"📍 {self.t('entry_price', lang)}: {entry}\n"
            f"🛡️ {self.t('sl_price', lang)}: {sl}"
        )

        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton(self.t("account_balance", lang), callback_data="ps_f_balance"))
        kb.add(types.InlineKeyboardButton(self.t("risk_percent", lang), callback_data="ps_f_risk"))
        kb.add(types.InlineKeyboardButton(self.t("entry_price", lang), callback_data="ps_f_entry"))
        kb.add(types.InlineKeyboardButton(self.t("sl_price", lang), callback_data="ps_f_sl"))
        kb.add(types.InlineKeyboardButton("✅ " + self.t("calculate_btn", lang), callback_data="ps_calc"))
        kb.add(types.InlineKeyboardButton("📌 مثال", callback_data="ps_example"))
        kb.add(types.InlineKeyboardButton("🔙", callback_data="back_trading_menu"))

        self.bot.edit_message_text(text, uid, msg.message_id, reply_markup=kb)

    # ----------------------------------------------------
    def ask_for_input(self, call, field):
        """يطلب من المستخدم أن يكتب القيمة"""
        uid = call.message.chat.id
        lang = self.user_data.get(uid, {}).get("language", "ar")
        field_names = {
            "balance": self.t("account_balance", lang),
            "risk": self.t("risk_percent", lang),
            "entry": self.t("entry_price", lang),
            "sl": self.t("sl_price", lang)
        }
        self.states[uid]["awaiting"] = field
        self.bot.answer_callback_query(call.id)
        self.bot.send_message(uid, f"{self.t('fill_form', lang)} ➤ {field_names[field]}")
        self.bot.register_next_step_handler(call.message, lambda m: self.save_value(m, field))

# ----------------------------------------------------
    def save_value(self, message, field):
        """يحفظ قيمة الحقل بعد أن يكتبها المستخدم"""
        uid = message.chat.id
        lang = self.user_data.get(uid, {}).get("language", "ar")
        value = message.text.strip()

        # إذا لم يكن رقمًا
        try:
            _ = float(value)
        except:
            self.bot.send_message(uid, "❗ رقم غير صالح", reply_markup=types.ReplyKeyboardRemove())
            self.edit_form(message, lang)
            return

        # حفظ القيمة
        self.states[uid][field] = value
        # حفظ آخر قيمة لسهولة الاستخدام لاحقًا
        if uid not in self.last_inputs:
            self.last_inputs[uid] = {}
        self.last_inputs[uid][field] = value

        self.edit_form(message, lang)

    # ----------------------------------------------------
    def calculate(self, call):
        uid = call.message.chat.id
        lang = self.user_data.get(uid, {}).get("language", "ar")
        st = self.states.get(uid, {})

        try:
            balance = float(st["balance"])
            risk = float(st["risk"])/100
            entry = float(st["entry"])
            sl = float(st["sl"])
        except:
            self.bot.answer_callback_query(call.id, "❗املأ جميع الحقول أولاً", show_alert=True)
            return

        risk_amount = balance * risk
        distance = abs(entry - sl)
        position = risk_amount / distance

        unit = {
            "fx": "Lot",
            "stocks": "Shares",
            "crypto": "Units",
            "commodities": "Contracts",
            "gold": "Contracts",
            "oil": "Contracts",
            "indices": "Contracts"
        }.get(st.get("market"), "")

        text = (f"✅ {self.t('position_size', lang)}: *{round(position,2)} {unit}*\n"
                f"💸 {self.t('risk_amount', lang)}: {round(risk_amount,2)}")

        self.bot.edit_message_text(text, uid, call.message.message_id, parse_mode="Markdown")

    # ----------------------------------------------------
    def send_example(self, call):
        uid = call.message.chat.id
        lang = self.user_data.get(uid, {}).get("language", "ar")
        ex = (
            "مثال توضيحي:\n"
            "- رصيد الحساب: 5000\n- نسبة المخاطرة: 2%\n"
            "- سعر الدخول: 1.2100\n- وقف الخسارة: 1.2050\n\n"
            "➤ قيمة الخسارة = 100\n➤ المسافة = 0.0050\n➤ الحجم = 100/0.0050 = *20 Lot*"
        )
        self.bot.answer_callback_query(call.id)
        self.bot.send_message(uid, ex)