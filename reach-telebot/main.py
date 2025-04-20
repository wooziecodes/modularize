# main.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import config
from handlers import common, onboarding, goals, expenses, advice

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    logger.info("Starting REACH-telebot...")

    # Initialize services
    try:
        from utils.firebase_client import initialize_firebase
        from utils.openai_client import initialize_openai
        initialize_firebase()
        initialize_openai()
    except Exception as e:
        logger.critical(f"Failed to initialize critical services: {e}", exc_info=True)
        return

    # Create the Application and pass it your bot's token
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register common handlers
    application.add_handler(common.start_handler)
    application.add_handler(common.menu_handler)
    application.add_handler(common.language_callback_handler)
    application.add_handler(common.menu_callback_handler)
    
    # Register conversation handlers
    # Goals handler should go first to make sure it catches all income assessment callbacks
    application.add_handler(goals.goal_handler)
    application.add_handler(onboarding.onboarding_handler)
    
    # Register command handlers
    application.add_handler(CommandHandler('log', expenses.log_expense_command))
    application.add_handler(CommandHandler('view_expenses', expenses.view_expenses))
    application.add_handler(CommandHandler('ask', advice.ask_advice_command))
    application.add_handler(CommandHandler('view_goal', goals.view_goal))
    
    # Register callback handlers
    application.add_handler(expenses.expense_callback_handler)
    application.add_handler(advice.advice_category_handler)
    application.add_handler(advice.advice_callback_handler)
    
    # Add standalone handlers for goal flow
    application.add_handler(CallbackQueryHandler(goals.goal_type_standalone_callback, pattern='^goal_type_'))
    application.add_handler(CallbackQueryHandler(goals.goal_deadline_callback, pattern='^deadline_'))
    application.add_handler(CallbackQueryHandler(goals.goal_steps_callback, pattern='^steps_'))
    application.add_handler(CallbackQueryHandler(goals.goal_confirmation_callback, pattern='^goal_confirm_'))
    application.add_handler(CallbackQueryHandler(goals.goal_suggestion_callback, pattern='^goal_sugg_'))
    application.add_handler(CallbackQueryHandler(goals.share_goal_with_family, pattern='^share_goal_with_family'))
    
    # Add standalone handlers for onboarding flow and new goal assessment flow
    # Note: Income callback is used in both onboarding and goal setting flow
    # The income callback for goal flow has a specific handler in the ConversationHandler
    application.add_handler(CallbackQueryHandler(onboarding.income_callback, pattern='^income_[1-5]$'))
    application.add_handler(CallbackQueryHandler(goals.family_assessment_callback, pattern='^family_needs_'))
    application.add_handler(CallbackQueryHandler(goals.spending_assessment_callback, pattern='^spending_'))
    application.add_handler(CallbackQueryHandler(onboarding.goal_callback, pattern='^goal_[1-4]$'))
    application.add_handler(CallbackQueryHandler(onboarding.debt_callback, pattern='^debt_'))
    application.add_handler(CallbackQueryHandler(onboarding.family_callback, pattern='^family_'))
    application.add_handler(CallbackQueryHandler(onboarding.confirmation_callback, pattern='^confirm_'))
    
    # Handler for unhandled callbacks
    async def unhandled_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        logger.warning(f"Unhandled callback pattern: {query.data}")
        
    application.add_handler(CallbackQueryHandler(unhandled_callback))
    
    # Custom message handler for goal amount
    async def custom_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles text messages for both goal amount and regular messages."""
        conversation_state = context.user_data.get('conversation_state')
        logger.info(f"Current conversation state: {conversation_state}")
        
        if conversation_state == goals.GOAL_AMOUNT:
            logger.info("Detected goal amount message")
            await goals.goal_amount_handler(update, context)
        elif conversation_state == goals.GOAL_STEPS:
            logger.info("Detected goal steps message")
            await goals.goal_custom_steps_handler(update, context)
        elif conversation_state == goals.MICRO_GOALS:
            logger.info("Detected micro goal message")
            # This is for handling any specific micro-goal inputs if needed later
            await handle_text_message(update, context)
        else:
            await handle_text_message(update, context)
            
    # Register message handlers
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & 
        filters.ChatType.PRIVATE, 
        custom_text_handler
    ))
    
    # Error handler
    application.add_error_handler(common.error_handler)

    # Start the Bot
    logger.info("Bot is running...")
    application.run_polling()

async def handle_text_message(update, context):
    """Route text messages to the appropriate handler based on context."""
    # Check for expense logging
    if context.user_data.get("expecting_expense"):
        await expenses.handle_expense_message(update, context)
    # Check for advice question
    elif context.user_data.get("expecting_advice_question"):
        await advice.handle_advice_question(update, context)
    # Default: show help message
    else:
        user_id = update.effective_user.id
        from utils.firebase_client import get_user_language
        lang_code = get_user_language(user_id)
        from utils.localization import get_text
        help_text = get_text("error_generic", lang_code)
        await update.message.reply_text(help_text)

if __name__ == '__main__':
    main() 