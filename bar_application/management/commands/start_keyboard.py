from telegram import KeyboardButton, ReplyKeyboardMarkup

def start_keyboard(update, context):
    keyboard = [[KeyboardButton('🪪 Виртуальная карта'), KeyboardButton('👨‍💼 Профиль')],[KeyboardButton('📆 Афиша'), KeyboardButton('📗 Контакты')]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text='⤵️ Выберите действие:', reply_markup=reply_markup)