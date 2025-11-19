# config.py
# Email Configuration

# SMTP Configuration
SMTP_CONFIG = {
    'host': 'smtp.gmail.com',
    'port': 587,
    'user': 'harishmurali1289@gmail.com',
    'password': 'mxsmfewatohrezmc'  # Google App Password
}

# Test Mode Settings
TEST_MODE = False  # Set to True for testing with dummy emails, False for production

# Dummy Email Mappings (only used when TEST_MODE = True)
# Map any email to a test email address for testing purposes
DUMMY_EMAIL_MAPPING = {
    'john.doe@example.com': 'harishmurali1289+john@gmail.com',
    'jane.smith@example.com': 'harishmurali1289+jane@gmail.com',
    'alice.wonder@example.com': 'harishmurali1289+alice@gmail.com',
    'bob.builder@example.com': 'harishmurali1289+bob@gmail.com',
    'charlie.brown@example.com': 'harishmurali1289+charlie@gmail.com',
    'david.jones@example.com': 'harishmurali1289+david@gmail.com',
    'emma.watson@example.com': 'harishmurali1289+emma@gmail.com',
    'frank.ocean@example.com': 'harishmurali1289+frank@gmail.com',
    'grace.hopper@example.com': 'harishmurali1289+grace@gmail.com',
    'henry.ford@example.com': 'harishmurali1289+henry@gmail.com',
}

# Single test email (if you want ALL test emails to go to one address)
SINGLE_TEST_EMAIL = 'harishmurali1289@gmail.com'

# Use single email vs mapping (only applies when TEST_MODE = True)
USE_SINGLE_TEST_EMAIL = False  # If True, all test emails go to SINGLE_TEST_EMAIL

# Email logging
LOG_EMAILS = True  # Log all email attempts


def get_recipient_email(original_email):
    """
    Get the actual recipient email address
    - In production (TEST_MODE=False): Returns the original email (dynamic)
    - In test mode (TEST_MODE=True): Returns mapped test email or fallback
    
    Args:
        original_email: The email address from registration
        
    Returns:
        The email address where the email should be sent
    """
    if not TEST_MODE:
        # Production mode: send to actual email addresses
        return original_email
    
    # Test mode: use dummy emails
    if USE_SINGLE_TEST_EMAIL:
        return SINGLE_TEST_EMAIL
    
    # Return mapped email if exists, otherwise return single test email
    return DUMMY_EMAIL_MAPPING.get(original_email, SINGLE_TEST_EMAIL)


def is_test_mode():
    """Check if we're in test mode"""
    return TEST_MODE


def add_dummy_mapping(original_email, test_email):
    """Add a new dummy email mapping"""
    DUMMY_EMAIL_MAPPING[original_email] = test_email
    return True


def remove_dummy_mapping(original_email):
    """Remove a dummy email mapping"""
    if original_email in DUMMY_EMAIL_MAPPING:
        del DUMMY_EMAIL_MAPPING[original_email]
        return True
    return False


def get_all_mappings():
    """Get all dummy email mappings"""
    return DUMMY_EMAIL_MAPPING.copy()