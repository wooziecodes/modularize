# handlers/onboarding.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from utils.localization import get_text
from utils.firebase_client import get_user_language, get_profile, save_profile

# Define conversation states
INCOME, GOAL, DEBT, FAMILY, CONFIRMATION = range(5)

# Configure logging
logger = logging.getLogger(__name__)

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the onboarding process to collect user profile information."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    # Start with income question
    await ask_income(update, context, lang_code)
    return INCOME

async def ask_income(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_code: str) -> None:
    """Asks for the user's income range."""
    keyboard = [
        [InlineKeyboardButton(get_text("income_option_1", lang_code), callback_data="income_1")],
        [InlineKeyboardButton(get_text("income_option_2", lang_code), callback_data="income_2")],
        [InlineKeyboardButton(get_text("income_option_3", lang_code), callback_data="income_3")],
        [InlineKeyboardButton(get_text("income_option_4", lang_code), callback_data="income_4")],
        [InlineKeyboardButton(get_text("income_option_5", lang_code), callback_data="income_5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    prompt = get_text("income_question", lang_code)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=prompt, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=prompt, reply_markup=reply_markup)

async def income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles income selection and asks about financial goals."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    # Save income selection
    income_level = query.data.split('_')[1]
    context.user_data['profile_income'] = income_level
    
    # Now ask about financial goals
    keyboard = [
        [InlineKeyboardButton(get_text("goal_option_1", lang_code), callback_data="goal_1")],
        [InlineKeyboardButton(get_text("goal_option_2", lang_code), callback_data="goal_2")],
        [InlineKeyboardButton(get_text("goal_option_3", lang_code), callback_data="goal_3")],
        [InlineKeyboardButton(get_text("goal_option_4", lang_code), callback_data="goal_4")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    prompt = get_text("goal_question", lang_code)
    await query.edit_message_text(text=prompt, reply_markup=reply_markup)
    
    return GOAL

async def goal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles goal selection and asks about debt situation."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    # Save goal selection
    goal_type = query.data.split('_')[1]
    context.user_data['profile_goal'] = goal_type
    
    # Now ask about debt
    keyboard = [
        [InlineKeyboardButton(get_text("debt_option_1", lang_code), callback_data="debt_1")],
        [InlineKeyboardButton(get_text("debt_option_2", lang_code), callback_data="debt_2")],
        [InlineKeyboardButton(get_text("debt_option_3", lang_code), callback_data="debt_3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    prompt = get_text("debt_question", lang_code)
    await query.edit_message_text(text=prompt, reply_markup=reply_markup)
    
    return DEBT

async def debt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles debt selection and asks about family financial responsibilities."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    # Save debt selection
    debt_level = query.data.split('_')[1]
    context.user_data['profile_debt'] = debt_level
    
    # Now ask about family responsibilities
    keyboard = [
        [InlineKeyboardButton(get_text("family_option_1", lang_code), callback_data="family_1")],
        [InlineKeyboardButton(get_text("family_option_2", lang_code), callback_data="family_2")],
        [InlineKeyboardButton(get_text("family_option_3", lang_code), callback_data="family_3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    prompt = get_text("family_question", lang_code)
    await query.edit_message_text(text=prompt, reply_markup=reply_markup)
    
    return FAMILY

async def family_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles family selection and asks for confirmation."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    # Save family selection
    family_support = query.data.split('_')[1]
    context.user_data['profile_family'] = family_support
    
    # Show summary and ask for confirmation
    profile_summary = get_text("profile_summary", lang_code).format(
        income=get_text(f"income_option_{context.user_data['profile_income']}", lang_code),
        goal=get_text(f"goal_option_{context.user_data['profile_goal']}", lang_code),
        debt=get_text(f"debt_option_{context.user_data['profile_debt']}", lang_code),
        family=get_text(f"family_option_{context.user_data['profile_family']}", lang_code)
    )
    
    keyboard = [
        [
            InlineKeyboardButton(get_text("confirm_yes", lang_code), callback_data="confirm_yes"),
            InlineKeyboardButton(get_text("confirm_no", lang_code), callback_data="confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=profile_summary, reply_markup=reply_markup)
    
    return CONFIRMATION

async def confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the final confirmation of the profile."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    if query.data == "confirm_yes":
        # Save the profile to Firebase
        profile_data = {
            'income': context.user_data['profile_income'],
            'goal': context.user_data['profile_goal'],
            'debt': context.user_data['profile_debt'],
            'family': context.user_data['profile_family']
        }
        save_profile(user_id, profile_data)
        
        # Thank the user and show the main menu
        thank_text = get_text("profile_saved", lang_code)
        await query.edit_message_text(text=thank_text)
        
        # Clean up user_data
        for key in list(context.user_data.keys()):
            if key.startswith('profile_'):
                del context.user_data[key]
        
        # Show main menu
        from handlers.common import show_main_menu
        await show_main_menu(update, context, lang_code)
        
        return ConversationHandler.END
    else:
        # User wants to restart
        restart_text = get_text("profile_restart", lang_code)
        await query.edit_message_text(text=restart_text)
        
        # Start over
        await ask_income(update, context, lang_code)
        return INCOME

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    # Clean up user_data
    for key in list(context.user_data.keys()):
        if key.startswith('profile_'):
            del context.user_data[key]
    
    cancel_text = get_text("onboarding_cancelled", lang_code)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=cancel_text)
    else:
        await update.message.reply_text(text=cancel_text)
    
    return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the user's profile or starts onboarding if no profile exists."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    profile = get_profile(user_id)
    
    if not profile:
        # No profile found, start onboarding
        start_text = get_text("profile_not_found", lang_code)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text=start_text)
            await ask_income(update, context, lang_code)
        else:
            await update.message.reply_text(text=start_text)
            await ask_income(update, context, lang_code)
    else:
        # Show existing profile
        profile_text = get_text("profile_summary", lang_code).format(
            income=get_text(f"income_option_{profile.get('income', '1')}", lang_code),
            goal=get_text(f"goal_option_{profile.get('goal', '1')}", lang_code),
            debt=get_text(f"debt_option_{profile.get('debt', '1')}", lang_code),
            family=get_text(f"family_option_{profile.get('family', '1')}", lang_code)
        )
        
        keyboard = [
            [InlineKeyboardButton(get_text("update_profile", lang_code), callback_data="start_onboarding")],
            [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text=profile_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text=profile_text, reply_markup=reply_markup)

# Create the onboarding conversation handler
onboarding_handler = ConversationHandler(
    entry_points=[
        CommandHandler('profile', start_onboarding),
        CallbackQueryHandler(start_onboarding, pattern='^start_onboarding$')
    ],
    states={
        INCOME: [CallbackQueryHandler(income_callback, pattern='^income_')],
        GOAL: [CallbackQueryHandler(goal_callback, pattern='^goal_')],
        DEBT: [CallbackQueryHandler(debt_callback, pattern='^debt_')],
        FAMILY: [CallbackQueryHandler(family_callback, pattern='^family_')],
        CONFIRMATION: [CallbackQueryHandler(confirmation_callback, pattern='^confirm_')]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)