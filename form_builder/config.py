"""
Configuration for the smart drag-and-drop form builder.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

# Ensure directories exist
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Form builder configuration
FORM_BUILDER = {
    "max_form_size_kb": 1024,  # Maximum form definition size in KB
    "max_csv_upload_size_mb": 10,  # Maximum CSV upload size in MB
    "allowed_file_extensions": [".csv", ".xlsx", ".xls"],
    "form_templates_enabled": True,
    "form_versioning_enabled": True,
    "max_versions_per_form": 50,
    "auto_save_interval_seconds": 30,
}

# Form components configuration
FORM_COMPONENTS = {
    "basic": [
        {
            "type": "text",
            "label": "Text Input",
            "icon": "text_fields",
            "properties": ["required", "default", "hint", "constraint", "readonly"]
        },
        {
            "type": "number",
            "label": "Number Input",
            "icon": "dialpad",
            "properties": ["required", "default", "hint", "constraint", "readonly", "min", "max"]
        },
        {
            "type": "date",
            "label": "Date Picker",
            "icon": "calendar_today",
            "properties": ["required", "default", "hint", "constraint", "readonly", "min", "max"]
        },
        {
            "type": "time",
            "label": "Time Picker",
            "icon": "access_time",
            "properties": ["required", "default", "hint", "constraint", "readonly"]
        },
        {
            "type": "select_one",
            "label": "Select Dropdown",
            "icon": "arrow_drop_down_circle",
            "properties": ["required", "default", "hint", "options", "appearance"]
        },
        {
            "type": "select_multiple",
            "label": "Multi-Select",
            "icon": "check_box",
            "properties": ["required", "default", "hint", "options", "appearance"]
        },
        {
            "type": "radio",
            "label": "Radio Buttons",
            "icon": "radio_button_checked",
            "properties": ["required", "default", "hint", "options", "appearance"]
        },
        {
            "type": "checkbox",
            "label": "Checkboxes",
            "icon": "check_box_outline_blank",
            "properties": ["required", "default", "hint", "options", "appearance"]
        }
    ],
    "advanced": [
        {
            "type": "geopoint",
            "label": "GPS Location",
            "icon": "location_on",
            "properties": ["required", "hint", "appearance"]
        },
        {
            "type": "image",
            "label": "Image Capture",
            "icon": "photo_camera",
            "properties": ["required", "hint", "appearance"]
        },
        {
            "type": "audio",
            "label": "Audio Recording",
            "icon": "mic",
            "properties": ["required", "hint", "appearance"]
        },
        {
            "type": "signature",
            "label": "Signature Capture",
            "icon": "draw",
            "properties": ["required", "hint", "appearance"]
        },
        {
            "type": "barcode",
            "label": "Barcode/QR Scanner",
            "icon": "qr_code_scanner",
            "properties": ["required", "hint", "appearance"]
        },
        {
            "type": "rating",
            "label": "Rating Scale",
            "icon": "star_rate",
            "properties": ["required", "default", "hint", "min", "max", "step"]
        },
        {
            "type": "matrix",
            "label": "Matrix/Grid Questions",
            "icon": "grid_on",
            "properties": ["required", "hint", "rows", "columns", "appearance"]
        }
    ],
    "layout": [
        {
            "type": "section",
            "label": "Section Divider",
            "icon": "horizontal_rule",
            "properties": ["label", "appearance"]
        },
        {
            "type": "page",
            "label": "Page Break",
            "icon": "last_page",
            "properties": ["label"]
        },
        {
            "type": "repeat",
            "label": "Repeating Group",
            "icon": "repeat",
            "properties": ["label", "hint", "min", "max", "count"]
        },
        {
            "type": "group",
            "label": "Conditional Group",
            "icon": "folder",
            "properties": ["label", "hint", "relevant"]
        }
    ]
}

# AI integration configuration
AI_INTEGRATION = {
    "enabled": True,
    "csv_structure_suggestions": True,
    "field_type_prediction": True,
    "constraint_suggestions": True,
    "form_templates_suggestions": True,
    "similarity_threshold": 0.75,
    "max_suggestions": 5,
}

# XLSForm export configuration
XLSFORM_EXPORT = {
    "enabled": True,
    "include_metadata": True,
    "default_language": "en",
    "supported_languages": ["en", "es", "fr", "sw", "hi", "zh"],
}

# JSON schema export configuration
JSON_SCHEMA_EXPORT = {
    "enabled": True,
    "schema_version": "draft-07",
    "include_ui_schema": True,
}

# Subscription tier limitations
SUBSCRIPTION_LIMITS = {
    "free": {
        "form_builder_enabled": False,
        "max_form_fields": 20,
        "advanced_components": False,
        "ai_suggestions": False,
        "form_templates": False,
        "form_versioning": False,
    },
    "starter": {
        "form_builder_enabled": True,
        "max_form_fields": 50,
        "advanced_components": True,
        "ai_suggestions": False,
        "form_templates": True,
        "form_versioning": True,
    },
    "pro": {
        "form_builder_enabled": True,
        "max_form_fields": 200,
        "advanced_components": True,
        "ai_suggestions": True,
        "form_templates": True,
        "form_versioning": True,
    },
    "enterprise": {
        "form_builder_enabled": True,
        "max_form_fields": -1,  # Unlimited
        "advanced_components": True,
        "ai_suggestions": True,
        "form_templates": True,
        "form_versioning": True,
    }
}

# Logging configuration
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": os.path.join(BASE_DIR, "form_builder.log"),
}

