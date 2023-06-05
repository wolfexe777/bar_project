from telegram import KeyboardButton, ReplyKeyboardMarkup
def start_keyboard(update, context):
    keyboard = [[KeyboardButton('🔳 Отсканировать QR-код'),KeyboardButton('👆 Ввести ID клиента')], [KeyboardButton('📋 Инструкция')]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id,text='Выберите действие:', reply_markup=reply_markup)