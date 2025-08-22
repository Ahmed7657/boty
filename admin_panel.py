from telebot import types
from signals_manager import load_signals, save_signals
 
class AdminPanel:
    def __init__(self, bot, user_data, admin_state, save_data, admin_id):
        self.bot = bot
        self.user_data = user_data
        self.admin_state = admin_state
        self.save_data = save_data
        self.admin_id = admin_id
 
    # 📌 القائمة الرئيسية
    def get_main_menu(self):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(
            types.KeyboardButton("📋 قائمة المستخدمين"),
            types.KeyboardButton("📊 عرض التوصيات"),
        )
        keyboard.add(
            types.KeyboardButton("✉️ إرسال رسالة للجميع"),
            types.KeyboardButton("👤 إرسال رسالة لمستخدم"),
        )
        keyboard.add(
            types.KeyboardButton("🚫 حظر مستخدم"),
            types.KeyboardButton("✅ إلغاء حظر مستخدم"),
        )
        keyboard.add(
            types.KeyboardButton("💰 إضافة رصيد"),
            types.KeyboardButton("➖ خصم رصيد"),
        )
        keyboard.add(
            types.KeyboardButton("💸 إضافة أرباح"),
            types.KeyboardButton("➖ خصم من الأرباح"),
        )
        keyboard.add(
            types.KeyboardButton("🟢 إضافة توصية"),
            types.KeyboardButton("🔴 حذف توصية"),
        )
        keyboard.add(
            types.KeyboardButton("➕ إضافة باقة"),
            types.KeyboardButton("❌ حذف باقة"),
        )
        keyboard.add(
            types.KeyboardButton("📊 تقارير النظام"),
            types.KeyboardButton("⬅️ رجوع"),
        )
        return keyboard
 
    # 📌 تفعيل لوحة التحكم
    def register_handlers(self):
        @self.bot.message_handler(commands=["admin"])
        def admin_panel(message):
            if message.chat.id == self.admin_id:
                self.bot.send_message(message.chat.id, "✅ أهلاً بك في لوحة الأدمن", reply_markup=self.get_main_menu())
            else:
                self.bot.send_message(message.chat.id, "❌ غير مصرح لك بالدخول.")
 
        @self.bot.message_handler(func=lambda msg: msg.chat.id == self.admin_id, content_types=["text"])
        def handle_admin(message):
            chat_id = message.chat.id
            text = message.text
            state = self.admin_state.get(chat_id)
 
            # ========== قائمة المستخدمين ==========
            if text == "📋 قائمة المستخدمين":
                if not self.user_data:
                    self.bot.send_message(chat_id, "📭 لا يوجد مستخدمين مسجلين.")
                else:
                    msg = f"📋 عدد المستخدمين: {len(self.user_data)}\n\n"
                    for uid, info in self.user_data.items():
                        balance = info.get("balance", 0)
                        profit = info.get("profit", 0)
                        banned = "🚫" if info.get("banned") else "✅"
                        msg += f"🆔 {uid} | 💰 {balance} | 📈 {profit} | {banned}\n"
                    self.bot.send_message(chat_id, msg)
 
            # ========== إرسال رسالة للجميع ==========
            elif text == "✉️ إرسال رسالة للجميع":
                self.admin_state[chat_id] = "broadcast"
                self.bot.send_message(chat_id, "✉️ اكتب نص الرسالة ليتم إرسالها للجميع:")
 
            elif state == "broadcast":
                for uid in self.user_data.keys():
                    try:
                        self.bot.send_message(uid, f"📢 رسالة من الإدارة:\n\n{text}")
                    except:
                        pass
                self.bot.send_message(chat_id, "✅ تم إرسال الرسالة للجميع.")
                self.admin_state.pop(chat_id, None)
 
            # ========== إرسال رسالة لمستخدم ==========
            elif text == "👤 إرسال رسالة لمستخدم":
                self.admin_state[chat_id] = "send_user_id"
                self.bot.send_message(chat_id, "👤 أرسل الآن ID المستخدم:")
 
            elif state == "send_user_id":
                try:
                    target_id = int(text)
                    if target_id in self.user_data:
                        self.admin_state[chat_id] = f"send_user_msg_{target_id}"
                        self.bot.send_message(chat_id, f"✉️ اكتب الرسالة ليتم إرسالها للمستخدم {target_id}:")
                    else:
                        self.bot.send_message(chat_id, "❌ المستخدم غير موجود.")
                        self.admin_state.pop(chat_id, None)
                except:
                    self.bot.send_message(chat_id, "❌ ID غير صحيح.")
 
            elif state and state.startswith("send_user_msg_"):
                target_id = int(state.split("_")[-1])
                try:
                    self.bot.send_message(target_id, f"📢 رسالة من الإدارة:\n\n{text}")
                    self.bot.send_message(chat_id, "✅ تم إرسال الرسالة للمستخدم.")
                except:
                    self.bot.send_message(chat_id, "❌ فشل إرسال الرسالة.")
                self.admin_state.pop(chat_id, None)
 
            # ========== حظر وإلغاء حظر ==========
            elif text == "🚫 حظر مستخدم":
                self.admin_state[chat_id] = "ban_user"
                self.bot.send_message(chat_id, "🚫 أرسل ID المستخدم لحظره:")
 
            elif state == "ban_user":
                try:
                    target_id = int(text)
                    if target_id in self.user_data:
                        self.user_data[target_id]["banned"] = True
                        self.save_data()
                        self.bot.send_message(chat_id, f"🚫 تم حظر المستخدم {target_id}")
                    else:
                        self.bot.send_message(chat_id, "❌ المستخدم غير موجود.")
                except:
                    self.bot.send_message(chat_id, "❌ ID غير صحيح.")
                self.admin_state.pop(chat_id, None)
 
            elif text == "✅ إلغاء حظر مستخدم":
                self.admin_state[chat_id] = "unban_user"
                self.bot.send_message(chat_id, "✅ أرسل ID المستخدم لإلغاء الحظر:")
 
            elif state == "unban_user":
                try:
                    target_id = int(text)
                    if target_id in self.user_data:
                        self.user_data[target_id]["banned"] = False
                        self.save_data()
                        self.bot.send_message(chat_id, f"✅ تم إلغاء حظر المستخدم {target_id}")
                    else:
                        self.bot.send_message(chat_id, "❌ المستخدم غير موجود.")
                except:
                    self.bot.send_message(chat_id, "❌ ID غير صحيح.")
                self.admin_state.pop(chat_id, None)
 
            # ========== إضافة / خصم رصيد ==========
            elif text == "💰 إضافة رصيد":
                self.admin_state[chat_id] = "add_balance_id"
                self.bot.send_message(chat_id, "💰 أرسل ID المستخدم لإضافة رصيد له:")
 
            elif state == "add_balance_id":
                try:
                    self.admin_state[chat_id] = f"add_balance_amount_{int(text)}"
                    self.bot.send_message(chat_id, "💵 أرسل المبلغ المراد إضافته:")
                except:
                    self.bot.send_message(chat_id, "❌ ID غير صحيح.")
 
            elif state and state.startswith("add_balance_amount_"):
                target_id = int(state.split("_")[-1])
                try:
                    amount = float(text)
                    self.user_data[target_id]["balance"] = self.user_data[target_id].get("balance", 0) + amount
                    self.save_data()
                    self.bot.send_message(chat_id, f"✅ تم إضافة {amount} رصيد للمستخدم {target_id}")
                except:
                    self.bot.send_message(chat_id, "❌ المبلغ غير صحيح.")
                self.admin_state.pop(chat_id, None)
 
            elif text == "➖ خصم رصيد":
                self.admin_state[chat_id] = "sub_balance_id"
                self.bot.send_message(chat_id, "➖ أرسل ID المستخدم لخصم الرصيد منه:")
 
            elif state == "sub_balance_id":
                try:
                    self.admin_state[chat_id] = f"sub_balance_amount_{int(text)}"
                    self.bot.send_message(chat_id, "💵 أرسل المبلغ المراد خصمه:")
                except:
                    self.bot.send_message(chat_id, "❌ ID غير صحيح.")
 
            elif state and state.startswith("sub_balance_amount_"):
                target_id = int(state.split("_")[-1])
                try:
                    amount = float(text)
                    self.user_data[target_id]["balance"] = self.user_data[target_id].get("balance", 0) - amount
                    self.save_data()
                    self.bot.send_message(chat_id, f"✅ تم خصم {amount} من رصيد المستخدم {target_id}")
                except:
                    self.bot.send_message(chat_id, "❌ المبلغ غير صحيح.")
                self.admin_state.pop(chat_id, None)
 
            # ========== إضافة / خصم أرباح ==========
            elif text == "💸 إضافة أرباح":
                self.admin_state[chat_id] = "add_profit_id"
                self.bot.send_message(chat_id, "💸 أرسل ID المستخدم لإضافة أرباح له:")
 
            elif state == "add_profit_id":
                try:
                    self.admin_state[chat_id] = f"add_profit_amount_{int(text)}"
                    self.bot.send_message(chat_id, "💵 أرسل المبلغ المراد إضافته كأرباح:")
                except:
                    self.bot.send_message(chat_id, "❌ ID غير صحيح.")
 
            elif state and state.startswith("add_profit_amount_"):
                target_id = int(state.split("_")[-1])
                try:
                    amount = float(text)
                    self.user_data[target_id]["profit"] = self.user_data[target_id].get("profit", 0) + amount
                    self.save_data()
                    self.bot.send_message(chat_id, f"✅ تم إضافة {amount} أرباح للمستخدم {target_id}")
                except:
                    self.bot.send_message(chat_id, "❌ المبلغ غير صحيح.")
                self.admin_state.pop(chat_id, None)
 
            elif text == "➖ خصم من الأرباح":
                self.admin_state[chat_id] = "sub_profit_id"
                self.bot.send_message(chat_id, "➖ أرسل ID المستخدم لخصم الأرباح منه:")
 
            elif state == "sub_profit_id":
                try:
                    self.admin_state[chat_id] = f"sub_profit_amount_{int(text)}"
                    self.bot.send_message(chat_id, "💵 أرسل المبلغ المراد خصمه من الأرباح:")
                except:
                    self.bot.send_message(chat_id, "❌ ID غير صحيح.")
 
            elif state and state.startswith("sub_profit_amount_"):
                target_id = int(state.split("_")[-1])
                try:
                    amount = float(text)
                    self.user_data[target_id]["profit"] = self.user_data[target_id].get("profit", 0) - amount
                    self.save_data()
                    self.bot.send_message(chat_id, f"✅ تم خصم {amount} من أرباح المستخدم {target_id}")
                except:
                    self.bot.send_message(chat_id, "❌ المبلغ غير صحيح.")
                self.admin_state.pop(chat_id, None)
 
            # ========== إدارة التوصيات ==========
            elif text == "📊 عرض التوصيات":
                signals = load_signals()
                if not signals:
                    self.bot.send_message(chat_id, "📭 لا توجد توصيات حالياً.")
                else:
                    msg = "📊 قائمة التوصيات:\n\n"
                    for i, sig in enumerate(signals, 1):
                        msg += f"{i}- {sig}\n"
                    self.bot.send_message(chat_id, msg)
 
            elif text == "🟢 إضافة توصية":
                self.admin_state[chat_id] = "add_signal"
                self.bot.send_message(chat_id, "🟢 اكتب نص التوصية الجديدة:")
 
            elif text == "🔴 حذف توصية":
                signals = load_signals()
                if not signals:
                    self.bot.send_message(chat_id, "❌ لا توجد توصيات للحذف.")
                else:
                    msg = "🔴 اكتب رقم التوصية التي تريد حذفها:\n\n"
                    for i, sig in enumerate(signals, 1):
                        msg += f"{i}- {sig}\n"
                    self.bot.send_message(chat_id, msg)
                    self.admin_state[chat_id] = "delete_signal"
 
            elif state == "add_signal":
                signals = load_signals()
                signals.append(text)
                save_signals(signals)
                self.bot.send_message(chat_id, f"✅ تم إضافة التوصية:\n{text}")
                self.admin_state.pop(chat_id, None)
 
            elif state == "delete_signal":
                try:
                    index = int(text) - 1
                    signals = load_signals()
                    if 0 <= index < len(signals):
                        deleted = signals.pop(index)
                        save_signals(signals)
                        self.bot.send_message(chat_id, f"✅ تم حذف التوصية:\n{deleted}")
                    else:
                        self.bot.send_message(chat_id, "❌ رقم التوصية غير صحيح.")
                except ValueError:
                    self.bot.send_message(chat_id, "❌ يجب إدخال رقم صحيح.")
                self.admin_state.pop(chat_id, None)