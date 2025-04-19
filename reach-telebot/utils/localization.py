# utils/localization.py
import json
import os
import logging
from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

_translations = {}

def load_translations():
    """Loads translation files from the locales directory."""
    locales_dir = os.path.join(os.path.dirname(__file__), '..', 'locales')
    logging.debug(f"Looking for locales in: {locales_dir}")
    
    for lang_code in SUPPORTED_LANGUAGES:
        filepath = os.path.join(locales_dir, f"{lang_code}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    _translations[lang_code] = json.load(f)
                logging.info(f"Loaded translations for: {lang_code}")
            except Exception as e:
                logging.error(f"Error loading translation file {filepath}: {e}")
        else:
            logging.warning(f"Translation file not found for language '{lang_code}' at {filepath}")

def get_text(key: str, lang_code: str = DEFAULT_LANGUAGE) -> str:
    """Gets translated text for a given key and language code."""
    # If translations haven't been loaded yet, load them
    if not _translations:
        load_translations()
        
    # Fallback to default language if the requested language is not available
    lang_to_use = lang_code if lang_code in _translations else DEFAULT_LANGUAGE
    
    # If default language is also not available, return a placeholder
    if lang_to_use not in _translations:
        logging.error(f"No translations available for language: {lang_to_use}")
        return f"[{key}]"
    
    # Return the translation or a placeholder if the key is missing
    return _translations.get(lang_to_use, {}).get(key, f"[{key}]")

def get_language_name(lang_code: str) -> str:
    """Returns the display name of a language based on its code."""
    language_names = {
        "en": "English",
        "bn": "Bengali",
        "ta": "Tamil"
    }
    return language_names.get(lang_code, lang_code)

# Load translations when the module is imported
load_translations()