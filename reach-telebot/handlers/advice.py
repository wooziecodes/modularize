# handlers/advice.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from utils.localization import get_text
from utils.firebase_client import get_user_language, get_profile, get_goals, get_expenses
from utils.openai_client import get_ai_advice

# Configure logging
logger = logging.getLogger(__name__)

async def ask_advice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to get AI-powered financial advice."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    # Check if there are arguments
    if context.args:
        # Use arguments as the question
        question = ' '.join(context.args)
        await generate_advice(update, context, question)
    else:
        # Show advice categories
        await show_advice_categories(update, context)

async def show_advice_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows financial advice categories."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    keyboard = [
        [InlineKeyboardButton(get_text("advice_category_savings", lang_code), callback_data="advice_savings")],
        [InlineKeyboardButton(get_text("advice_category_debt", lang_code), callback_data="advice_debt")],
        [InlineKeyboardButton(get_text("advice_category_remittance", lang_code), callback_data="advice_remittance")],
        [InlineKeyboardButton(get_text("advice_category_budget", lang_code), callback_data="advice_budget")],
        [InlineKeyboardButton(get_text("advice_category_custom", lang_code), callback_data="advice_custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    prompt = get_text("advice_category_prompt", lang_code)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=prompt, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=prompt, reply_markup=reply_markup)

async def advice_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles advice category selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    category = query.data.split('_')[1]
    
    if category == "custom":
        # Ask for custom question
        prompt = get_text("enter_advice_question", lang_code)
        await query.edit_message_text(text=prompt)
        context.user_data["expecting_advice_question"] = True
    else:
        # Generate advice for pre-defined category
        if category == "savings":
            question = get_text("advice_question_savings", lang_code)
        elif category == "debt":
            question = get_text("advice_question_debt", lang_code)
        elif category == "remittance":
            question = get_text("advice_question_remittance", lang_code)
        elif category == "budget":
            question = get_text("advice_question_budget", lang_code)
        else:
            question = get_text("advice_question_general", lang_code)
        
        # Show thinking message
        thinking_text = get_text("ai_thinking", lang_code)
        await query.edit_message_text(text=thinking_text)
        
        # Generate and show advice
        await generate_advice_from_callback(update, context, question)

async def handle_advice_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles a custom advice question when the user is expected to enter one."""
    if context.user_data.get("expecting_advice_question"):
        # Process the question
        question = update.message.text
        await generate_advice(update, context, question)
        # Reset the flag
        context.user_data["expecting_advice_question"] = False

async def generate_advice(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
    """Generates AI advice based on the question and user profile."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    # Show thinking message
    thinking_text = get_text("ai_thinking", lang_code)
    thinking_message = await update.message.reply_text(text=thinking_text)
    
    # Get user profile data
    profile = get_profile(user_id)
    goals = get_goals(user_id)
    expenses = get_expenses(user_id)[:10]  # Get only the 10 most recent expenses
    
    # Build context for AI
    ai_context = _build_ai_context(profile, goals, expenses, question, lang_code)
    
    # Get advice from OpenAI
    advice = get_ai_advice(ai_context, lang_code)
    
    # Add buttons for follow-up actions
    keyboard = [
        [InlineKeyboardButton(get_text("ask_another", lang_code), callback_data="advice_another")],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Edit the thinking message with the advice
    await thinking_message.edit_text(text=advice, reply_markup=reply_markup)

async def generate_advice_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
    """Generates AI advice for callback queries."""
    user_id = update.callback_query.from_user.id
    lang_code = get_user_language(user_id)
    
    # Get user profile data
    profile = get_profile(user_id)
    goals = get_goals(user_id)
    expenses = get_expenses(user_id)[:10]  # Get only the 10 most recent expenses
    
    # Build context for AI
    ai_context = _build_ai_context(profile, goals, expenses, question, lang_code)
    
    # Get advice from OpenAI
    advice = get_ai_advice(ai_context, lang_code)
    
    # Add buttons for follow-up actions
    keyboard = [
        [InlineKeyboardButton(get_text("ask_another", lang_code), callback_data="advice_another")],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Edit the thinking message with the advice
    await update.callback_query.edit_message_text(text=advice, reply_markup=reply_markup)

def _build_ai_context(profile: dict, goals: list, expenses: list, question: str, lang_code: str) -> str:
    """Builds a context string for the AI based on user data."""
    context = f"Question: {question}\n\n"
    
    # Add profile information if available
    if profile:
        context += "User Profile:\n"
        if 'income' in profile:
            context += f"- Income Level: {profile['income']}\n"
        if 'goal' in profile:
            context += f"- Financial Goal: {profile['goal']}\n"
        if 'debt' in profile:
            context += f"- Debt Level: {profile['debt']}\n"
        if 'family' in profile:
            context += f"- Family Responsibilities: {profile['family']}\n"
        context += "\n"
    
    # Add active goals if available
    if goals:
        context += "Financial Goals:\n"
        for i, goal in enumerate(goals):
            context += f"Goal {i+1}:\n"
            if 'type' in goal:
                context += f"- Type: {goal['type']}\n"
            if 'amount' in goal:
                context += f"- Target Amount: {goal['amount']}\n"
            if 'deadline' in goal:
                context += f"- Deadline: {goal['deadline']}\n"
            if 'progress' in goal:
                context += f"- Current Progress: {goal['progress']}\n"
            context += "\n"
    
    # Add recent expenses if available
    if expenses:
        context += "Recent Expenses:\n"
        for expense in expenses:
            if 'amount' in expense and 'category' in expense:
                context += f"- {expense.get('amount', 0)} {expense.get('currency', '')} for {expense.get('category', 'Other')}"
                if 'description' in expense:
                    context += f" ({expense['description']})"
                context += "\n"
        context += "\n"
    
    # Add language information
    context += f"Please respond in the {lang_code} language. Provide practical, culturally sensitive financial advice for a migrant worker based on the information above."
    
    return context

async def advice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles advice-related callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    if query.data == "advice_another":
        # Show advice categories again
        await show_advice_categories(update, context)
    
    elif query.data == "back_to_menu":
        # Show main menu
        from handlers.common import show_main_menu
        await show_main_menu(update, context, lang_code)

# Register handlers
advice_category_handler = CallbackQueryHandler(advice_category_callback, pattern='^advice_')
advice_callback_handler = CallbackQueryHandler(advice_callback, pattern='^(advice_another|back_to_menu)$')