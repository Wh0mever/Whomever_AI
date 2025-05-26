from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove, FSInputFile
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import (
    TELEGRAM_BOT_TOKEN, CHARACTERS, COMMUNICATION_STYLES, ANALYSIS_DEPTH,
    MAX_FILE_SIZE, ALLOWED_FILE_TYPES, FILE_UPLOAD_DIR, TEMP_DIR,
    SEARCH_SETTINGS, OPENAI_API_KEY, DEEPSEEKCHAT_API_KEY
)
from database import Database
from openai_api import OpenAIAPI
from search_api import SearchAPI
import logging
import asyncio
import os
import mimetypes
from datetime import datetime

# Создаем необходимые директории
os.makedirs(FILE_UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ImageGenStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_size = State()
    waiting_for_quality = State()
    waiting_for_variation = State()
    waiting_for_edit_prompt = State()
    waiting_for_mask = State()

class TelegramBot:
    def __init__(self):
        self.db = Database()
        self.api = OpenAIAPI(max_workers=50)
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self.setup_handlers()

    def setup_handlers(self):
        # Обработчики команд
        self.dp.message.register(self.start, Command("start"))
        self.dp.message.register(self.help, Command("help"))
        self.dp.message.register(self.search, Command("search"))
        self.dp.message.register(self.image_command, Command("image"))
        self.dp.message.register(self.edit_command, Command("edit"))
        self.dp.message.register(self.variation_command, Command("variation"))
        
        # Обработчики кнопок
        self.dp.callback_query.register(self.button)
        
        # Обработчик текстовых сообщений
        self.dp.message.register(self.handle_message, ~F.text.startswith('/'))
        
        # Обработчики файлов
        self.dp.message.register(self.handle_document, F.document)
        self.dp.message.register(self.handle_photo, F.photo)
        self.dp.message.register(self.handle_voice, F.voice)
        self.dp.message.register(self.handle_video_note, F.video_note)
        self.dp.message.register(self.handle_video, F.video)
        self.dp.message.register(self.handle_audio, F.audio)

        # Обработчики состояний для генерации изображений
        self.dp.message.register(self.process_image_prompt, ImageGenStates.waiting_for_prompt)
        self.dp.message.register(self.process_image_size, ImageGenStates.waiting_for_size)
        self.dp.message.register(self.process_image_quality, ImageGenStates.waiting_for_quality)
        self.dp.message.register(self.process_variation_image, ImageGenStates.waiting_for_variation)
        self.dp.message.register(self.process_edit_prompt, ImageGenStates.waiting_for_edit_prompt)
        self.dp.message.register(self.process_edit_mask, ImageGenStates.waiting_for_mask)

    def get_main_keyboard(self):
        """Создание основной клавиатуры"""
        keyboard = [
            [KeyboardButton(text="👤 Выбрать персонажа")],
            [KeyboardButton(text="🎨 Генерация изображений"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="❓ Помощь")]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

    def get_image_keyboard(self):
        """Создание клавиатуры для работы с изображениями"""
        keyboard = [
            [InlineKeyboardButton(text="🎨 Создать новое", callback_data="img_new")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="img_edit")],
            [InlineKeyboardButton(text="🔄 Создать вариацию", callback_data="img_variation")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    def get_image_size_keyboard(self):
        """Создание клавиатуры для выбора размера изображения"""
        keyboard = [
            [InlineKeyboardButton(text="1024x1024", callback_data="size_1024")],
            [InlineKeyboardButton(text="1024x1792", callback_data="size_1024x1792")],
            [InlineKeyboardButton(text="1792x1024", callback_data="size_1792x1024")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    def get_image_quality_keyboard(self):
        """Создание клавиатуры для выбора качества изображения"""
        keyboard = [
            [InlineKeyboardButton(text="Стандартное", callback_data="quality_standard")],
            [InlineKeyboardButton(text="HD", callback_data="quality_hd")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    async def start(self, message: types.Message) -> None:
        user = message.from_user
        self.db.add_user(user.id, user.username)
        
        welcome_message = (
            f"Привет, {user.first_name}! 👋\n\n"
            "Я - ваш интеллектуальный ассистент на базе GPT-4o. "
            "Я могу общаться с вами в роли различных специалистов и помогать решать разные задачи.\n\n"
            "🔹 Используйте кнопку 'Выбрать персонажа' для выбора специализации\n"
            "🔹 'Генерация изображений' для работы с DALL-E\n"
            "🔹 Отправляйте файлы для анализа (текст, PDF, DOC, изображения)\n"
            "🔹 Отправляйте голосовые сообщения или видео\n"
            "🔹 Используйте команду /search для поиска информации\n"
            "🔹 Нажмите 'Помощь' для получения дополнительной информации"
        )
        
        await message.answer(welcome_message, reply_markup=self.get_main_keyboard())

    async def help(self, message: types.Message) -> None:
        help_text = (
            "🤖 *Как использовать бота:*\n\n"
            "1\\. *Выбор персонажа:*\n"
            "   \\- Нажмите '👤 Выбрать персонажа'\n"
            "   \\- Выберите нужного специалиста из списка\n\n"
            "2\\. *Работа с изображениями:*\n"
            "   \\- Используйте '🎨 Генерация изображений'\n"
            "   \\- Команда /image для создания изображений\n"
            "   \\- Команда /edit для редактирования\n"
            "   \\- Команда /variation для создания вариаций\n\n"
            "3\\. *Работа с файлами:*\n"
            "   \\- Отправьте файл \\(текст, PDF, DOC, изображение\\)\n"
            "   \\- Отправьте голосовое сообщение или видео\n"
            "   \\- Бот проанализирует содержимое\n\n"
            "4\\. *Поиск информации:*\n"
            "   \\- Используйте команду /search \\<запрос\\>\n"
            "   \\- Бот найдет актуальную информацию\n\n"
            "5\\. *Общение:*\n"
            "   \\- Просто напишите свой вопрос\n"
            "   \\- Бот ответит в соответствии с выбранной ролью и настройками"
        )
        await message.answer(help_text, parse_mode="MarkdownV2")

    async def image_command(self, message: types.Message, state: FSMContext) -> None:
        """Обработка команды /image"""
        await message.answer(
            "🎨 Генерация изображений через DALL-E 3\n\n"
            "Пожалуйста, опишите изображение, которое хотите создать:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(ImageGenStates.waiting_for_prompt)

    async def process_image_prompt(self, message: types.Message, state: FSMContext) -> None:
        """Обработка промпта для генерации изображения"""
        await state.update_data(prompt=message.text)
        await message.answer(
            "Выберите размер изображения:",
            reply_markup=self.get_image_size_keyboard()
        )
        await state.set_state(ImageGenStates.waiting_for_size)

    async def process_image_size(self, message: types.Message, state: FSMContext) -> None:
        """Обработка выбора размера изображения"""
        size = message.text
        await state.update_data(size=size)
        await message.answer(
            "Выберите качество изображения:",
            reply_markup=self.get_image_quality_keyboard()
        )
        await state.set_state(ImageGenStates.waiting_for_quality)

    async def process_image_quality(self, message: types.Message, state: FSMContext) -> None:
        """Обработка выбора качества и генерация изображения"""
        quality = message.text
        data = await state.get_data()
        
        await message.answer("🎨 Генерирую изображение...")
        
        urls = await self.api.generate_image(
            prompt=data['prompt'],
            size=data['size'],
            quality=quality
        )
        
        if urls:
            for url in urls:
                await message.answer_photo(
                    url,
                    caption="✨ Сгенерированное изображение"
                )
        else:
            await message.answer("Произошла ошибка при генерации изображения.")
        
        await state.clear()
        await message.answer(
            "Что бы вы хотели сделать дальше?",
            reply_markup=self.get_main_keyboard()
        )

    async def edit_command(self, message: types.Message, state: FSMContext) -> None:
        """Обработка команды /edit"""
        await message.answer(
            "✏️ Редактирование изображения\n\n"
            "Пожалуйста, отправьте изображение, которое хотите отредактировать:"
        )
        await state.set_state(ImageGenStates.waiting_for_edit_prompt)

    async def process_edit_prompt(self, message: types.Message, state: FSMContext) -> None:
        """Обработка промпта для редактирования изображения"""
        if not message.photo:
            await message.answer("Пожалуйста, отправьте изображение.")
            return
        
        photo = message.photo[-1]
        file_info = await self.bot.get_file(photo.file_id)
        file_path = os.path.join(TEMP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        await self.bot.download_file(file_info.file_path, file_path)
        
        await state.update_data(image_path=file_path)
        await message.answer(
            "Теперь отправьте маску (черно-белое изображение, где белым отмечена область для редактирования):"
        )
        await state.set_state(ImageGenStates.waiting_for_mask)

    async def process_edit_mask(self, message: types.Message, state: FSMContext) -> None:
        """Обработка маски и редактирование изображения"""
        if not message.photo:
            await message.answer("Пожалуйста, отправьте маску.")
            return
        
        photo = message.photo[-1]
        file_info = await self.bot.get_file(photo.file_id)
        mask_path = os.path.join(TEMP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_mask.png")
        await self.bot.download_file(file_info.file_path, mask_path)
        
        data = await state.get_data()
        image_path = data['image_path']
        
        await message.answer("✏️ Редактирую изображение...")
        
        urls = await self.api.edit_image(
            image_path=image_path,
            mask_path=mask_path,
            prompt=message.caption or "Улучшить изображение"
        )
        
        # Удаляем временные файлы
        os.remove(image_path)
        os.remove(mask_path)
        
        if urls:
            for url in urls:
                await message.answer_photo(
                    url,
                    caption="✨ Отредактированное изображение"
                )
        else:
            await message.answer("Произошла ошибка при редактировании изображения.")
        
        await state.clear()
        await message.answer(
            "Что бы вы хотели сделать дальше?",
            reply_markup=self.get_main_keyboard()
        )

    async def variation_command(self, message: types.Message, state: FSMContext) -> None:
        """Обработка команды /variation"""
        await message.answer(
            "🔄 Создание вариации изображения\n\n"
            "Пожалуйста, отправьте изображение, для которого хотите создать вариацию:"
        )
        await state.set_state(ImageGenStates.waiting_for_variation)

    async def process_variation_image(self, message: types.Message, state: FSMContext) -> None:
        """Обработка изображения для создания вариации"""
        if not message.photo:
            await message.answer("Пожалуйста, отправьте изображение.")
            return
        
        photo = message.photo[-1]
        file_info = await self.bot.get_file(photo.file_id)
        file_path = os.path.join(TEMP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        await self.bot.download_file(file_info.file_path, file_path)
        
        await message.answer("🔄 Создаю вариацию...")
        
        urls = await self.api.create_image_variation(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if urls:
            for url in urls:
                await message.answer_photo(
                    url,
                    caption="✨ Вариация изображения"
                )
        else:
            await message.answer("Произошла ошибка при создании вариации.")
        
        await state.clear()
        await message.answer(
            "Что бы вы хотели сделать дальше?",
            reply_markup=self.get_main_keyboard()
        )

    async def search(self, message: types.Message) -> None:
        """Обработка команды поиска"""
        query = message.text.replace('/search', '').strip()
        if not query:
            await message.answer(
                "Пожалуйста, укажите поисковый запрос после команды /search\n"
                "Например: /search последние новости технологий"
            )
            return
        
        status_message = await message.answer("🔍 Ищу информацию...")
        
        try:
            search_api = SearchAPI()
            
            # Получаем результаты поиска
            results = await search_api.search(
                query=query,
                engine=SEARCH_SETTINGS['default_engine'],
                country=SEARCH_SETTINGS['default_country'],
                pages=1
            )
            
            if not results:
                await status_message.edit_text("К сожалению, по вашему запросу ничего не найдено. Попробуйте изменить запрос.")
                return
            
            # Форматируем результаты
            response_text = "🔍 Результаты поиска:\n\n"
            for i, result in enumerate(results[:5], 1):
                response_text += (
                    f"{i}. {result['title']}\n"
                    f"📎 {result['url']}\n"
                    f"📝 {result['description']}\n\n"
                )
            
            await status_message.edit_text(response_text)
            
            # Получаем поисковые подсказки
            try:
                suggestions = await search_api.get_suggestions(query)
                if suggestions:
                    suggest_text = "💡 Похожие запросы:\n"
                    for suggestion in suggestions[:5]:
                        suggest_text += f"• {suggestion['keyword']}\n"
                    await message.answer(suggest_text)
            except Exception as e:
                logger.warning(f"Ошибка при получении подсказок: {str(e)}")
                
        except Exception as e:
            error_message = f"Ошибка при поиске: {str(e)}"
            logger.error(error_message)
            await status_message.edit_text("Извините, произошла ошибка при выполнении поиска. Попробуйте позже.")

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
            character, style, depth = 'default', 'formal', 'detailed'
        
        # Подготавливаем сообщения для API
        messages = [
            {"role": "system", "content": f"Вы - {CHARACTERS.get(character, 'Универсальный помощник')}. Используйте {style} стиль общения и давайте {depth} ответы."},
            {"role": "user", "content": message_text}
        ]
        
        # Отправляем "печатает" статус
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Генерируем ответ через OpenAI API
        response = await self.api.generate_response(messages)
        
        # Сохраняем историю диалога
        self.db.add_chat_history(user_id, message_text, response, character or 'default')
        
        # Отправляем ответ пользователю
        await message.answer(response)

    async def handle_document(self, message: types.Message) -> None:
        """Обработка документов"""
        try:
            # Проверяем размер файла
            if message.document.file_size > MAX_FILE_SIZE:
                await message.answer("Файл слишком большой. Максимальный размер: 20 MB")
                return
            
            # Проверяем тип файла
            mime_type = message.document.mime_type
            if mime_type not in ALLOWED_FILE_TYPES:
                await message.answer("Этот тип файла не поддерживается.")
                return
            
            # Скачиваем файл
            file_info = await self.bot.get_file(message.document.file_id)
            file_path = os.path.join(FILE_UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{message.document.file_name}")
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("Анализирую документ...")
            
            # Обрабатываем файл
            prompt_template = "Проанализируйте следующий текст и предоставьте краткое резюме: {text}"
            results = await self.api.process_file(file_path, prompt_template)
            
            # Отправляем результаты
            for result in results:
                await message.answer(result[:4096])  # Telegram limit
            
            # Удаляем временный файл
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке документа.")

    async def handle_photo(self, message: types.Message) -> None:
        """Обработка изображений"""
        try:
            # Получаем самую большую версию фото
            photo = message.photo[-1]
            
            # Скачиваем фото
            file_info = await self.bot.get_file(photo.file_id)
            file_path = os.path.join(FILE_UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("Анализирую изображение...")
            
            # Обрабатываем изображение
            prompt_template = "Опишите, что вы видите на этом изображении:"
            results = await self.api.process_file(file_path, prompt_template)
            
            # Отправляем результаты
            for result in results:
                await message.answer(result[:4096])  # Telegram limit
            
            # Удаляем временный файл
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке изображения.")

    async def _process_audio_message(self, message: types.Message, file_id: str, file_name: str) -> None:
        """Общая функция для обработки аудио сообщений"""
        try:
            # Скачиваем файл
            file_info = await self.bot.get_file(file_id)
            file_path = os.path.join(FILE_UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}")
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("🎧 Анализирую аудио...")
            
            # Обрабатываем файл
            results = await self.api.process_file(file_path, "")
            
            # Отправляем результаты
            for result in results:
                await message.answer(result[:4096])
            
            # Удаляем временный файл и статусное сообщение
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке аудио.")

    async def handle_voice(self, message: types.Message) -> None:
        """Обработка голосовых сообщений"""
        await self._process_audio_message(
            message,
            message.voice.file_id,
            f"voice_{message.voice.file_id}.ogg"
        )

    async def handle_audio(self, message: types.Message) -> None:
        """Обработка аудио файлов"""
        await self._process_audio_message(
            message,
            message.audio.file_id,
            message.audio.file_name or f"audio_{message.audio.file_id}.mp3"
        )

    async def handle_video_note(self, message: types.Message) -> None:
        """Обработка видео-сообщений"""
        try:
            # Скачиваем файл
            file_info = await self.bot.get_file(message.video_note.file_id)
            file_path = os.path.join(FILE_UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_video_note.mp4")
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("🎥 Анализирую видео-сообщение...")
            
            # Обрабатываем файл
            results = await self.api.process_file(file_path, "")
            
            # Отправляем результаты
            for result in results:
                await message.answer(result[:4096])
            
            # Удаляем временный файл и статусное сообщение
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео-сообщения: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке видео-сообщения.")

    async def handle_video(self, message: types.Message) -> None:
        """Обработка видео файлов"""
        try:
            # Скачиваем файл
            file_info = await self.bot.get_file(message.video.file_id)
            file_path = os.path.join(FILE_UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{message.video.file_name or 'video.mp4'}")
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("🎬 Анализирую видео...")
            
            # Обрабатываем файл
            results = await self.api.process_file(file_path, "")
            
            # Отправляем результаты
            for result in results:
                await message.answer(result[:4096])
            
            # Удаляем временный файл и статусное сообщение
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке видео.")

    async def run(self):
        print("Запуск бота...")
        await self.dp.start_polling(self.bot)

if __name__ == '__main__':
    try:
        bot = TelegramBot()
        asyncio.run(bot.run())
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}") 