# handlers/goals.py
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
from utils.localization import get_text
from utils.firebase_client import get_user_language, save_goal, get_goals
from utils.openai_client import get_behavioral_goal_suggestions

# Define conversation states
INCOME_ASSESSMENT, FAMILY_ASSESSMENT, SPENDING_ASSESSMENT, GOAL_TYPE, GOAL_AMOUNT, GOAL_DEADLINE, GOAL_STEPS, GOAL_CONFIRMATION, MICRO_GOALS = range(9)

# Configure logging
logger = logging.getLogger(__name__)

async def start_goal_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the enhanced goal setting process with multiple assessments for context."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    logger.info(f"====== STARTING GOAL SETTING FLOW for user {user_id} ======")
    logger.info(f"🔍 This should lead through: income → family → spending → personalized goals")
    
    # Check if the function was called directly or via a callback
    if update.callback_query:
        logger.info(f"👉 Called via callback: {update.callback_query.data}")
    else:
        logger.info(f"👉 Called directly via command")
    
    # Clear any previous goal data to start fresh
    for key in list(context.user_data.keys()):
        if key.startswith('goal_'):
            del context.user_data[key]
    
    # Start with income assessment to make goals more contextual
    keyboard = [
        [InlineKeyboardButton(get_text("income_option_1", lang_code), callback_data="income_1")],
        [InlineKeyboardButton(get_text("income_option_2", lang_code), callback_data="income_2")],
        [InlineKeyboardButton(get_text("income_option_3", lang_code), callback_data="income_3")],
        [InlineKeyboardButton(get_text("income_option_4", lang_code), callback_data="income_4")],
        [InlineKeyboardButton(get_text("income_option_5", lang_code), callback_data="income_5")],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    logger.info(f"Creating income assessment keyboard for goal setting")
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Add an emoji and behavioral science explanation about income context
    prompt = get_text("income_question_behavioral", lang_code)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=prompt, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=prompt, reply_markup=reply_markup)
    
    return INCOME_ASSESSMENT

