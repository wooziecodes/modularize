# handlers/common.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.localization import get_text, get_language_name
from utils.firebase_client import set_user_language, get_user_language
from config import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and language selection prompt when /start is issued."""
    user = update.effective_user
    user_id = user.id
    logger.info(f"User {user_id} ({user.username}) started the bot.")

    # Get user's stored language, default if not set
    lang_code = get_user_language(user_id)

    # Build language selection buttons
    keyboard = []
    row = []
    for code in SUPPORTED_LANGUAGES:
        lang_name = get_language_name(code)
        row.append(InlineKeyboardButton(lang_name, callback_data=f"set_lang_{code}"))
        if len(row) == 2:  # Two buttons per row
            keyboard.append(row)
            row = []
    if row:  # Add any remaining buttons
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Use get_text for the welcome message
    welcome_text = get_text("welcome", lang_code)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def language_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callback query for language selection."""
    query = update.callback_query
    await query.answer()  # Answer callback query

    user_id = query.from_user.id
    lang_code = query.data.split('_')[-1]  # Extract lang code from 'set_lang_xx'

    if lang_code in SUPPORTED_LANGUAGES:
        set_user_language(user_id, lang_code)
        logger.info(f"User {user_id} selected language: {lang_code}")
        selected_text = get_text("language_selected", lang_code)
        await query.edit_message_text(text=selected_text)

        # Show main menu after language selection
        await show_main_menu(update, context, lang_code)
    else:
        logger.warning(f"User {user_id} selected invalid language code: {lang_code}")
        error_text = get_text("error_generic", DEFAULT_LANGUAGE)
        await query.edit_message_text(text=error_text)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_code: str = None):
    """Shows the main menu with options for financial assistance."""
    user_id = update.effective_user.id
    
    if lang_code is None:
        lang_code = get_user_language(user_id)
    
    # Create menu buttons
    keyboard = [
        [
            InlineKeyboardButton(get_text("menu_set_goal", lang_code), callback_data="menu_set_goal"),
            InlineKeyboardButton(get_text("menu_log_expense", lang_code), callback_data="menu_log_expense")
        ],
        [
            InlineKeyboardButton(get_text("menu_ask_advice", lang_code), callback_data="menu_ask_advice"),
            InlineKeyboardButton(get_text("menu_view_expenses", lang_code), callback_data="menu_view_expenses")
        ],
        [
            InlineKeyboardButton(get_text("menu_profile", lang_code), callback_data="menu_profile"),
            InlineKeyboardButton(get_text("menu_change_language", lang_code), callback_data="menu_change_language")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_text = get_text("main_menu", lang_code)
    
    # If this is from a callback query (language selection), edit the message
    if update.callback_query:
        await update.callback_query.edit_message_text(text=menu_text, reply_markup=reply_markup)
    # Otherwise, send a new message (e.g., from /menu command)
    else:
        await update.message.reply_text(text=menu_text, reply_markup=reply_markup)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles main menu button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    lang_code = get_user_language(user_id)
    
    # Process different menu options
    if callback_data == "menu_set_goal":
        # Redirect to goals module
        logger.info(f"🎯 User {user_id} selected SET GOAL MENU OPTION")
        logger.info(f"👉 Now redirecting to the goal setting flow which should start with income assessment")
        from handlers import goals
        await goals.start_goal_setting(update, context)
        
    elif callback_data == "menu_log_expense":
        # Ask user to enter expense
        prompt_text = get_text("enter_expense", lang_code)
        await query.edit_message_text(text=prompt_text)
        context.user_data["expecting_expense"] = True
        
    elif callback_data == "menu_ask_advice":
        # Ask user what they need advice on
        logger.info(f"User {user_id} selected menu_ask_advice")
        from handlers import advice
        await advice.show_advice_categories(update, context)
        
    elif callback_data == "menu_view_expenses":
        # Redirect to expenses module
        from handlers import expenses
        await expenses.show_expenses(update, context)
        
    elif callback_data == "menu_profile":
        # Redirect to onboarding/profile module
        from handlers import onboarding
        await onboarding.show_profile(update, context)
        
    elif callback_data == "menu_change_language":
        # Show language selection again
        keyboard = []
        row = []
        for code in SUPPORTED_LANGUAGES:
            lang_name = get_language_name(code)
            row.append(InlineKeyboardButton(lang_name, callback_data=f"set_lang_{code}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        prompt_text = get_text("select_language_prompt", lang_code)
        await query.edit_message_text(text=prompt_text, reply_markup=reply_markup)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles errors in the telegram-python-bot library."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # If we can identify the user, send them an error message
    if update and update.effective_user:
        user_id = update.effective_user.id
        lang_code = get_user_language(user_id)
        error_text = get_text("error_generic", lang_code)
        
        # Try to send a message to the user
        try:
            if update.callback_query:
                await update.callback_query.answer(error_text)
            elif update.effective_message:
                await update.effective_message.reply_text(error_text)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

# Command handlers
start_handler = CommandHandler('start', start)
menu_handler = CommandHandler('menu', show_main_menu)

# Callback handlers
language_callback_handler = CallbackQueryHandler(language_select_callback, pattern='^set_lang_')
menu_callback_handler = CallbackQueryHandler(menu_callback, pattern='^menu_')