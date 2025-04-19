# utils/firebase_client.py
import firebase_admin
from firebase_admin import credentials, firestore
from config import FIREBASE_SERVICE_ACCOUNT_KEY_PATH, DEFAULT_LANGUAGE
import logging
import os

_db = None
_mock_data = {}  # For development/testing

def initialize_firebase():
    """Initializes the Firebase Admin SDK."""
    global _db
    if _db is None:
        try:
            # Check if we're using a mock setup
            if os.path.basename(FIREBASE_SERVICE_ACCOUNT_KEY_PATH) == 'test_firebase_key.json':
                logging.info("Using mock Firebase setup for development/testing")
                # Mock is handled in the other functions
                return
                
            cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)
            _db = firestore.client()
            logging.info("Firebase initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize Firebase: {e}", exc_info=True)
            logging.warning("Continuing with mock Firebase for development")
            # We'll continue without raising an exception

def get_user_data(user_id: int) -> dict:
    """Retrieves user data from Firestore or mock data store."""
    # Check if we're using a mock setup
    if os.path.basename(FIREBASE_SERVICE_ACCOUNT_KEY_PATH) == 'test_firebase_key.json':
        # Return mock data for development/testing
        user_key = str(user_id)
        if user_key not in _mock_data:
            _mock_data[user_key] = {'language': DEFAULT_LANGUAGE, 'profile': {}, 'goals': [], 'expenses': []}
        return _mock_data[user_key]
        
    if not _db:
        # If we're not in mock mode but db is None, this is an error
        logging.warning("Firebase not initialized, using mock data")
        user_key = str(user_id)
        if user_key not in _mock_data:
            _mock_data[user_key] = {'language': DEFAULT_LANGUAGE, 'profile': {}, 'goals': [], 'expenses': []}
        return _mock_data[user_key]
        
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
    """Updates user data in Firestore or mock data store."""
    # Check if we're using a mock setup
    if os.path.basename(FIREBASE_SERVICE_ACCOUNT_KEY_PATH) == 'test_firebase_key.json':
        user_key = str(user_id)
        if user_key not in _mock_data:
            _mock_data[user_key] = {'language': DEFAULT_LANGUAGE, 'profile': {}, 'goals': [], 'expenses': []}
        
        # Merge the data
        for key, value in data.items():
            _mock_data[user_key][key] = value
            
        logging.debug(f"[MOCK] Updated data for user {user_id}")
        return
        
    if not _db:
        # If we're not in mock mode but db is None, use mock data
        logging.warning("Firebase not initialized, using mock data")
        user_key = str(user_id)
        if user_key not in _mock_data:
            _mock_data[user_key] = {'language': DEFAULT_LANGUAGE, 'profile': {}, 'goals': [], 'expenses': []}
        
        # Merge the data
        for key, value in data.items():
            _mock_data[user_key][key] = value
            
        logging.debug(f"[MOCK] Updated data for user {user_id}")
        return
    
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