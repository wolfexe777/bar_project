from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import qrcode
import telegram
import os
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from ...models import UserProfile, JobProfile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.utils.request import Request
from io import BytesIO
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from .start_keyboard import start_keyboard, start_job_keyboard
import re
from datetime import datetime
import decimal
import cv2

"""
КОД КЛИЕНТА
"""

def start(update, context):
    context.bot_data['state'] = 'start'
    user = update.effective_user
    user_id = user.id

    # Проверяем, есть ли пользователь в базе данных
    try:
        user_profile = UserProfile.objects.get(external_id=user_id)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='🟢 Вы уже зарегистрированы!')
    except UserProfile.DoesNotExist:
        # Отправляем запрос на номер телефона
        context.bot.send_message(chat_id=update.effective_chat.id, text='Пожалуйста, отправьте ваш номер телефона', reply_markup=ReplyKeyboardRemove(remove_keyboard=True))
        context.bot.send_message(chat_id=update.effective_chat.id, text='Для этого нажмите на кнопку "Отправить номер 📲"', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('📲 Отправить номер', request_contact=True)]], resize_keyboard=True, one_time_keyboard=True))
        return
    start_keyboard(update, context)

def handle_phone_number(update, context):
    state = context.bot_data.get('state')
    if state == 'start':
        user = update.effective_user
        user_id = user.id
        phone_number = update.effective_message.contact.phone_number

        # Проверяем, есть ли пользователь в базе данных
        try:
            user_profile = UserProfile.objects.get(external_id=user_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text='🟢 Вы уже зарегистрированы!')
        except UserProfile.DoesNotExist:

            # Создаем профиль пользователя
            user_profile = UserProfile.objects.create(external_id=user_id, phone_number=phone_number)
            # Создаем QR-код
            qr_data = f'🆔 ID : {user_profile.external_id}' \
                      f'📉 Скидка: {user_profile.discount_percentage}%'

            # Генерация ключевой пары RSA
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            qr_code = create_signed_qr_code(user_profile, qr_data, private_key)
            user_profile.qr_code = qr_code  # Привязываем QR-код к профилю пользователя
            user_profile.save()

            # Отправляем QR-код
            context.bot.send_message(chat_id=update.effective_chat.id, text='✅ Вы успешно зарегистрированы!')
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'🆔 Ваш ID: {user_profile.external_id}\n🔳 Персональный QR-код: ',
                                     reply_markup=ReplyKeyboardRemove(remove_keyboard=True))
            context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(qr_code, 'rb'))
            context.bot.send_message(chat_id=update.effective_chat.id, text='📁 Данные будут доступны во вкладке "🪪 Виртуальная карта"')
            start_keyboard(update, context)
    elif state == 'start_job':
        user = update.effective_user
        user_id = user.id
        phone_number = update.effective_message.contact.phone_number

        # Проверяем, есть ли пользователь в базе данных
        try:
            job_profile = JobProfile.objects.get(external_id=user_id)
            context.bot.send_message(chat_id=update.effective_chat.id, text='🟢 Вы уже зарегистрированы!')
        except JobProfile.DoesNotExist:
            # Создаем профиль пользователя
            job_profile = JobProfile.objects.create(external_id=user_id, phone_number=phone_number)
            job_profile.save()

            # Отправляем информацию о работнике
            context.bot.send_message(chat_id=update.effective_chat.id, text='✅ Вы успешно зарегистрированы!')
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Ваш ID: {job_profile.external_id}', reply_markup=ReplyKeyboardRemove(remove_keyboard=True))
            start_job_keyboard(update, context)
    else:
        pass
