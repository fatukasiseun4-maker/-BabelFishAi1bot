import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from typing import Dict
import aiohttp
import asyncio
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Language mappings
LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh': 'Chinese',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'id': 'Indonesian',
    'ms': 'Malay',
    'fil': 'Filipino'
}

# User preferences storage (in-memory, for demo)
# In production, use a database
user_preferences: Dict[int, Dict] = {}

class BabelFishBot:
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN environment variable not set")
        
        # AI API key (optional - for enhanced translations)
        self.ai_api_key = os.environ.get('OPENAI_API_KEY')
        self.use_ai = bool(self.ai_api_key)
        
        # Initialize the application
        self.app = Application.builder().token(self.token).build()
        
        # Register handlers
        self.register_handlers()
    
    def register_handlers(self):
        """Register all command and message handlers"""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("setlang", self.set_language_command))
        self.app.add_handler(CommandHandler("mylang", self.my_language_command))
        self.app.add_handler(CommandHandler("languages", self.list_languages_command))
        self.app.add_handler(CommandHandler("translate", self.translate_command))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Callback query handler (for inline keyboards)
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        self.app.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_message = (
            f"🌊 Hello {user.first_name}! Welcome to BabelFish AI Bot!\n\n"
            "I can translate messages between different languages instantly. "
            "Just send me any text and I'll translate it for you!\n\n"
            "📌 *Features:*\n"
            "• Translate any text to your preferred language\n"
            "• Set your default target language\n"
            "• Support for 20+ languages\n"
            "• AI-powered translations (when available)\n\n"
            "🔧 *Commands:*\n"
            "/setlang - Set your preferred language\n"
            "/mylang - Check your current language\n"
            "/languages - List all supported languages\n"
            "/translate - Translate specific text\n"
            "/help - Show this help message"
        )
        
        keyboard = [
            [InlineKeyboardButton("🌍 Set Language", callback_data="set_lang")],
            [InlineKeyboardButton("📖 View Languages", callback_data="view_langs")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "🔍 *How to use BabelFish AI Bot:*\n\n"
            "1️⃣ *Direct Translation*\n"
            "Just send any text and I'll translate it to your preferred language.\n\n"
            "2️⃣ *Set Your Language*\n"
            "Use /setlang to choose your default target language.\n\n"
            "3️⃣ *Translate Specific Text*\n"
            "Use /translate [text] to translate specific text to your language.\n\n"
            "4️⃣ *AI Translation*\n"
            "When AI is enabled, translations will be more natural and context-aware.\n\n"
            "🛠 *Available Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/setlang - Set your preferred language\n"
            "/mylang - View your current language\n"
            "/languages - List all supported languages\n"
            "/translate - Translate specific text\n\n"
            "💡 *Tip:* You can also reply to a message with the /translate command!"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def set_language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setlang command - show language selection"""
        keyboard = []
        row = []
        for i, (code, name) in enumerate(LANGUAGES.items()):
            row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🌍 *Select your preferred language:*\n\n"
            "Choose the language you want messages translated to:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def my_language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mylang command"""
        user_id = update.effective_user.id
        pref = user_preferences.get(user_id, {})
        lang_code = pref.get('target_lang', 'en')
        lang_name = LANGUAGES.get(lang_code, 'English')
        
        await update.message.reply_text(
            f"📌 *Your current language:* {lang_name} ({lang_code})\n\n"
            f"Use /setlang to change your preferred language.",
            parse_mode='Markdown'
        )
    
    async def list_languages_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /languages command"""
        lang_list = "\n".join([f"• {name} (`{code}`)" for code, name in LANGUAGES.items()])
        await update.message.reply_text(
            f"🌍 *Supported Languages:*\n\n{lang_list}\n\n"
            f"Use /setlang to set your preferred language.",
            parse_mode='Markdown'
        )
    
    async def translate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /translate command"""
        if not context.args:
            # If replying to a message, translate that
            if update.message.reply_to_message and update.message.reply_to_message.text:
                text = update.message.reply_to_message.text
                await self.perform_translation(update, text)
            else:
                await update.message.reply_text(
                    "❌ Please provide text to translate.\n"
                    "Example: `/translate Hello world`\n"
                    "Or reply to a message with /translate",
                    parse_mode='Markdown'
                )
            return
        
        text = ' '.join(context.args)
        await self.perform_translation(update, text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        if not update.message or not update.message.text:
            return
        
        text = update.message.text
        await self.perform_translation(update, text)
    
    async def perform_translation(self, update: Update, text: str):
        """Perform the actual translation"""
        user_id = update.effective_user.id
        pref = user_preferences.get(user_id, {})
        target_lang = pref.get('target_lang', 'en')
        
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Translate the text
        translated_text = await self.translate_text(text, target_lang)
        
        # Prepare the response
        lang_name = LANGUAGES.get(target_lang, 'English')
        response = (
            f"🔤 *Translation to {lang_name}:*\n\n"
            f"{translated_text}\n\n"
            f"📝 *Original:*\n"
            f"`{text[:200]}{'...' if len(text) > 200 else ''}`"
        )
        
        # Add buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Change Language", callback_data="set_lang")],
            [InlineKeyboardButton("📖 View All Languages", callback_data="view_langs")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def translate_text(self, text: str, target_lang: str) -> str:
        """Translate text using AI or fallback to basic translation"""
        if self.use_ai and self.ai_api_key:
            return await self.translate_with_ai(text, target_lang)
        else:
            return await self.translate_basic(text, target_lang)
    
    async def translate_with_ai(self, text: str, target_lang: str) -> str:
        """Translate using OpenAI API"""
        try:
            lang_name = LANGUAGES.get(target_lang, 'English')
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.ai_api_key}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {'role': 'system', 'content': f'You are a translator. Translate the following text to {lang_name}. Only respond with the translation, nothing else.'},
                        {'role': 'user', 'content': text}
                    ],
                    'max_tokens': 500,
                    'temperature': 0.3
                }
                
                async with session.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content'].strip()
                    else:
                        logger.error(f"OpenAI API error: {response.status}")
                        return await self.translate_basic(text, target_lang)
        except Exception as e:
            logger.error(f"AI translation error: {e}")
            return await self.translate_basic(text, target_lang)
    
    async def translate_basic(self, text: str, target_lang: str) -> str:
        """Basic fallback translation using free API"""
        try:
            # Using MyMemory Translation API as fallback
            url = f"https://api.mymemory.translated.net/get?q={text}&langpair=en|{target_lang}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'responseData' in data and 'translatedText' in data['responseData']:
                            return data['responseData']['translatedText']
            
            # If all fails, return original text with a note
            return f"⚠️ *Translation unavailable. Original text:*\n\n{text}"
        except Exception as e:
            logger.error(f"Basic translation error: {e}")
            return f"⚠️ *Translation error. Original text:*\n\n{text}"
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data == "set_lang":
            # Show language selection
            keyboard = []
            row = []
            for i, (code, name) in enumerate(LANGUAGES.items()):
                row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🌍 *Select your preferred language:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif data == "view_langs":
            lang_list = "\n".join([f"• {name} (`{code}`)" for code, name in LANGUAGES.items()])
            await query.edit_message_text(
                f"🌍 *Supported Languages:*\n\n{lang_list}",
                parse_mode='Markdown'
            )
        
        elif data == "help":
            help_text = (
                "🔍 *How to use BabelFish AI Bot:*\n\n"
                "1️⃣ *Direct Translation*\n"
                "Just send any text and I'll translate it to your preferred language.\n\n"
                "2️⃣ *Set Your Language*\n"
                "Use /setlang to choose your default target language.\n\n"
                "3️⃣ *Translate Specific Text*\n"
                "Use /translate [text] to translate specific text to your language.\n\n"
                "4️⃣ *AI Translation*\n"
                "When AI is enabled, translations will be more natural and context-aware.\n\n"
                "🛠 *Available Commands:*\n"
                "/start - Start the bot\n"
                "/help - Show this help\n"
                "/setlang - Set your preferred language\n"
                "/mylang - View your current language\n"
                "/languages - List all supported languages\n"
                "/translate - Translate specific text"
            )
            await query.edit_message_text(help_text, parse_mode='Markdown')
        
        elif data.startswith("lang_"):
            # Set user's preferred language
            lang_code = data.split("_")[1]
            lang_name = LANGUAGES.get(lang_code, 'Unknown')
            
            if user_id not in user_preferences:
                user_preferences[user_id] = {}
            user_preferences[user_id]['target_lang'] = lang_code
            
            await query.edit_message_text(
                f"✅ *Language set to {lang_name} ({lang_code})!*\n\n"
                f"Now send me any text and I'll translate it to {lang_name}.",
                parse_mode='Markdown'
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Sorry, an error occurred while processing your request. Please try again later."
            )
    
    def run(self):
        """Start the bot"""
        logger.info("Starting BabelFish AI Bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = BabelFishBot()
    bot.run()
