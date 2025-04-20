# utils/firebase_client.py
import firebase_admin
from firebase_admin import credentials, firestore
from config import FIREBASE_SERVICE_ACCOUNT_KEY_PATH, DEFAULT_LANGUAGE
import logging
import os

_db = None

def initialize_firebase():
    """Initializes the Firebase Admin SDK."""
    global _db
    if _db is None:
        try:
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)
            _db = firestore.client()
            logging.info("Firebase initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize Firebase: {e}", exc_info=True)
            raise Exception(f"Failed to initialize Firebase: {e}")

def get_user_data(user_id: int) -> dict:
    """Retrieves user data from Firestore."""
    if not _db:
        initialize_firebase()
        
    try:
        user_ref = _db.collection('users').document(str(user_id))
        user_snapshot = user_ref.get()
        if user_snapshot.exists:
            return user_snapshot.to_dict()
        else:
            # Return a default structure for new users
            return {'language': DEFAULT_LANGUAGE, 'profile': {}, 'goals': [], 'expenses': []}
    except Exception as e:
        logging.error(f"Error getting user data for {user_id}: {e}", exc_info=True)
        return {'language': DEFAULT_LANGUAGE, 'profile': {}, 'goals': [], 'expenses': []}

def update_user_data(user_id: int, data: dict):
    """Updates user data in Firestore."""
    if not _db:
        initialize_firebase()
    
    try:
        user_ref = _db.collection('users').document(str(user_id))
        # Use merge=True to only update fields present in the data dict
        user_ref.set(data, merge=True)
        logging.debug(f"Updated data for user {user_id}")
    except Exception as e:
        logging.error(f"Error updating user data for {user_id}: {e}", exc_info=True)

def set_user_language(user_id: int, lang_code: str):
    """Specifically sets the user's language preference."""
    update_user_data(user_id, {'language': lang_code})

def get_user_language(user_id: int) -> str:
    """Gets the user's language preference, falling back to default."""
    user_data = get_user_data(user_id)
    return user_data.get('language', DEFAULT_LANGUAGE)

def save_goal(user_id: int, goal_data: dict):
    """Saves a user's financial goal."""
    user_data = get_user_data(user_id)
    goals = user_data.get('goals', [])
    goals.append(goal_data)
    update_user_data(user_id, {'goals': goals})

def get_goals(user_id: int) -> list:
    """Gets the user's financial goals."""
    user_data = get_user_data(user_id)
    return user_data.get('goals', [])

def save_expense(user_id: int, expense_data: dict):
    """Saves a user's expense."""
    user_data = get_user_data(user_id)
    expenses = user_data.get('expenses', [])
    expenses.append(expense_data)
    update_user_data(user_id, {'expenses': expenses})

def get_expenses(user_id: int) -> list:
    """Gets the user's expenses."""
    user_data = get_user_data(user_id)
    return user_data.get('expenses', [])

def save_profile(user_id: int, profile_data: dict):
    """Saves a user's profile information."""
    update_user_data(user_id, {'profile': profile_data})

def get_profile(user_id: int) -> dict:
    """Gets the user's profile information."""
    user_data = get_user_data(user_id)
    return user_data.get('profile', {})

# Initialize Firebase when the module is imported
initialize_firebase()