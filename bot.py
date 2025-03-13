from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from config import TELEGRAM_BOT_TOKEN, CHARACTERS, COMMUNICATION_STYLES, ANALYSIS_DEPTH
from database import Database
from deepseek_api import DeepseekAPI
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.db = Database()
        self.api = DeepseekAPI()
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self.setup_handlers()

    def setup_handlers(self):
        # Обработчики команд
        self.dp.message.register(self.start, Command("start"))
        self.dp.message.register(self.help, Command("help"))
        
        # Обработчики кнопок
        self.dp.callback_query.register(self.button)
        
        # Обработчик текстовых сообщений
        self.dp.message.register(self.handle_message, ~F.text.startswith('/'))

    async def start(self, message: types.Message) -> None:
        user = message.from_user
        self.db.add_user(user.id, user.username)
        
        keyboard = [
            [KeyboardButton(text="👤 Выбрать персонажа")],
            [KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="❓ Помощь")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
        
        welcome_message = (
            f"Привет, {user.first_name}! 👋\n\n"
            "Я - ваш интеллектуальный ассистент на базе Deepseek. "
            "Я могу общаться с вами в роли различных специалистов и помогать решать разные задачи.\n\n"
            "🔹 Используйте кнопку 'Выбрать персонажа' для выбора специализации\n"
            "🔹 В 'Настройках' можно изменить стиль общения и глубину анализа\n"
            "🔹 Нажмите 'Помощь' для получения дополнительной информации"
        )
        
        await message.answer(welcome_message, reply_markup=reply_markup)

    async def help(self, message: types.Message) -> None:
        help_text = (
            "🤖 *Как использовать бота:*\n\n"
            "1\\. *Выбор персонажа:*\n"
            "   \\- Нажмите '👤 Выбрать персонажа'\n"
            "   \\- Выберите нужного специалиста из списка\n\n"
            "2\\. *Настройка общения:*\n"
            "   \\- Нажмите '⚙️ Настройки'\n"
            "   \\- Выберите стиль общения и глубину анализа\n\n"
            "3\\. *Общение:*\n"
            "   \\- Просто напишите свой вопрос\n"
            "   \\- Бот ответит в соответствии с выбранной ролью и настройками\n\n"
            "4\\. *Дополнительно:*\n"
            "   \\- /start \\- перезапуск бота\n"
            "   \\- /help \\- это сообщение"
        )
        await message.answer(help_text, parse_mode="MarkdownV2")

    async def show_character_selection(self, message: types.Message | types.CallbackQuery) -> None:
        keyboard = []
        row = []
        for i, (char_id, char_info) in enumerate(CHARACTERS.items(), 1):
            row.append(InlineKeyboardButton(
                text=char_info.split(':')[0],
                callback_data=f"char_{char_id}"
            ))
            if i % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        if isinstance(message, types.Message):
            await message.answer("Выберите персонажа:", reply_markup=reply_markup)
        else:
            await message.message.edit_text("Выберите персонажа:", reply_markup=reply_markup)

    async def show_settings(self, message: types.Message | types.CallbackQuery) -> None:
        keyboard = [
            [InlineKeyboardButton(text="Стиль общения", callback_data="settings_style")],
            [InlineKeyboardButton(text="Глубина анализа", callback_data="settings_depth")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        if isinstance(message, types.Message):
            await message.answer("Настройки:", reply_markup=reply_markup)
        else:
            await message.message.edit_text("Настройки:", reply_markup=reply_markup)

    async def button(self, callback_query: types.CallbackQuery) -> None:
        await callback_query.answer()
        
        data = callback_query.data
        user_id = callback_query.from_user.id
        
        if data.startswith("char_"):
            character = data.split("_")[1]
            self.db.update_user_settings(user_id, current_character=character)
            character_name = CHARACTERS[character].split(':')[0]
            await callback_query.message.edit_text(f"Выбран персонаж: {character_name}")
            
        elif data.startswith("settings_"):
            setting_type = data.split("_")[1]
            if setting_type == "style":
                await self._show_style_settings(callback_query)
            elif setting_type == "depth":
                await self._show_depth_settings(callback_query)
                
        elif data.startswith("style_"):
            style = data.split("_")[1]
            self.db.update_user_settings(user_id, communication_style=style)
            await callback_query.message.edit_text(f"Установлен стиль общения: {COMMUNICATION_STYLES[style]}")
            
        elif data.startswith("depth_"):
            depth = data.split("_")[1]
            self.db.update_user_settings(user_id, analysis_depth=depth)
            await callback_query.message.edit_text(f"Установлена глубина анализа: {ANALYSIS_DEPTH[depth]}")

    async def _show_style_settings(self, callback_query: types.CallbackQuery) -> None:
        keyboard = []
        for style_id, style_name in COMMUNICATION_STYLES.items():
            keyboard.append([InlineKeyboardButton(
                text=style_name,
                callback_data=f"style_{style_id}"
            )])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback_query.message.edit_text("Выберите стиль общения:", reply_markup=reply_markup)

    async def _show_depth_settings(self, callback_query: types.CallbackQuery) -> None:
        keyboard = []
        for depth_id, depth_name in ANALYSIS_DEPTH.items():
            keyboard.append([InlineKeyboardButton(
                text=depth_name,
                callback_data=f"depth_{depth_id}"
            )])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback_query.message.edit_text("Выберите глубину анализа:", reply_markup=reply_markup)

    async def handle_message(self, message: types.Message) -> None:
        user_id = message.from_user.id
        message_text = message.text
        
        if message_text == "👤 Выбрать персонажа":
            await self.show_character_selection(message)
            return
        elif message_text == "⚙️ Настройки":
            await self.show_settings(message)
            return
        elif message_text == "❓ Помощь":
            await self.help(message)
            return
        
        # Получаем настройки пользователя
        settings = self.db.get_user_settings(user_id)
        if settings:
            character, style, depth, _ = settings
        else:
            character, style, depth = None, 'formal', 'detailed'
        
        # Генерируем ответ через DeepseekCHAT API
        response = self.api.generate_response(
            message_text,
            character=character,
            style=style,
            depth=depth
        )
        
        # Сохраняем историю диалога
        self.db.add_chat_history(user_id, message_text, response, character or 'default')
        
        # Отправляем ответ пользователю
        await message.answer(response)

    async def run(self):
        print("Запуск бота...")
        await self.dp.start_polling(self.bot)

if __name__ == '__main__':
    try:
        bot = TelegramBot()
        asyncio.run(bot.run())
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}") 