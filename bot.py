import logging
import base64
import requests
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InputFile
from telegram.ext import filters, Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Этапы диалога
NAME, PHONE, ROLE, MARKETPLACE, MANAGEMENT, TEAM, ISSUES, ISSUES_DESCRIPTION = range(8)

# Путь к CSV-файлу в репозитории GitHub
GITHUB_REPO = "gromykolina/myfirstbot"
GITHUB_FILE_PATH = "contacts.csv"
GITHUB_TOKEN = "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"

# Приветственное изображение
WELCOME_IMAGE_PATH = r'profile_icon2.png'

# Запись данных в файл на GitHub
def save_to_github(data):
    try:
        # Получаем содержимое файла из репозитория
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)
        response_data = response.json()

        if response.status_code == 404:
            # Файл не существует, создаем новый
            sha = None
            content = ""
        else:
            # Файл существует, получаем его SHA и содержимое
            sha = response_data.get("sha")
            content = base64.b64decode(response_data.get("content")).decode('utf-8')

        # Добавляем новые данные к содержимому
        csv_data = content + ','.join(data) + "\n"

        # Кодируем обновленные данные в base64
        updated_content = base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')

        # Подготовка данных для запроса
        data = {
            "message": "Update contacts.csv",
            "content": updated_content,
            "sha": sha
        }

        # Обновляем файл в репозитории
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        logger.info("Данные успешно сохранены на GitHub.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных на GitHub: {e}")

# Стартовая функция
async def start(update: Update, context: CallbackContext) -> int:
    try:
        await update.message.reply_text('Привет от команды "Оптимизатор"! 🎉 Чтобы получить чек-лист по эффективному построению команды, ответьте, пожалуйста, на пару вопросов.')
        # Отправка приветственного изображения
        with open(WELCOME_IMAGE_PATH, 'rb') as photo:
            await update.message.reply_photo(photo=InputFile(photo), caption='Как вас зовут?')
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного сообщения: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
    return NAME

# Получение имени
async def get_name(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['name'] = update.message.text
        contact_button = KeyboardButton("Поделиться номером телефона", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(f'Отлично, {context.user_data["name"]}! Пожалуйста, поделитесь своим номером телефона (не нужно ничего вводить, просто нажмите кнопку "Поделиться").', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при получении имени: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
    return PHONE

# Получение номера телефона
async def get_phone(update: Update, context: CallbackContext) -> int:
    try:
        contact = update.effective_message.contact
        context.user_data['phone'] = contact.phone_number if contact else update.message.text
        reply_markup = ReplyKeyboardMarkup(
            [['Собственник', 'Руководитель среднего звена'],
             ['Новичок', 'Другое']],
            one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text(
            f'А какую роль вы занимаете в бизнесе?',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка при получении номера телефона: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
    return ROLE

# Получение роли в бизнесе
async def get_role(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['role'] = update.message.text
        reply_markup = ReplyKeyboardMarkup([['Да', 'Нет']], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(f'{context.user_data["name"]}, подскажите, вы торгуете на маркетплейсах Wildberries или Ozon?', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при получении роли: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
    return MARKETPLACE

# Вопрос о торговле на маркетплейсах
async def get_marketplace(update: Update, context: CallbackContext) -> int:
    try:
        answer = update.message.text.lower()
        context.user_data['marketplace'] = answer
        if answer == 'да':
            reply_markup = ReplyKeyboardMarkup(
                [['Я один', 'С менеджером'], ['С командой']],
                one_time_keyboard=True, resize_keyboard=True
            )
            await update.message.reply_text(
                f'Сколько человек занимается развитием вашего бренда?',
                reply_markup=reply_markup
            )
            return MANAGEMENT
        else:
            await save_and_send_checklist(update, context)
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при вопросе о торговле на маркетплейсах: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
        return ConversationHandler.END

# Управление продажами
async def get_management(update: Update, context: CallbackContext) -> int:
    try:
        management_type = update.message.text.lower()
        context.user_data['management'] = management_type
        if management_type == 'я один':
            reply_markup = ReplyKeyboardMarkup([['Да', 'Нет']], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                f'{context.user_data["name"]}, а задумывались ли вы о найме команды?',
                reply_markup=reply_markup
            )
            return TEAM
        elif management_type in ['с менеджером', 'с командой']:
            reply_markup = ReplyKeyboardMarkup([['Да', 'Нет']], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                f'Возникают ли у вас трудности в работе с менеджером или командой?',
                reply_markup=reply_markup
            )
            return ISSUES
        else:
            await update.message.reply_text(
                'Пожалуйста, выберите один из предложенных вариантов: "Я один", "С менеджером", "С командой".'
            )
            return MANAGEMENT
    except Exception as e:
        logger.error(f"Ошибка при управлении продажами: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
        return MANAGEMENT

# Вопрос о найме команды
async def get_team(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['team'] = update.message.text.lower()
        await save_and_send_checklist(update, context)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при вопросе о найме команды: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
        return ConversationHandler.END

# Трудности с командой
async def get_issues(update: Update, context: CallbackContext) -> int:
    try:
        answer = update.message.text.lower()
        if answer == 'да':
            context.user_data['issues'] = True
            await update.message.reply_text('Пожалуйста, опишите, какие трудности у вас возникают.')
            return ISSUES_DESCRIPTION
        else:
            context.user_data['issues'] = False
            await save_and_send_checklist(update, context)
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при вопросе о трудностях с командой: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
        return ConversationHandler.END

# Уточнение проблем с командой
async def get_issues_description(update: Update, context: CallbackContext) -> int:
    try:
        context.user_data['issues_description'] = update.message.text
        await save_and_send_checklist(update, context)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при описании трудностей: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
        return ConversationHandler.END

# Сохранение данных и отправка чек-листа
async def save_and_send_checklist(update: Update, context: CallbackContext):
    try:
        user_data = context.user_data
        data = [
            user_data.get('name', ''),
            user_data.get('phone', ''),
            user_data.get('role', ''),
            user_data.get('marketplace', ''),
            user_data.get('management', ''),
            user_data.get('team', ''),
            user_data.get('issues', ''),
            user_data.get('issues_description', '')
        ]
        save_to_github(data)
        await update.message.reply_text("Ваш чек-лист сохранен! Спасибо за ответы.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных и отправке чек-листа: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")

# Основная функция
def main():
    # Создание и запуск бота
    application = Application.builder().token("7409762233:AAExIGMf0Ulz_Wx74SzU01S9VbUObX952Z0").build()

    # Определение обработчиков
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT, get_phone)],
            ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
            MARKETPLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_marketplace)],
            MANAGEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_management)],
            TEAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_team)],
            ISSUES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_issues)],
            ISSUES_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_issues_description)],
        },
        fallbacks=[CommandHandler('cancel', start)],
    )

    application.add_handler(conv_handler)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
