# handlers/expenses.py
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from utils.localization import get_text
from utils.firebase_client import get_user_language, save_expense, get_expenses
from utils.openai_client import parse_expense

# Configure logging
logger = logging.getLogger(__name__)

async def log_expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to log an expense."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    # Check if there are arguments
    if context.args:
        # Try to parse expense from command arguments
        expense_text = ' '.join(context.args)
        await process_expense_text(update, context, expense_text)
    else:
        # Ask user to enter expense details
        prompt = get_text("enter_expense", lang_code)
        await update.message.reply_text(text=prompt)
        context.user_data["expecting_expense"] = True

async def handle_expense_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles an expense message when the user is expected to enter one."""
    if context.user_data.get("expecting_expense"):
        # Process the expense text
        expense_text = update.message.text
        await process_expense_text(update, context, expense_text)
        # Reset the flag
        context.user_data["expecting_expense"] = False

async def process_expense_text(update: Update, context: ContextTypes.DEFAULT_TYPE, expense_text: str) -> None:
    """Processes expense text and saves it to Firebase."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    # Use OpenAI to parse the expense
    expense_data = parse_expense(expense_text, lang_code)
    
    if "error" in expense_data:
        # Failed to parse expense
        error_message = get_text("expense_parse_error", lang_code)
        await update.message.reply_text(text=error_message)
        return
    
    # Add timestamp and user ID
    expense_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save the expense
    save_expense(user_id, expense_data)
    
    # Confirm to the user
    amount = expense_data.get("amount", 0)
    currency = expense_data.get("currency", "")
    category = expense_data.get("category", "")
    description = expense_data.get("description", "")
    
    confirmation = get_text("expense_saved", lang_code).format(
        amount=amount,
        currency=currency,
        category=category,
        description=description
    )
    
    # Add buttons to add another expense or view all expenses
    keyboard = [
        [InlineKeyboardButton(get_text("log_another_expense", lang_code), callback_data="log_another_expense")],
        [InlineKeyboardButton(get_text("view_expenses", lang_code), callback_data="menu_view_expenses")],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text=confirmation, reply_markup=reply_markup)

async def view_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to view all expenses."""
    await show_expenses(update, context)

async def show_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the user's expenses."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    expenses = get_expenses(user_id)
    
    if not expenses:
        # No expenses found
        no_expenses_text = get_text("no_expenses", lang_code)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text=no_expenses_text)
        else:
            await update.message.reply_text(text=no_expenses_text)
        return
    
    # Calculate total and organize by category
    total = 0
    categories = {}
    
    for expense in expenses:
        amount = expense.get("amount", 0)
        currency = expense.get("currency", "")
        category = expense.get("category", "Other")
        
        total += amount
        
        if category not in categories:
            categories[category] = 0
        categories[category] += amount
    
    # Format expenses summary
    expenses_text = get_text("expenses_summary", lang_code).format(
        count=len(expenses),
        total=total,
        currency=expenses[0].get("currency", "") if expenses else ""
    )
    
    # Add category breakdown
    expenses_text += "\n\n" + get_text("expenses_by_category", lang_code) + "\n"
    
    for category, amount in categories.items():
        expenses_text += f"{category}: {amount}\n"
    
    # Add recent expenses (last 5)
    if len(expenses) > 0:
        expenses_text += "\n" + get_text("recent_expenses", lang_code) + "\n"
        
        for expense in reversed(expenses[-5:]): # Show last 5 expenses in reverse order (newest first)
            date = expense.get("timestamp", "").split(" ")[0] if "timestamp" in expense else ""
            amount = expense.get("amount", 0)
            currency = expense.get("currency", "")
            category = expense.get("category", "")
            description = expense.get("description", "")
            
            expenses_text += f"{date}: {amount} {currency} - {category} ({description})\n"
    
    # Add action buttons
    keyboard = [
        [InlineKeyboardButton(get_text("log_expense", lang_code), callback_data="log_another_expense")],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=expenses_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=expenses_text, reply_markup=reply_markup)

async def expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles expense-related callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    if query.data == "log_another_expense":
        # Ask user to enter expense details
        prompt = get_text("enter_expense", lang_code)
        await query.edit_message_text(text=prompt)
        context.user_data["expecting_expense"] = True
    
    elif query.data == "menu_view_expenses":
        # Show expenses
        await show_expenses(update, context)
    
    elif query.data == "back_to_menu":
        # Show main menu
        from handlers.common import show_main_menu
        await show_main_menu(update, context, lang_code)

# Register handlers
expense_callback_handler = CallbackQueryHandler(expense_callback, pattern='^(log_another_expense|menu_view_expenses|back_to_menu)$')