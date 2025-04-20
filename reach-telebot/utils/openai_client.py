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
            # Initialize with only the required parameters to avoid proxies error
            _client = OpenAI(api_key=OPENAI_API_KEY)
            logging.info("OpenAI client initialized successfully.")
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
            logging.error("OpenAI client initialization failed")
            raise Exception("Failed to initialize OpenAI client")

    try:
        # Create a detailed system prompt using behavioral science principles
        system_prompt = "You are a financial goal advisor for migrant workers in Singapore using behavioral science principles (specifically the COM-B model: Capability, Opportunity, Motivation -> Behavior).\n\n" + \
        "Create contextual, meaningful financial goal suggestions based on the user's income level and family needs.\n\n" + \
        "Use these behavioral science principles:\n" + \
        "1. Make goals concrete and specific (rather than abstract)\n" + \
        "2. Connect goals to family values and relationships\n" + \
        "3. Focus on small wins and manageable steps\n" + \
        "4. Create psychological ownership over goals\n" + \
        "5. Reduce mental effort required for decision making\n\n" + \
        f"Based on the provided income and family information, generate 3-4 contextual financial goals in {lang_code} language that would be most appropriate.\n\n" + \
        "IMPORTANT: Return ONLY a JSON array with objects containing:\n" + \
        "- \"goal\": Short goal name (3-5 words)\n" + \
        "- \"description\": Brief description of the goal (10-15 words)\n" + \
        "- \"rationale\": Why this goal matters using behavioral science (10-15 words)\n\n" + \
        "The goals should be specific to the migrant worker context and address both short-term needs and long-term aspirations."

        # Create a user prompt with the specific information
        user_prompt = f"Income: {income}\nFamily needs: {family_needs}\nCurrent situation: {current_situation}"
        
        logging.info(f"⭐⭐⭐ CALLING OPENAI API for personalized goal suggestions")
        # Create the response - manually handle the JSON format to avoid errors
        try:
            response = _client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
        except Exception as e:
            logging.error(f"Error with response_format parameter: {e}")
            # Fallback without response_format if it's not supported
            response = _client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt + "\nReturn your response as a valid JSON object."},
                    {"role": "user", "content": user_prompt}
                ]
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
            logging.error("OpenAI client initialization failed")
            raise Exception("Failed to initialize OpenAI client")

    try:
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
            logging.error("OpenAI client initialization failed")
            raise Exception("Failed to initialize OpenAI client")

    try:
        try:
            response = _client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Extract expense information from the following text in {lang_code} language. Return ONLY a JSON object with amount (number), currency (string), category (string), and description (string)."},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"}
            )
        except Exception as e:
            logging.error(f"Error with expense parsing response_format: {e}")
            # Fallback without response_format if it's not supported
            try:
                response = _client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": f"Extract expense information from the following text in {lang_code} language. Return ONLY a JSON object with amount (number), currency (string), category (string), and description (string). The response must be valid JSON."},
                        {"role": "user", "content": text}
                    ]
                )
            except Exception as e2:
                logging.error(f"Error in fallback expense parsing: {e2}")
                return {"error": f"Error parsing expense: {str(e2)}"}
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