def create_signed_qr_code(user_profile, data, private_key,):

    # Создание цифровой подписи
    signature = private_key.sign(
        data.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    user_profile.signature = signature  # Сохраняем цифровую подпись в профиле пользователя
    user_profile.save()
    qr_data = f'{data}\nЦифровая подпись: {signature.hex()}'
    qr = qrcode.QRCode(version=1,error_correction=qrcode.constants.ERROR_CORRECT_L,box_size=10,border=4)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_bytes = BytesIO()
    qr_img.save(qr_bytes, format='PNG')
    qr_bytes.seek(0)

    # Генерируем имя файла на основе ID пользователя и номера телефона
    qr_code_filename = f"qr_code_{user_profile.external_id}.png"
    qr_code_path = os.path.join("media", "qr_codes", qr_code_filename)

    # Сохраняем QR-код в файл
    with open(qr_code_path, 'wb') as f:
        f.write(qr_bytes.read())

    return qr_code_path

def virtual_card(update, context):
    user = update.effective_user
    user_id = user.id
    user_profile = UserProfile.objects.get(external_id=user_id)
    context.bot.send_message(chat_id=update.effective_chat.id, text='🪪 Ваша виртуальная карта:')

    # Создаем QR-код
    qr_data = f'ID : {user_profile.external_id}\n Скидка: {user_profile.discount_percentage}%\n'

    # Генерация ключевой пары RSA
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    qr_code = create_signed_qr_code(user_profile, qr_data, private_key)
    user_profile.qr_code = qr_code  # Привязываем QR-код к профилю пользователя
    user_profile.save()

    # Отправляем QR-код
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'🆔 Ваш ID: {user_profile.external_id}\n🔳 Персональный QR-код:')
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(qr_code, 'rb'))
    start_keyboard(update, context)

def profile(update, context):
    user = update.effective_user
    user_id = user.id
    # Проверяем, есть ли пользователь в базе данных
    try:
        user_profile = UserProfile.objects.get(external_id=user_id)
    except UserProfile.DoesNotExist:
        context.bot.send_message(chat_id=update.effective_chat.id, text='🔴 Вы не зарегистрированы!')
        return

    message = ""
    # Проверяем, является ли пользователь VIP
    if user_profile.is_special:
        message = "Статус: VIP клиент ⭐️⭐️⭐️"
        message += "\n📉 Ваша скидка - 15%"
        message += f"\n🆔 Ваш ID: {user_profile.external_id}"
        message += f"\n💰 Общая сумма заказов: {user_profile.total_spent} руб."
        message += f"\n💵 Сумма текущего заказа: {user_profile.menu_total} руб."
    else:
        discount_percentage = user_profile.calculate_discount_percentage()
        if discount_percentage == 10:
            message = f"Cтатус: Привилегированный клиент ⭐️⭐️"
            message += f"\n🆔 Ваш ID: {user_profile.external_id}"
            message += "\n📉 Ваша скидка максимальная - 10%"
            message += f"\n💰 Общая сумма заказов: {user_profile.total_spent} руб."
            message += f"\n💵 Сумма текущего заказа: {user_profile.menu_total} руб."
        else:
            message = f"Cтатус: Обычный клиент ⭐️"
            message += f"\n🆔 Ваш ID: {user_profile.external_id}"
            message += f"\n📉 Текущая скидка: {discount_percentage}%"
            message += f"\n💰 Общая сумма заказов: {user_profile.total_spent} руб."
            message += f"\n💵 Сумма текущего заказа: {user_profile.menu_total} руб."

    if not user_profile.is_special and discount_percentage != 10:
        # Определяем, сколько еще надо потратить для повышения скидочного процента
        thresholds = { 0: 0, 3: 1000, 5: 2000, 7: 3000, 10: 5000}
        for threshold, amount in thresholds.items():
            if user_profile.total_spent < amount:
                remaining_amount = amount - user_profile.total_spent
                message += f"\n📣 Для повышения скидки до {threshold}% необходимо потратить еще {remaining_amount} руб.\n"
                break
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

# Публикация актуальных новостей на неделю
def afisha(update, context):
    pass

# Ссылки на источники контактов
def contacts(update, context):
    message = "📚 Контакты:\n"
    message += "\\- 💻 [Сайт компании](http://www.example.com)\n"
    message += "\\- 📧 [Email](mailto:info@example.com)\n"
    message += "\\- ☎️ Телефон: \\+79132222234\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode='MarkdownV2')

"""
КОД ДЛЯ РАБОТНИКА
"""

