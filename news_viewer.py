# news_viewer.py
import requests
from telebot import types
from deep_translator import GoogleTranslator

API_KEY = "089wRXsDWUqMEP0jXUTUysIFMCtwHkak43WmMDZS"


class NewsViewer:
    def __init__(self, bot, user_data, t):
        self.bot = bot
        self.user_data = user_data
        self.t = t
        self.news_cache = {}  # لتخزين الأخبار لكل مستخدم + مؤشر الصفحة

    # ----------------------------
    def fetch_news(self, region="us", crypto=False):
        if crypto:
            url = f"https://api.marketaux.com/v1/news/crypto?api_token={API_KEY}"
        else:
            url = f"https://api.marketaux.com/v1/news/all?countries={region}&api_token={API_KEY}"
        data = requests.get(url).json()
        return data.get("data", [])[:5]

    def translate(self, text, target):
        try:
            return GoogleTranslator(source="auto", target=target).translate(text)
        except:
            return text

    # ----------------------------
    def open_menu(self, message):
        user_id = message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(self.t("news_eg_btn", lang), callback_data="news_eg"),
            types.InlineKeyboardButton(self.t("news_us_btn", lang), callback_data="news_us"),
            types.InlineKeyboardButton(self.t("news_eu_btn", lang), callback_data="news_eu"),
            types.InlineKeyboardButton(self.t("news_crypto_btn", lang), callback_data="news_crypto"),
        )
        markup.add(types.InlineKeyboardButton("🔙", callback_data="back_trading_menu"))

        self.bot.send_message(user_id, self.t("choose_news_region", lang), reply_markup=markup)

    # ----------------------------
    def show_article(self, call, index=0):
        user_id = call.message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")
        article = self.news_cache[user_id]["articles"][index]

        title = article.get("title", "—")
        desc = article.get("description", "")
        link = article.get("url", "")
        image = article.get("image_url")

        msg = f"📰 *{title}*\n\n{desc}"

        markup = types.InlineKeyboardMarkup(row_width=2)
        if index > 0:
            markup.add(types.InlineKeyboardButton("⏮️", callback_data="prev"))
        if index < len(self.news_cache[user_id]["articles"]) - 1:
            markup.add(types.InlineKeyboardButton("⏭️", callback_data="next"))
        markup.add(
            types.InlineKeyboardButton(self.t("translate_to_ar_btn", lang), callback_data="tr_ar"),
            types.InlineKeyboardButton(self.t("translate_to_ru_btn", lang), callback_data="tr_ru")
        )
        markup.add(types.InlineKeyboardButton("🔁 " + self.t("back_to_original_btn", lang), callback_data="tr_back"))
        markup.add(types.InlineKeyboardButton("🔙", callback_data="back_trading_menu"))

        if image:
            self.bot.edit_message_media(
                media=types.InputMediaPhoto(image, caption=msg, parse_mode="Markdown"),
                chat_id=user_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        else:
            self.bot.edit_message_text(
                msg, chat_id=user_id, message_id=call.message.message_id,
                parse_mode="Markdown", reply_markup=markup
            )

    # ----------------------------
    def handle_region(self, call, code):
        user_id = call.message.chat.id
        crypto = (code == "crypto")
        articles = self.fetch_news("", crypto) if crypto else self.fetch_news(code)

        if not articles:
            self.bot.answer_callback_query(call.id, self.t("no_news_now", "ar"), show_alert=True)
            return

        self.news_cache[user_id] = {"articles": articles, "index": 0}
        self.show_article(call, index=0)
        self.bot.answer_callback_query(call.id)

    # ----------------------------
    def handle_callback(self, call):
        user_id = call.message.chat.id
        lang = self.user_data.get(user_id, {}).get("language", "ar")
        data = call.data

        if data == "next":
            self.news_cache[user_id]["index"] += 1
            self.show_article(call, self.news_cache[user_id]["index"])

        elif data == "prev":
            self.news_cache[user_id]["index"] -= 1
            self.show_article(call, self.news_cache[user_id]["index"])

        elif data == "tr_ar":
            i = self.news_cache[user_id]["index"]
            art = self.news_cache[user_id]["articles"][i]
            art["description"] = self.translate(art.get("description", ""), "ar")
            self.show_article(call, i)

        elif data == "tr_ru":
            i = self.news_cache[user_id]["index"]
            art = self.news_cache[user_id]["articles"][i]
            art["description"] = self.translate(art.get("description", ""), "ru")
            self.show_article(call, i)

        elif data == "tr_back":
            # نعيد وصف الـ API الأصلي من جديد
            idx = self.news_cache[user_id]["index"]
            code = self.news_cache[user_id].get("region", "us")
            crypto = (code == "crypto")
            original = self.fetch_news("" if crypto else code, crypto)
            self.news_cache[user_id]["articles"][idx]["description"] = original[idx].get("description", "")
            self.show_article(call, idx)