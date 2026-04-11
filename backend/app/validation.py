# Field length limits
MAX_COMMENT_LENGTH = 2000
MAX_DISPLAY_NAME_LENGTH = 100
MAX_LIST_NAME_LENGTH = 200
MAX_LIST_DESCRIPTION_LENGTH = 500
MAX_PHOTO_CAPTION_LENGTH = 200
MAX_SEARCH_QUERY_LENGTH = 200
MIN_PASSWORD_LENGTH = 8

# Password policy
import re


def validate_password_strength(password: str) -> str:
    """Validate password has min 8 chars, 1 uppercase, 1 lowercase, 1 digit. Returns password or raises ValueError."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password
