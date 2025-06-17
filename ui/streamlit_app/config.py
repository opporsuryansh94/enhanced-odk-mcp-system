"""
Configuration module for the ODK MCP System Streamlit UI.

This module loads configuration from environment variables or a .env file
and provides configuration values to the Streamlit application.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# MCP API endpoints
FORM_MANAGEMENT_API = os.getenv("FORM_MANAGEMENT_API", "http://localhost:5001/v1")
DATA_COLLECTION_API = os.getenv("DATA_COLLECTION_API", "http://localhost:5002/v1")
DATA_AGGREGATION_API = os.getenv("DATA_AGGREGATION_API", "http://localhost:5003/v1")

# Authentication settings
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "odk_mcp_auth")
AUTH_COOKIE_EXPIRY_DAYS = int(os.getenv("AUTH_COOKIE_EXPIRY_DAYS", "30"))
AUTH_COOKIE_KEY = os.getenv("AUTH_COOKIE_KEY", "odk_mcp_streamlit_cookie_key")

# Default users (for development/testing)
DEFAULT_USERS_FILE = os.getenv("DEFAULT_USERS_FILE", str(BASE_DIR / "default_users.json"))

def load_default_users() -> Dict[str, Any]:
    """
    Load default users from the users file.
    
    Returns:
        Dict[str, Any]: Dictionary with user configuration.
    """
    if os.path.exists(DEFAULT_USERS_FILE):
        try:
            with open(DEFAULT_USERS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading default users: {e}")
    
    # Return a default configuration with a single admin user
    return {
        "credentials": {
            "usernames": {
                "admin": {
                    "email": "admin@example.com",
                    "name": "Admin User",
                    "password": "$2b$12$TP7oLGvdYUDyfiHSJRKQ0.eKwgSFWdIZFZlHcRJkHHBBhDNyYCB1C"  # "password"
                }
            }
        },
        "cookie": {
            "name": AUTH_COOKIE_NAME,
            "key": AUTH_COOKIE_KEY,
            "expiry_days": AUTH_COOKIE_EXPIRY_DAYS
        }
    }

# UI settings
PAGE_TITLE = os.getenv("PAGE_TITLE", "ODK MCP System")
PAGE_ICON = os.getenv("PAGE_ICON", "📊")
LAYOUT = os.getenv("LAYOUT", "wide")  # "centered" or "wide"

# Theme settings
PRIMARY_COLOR = os.getenv("PRIMARY_COLOR", "#FF4B4B")  # ODK red
BACKGROUND_COLOR = os.getenv("BACKGROUND_COLOR", "#FFFFFF")
SECONDARY_BACKGROUND_COLOR = os.getenv("SECONDARY_BACKGROUND_COLOR", "#F0F2F6")
TEXT_COLOR = os.getenv("TEXT_COLOR", "#262730")
FONT = os.getenv("FONT", "sans serif")

# File upload settings
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "200"))  # MB

# Cache settings
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # seconds

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(BASE_DIR / "streamlit_app.log"))

# Create a dictionary of theme settings for Streamlit
THEME = {
    "primaryColor": PRIMARY_COLOR,
    "backgroundColor": BACKGROUND_COLOR,
    "secondaryBackgroundColor": SECONDARY_BACKGROUND_COLOR,
    "textColor": TEXT_COLOR,
    "font": FONT
}

# Export all settings
__all__ = [
    "FORM_MANAGEMENT_API",
    "DATA_COLLECTION_API",
    "DATA_AGGREGATION_API",
    "AUTH_ENABLED",
    "AUTH_COOKIE_NAME",
    "AUTH_COOKIE_EXPIRY_DAYS",
    "AUTH_COOKIE_KEY",
    "load_default_users",
    "PAGE_TITLE",
    "PAGE_ICON",
    "LAYOUT",
    "THEME",
    "MAX_UPLOAD_SIZE",
    "CACHE_TTL",
    "LOG_LEVEL",
    "LOG_FILE"
]