def start_job(update, context):
    context.bot_data['state'] = 'start_job'
    user = update.effective_user
    user_id = user.id
    # Проверяем, есть ли пользователь в базе данных
    try:
        job_profile = JobProfile.objects.get(external_id=user_id)
        context.bot.send_message(chat_id=update.effective_chat.id, text='Вы уже зарегистрированы!')
    except JobProfile.DoesNotExist:
        # Отправляем запрос на номер телефона
        context.bot.send_message(chat_id=update.effective_chat.id, text='Пожалуйста, отправьте ваш номер телефона', reply_markup=ReplyKeyboardRemove(remove_keyboard=True))
        context.bot.send_message(chat_id=update.effective_chat.id, text='Для этого нажмите на кнопку "📲 Отправить номер"', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('📲 Отправить номер', request_contact=True)]], resize_keyboard=True, one_time_keyboard=True))
        return
    start_job_keyboard(update, context)

def scan_code(update, context):
    button_text = '🔳 Отсканировать QR-код'
    button_url = 'https://www.online-qr-scanner.com/'
    keyboard = [[InlineKeyboardButton(button_text, url=button_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Нажмите кнопку ниже, чтобы открыть сканер QR-кодов:', reply_markup=reply_markup)

def add_menu_total_button(update, context):
    keyboard = [
        [KeyboardButton('❌ Удалить сумму текущего заказа')],
        [KeyboardButton('↩️ Назад')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Пожалуйста, введите 🆔 клиента.', reply_markup=reply_markup)
    # Устанавливаем флаг ожидания ID клиента
    context.user_data['waiting_for_id'] = True

def cancel_operation(update, context):
    start_job_keyboard(update, context)
    # Сбрасываем флаги ожидания
    context.user_data['waiting_for_id'] = False
    context.user_data['waiting_for_menu_total'] = False

def handle_menu_total(update, context):
    if update.message.text == '❌ Удалить сумму текущего заказа':
        user_profile = context.user_data.get('user_profile')
        if user_profile:
            # Возврат суммы из предыдущего меню в текущую сумму меню
            user_profile.total_spent = user_profile.total_spent - decimal.Decimal(user_profile.menu_total)
            user_profile.menu_total = 0
            user_profile.save()
            update.message.reply_text(f'✅ Сумма текущего заказа успешно отменена. Текущая сумма заказа: {user_profile.menu_total} руб.')
        else:
            update.message.reply_text('🔴 Произошла ошибка. Пожалуйста, повторите попытку.')
            start_job_keyboard(update, context)

        # Сбрасываем флаги ожидания
        context.user_data['waiting_for_menu_total'] = False
        context.user_data.pop('user_profile', None)
    if context.user_data.get('waiting_for_id'):
        user_id = update.message.text
        if not user_id.isdigit():
            update.message.reply_text('ID клиента должно быть числом, повторите ввод:')
            return
        try:
            user_profile = UserProfile.objects.get(external_id=user_id)
            vip_status = "VIP-клиент ⭐️⭐️⭐️" if user_profile.is_special else "Обычный клиент ⭐️"
            # Формируем информацию о пользователе
            reply_message = f"Статус: {vip_status}\n"
            reply_message += f"🆔 ID клиента: {user_profile.external_id}\n"
            reply_message += f"📱 Номер телефона: {user_profile.phone_number}\n"
            reply_message += f"📉 Текущая скидка: {user_profile.discount_percentage}%\n"
            # Отправляем информацию о пользователе
            context.bot.send_message(chat_id=update.effective_chat.id, text=reply_message)

        except ObjectDoesNotExist:
            update.message.reply_text('Клиент с указанным ID не найден.')
            return

        context.user_data['waiting_for_id'] = False
        context.user_data['user_profile'] = user_profile
        context.bot.send_message(chat_id=update.effective_chat.id, text='Пожалуйста, введите 👆 сумму текущего заказа\n '
                                                                        'или отмените введенную ранее сумму заказа, нажав на кнопку\n'
                                                                        '"❌ Удалить сумму текущего заказа"')
        # Устанавливаем флаг ожидания суммы меню
        context.user_data['waiting_for_menu_total'] = True

    elif context.user_data.get('waiting_for_menu_total'):
        menu_total = update.message.text

        if not re.match(r'^\d+\.\d{2}$', menu_total.replace(',', '.')):
            update.message.reply_text('Сумма заказа должна содержать рубли и копейки (0.00)')
            return

        user_profile = context.user_data.get('user_profile')
        if user_profile:
            # Сохраняем предыдущую сумму меню
            user_profile.previous_menu_total = user_profile.menu_total

            # Обновляем сумму текущего меню в профиле пользователя
            user_profile.menu_total = '{:.2f}'.format(float(menu_total))
            user_profile.total_spent += decimal.Decimal(user_profile.menu_total)

            # Сохраняем дату и время обновления меню
            user_profile.menu_total_timestamp = datetime.now()
            user_profile.save()
            update.message.reply_text(f'Сумма текущего заказа {user_profile.menu_total} руб. успешно добавлена.')
            vip_status = "VIP-клиент ⭐️⭐️⭐️" if user_profile.is_special else "Обычный клиент ⭐️"
            # Формируем информацию о пользователе
            reply_message = f"Статус: {vip_status}\n"
            reply_message += f"🆔 ID клиента: {user_profile.external_id}\n"
            reply_message += f"📱 Номер телефона: {user_profile.phone_number}\n"
            reply_message += f"📉 Текущая скидка: {user_profile.discount_percentage}%\n"
            reply_message += f"💵 Сумма текущего заказа: {user_profile.menu_total} руб.\n"
            # Отправляем информацию о пользователе
            context.bot.send_message(chat_id=update.effective_chat.id, text=reply_message)
            start_job_keyboard(update, context)
        else:
            update.message.reply_text('🔴 Произошла ошибка. Пожалуйста, повторите попытку.')
        # Сбрасываем флаги ожидания
        context.user_data['waiting_for_menu_total'] = False
        context.user_data.pop('user_profile', None)
    else:
        start_job_keyboard(update, context)

def instruction(update, context):
    # Получение полного пути к файлу с инструкцией в папке media
    file_path = os.path.join('media', 'instructions', 'instruction.pdf')

    # Отправка документа и приглашение открыть файл
    with open(file_path, 'rb') as file:
        context.bot.send_document(chat_id=update.effective_chat.id,document=file,caption='Пожалуйста, откройте инструкцию для просмотра')

class Command(BaseCommand):
    help = 'Телеграм-бот'

    def handle(self, *args, **options):
        request = Request(connect_timeout=0.5,read_timeout=1.0)
        bot = telegram.Bot(request=request,token=settings.TOKEN)
        print(bot.get_me())
        updater = Updater(bot=bot,use_context=True)
        # Обработчики команд для пользователя
        dp = updater.dispatcher
        dp.add_handler(CommandHandler('start', start))
        dp.add_handler(MessageHandler(Filters.contact, handle_phone_number))
        dp.add_handler(MessageHandler(Filters.text('‍👨‍💼 Профиль'), profile))
        dp.add_handler(MessageHandler(Filters.text('📆 Афиша'), afisha))
        dp.add_handler(MessageHandler(Filters.text('📗 Контакты'),contacts))
        dp.add_handler(MessageHandler(Filters.text('🪪 Виртуальная карта'),virtual_card))


        # обработчики команд для работника
        dp.add_handler(CommandHandler('start_job', start_job))
        dp.add_handler(MessageHandler(Filters.text('🔳 Отсканировать QR-код'), scan_code))
        dp.add_handler(MessageHandler(Filters.text('📋 Инструкция'), instruction))
        dp.add_handler(MessageHandler(Filters.text('👆 Ввести ID клиента'), add_menu_total_button))
        dp.add_handler(MessageHandler(Filters.text('↩️ Назад'), cancel_operation))
        dp.add_handler(MessageHandler(Filters.text, handle_menu_total))


        updater.start_polling()
        updater.idle()

if __name__ == '__main__':
    command = Command()
    command.handle()



