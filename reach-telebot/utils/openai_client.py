# utils/openai_client.py
from openai import OpenAI
from config import OPENAI_API_KEY
import logging

_client = None

def initialize_openai():
    """Initializes the OpenAI client."""
    global _client
    if _client is None:
        try:
            # Check if we're in development/test mode
            if OPENAI_API_KEY.startswith("sk-proj-") or OPENAI_API_KEY.startswith("test_"):
                logging.info("Using OpenAI in development/test mode")
            
            _client = OpenAI(api_key=OPENAI_API_KEY)
            logging.info("OpenAI client initialized.")
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            logging.warning("Continuing without OpenAI for development")
            # We'll continue without raising an exception

def get_behavioral_goal_suggestions(income: str, family_needs: str, current_situation: str, lang_code: str = "en", model: str = "gpt-3.5-turbo") -> list:
    """
    Gets personalized goal suggestions using behavioral science principles.
    
    Args:
        income: The user's income level
        family_needs: The user's family needs description
        current_situation: Additional context about the user's situation
        lang_code: The language code for the response
        model: The model to use for generation
        
    Returns:
        A list of suggested goals with behavioral science rationale
    """
    if not _client:
        initialize_openai()
        if not _client:
            # Provide mock response for development
            logging.warning("Using mock goal suggestions for development")
            return [
                {"goal": "Emergency Savings", "description": "Create a safety net for unexpected expenses", "rationale": "Helps reduce stress and provides security"},
                {"goal": "Send Money Home", "description": "Regular remittance to support family", "rationale": "Strengthens family bonds and fulfills responsibilities"},
                {"goal": "Education Fund", "description": "Save for family education expenses", "rationale": "Investing in future opportunities and growth"}
            ]

    try:
        # If we're in development/test mode, return a mock response
        if OPENAI_API_KEY.startswith("sk-proj-") or OPENAI_API_KEY.startswith("test_"):
            logging.info("Using mock goal suggestions for development")
            mock_goals = {
                "en": [
                    {"goal": "Emergency Savings", "description": "Create a safety net for unexpected expenses", "rationale": "Helps reduce stress and provides security"},
                    {"goal": "Send Money Home", "description": "Regular remittance to support family", "rationale": "Strengthens family bonds and fulfills responsibilities"},
                    {"goal": "Education Fund", "description": "Save for family education expenses", "rationale": "Investing in future opportunities and growth"}
                ],
                "bn": [
                    {"goal": "জরুরী সঞ্চয়", "description": "অপ্রত্যাশিত খরচের জন্য সুরক্ষা তৈরি করুন", "rationale": "চাপ কমাতে এবং নিরাপত্তা প্রদান করে"},
                    {"goal": "বাড়িতে টাকা পাঠান", "description": "পরিবারকে সমর্থন করার জন্য নিয়মিত অর্থ প্রেরণ", "rationale": "পারিবারিক বন্ধন শক্তিশালী করে এবং দায়িত্ব পূরণ করে"},
                    {"goal": "শিক্ষা তহবিল", "description": "পরিবারের শিক্ষা খরচের জন্য সঞ্চয়", "rationale": "ভবিষ্যতের সুযোগ এবং বৃদ্ধিতে বিনিয়োগ করা"}
                ],
                "ta": [
                    {"goal": "அவசர சேமிப்பு", "description": "எதிர்பாராத செலவுகளுக்கான பாதுகாப்பு வலை", "rationale": "மன அழுத்தத்தைக் குறைக்க உதவுகிறது மற்றும் பாதுகாப்பை வழங்குகிறது"},
                    {"goal": "வீட்டிற்கு பணம் அனுப்புங்கள்", "description": "குடும்பத்திற்கு ஆதரவளிக்க வழக்கமான பணம் அனுப்புதல்", "rationale": "குடும்ப பிணைப்புகளை வலுப்படுத்துகிறது மற்றும் பொறுப்புகளை நிறைவேற்றுகிறது"},
                    {"goal": "கல்வி நிதி", "description": "குடும்ப கல்விச் செலவுகளுக்காக சேமிக்கவும்", "rationale": "எதிர்கால வாய்ப்புகள் மற்றும் வளர்ச்சியில் முதலீடு செய்தல்"}
                ]
            }
            return mock_goals.get(lang_code, mock_goals["en"])
            
        # Create a detailed system prompt using behavioral science principles
        system_prompt = f"""
        You are a financial goal advisor for migrant workers in Singapore using behavioral science principles (specifically the COM-B model: Capability, Opportunity, Motivation -> Behavior).
        
        Create contextual, meaningful financial goal suggestions based on the user's income level and family needs.
        
        Use these behavioral science principles:
        1. Make goals concrete and specific (rather than abstract)
        2. Connect goals to family values and relationships
        3. Focus on small wins and manageable steps
        4. Create psychological ownership over goals
        5. Reduce mental effort required for decision making
        
        Based on the provided income and family information, generate 3-4 contextual financial goals in {lang_code} language that would be most appropriate.

        IMPORTANT: Return ONLY a JSON array with objects containing:
        - "goal": Short goal name (3-5 words)
        - "description": Brief description of the goal (10-15 words)
        - "rationale": Why this goal matters using behavioral science (10-15 words)
        
        The goals should be specific to the migrant worker context and address both short-term needs and long-term aspirations.
        """
        
        # Create a user prompt with the specific information
        user_prompt = f"Income: {income}\nFamily needs: {family_needs}\nCurrent situation: {current_situation}"
        
        response = _client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        if response.choices and len(response.choices) > 0:
            result = response.choices[0].message.content.strip()
            logging.debug(f"Generated goal suggestions: {result}")
            import json
            try:
                parsed_result = json.loads(result)
                if isinstance(parsed_result, dict) and "goals" in parsed_result:
                    return parsed_result["goals"]
                elif isinstance(parsed_result, list):
                    return parsed_result
                else:
                    return [{"goal": "Emergency Fund", "description": "Save for unexpected expenses", "rationale": "Creates financial security"}]
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON response: {result}")
                return [{"goal": "Emergency Fund", "description": "Save for unexpected expenses", "rationale": "Creates financial security"}]
        else:
            logging.error("OpenAI response missing choices.")
            return [{"goal": "Emergency Fund", "description": "Save for unexpected expenses", "rationale": "Creates financial security"}]
    except Exception as e:
        logging.error(f"Error calling OpenAI API for goal suggestions: {e}", exc_info=True)
        return [{"goal": "Emergency Fund", "description": "Save for unexpected expenses", "rationale": "Creates financial security"}]