async def income_assessment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles income selection and proceeds to family needs assessment."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    logger.info(f"⭐ INCOME ASSESSMENT CALLBACK TRIGGERED: {query.data}")
    logger.info(f"👉 This should now proceed to family assessment")
    
    # Debug the user's current state
    logger.info(f"Current conversation state: {context.user_data.get('conversation_state')}")
    logger.info(f"User data keys: {list(context.user_data.keys())}")
    
    # Save income level
    income_level = int(query.data.split('_')[1])
    context.user_data['income_level'] = income_level
    
    # Store income text description for OpenAI context
    income_options = {
        1: "Less than $500 per month",
        2: "$500-1000 per month", 
        3: "$1000-1500 per month",
        4: "$1500-2000 per month",
        5: "More than $2000 per month"
    }
    context.user_data['income_text'] = income_options.get(income_level)
    
    # Create keyboard with family needs assessment options
    keyboard = [
        [InlineKeyboardButton(get_text("family_option_1", lang_code), callback_data="family_needs_1")],
        [InlineKeyboardButton(get_text("family_option_2", lang_code), callback_data="family_needs_2")],
        [InlineKeyboardButton(get_text("family_option_3", lang_code), callback_data="family_needs_3")],
        [InlineKeyboardButton(get_text("family_option_4", lang_code), callback_data="family_needs_4")],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    logger.info(f"Creating family needs assessment keyboard")
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show behaviorally-informed prompt based on income level
    income_prompt = ""
    if income_level <= 2:  # Lower income levels
        income_prompt = get_text("family_question_low_income", lang_code)
    else:  # Higher income levels
        income_prompt = get_text("family_question_high_income", lang_code)
        
    await query.edit_message_text(text=income_prompt, reply_markup=reply_markup)
    
    return FAMILY_ASSESSMENT

async def family_assessment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles family needs assessment and moves to spending patterns."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    logger.info(f"Family needs assessment callback: {query.data}")
    
    # Save family needs information
    family_option = int(query.data.split('_')[-1])
    context.user_data['family_needs'] = family_option
    
    # Store family text description for OpenAI context
    family_options = {
        1: "Single, no dependents",
        2: "Supporting family in Singapore", 
        3: "Sending money to family in home country",
        4: "Supporting children's education"
    }
    context.user_data['family_text'] = family_options.get(family_option)
    
    # Create keyboard with spending patterns assessment
    keyboard = [
        [InlineKeyboardButton(get_text("spending_option_1", lang_code), callback_data="spending_1")],
        [InlineKeyboardButton(get_text("spending_option_2", lang_code), callback_data="spending_2")],
        [InlineKeyboardButton(get_text("spending_option_3", lang_code), callback_data="spending_3")],
        [InlineKeyboardButton(get_text("spending_option_4", lang_code), callback_data="spending_4")],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    logger.info(f"Creating spending assessment keyboard")
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show behaviorally-informed prompt based on family needs
    spending_prompt = get_text("spending_question", lang_code)
    
    # Add family-specific context
    if family_option == 3:  # Sending money home
        spending_prompt += "\n\n" + get_text("spending_context_remittance", lang_code)
    elif family_option == 4:  # Education
        spending_prompt += "\n\n" + get_text("spending_context_education", lang_code)
        
    await query.edit_message_text(text=spending_prompt, reply_markup=reply_markup)
    
    return SPENDING_ASSESSMENT

async def spending_assessment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles spending assessment and gets contextual goal suggestions using behavioral science."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    logger.info(f"Spending assessment callback: {query.data}")
    
    # Save spending pattern information
    spending_option = int(query.data.split('_')[-1])
    context.user_data['spending_pattern'] = spending_option
    
    # Store spending text description for OpenAI context
    spending_options = {
        1: "Saves regularly with discipline",
        2: "Sends most income to family", 
        3: "Spends as needed, some impulse purchases",
        4: "Struggles to make income last until next payday"
    }
    context.user_data['spending_text'] = spending_options.get(spending_option)
    
    # Notify user we're generating personalized goals
    processing_text = get_text("generating_personalized_goals", lang_code)
    await query.edit_message_text(text=processing_text)
    
    # Gather all context for OpenAI
    income_text = context.user_data.get('income_text', "Income information not provided")
    family_text = context.user_data.get('family_text', "Family information not provided")
    spending_text = context.user_data.get('spending_text', "Spending information not provided")
    
    # Additional migrant worker context
    current_situation = "Migrant worker in Singapore. Likely uses cash for most transactions. May send money home through remittance services. Possibly has limited financial literacy and banking access."
    
    logger.info(f"Getting behavioral goal suggestions for user {user_id}")
    logger.info(f"Context - Income: {income_text}, Family: {family_text}, Spending: {spending_text}")
    
    # Get personalized goal suggestions from OpenAI as originally intended
    try:
        logger.info("⭐⭐⭐ ATTEMPTING TO GET PERSONALIZED GOAL SUGGESTIONS FROM OPENAI ⭐⭐⭐")
        # Call OpenAI for personalized suggestions using the behavioral science context
        goal_suggestions = get_behavioral_goal_suggestions(
            income=income_text,
            family_needs=family_text,
            current_situation=f"{spending_text}. {current_situation}",
            lang_code=lang_code
        )
        logger.info(f"Received {len(goal_suggestions)} goal suggestions from OpenAI")
        # Log the actual suggestions for debugging
        logger.info(f"Suggestion details: {goal_suggestions}")
        
        # If OpenAI fails to provide suggestions, log error and raise exception
        if not goal_suggestions:
            logger.error("OpenAI returned empty suggestions")
            raise Exception("Failed to get goal suggestions from OpenAI")
        
        # Store suggestions for later use
        context.user_data['goal_suggestions'] = goal_suggestions
        logger.info(f"Created {len(goal_suggestions)} contextual goal suggestions")
        
        # Create keyboard with suggested goals
        keyboard = []
        for i, suggestion in enumerate(goal_suggestions):
            goal_name = suggestion.get('goal')
            # Generate a more distinctive callback pattern
            goal_id = f"goal_sugg_{i}"
            
            # Format button text with emoji prefix based on goal type
            if "Emergency" in goal_name or "Sav" in goal_name:
                emoji = "💰"
            elif "Remittance" in goal_name or "home" in goal_name or "Family" in goal_name:
                emoji = "🏠"
            elif "Education" in goal_name or "School" in goal_name:
                emoji = "📚"
            elif "Health" in goal_name or "Medical" in goal_name:
                emoji = "❤️"
            elif "Payday" in goal_name or "Budget" in goal_name:
                emoji = "📊"
            elif "No-Spend" in goal_name:
                emoji = "🛑"
            else:
                emoji = "🎯"
                
            # Create button with emoji and goal name
            button_text = f"{emoji} {goal_name}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=goal_id)])
            logger.info(f"Added suggestion button with callback: {goal_id}")
        
        # Add custom goal option at the bottom
        keyboard.append([InlineKeyboardButton(get_text("custom_goal_option", lang_code), callback_data="goal_custom")])
        logger.info("Added custom goal option with callback: goal_custom")
        keyboard.append([InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Show goal suggestions with behavioral science context
        goal_prompt = get_text("goal_suggestions_prompt", lang_code)
        
        # Add behavioral science explanation about why these goals are suggested
        behavioral_context = get_text("goal_behavioral_context", lang_code)
        
        logger.info(f"Showing goal suggestions with callbacks: {[btn[0].callback_data for btn in keyboard if len(btn) > 0]}")
        await query.edit_message_text(text=f"{goal_prompt}\n\n{behavioral_context}", reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"❌❌❌ ERROR GETTING PERSONALIZED GOALS: {type(e).__name__}: {e}", exc_info=True)
        logger.error(f"User context data: {context.user_data}")
        # Fallback to default goal types if OpenAI integration fails
        keyboard = [
            [InlineKeyboardButton(get_text("family_goal_savings", lang_code), callback_data="goal_type_savings")],
            [InlineKeyboardButton(get_text("family_goal_remittance", lang_code), callback_data="goal_type_remittance")],
            [InlineKeyboardButton(get_text("family_goal_education", lang_code), callback_data="goal_type_education")],
            [InlineKeyboardButton(get_text("family_goal_health", lang_code), callback_data="goal_type_health")],
            [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        prompt = get_text("family_goal_question", lang_code)
        await query.edit_message_text(text=prompt, reply_markup=reply_markup)
    
    return GOAL_TYPE

async def goal_suggestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles selection of a suggested goal from OpenAI."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    logger.info(f"Goal suggestion callback: {query.data}")
    
    # Get the selected suggestion index from callback data like 'goal_sugg_0'
    try:
        # Extract the number at the end (the suggestion index)
        suggestion_index = int(query.data.split('_')[-1])
        logger.info(f"Selected suggestion index: {suggestion_index}")
        goal_suggestions = context.user_data.get('goal_suggestions', [])
        logger.info(f"Available goal suggestions: {len(goal_suggestions)}")
        
        # Check if we have this suggestion in our context data
        if not goal_suggestions:
            logger.warning(f"No goal suggestions found in context for callback: {query.data}")
            # Debugging: print all user context data
            logger.info(f"User context keys: {list(context.user_data.keys())}")
            return await goal_type_callback(update, context)
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing suggestion index from {query.data}: {e}")
        return await goal_type_callback(update, context)
    
    if suggestion_index < len(goal_suggestions):
        selected_goal = goal_suggestions[suggestion_index]
        
        # Save goal information
        goal_name = selected_goal.get('goal', "Custom Goal")
        goal_description = selected_goal.get('description', "")
        goal_rationale = selected_goal.get('rationale', "")
        
        # Determine the goal type based on the name for compatibility with existing code
        if any(word in goal_name.lower() for word in ["emergency", "save", "saving"]):
            goal_type = "savings"
        elif any(word in goal_name.lower() for word in ["send", "home", "remit"]):
            goal_type = "remittance"
        elif any(word in goal_name.lower() for word in ["education", "school", "learn"]):
            goal_type = "education"
        elif any(word in goal_name.lower() for word in ["health", "medical", "hospital"]):
            goal_type = "health"
        else:
            goal_type = "savings"  # Default fallback
            
        # Save in context
        context.user_data['goal_type'] = goal_type
        context.user_data['goal_name'] = goal_name
        context.user_data['goal_description'] = goal_description
        context.user_data['goal_rationale'] = goal_rationale
        
        # Show why this goal matters with behavioral science context
        rationale_text = get_text("goal_rationale_prefix", lang_code) + " " + goal_rationale
        
        # Ask for amount with context from the selected goal
        prompt = get_text(f"goal_amount_question_{goal_type}", lang_code) + "\n\n" + rationale_text
        await query.edit_message_text(text=prompt)
        
        return GOAL_AMOUNT
    else:
        # Fallback if we can't find the suggestion
        await goal_type_callback(update, context)
        return GOAL_TYPE

async def goal_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles goal type selection and asks for amount."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    logger.info(f"Goal type callback: {query.data}")
    
    # Check if this is a custom goal selection
    if query.data == "goal_custom":
        # Show standard goal type options
        keyboard = [
            [InlineKeyboardButton(get_text("family_goal_savings", lang_code), callback_data="goal_type_savings")],
            [InlineKeyboardButton(get_text("family_goal_remittance", lang_code), callback_data="goal_type_remittance")],
            [InlineKeyboardButton(get_text("family_goal_education", lang_code), callback_data="goal_type_education")],
            [InlineKeyboardButton(get_text("family_goal_health", lang_code), callback_data="goal_type_health")],
            [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        prompt = get_text("custom_goal_prompt", lang_code)
        await query.edit_message_text(text=prompt, reply_markup=reply_markup)
        return GOAL_TYPE
    
    # Handle standard goal type selection
    if query.data.startswith("goal_type_"):
        # Save goal type
        goal_type = query.data.split('_')[-1]
        context.user_data['goal_type'] = goal_type
        
        # Provide more context based on goal type and income
        income_level = context.user_data.get('income_level', 3)  # Default to middle income if not set
        family_needs = context.user_data.get('family_needs', 1)  # Default to single
        
        # Customize context based on user's situation
        context_text = ""
        if goal_type == "savings":
            if income_level <= 2:
                context_text = "💡 Even saving $10 each payday builds security for your family."
            else:
                context_text = "💡 Try saving 10-15% of each paycheck for emergencies."
        elif goal_type == "remittance":
            if family_needs == 3:  # Sending money home
                context_text = "💡 Setting a regular amount to send home helps both you and your family plan better."
            else:
                context_text = "💡 Sending money regularly? Consider setting aside a fixed percentage each month."
        elif goal_type == "education":
            context_text = "💡 Education is a great investment for your family's future."
        elif goal_type == "health":
            context_text = "💡 Health savings protect your ability to work and support your family."
        
        # Ask for amount with context
        prompt = get_text(f"goal_amount_question_{goal_type}", lang_code) + "\n\n" + context_text
        await query.edit_message_text(text=prompt)
        
        return GOAL_AMOUNT
    else:
        # Handle goal suggestion selection (callback pattern starts with 'goal_sugg_')
        if query.data.startswith('goal_sugg_'):
            logger.info(f"Redirecting to goal_suggestion_callback for {query.data}")
            return await goal_suggestion_callback(update, context)
        
        # If we get here, it's an unhandled callback
        logger.warning(f"Unhandled goal type callback: {query.data}")
        return GOAL_TYPE

async def goal_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles goal amount entry and asks for deadline."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    logger.info(f"Handling goal amount for user {user_id}")
    
    # Try to parse the amount
    try:
        amount_text = update.message.text.strip()
        # Remove currency symbols and commas if present
        amount_text = amount_text.replace("$", "").replace("€", "").replace(",", "").replace("USD", "").strip()
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Save goal amount
        context.user_data['goal_amount'] = amount
        logger.info(f"Parsed amount: {amount}")
        
        # Calculate monthly amount needed based on goal type
        goal_type = context.user_data.get('goal_type', 'savings')
        income_level = context.user_data.get('income_level', 3)
        
        # Provide contextual deadline options based on amount and income level
        keyboard = []
        
        # For smaller goals or lower income, offer shorter timeframes
        if amount < 500 or income_level <= 2:
            keyboard.append([InlineKeyboardButton("🗓️ " + get_text("deadline_next_payday", lang_code), callback_data="deadline_0.5")])
            keyboard.append([InlineKeyboardButton("🗓️ " + get_text("deadline_1month", lang_code), callback_data="deadline_1")])
            keyboard.append([InlineKeyboardButton("🗓️ " + get_text("deadline_3months", lang_code), callback_data="deadline_3")])
        else:
            keyboard.append([InlineKeyboardButton("🗓️ " + get_text("deadline_1month", lang_code), callback_data="deadline_1")])
            keyboard.append([InlineKeyboardButton("🗓️ " + get_text("deadline_3months", lang_code), callback_data="deadline_3")])
            keyboard.append([InlineKeyboardButton("🗓️ " + get_text("deadline_6months", lang_code), callback_data="deadline_6")])
            keyboard.append([InlineKeyboardButton("🗓️ " + get_text("deadline_1year", lang_code), callback_data="deadline_12")])
        
        keyboard.append([InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Calculate monthly savings needed and provide as context
        monthly_calculation = ""
        if amount > 100:
            if "deadline_0.5" in str(keyboard):
                monthly_calculation = f"💵 Need to save {amount} in 2 weeks = about {amount/2:.0f} per week"
            else:
                monthly_calculation = f"💵 Need to save {amount} in 1 month = about {amount/4:.0f} per week"
        
        prompt = get_text("goal_deadline_question", lang_code) + "\n\n" + monthly_calculation
        await update.message.reply_text(text=prompt, reply_markup=reply_markup)
        
        # Update the conversation state for our standalone path
        context.user_data['conversation_state'] = GOAL_DEADLINE
        
        # Still return the state for the ConversationHandler flow
        return GOAL_DEADLINE
    except (ValueError, TypeError):
        error_text = get_text("invalid_amount", lang_code)
        await update.message.reply_text(text=error_text)
        return GOAL_AMOUNT

async def goal_deadline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles deadline selection and creates micro-goals with concrete steps."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    # Save deadline
    months_str = query.data.split('_')[1]
    months = float(months_str)  # Support for half months (2 weeks)
    context.user_data['goal_deadline_months'] = months
    
    # Calculate deadline date
    now = datetime.now()
    if months < 1:
        # For deadlines less than a month (e.g., 0.5 for 2 weeks)
        days = int(months * 30)
        from datetime import timedelta
        deadline = now + timedelta(days=days)
    else:
        # For monthly deadlines
        months_int = int(months)
        deadline = datetime(now.year + ((now.month - 1 + months_int) // 12), 
                           ((now.month - 1 + months_int) % 12) + 1, 
                           min(now.day, 28))
    
    context.user_data['goal_deadline'] = deadline.strftime("%Y-%m-%d")
    
    # Create micro-goals based on goal type and deadline
    goal_type = context.user_data['goal_type']
    goal_amount = context.user_data['goal_amount']
    
    # Create concrete, family-oriented micro-goals with visual metaphors
    micro_goals = []
    
    if goal_type == "savings":
        # For savings goals, create weekly targets with payday focus
        weekly_amount = goal_amount / (months * 4)  # Roughly 4 weeks per month
        micro_goals = [
            f"🥇 Week 1: Save {weekly_amount:.0f} from your pay - 25% complete!",
            f"🥈 Week 2: Save another {weekly_amount:.0f} - 50% complete!",
            f"🥉 Week 3: Save another {weekly_amount:.0f} - 75% complete!",
            f"🏆 Week 4: Final {weekly_amount:.0f} - Goal reached! Celebrate with family!"
        ]
    elif goal_type == "remittance":
        # For remittance, focus on communication with family
        micro_goals = [
            f"🏠 Talk with family about how they'll use the {goal_amount:.0f}",
            f"💵 Save half ({goal_amount/2:.0f}) by halfway to deadline",
            f"📱 Share progress update with family",
            f"🎁 Send full amount and celebrate with a video call"
        ]
    elif goal_type == "education":
        # For education goals
        micro_goals = [
            f"📚 Research exact cost for education need (books, fees, etc.)",
            f"💰 Save first 25% ({goal_amount/4:.0f})",
            f"📝 Plan with family member for how education will help",
            f"🎓 Reach full amount and celebrate education opportunity"
        ]
    elif goal_type == "health":
        # For health goals
        micro_goals = [
            f"🩺 List exact health needs for family member",
            f"💊 Save first 25% ({goal_amount/4:.0f})",
            f"💪 Check progress and adjust if needed",
            f"❤️ Reach goal and support family health"
        ]
    else:
        # Generic micro-goals for other types
        micro_goals = [
            f"🚀 Start: Save first {goal_amount/4:.0f}",
            f"🔄 25% done: {goal_amount/4:.0f} saved",
            f"📈 Halfway there: {goal_amount/2:.0f} saved",
            f"🏁 Finish line: Full {goal_amount:.0f} saved!"
        ]
    
    # Save micro-goals
    context.user_data['micro_goals'] = micro_goals
    
    # Build concrete steps from micro-goals
    steps = "\n".join(micro_goals)
    context.user_data['goal_steps'] = steps
    
    # Ask if these steps are good
    keyboard = [
        [
            InlineKeyboardButton(get_text("confirm_yes", lang_code), callback_data="steps_yes"),
            InlineKeyboardButton(get_text("confirm_no", lang_code), callback_data="steps_no")
        ],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Add a motivational and family-oriented message
    motivation_text = ""
    if goal_type == "savings":
        motivation_text = "💝 These small steps will help secure your family's future!"
    elif goal_type == "remittance":
        motivation_text = "💝 Your family will be proud of your planning!"
    elif goal_type == "education":
        motivation_text = "💝 Education is the best gift for your family's future!"
    elif goal_type == "health":
        motivation_text = "💝 Taking care of health is taking care of your family!"
    
    prompt = get_text("goal_steps_question", lang_code).format(steps=steps) + "\n\n" + motivation_text
    await query.edit_message_text(text=prompt, reply_markup=reply_markup)
    
    # Update the conversation state for our standalone path
    context.user_data['conversation_state'] = GOAL_STEPS
    
    return GOAL_STEPS

async def goal_steps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles steps confirmation or asks for custom steps."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    if query.data == "steps_yes":
        # Steps are good, show goal summary
        return await show_goal_summary(update, context)
    else:
        # Ask for custom steps
        prompt = get_text("enter_custom_steps", lang_code)
        await query.edit_message_text(text=prompt)
        return GOAL_STEPS

async def goal_custom_steps_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles custom steps entry."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    # Save custom steps
    steps = update.message.text.strip()
    if not steps:
        error_text = get_text("invalid_steps", lang_code)
        await update.message.reply_text(text=error_text)
        return GOAL_STEPS
    
    context.user_data['goal_steps'] = steps
    
    # Show goal summary
    goal_type = context.user_data['goal_type']
    goal_amount = context.user_data['goal_amount']
    goal_deadline = context.user_data['goal_deadline']
    
    summary = get_text("goal_summary", lang_code).format(
        type=get_text(f"goal_type_{goal_type}", lang_code),
        amount=goal_amount,
        deadline=goal_deadline,
        steps=steps
    )
    
    keyboard = [
        [
            InlineKeyboardButton(get_text("confirm_yes", lang_code), callback_data="goal_confirm_yes"),
            InlineKeyboardButton(get_text("confirm_no", lang_code), callback_data="goal_confirm_no")
        ],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text=summary, reply_markup=reply_markup)
    
    return GOAL_CONFIRMATION

async def show_goal_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Shows the goal summary and asks for confirmation."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    goal_type = context.user_data['goal_type']
    goal_amount = context.user_data['goal_amount']
    goal_deadline = context.user_data['goal_deadline']
    goal_steps = context.user_data['goal_steps']
    
    summary = get_text("goal_summary", lang_code).format(
        type=get_text(f"goal_type_{goal_type}", lang_code),
        amount=goal_amount,
        deadline=goal_deadline,
        steps=goal_steps
    )
    
    keyboard = [
        [
            InlineKeyboardButton(get_text("confirm_yes", lang_code), callback_data="goal_confirm_yes"),
            InlineKeyboardButton(get_text("confirm_no", lang_code), callback_data="goal_confirm_no")
        ],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text=summary, reply_markup=reply_markup)
    
    return GOAL_CONFIRMATION

async def goal_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles goal confirmation."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    if query.data == "goal_confirm_yes":
        # Save goal to Firebase
        goal_data = {
            'type': context.user_data['goal_type'],
            'amount': context.user_data['goal_amount'],
            'deadline': context.user_data['goal_deadline'],
            'steps': context.user_data['goal_steps'],
            'created_at': datetime.now().strftime("%Y-%m-%d"),
            'progress': 0,
            'completed': False
        }
        save_goal(user_id, goal_data)
        
        # Thank the user
        thank_text = get_text("goal_saved", lang_code)
        await query.edit_message_text(text=thank_text)
        
        # Clean up user_data
        for key in list(context.user_data.keys()):
            if key.startswith('goal_'):
                del context.user_data[key]
        
        # Show main menu
        from handlers.common import show_main_menu
        await show_main_menu(update, context, lang_code)
        
        return ConversationHandler.END
    else:
        # Start over
        restart_text = get_text("goal_restart", lang_code)
        await query.edit_message_text(text=restart_text)
        
        # Go back to goal type selection
        return await start_goal_setting(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    # Clean up user_data
    for key in list(context.user_data.keys()):
        if key.startswith('goal_'):
            del context.user_data[key]
    
    cancel_text = get_text("goal_cancelled", lang_code)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=cancel_text)
    else:
        await update.message.reply_text(text=cancel_text)
    
    return ConversationHandler.END

async def view_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to view the current goal and progress with visual progress indicators."""
    user_id = update.effective_user.id
    lang_code = get_user_language(user_id)
    
    goals = get_goals(user_id)
    
    if not goals:
        # No goals found
        no_goals_text = get_text("no_goals", lang_code)
        await update.message.reply_text(text=no_goals_text)
        return
    
    # Simplification: Just show the most recent goal
    latest_goal = goals[-1]
    
    # Format goal progress
    progress = latest_goal.get('progress', 0)
    amount = latest_goal.get('amount', 0)
    progress_percentage = (progress / amount * 100) if amount > 0 else 0
    
    goal_type = latest_goal.get('type')
    deadline = latest_goal.get('deadline')
    steps = latest_goal.get('steps')
    
    # Create visual progress bar with emojis
    progress_bar = ""
    filled_blocks = int(progress_percentage / 10)  # 10 blocks for 100%
    
    for i in range(10):
        if i < filled_blocks:
            if goal_type == "savings":
                progress_bar += "💰"  # Money bag for savings
            elif goal_type == "remittance":
                progress_bar += "🏠"  # House for remittance/family
            elif goal_type == "education":
                progress_bar += "📚"  # Books for education
            elif goal_type == "health":
                progress_bar += "❤️"  # Heart for health
            else:
                progress_bar += "🟩"  # Green square for generic
        else:
            progress_bar += "⬜"  # Empty square
    
    # Add celebration emoji if complete
    if progress_percentage >= 100:
        progress_bar += " 🎉"
    
    # Identify which micro-goal the user is working on
    micro_goal_index = min(int(progress_percentage / 25), 3)  # 0-3 based on 25% increments
    
    # Try to extract micro-goals from steps
    micro_goals = []
    for line in steps.split("\n"):
        if line.strip():
            micro_goals.append(line)
    
    # Format current micro-goal with highlight
    current_micro_goal = ""
    if micro_goals and micro_goal_index < len(micro_goals):
        current_micro_goal = f"🎯 Current focus: {micro_goals[micro_goal_index]}"
    
    # Add days remaining calculation
    from datetime import datetime
    now = datetime.now()
    deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
    days_remaining = (deadline_date - now).days
    days_text = f"📅 {days_remaining} days left to reach your goal" if days_remaining > 0 else "⏰ Deadline reached!"
    
    # Format goal display with more visual elements
    goal_text = get_text("goal_display_visual", lang_code).format(
        type=get_text(f"goal_type_{goal_type}", lang_code) if f"goal_type_{goal_type}" in get_text("", lang_code, return_keys=True) else goal_type,
        amount=amount,
        deadline=deadline,
        progress=progress,
        percentage=progress_percentage,
        progress_bar=progress_bar,
        days_remaining=days_text,
        current_step=current_micro_goal
    )
    
    # Add motivation based on progress
    motivation = ""
    if progress_percentage < 25:
        motivation = "💪 You've started! Each small step matters."
    elif progress_percentage < 50:
        motivation = "👏 Keep going! You're making good progress."
    elif progress_percentage < 75:
        motivation = "🌟 You're over halfway there! Almost there."
    elif progress_percentage < 100:
        motivation = "🔥 So close to your goal! Final push!"
    else:
        motivation = "🏆 Congratulations! You reached your goal!"
    
    # Add all micro-goals with check marks for completed ones
    micro_goals_display = "\n\nProgress steps:"
    for i, goal in enumerate(micro_goals):
        if i <= micro_goal_index and progress_percentage > 0:
            # Mark completed micro-goals with check mark
            if progress_percentage >= 100 or i < micro_goal_index:
                micro_goals_display += f"\n✅ {goal.split(':', 1)[1] if ':' in goal else goal}"
            else:
                micro_goals_display += f"\n🔄 {goal.split(':', 1)[1] if ':' in goal else goal}"
        else:
            # Future micro-goals
            micro_goals_display += f"\n⬜ {goal.split(':', 1)[1] if ':' in goal else goal}"
    
    # Add action buttons
    keyboard = [
        [InlineKeyboardButton(get_text("update_progress", lang_code), callback_data="update_goal_progress")],
        [InlineKeyboardButton(get_text("share_with_family", lang_code), callback_data="share_goal_with_family")],
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text=goal_text + "\n\n" + motivation + micro_goals_display, reply_markup=reply_markup)

# Create a standalone handler for goal types
async def goal_type_standalone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Standalone handler for goal type selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    logger.info(f"Standalone goal type callback: {query.data}")
    
    # Save goal type
    goal_type = query.data.split('_')[-1]
    context.user_data['goal_type'] = goal_type
    
    # Let the user know we're ready for their input
    prompt = get_text(f"goal_amount_question_{goal_type}", lang_code)
    
    # Add cancel option
    keyboard = [
        [InlineKeyboardButton(get_text("back_to_menu", lang_code), callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=prompt + "\n\n" + "Type your amount directly in the chat.", reply_markup=reply_markup)
    
    # Now we need to manually advance the conversation
    context.user_data['conversation_state'] = GOAL_AMOUNT

# Add a handler for sharing goal progress with family
async def share_goal_with_family(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Creates a shareable message for family about goal progress."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = get_user_language(user_id)
    
    goals = get_goals(user_id)
    if not goals:
        await query.edit_message_text(text=get_text("no_goals", lang_code))
        return
    
    # Get latest goal
    latest_goal = goals[-1]
    goal_type = latest_goal.get('type')
    amount = latest_goal.get('amount', 0)
    progress = latest_goal.get('progress', 0)
    progress_percentage = (progress / amount * 100) if amount > 0 else 0
    
    # Create a simple shareable message
    if goal_type == "remittance":
        share_message = f"🏠 I'm saving to send {amount} to our family. So far I've saved {progress} ({progress_percentage:.0f}%)! I'll keep you updated."
    elif goal_type == "education":
        share_message = f"📚 I'm saving {amount} for education. Already saved {progress} ({progress_percentage:.0f}%)! Learning is our future."
    elif goal_type == "health":
        share_message = f"❤️ I'm saving {amount} for our health needs. Already saved {progress} ({progress_percentage:.0f}%)! Taking care of us."
    else:
        share_message = f"💰 I'm saving {amount} for our future. Already saved {progress} ({progress_percentage:.0f}%)! Making progress every day."
    
    # Show the shareable message to the user
    await query.edit_message_text(
        text=get_text("share_with_family_text", lang_code) + "\n\n" + 
        share_message + "\n\n" +
        get_text("share_message_instructions", lang_code)
    )

# Define a handler class for callbacks with additional logging
class LoggingCallbackHandler(CallbackQueryHandler):
    async def handle_update(self, update, dispatcher, check_result, context):
        if update.callback_query:
            logger.debug(f"Handling callback: {update.callback_query.data}")
        return await super().handle_update(update, dispatcher, check_result, context)

# Create the goal setting conversation handler with more verbose debugging
goal_handler = ConversationHandler(
    entry_points=[
        CommandHandler('goal', start_goal_setting),
        CallbackQueryHandler(start_goal_setting, pattern='^menu_set_goals')
    ],
    states={
        INCOME_ASSESSMENT: [LoggingCallbackHandler(income_assessment_callback, pattern='^income_[1-5]$')],
        FAMILY_ASSESSMENT: [LoggingCallbackHandler(family_assessment_callback, pattern='^family_needs_')],
        SPENDING_ASSESSMENT: [LoggingCallbackHandler(spending_assessment_callback, pattern='^spending_')],
        GOAL_TYPE: [
            # Add suggestion handlers first (more specific)
            LoggingCallbackHandler(goal_suggestion_callback, pattern='^goal_sugg_'),
            LoggingCallbackHandler(goal_type_callback, pattern='^goal_type_'),
            LoggingCallbackHandler(goal_type_callback, pattern='^goal_custom$')
        ],
        GOAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_amount_handler)],
        GOAL_DEADLINE: [LoggingCallbackHandler(goal_deadline_callback, pattern='^deadline_')],
        GOAL_STEPS: [
            LoggingCallbackHandler(goal_steps_callback, pattern='^steps_'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, goal_custom_steps_handler)
        ],
        GOAL_CONFIRMATION: [LoggingCallbackHandler(goal_confirmation_callback, pattern='^goal_confirm_')],
        MICRO_GOALS: [
            LoggingCallbackHandler(goal_confirmation_callback, pattern='^micro_goal_confirm_')
        ]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)