from telebot import types

class RiskRewardTool:
    def __init__(self, bot, user_data, t):
        self.bot = bot
        self.user_data = user_data
        self.t = t
        self.form_state = {}  # {user_id: {"step": 1, "entry": ..., "sl": ..., "tp": ...}}

    def open_form(self, message):
        user_id = message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")
        self.form_state[user_id] = {"step": 1}
        self.bot.send_message(user_id, self.t("enter_entry_price", lang))

    def process_input(self, message):
        user_id = message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")

        if user_id not in self.form_state:
            return  # مفيش عملية مفتوحة

        state = self.form_state[user_id]
        step = state["step"]

        try:
            value = float(message.text)
        except:
            self.bot.send_message(user_id, self.t("invalid_number", lang))
            return

        if step == 1:
            state["entry"] = value
            state["step"] = 2
            self.bot.send_message(user_id, self.t("enter_stop_loss", lang))

        elif step == 2:
            state["sl"] = value
            state["step"] = 3
            self.bot.send_message(user_id, self.t("enter_take_profit", lang))

        elif step == 3:
            state["tp"] = value
            entry, sl, tp = state["entry"], state["sl"], state["tp"]

            risk = abs(entry - sl)
            reward = abs(tp - entry)
            ratio = round(reward / risk, 2) if risk > 0 else "∞"

            msg = (
                f"📊 *Risk/Reward Analysis*\n\n"
                f"Entry: {entry}\n"
                f"Stop Loss: {sl}\n"
                f"Take Profit: {tp}\n\n"
                f"Risk: {risk}\n"
                f"Reward: {reward}\n"
                f"R/R Ratio: *{ratio}*"
            )

            self.bot.send_message(user_id, msg, parse_mode="Markdown")
            del self.form_state[user_id]