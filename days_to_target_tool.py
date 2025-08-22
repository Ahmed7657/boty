from telebot import types
import math
import matplotlib.pyplot as plt
import io

class DaysToTargetTool:
    def __init__(self, bot, user_data, t):
        self.bot = bot
        self.user_data = user_data
        self.t = t
        self.form_state = {}  # {user_id: {"step": 1, "capital": ..., "target": ..., "daily": ...}}

    def open_form(self, message):
        user_id = message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")
        self.form_state[user_id] = {"step": 1}
        self.bot.send_message(user_id, self.t("enter_capital", lang))

    def process_input(self, message):
        user_id = message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")

        if user_id not in self.form_state:
            return

        state = self.form_state[user_id]
        step = state["step"]

        try:
            value = float(message.text)
        except:
            self.bot.send_message(user_id, self.t("invalid_number", lang))
            return

        if step == 1:
            state["capital"] = value
            state["step"] = 2
            self.bot.send_message(user_id, self.t("enter_target", lang))

        elif step == 2:
            state["target"] = value
            state["step"] = 3
            self.bot.send_message(user_id, self.t("enter_daily_return", lang))

        elif step == 3:
            state["daily"] = value / 100
            capital, target, daily = state["capital"], state["target"], state["daily"]

            if capital <= 0 or target <= capital or daily <= 0:
                self.bot.send_message(user_id, self.t("invalid_goal_data", lang))
                del self.form_state[user_id]
                return

            # حساب الأيام المطلوبة للوصول للهدف
            days = math.log(target / capital) / math.log(1 + daily)
            days = math.ceil(days)

            msg = (
                f"📅 *Days To Target*\n\n"
                f"Capital: {capital}\n"
                f"Target: {target}\n"
                f"Daily Return: {state['daily']*100:.2f}%\n\n"
                f"⏳ Estimated Days: *{days}*"
            )
            self.bot.send_message(user_id, msg, parse_mode="Markdown")

            # 🎨 رسم بياني للتطور اليومي
            balances = []
            current = capital
            for d in range(days + 1):
                balances.append(current)
                current *= (1 + daily)

            plt.figure(figsize=(6, 4))
            plt.plot(range(days + 1), balances, marker="o", linewidth=2)
            plt.axhline(y=target, color="r", linestyle="--", label="Target")
            plt.title("Capital Growth Over Time", fontsize=12)
            plt.xlabel("Days")
            plt.ylabel("Balance")
            plt.legend()
            plt.grid(True)

            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            plt.close()

            self.bot.send_photo(user_id, buf)
            buf.close()

            del self.form_state[user_id]