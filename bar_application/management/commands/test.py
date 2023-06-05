from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from ...models import UserProfile  # Замените "yourapp" на название вашего приложения
from django.conf import settings
from django.core.management.base import BaseCommand
from telegram.utils.request import Request
import telegram

def start(update, context):
    update.message.reply_text('Привет! Введите сумму текущего меню:')

def menu_total(update, context):
    try:
        total = float(update.message.text)

        user_id = update.message.from_user.id
        user_profile, created = UserProfile.objects.get_or_create(user_id=user_id)
        user_profile.menu_total = total
        user_profile.save()

        update.message.reply_text(f'Сумма текущего меню: {total}')
    except ValueError:
        update.message.reply_text('Введите корректное число.')

class Command(BaseCommand):
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

        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, menu_total))

        updater.start_polling()
        updater.idle()

    def add_arguments(self, parser):
        pass
if __name__ == '__main__':
    command = Command()
    command.handle()