# position_calculator.py

from telebot import types

class PositionSizeCalculator:
    def __init__(self, bot, user_data, t):
        self.bot = bot
        self.user_data = user_data
        self.t = t
        # structure: { user_id: {"market": "", "balance": "", "risk": "", "entry": "", "sl": ""} }
        self.form_data = {}

    # قائمة الأسواق
    def open_market_menu(self, message):
        user_id = message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")

        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(types.InlineKeyboardButton("📈 Forex", callback_data="ps_fx"),
              types.InlineKeyboardButton("📊 Stocks", callback_data="ps_stocks"),
              types.InlineKeyboardButton("💰 Crypto", callback_data="ps_crypto"),
              types.InlineKeyboardButton("⚒️ Commodities", callback_data="ps_commodities"),
              types.InlineKeyboardButton("🟨 Gold", callback_data="ps_gold"),
              types.InlineKeyboardButton("🛢 Oil", callback_data="ps_oil"),
              types.InlineKeyboardButton("📉 Indices", callback_data="ps_indices"))
        m.add(types.InlineKeyboardButton("🔙", callback_data="back_trading_menu"))

        self.bot.send_message(user_id, "Select Market:", reply_markup=m)

    # حين اختيار السوق → نبدأ نموذج الإدخال
    def start_form(self, call, market_code):
        user_id = call.message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")

        # حفظ السوق المختار
        self.form_data[user_id] = {"market": market_code}

        # نموذج الإدخال
        text = (
            f"💰 {self.t('account_balance', lang)}:\n"
            f"⚠️ {self.t('risk_percent', lang)} (%):\n"
            f"📍 {self.t('entry_price', lang)}:\n"
            f"🛡️ {self.t('sl_price', lang)}:\n\n"
            f"{self.t('fill_form', lang)}"
        )

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✅ " + self.t("calculate_btn", lang), callback_data="ps_calc"))
        kb.add(types.InlineKeyboardButton("🔙", callback_data="back_trading_menu"))

        self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

    # الحساب
    def calculate(self, call):
        user_id = call.message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")
        d = self.form_data.get(user_id, {})

        try:
            balance = float(d.get("balance"))
            risk = float(d.get("risk")) / 100
            entry = float(d.get("entry"))
            sl = float(d.get("sl"))

            risk_amount = balance * risk
            distance = abs(entry - sl)
            position = risk_amount / distance

            unit = self.get_unit(d.get("market"))
            msg = (f"✅ {self.t('position_size', lang)}: *{round(position, 2)} {unit}*\n"
                   f"💸 {self.t('risk_amount', lang)}: {round(risk_amount,2)}")

            self.bot.answer_callback_query(call.id)
            self.bot.edit_message_text(msg, user_id, call.message.message_id, parse_mode="Markdown")
        except:
            self.bot.answer_callback_query(call.id, "❗Fill fields manually then click ✅", show_alert=True)

    def get_unit(self, m):
        return {
            "fx": "Lot",
            "stocks": "Shares",
            "crypto": "Units",
            "commodities": "Contracts",
            "gold": "Contracts",
            "oil": "Contracts",
            "indices": "Contracts"
        }.get(m, "")