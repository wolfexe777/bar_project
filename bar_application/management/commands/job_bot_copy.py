import decimal
from django.core.management.base import BaseCommand
from django.conf import settings
import telegram
import os
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from ...models import JobProfile, UserProfile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from django.core.exceptions import ObjectDoesNotExist
from telegram.utils.request import Request
import re
from datetime import datetime
from .start_keyboard import start_job_keyboard


def start_job(update, context):
    user = update.effective_user
    user_id = user.id
    # Проверяем, есть ли пользователь в базе данных
    try:
        job_profile = JobProfile.objects.get(external_id=user_id)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Вы уже зарегистрированы!')
    except JobProfile.DoesNotExist:
        # Отправляем запрос на номер телефона
        context.bot.send_message(chat_id=update.effective_chat.id, text='Пожалуйста, отправьте ваш номер телефона',
                                 reply_markup=ReplyKeyboardRemove(remove_keyboard=True))
        context.bot.send_message(chat_id=update.effective_chat.id, text='Для этого нажмите на кнопку "📲 Отправить номер"', reply_markup=ReplyKeyboardMarkup([[KeyboardButton('📲 Отправить номер', request_contact=True)]], resize_keyboard=True, one_time_keyboard=True))
        return

    keyboard = [[KeyboardButton('🔳 Отсканировать QR-код'),KeyboardButton('👆 Ввести ID клиента')], [KeyboardButton('📋 Инструкция')]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id,text='Выберите действие ⤵️:', reply_markup=reply_markup)


def handle_job_phone_number(update, context):
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

def scan_code(update, context):
    button_text = '🔳 Отсканировать QR-код'
    button_url = 'https://www.online-qr-scanner.com/'

    keyboard = [[InlineKeyboardButton(button_text, url=button_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Нажмите кнопку ниже, чтобы открыть сканер QR-кодов:', reply_markup=reply_markup)

def add_menu_total_button(update, context):
    keyboard = [[KeyboardButton('❌ Удалить сумму текущего заказа')]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Пожалуйста, введите ID клиента.', reply_markup=reply_markup)
    # Устанавливаем флаг ожидания ID клиента
    context.user_data['waiting_for_id'] = True

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
        context.bot.send_message(chat_id=update.effective_chat.id, text='Пожалуйста, введите сумму текущего заказа или\n '
                                                                        'отмените введенную ранее сумму заказа, нажав на кнопку\n'
                                                                        '"Удалить сумму текущего заказа"')
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
        context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file,
            caption='Пожалуйста, откройте инструкцию для просмотра'
        )

class Command(BaseCommand):
    waiting_for_menu_total = False
    waiting_for_handle_user_id = False
    help = 'Телеграм-бот'

    def handle(self, *args, **options):
        request = Request(
            connect_timeout=0.5,
            read_timeout=1.0,
        )
        bot = telegram.Bot(
            request=request,
            token=settings.TOKEN,
        )
        print(bot.get_me())

        updater = Updater(
            bot=bot,
            use_context=True,
        )

        # Обработчики команд
        dp = updater.dispatcher
        dp.add_handler(CommandHandler('start_job', start_job))
        dp.add_handler(MessageHandler(Filters.text('🔳 Отсканировать QR-код'), scan_code))
        dp.add_handler(MessageHandler(Filters.text('📋 Инструкция'), instruction))
        dp.add_handler(MessageHandler(Filters.text('👆 Ввести ID клиента'), add_menu_total_button))
        dp.add_handler(MessageHandler(Filters.text, handle_menu_total))
        dp.add_handler(MessageHandler(Filters.contact, handle_job_phone_number))

        updater.start_polling()
        updater.idle()

if __name__ == '__main__':
    command = Command()
    command.handle()