def get_ai_advice(prompt: str, lang_code: str = "en", model: str = "gpt-3.5-turbo") -> str:
    """
    Gets financial advice from OpenAI based on the prompt.
    
    Args:
        prompt: The prompt to send to the AI
        lang_code: The language code for the response
        model: The model to use for generation
        
    Returns:
        The AI-generated advice as a string
    """
    if not _client:
        initialize_openai()
        if not _client:
            # Provide mock response for development
            logging.warning("Using mock AI advice response for development")
            return f"[DEVELOPMENT MODE] Mock financial advice about: {prompt}"

    try:
        # If we're in development/test mode, return a mock response
        if OPENAI_API_KEY.startswith("sk-proj-") or OPENAI_API_KEY.startswith("test_"):
            logging.info("Using mock AI advice response for development")
            mock_responses = {
                "en": f"[DEVELOPMENT MODE] Here is some financial advice about {prompt}: Save regularly and avoid unnecessary expenses.",
                "bn": f"[DEVELOPMENT MODE] আর্থিক পরামর্শ: নিয়মিত সঞ্চয় করুন।", 
                "ta": f"[DEVELOPMENT MODE] நிதி ஆலோசனை: தொடர்ந்து சேமியுங்கள்."
            }
            return mock_responses.get(lang_code, mock_responses["en"])
            
        response = _client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"You are a helpful financial advisor for migrant workers. Provide simple, practical financial advice in {lang_code} language."},
                {"role": "user", "content": prompt}
            ]
        )
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()
        else:
            logging.error("OpenAI response missing choices.")
            return "Sorry, I couldn't generate advice at this time."
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}", exc_info=True)
        return "Sorry, I encountered an error while generating advice."

def parse_expense(text: str, lang_code: str = "en") -> dict:
    """
    Parses expense information from text using OpenAI.
    
    Args:
        text: The expense text to parse
        lang_code: The language code of the input text
        
    Returns:
        A dictionary with parsed expense information (amount, category, description)
    """
    if not _client:
        initialize_openai()
        if not _client:
            # Provide mock response for development
            logging.warning("Using mock expense parsing for development")
            return {"amount": 25, "currency": "USD", "category": "food", "description": f"Mock parsed expense: {text}"}

    try:
        # If we're in development/test mode, return a mock response
        if OPENAI_API_KEY.startswith("sk-proj-") or OPENAI_API_KEY.startswith("test_"):
            logging.info("Using mock expense parsing for development")
            
            # Create a simple mock parser based on keywords
            import re
            
            # Default values
            mock_result = {
                "amount": 25, 
                "currency": "USD", 
                "category": "miscellaneous", 
                "description": f"Mock parsed expense: {text}"
            }
            
            # Check for numbers in the text for amount
            numbers = re.findall(r'\d+', text)
            if numbers:
                mock_result["amount"] = int(numbers[0])
                
            # Check for currency
            if "USD" in text or "$" in text:
                mock_result["currency"] = "USD"
            elif "EUR" in text or "€" in text:
                mock_result["currency"] = "EUR"
                
            # Check for category
            if any(word in text.lower() for word in ["food", "eat", "meal", "grocery"]):
                mock_result["category"] = "food"
            elif any(word in text.lower() for word in ["transport", "bus", "train", "taxi"]):
                mock_result["category"] = "transportation"
            elif any(word in text.lower() for word in ["house", "rent", "apartment"]):
                mock_result["category"] = "housing"
                
            return mock_result
            
        response = _client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Extract expense information from the following text in {lang_code} language. Return ONLY a JSON object with amount (number), currency (string), category (string), and description (string)."},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        if response.choices and len(response.choices) > 0:
            result = response.choices[0].message.content.strip()
            logging.debug(f"Parsed expense: {result}")
            import json
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"error": "Failed to parse expense information"}
        else:
            logging.error("OpenAI response missing choices.")
            return {"error": "Failed to process expense"}
    except Exception as e:
        logging.error(f"Error calling OpenAI API for expense parsing: {e}", exc_info=True)
        return {"error": f"Error parsing expense: {str(e)}"}

# Initialize OpenAI when the module is imported
try:
    initialize_openai()
except Exception as e:
    logging.error(f"Failed to initialize OpenAI: {e}")