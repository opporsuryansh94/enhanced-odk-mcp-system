"""
Validation utilities for AI modules in ODK MCP System.
"""

import re
import json
from typing import Dict, List, Tuple, Union, Optional, Any, Callable

from ..config import AI_CONFIG
from .logging import setup_logger


class Validator:
    """
    Validator for AI module inputs and outputs.
    
    This class provides methods to validate inputs and outputs for AI modules.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the validator.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["validation"]
        self.logger = setup_logger("validator")
    
    def validate_input(self, input_data: Any, schema: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate input data against a schema.
        
        Args:
            input_data: Input data to validate.
            schema: Schema to validate against.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            # Check type
            if "type" in schema:
                if not self._validate_type(input_data, schema["type"]):
                    return False, f"Invalid type. Expected {schema['type']}, got {type(input_data).__name__}"
            
            # Check required fields
            if schema.get("type") == "object" and "required" in schema:
                for field in schema["required"]:
                    if field not in input_data:
                        return False, f"Missing required field: {field}"
            
            # Check properties
            if schema.get("type") == "object" and "properties" in schema:
                for field, field_schema in schema["properties"].items():
                    if field in input_data:
                        is_valid, error = self.validate_input(input_data[field], field_schema)
                        if not is_valid:
                            return False, f"Invalid field {field}: {error}"
            
            # Check items
            if schema.get("type") == "array" and "items" in schema:
                for i, item in enumerate(input_data):
                    is_valid, error = self.validate_input(item, schema["items"])
                    if not is_valid:
                        return False, f"Invalid item at index {i}: {error}"
            
            # Check enum
            if "enum" in schema:
                if input_data not in schema["enum"]:
                    return False, f"Value must be one of {schema['enum']}, got {input_data}"
            
            # Check minimum
            if "minimum" in schema:
                if input_data < schema["minimum"]:
                    return False, f"Value must be >= {schema['minimum']}, got {input_data}"
            
            # Check maximum
            if "maximum" in schema:
                if input_data > schema["maximum"]:
                    return False, f"Value must be <= {schema['maximum']}, got {input_data}"
            
            # Check minLength
            if "minLength" in schema:
                if len(input_data) < schema["minLength"]:
                    return False, f"Length must be >= {schema['minLength']}, got {len(input_data)}"
            
            # Check maxLength
            if "maxLength" in schema:
                if len(input_data) > schema["maxLength"]:
                    return False, f"Length must be <= {schema['maxLength']}, got {len(input_data)}"
            
            # Check pattern
            if "pattern" in schema:
                if not re.match(schema["pattern"], input_data):
                    return False, f"Value must match pattern {schema['pattern']}"
            
            # Check format
            if "format" in schema:
                is_valid, error = self._validate_format(input_data, schema["format"])
                if not is_valid:
                    return False, error
            
            return True, None
        except Exception as e:
            self.logger.error(f"Error validating input: {e}")
            return False, str(e)
    
    def validate_output(self, output_data: Any, schema: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate output data against a schema.
        
        Args:
            output_data: Output data to validate.
            schema: Schema to validate against.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        # Use the same validation logic as for inputs
        return self.validate_input(output_data, schema)
    
    def sanitize_input(self, input_data: Any, schema: Dict) -> Any:
        """
        Sanitize input data according to a schema.
        
        Args:
            input_data: Input data to sanitize.
            schema: Schema to sanitize against.
            
        Returns:
            Sanitized input data.
        """
        try:
            # Handle different types
            if schema.get("type") == "string":
                return self._sanitize_string(input_data, schema)
            elif schema.get("type") == "number" or schema.get("type") == "integer":
                return self._sanitize_number(input_data, schema)
            elif schema.get("type") == "boolean":
                return self._sanitize_boolean(input_data)
            elif schema.get("type") == "object":
                return self._sanitize_object(input_data, schema)
            elif schema.get("type") == "array":
                return self._sanitize_array(input_data, schema)
            else:
                return input_data
        except Exception as e:
            self.logger.error(f"Error sanitizing input: {e}")
            return input_data
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        Validate that a value has the expected type.
        
        Args:
            value: Value to validate.
            expected_type: Expected type.
            
        Returns:
            True if valid, False otherwise.
        """
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "object":
            return isinstance(value, dict)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "null":
            return value is None
        else:
            return True
    
    def _validate_format(self, value: str, format_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a string value has the expected format.
        
        Args:
            value: String value to validate.
            format_name: Format name.
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        if format_name == "email":
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, value):
                return False, "Invalid email format"
        elif format_name == "date":
            pattern = r'^\d{4}-\d{2}-\d{2}$'
            if not re.match(pattern, value):
                return False, "Invalid date format (YYYY-MM-DD)"
        elif format_name == "time":
            pattern = r'^\d{2}:\d{2}:\d{2}$'
            if not re.match(pattern, value):
                return False, "Invalid time format (HH:MM:SS)"
        elif format_name == "date-time":
            pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'
            if not re.match(pattern, value):
                return False, "Invalid date-time format (ISO 8601)"
        elif format_name == "uri":
            pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
            if not re.match(pattern, value):
                return False, "Invalid URI format"
        elif format_name == "ipv4":
            pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(pattern, value):
                return False, "Invalid IPv4 format"
        elif format_name == "ipv6":
            pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
            if not re.match(pattern, value):
                return False, "Invalid IPv6 format"
        
        return True, None
    
    def _sanitize_string(self, value: Any, schema: Dict) -> str:
        """
        Sanitize a string value.
        
        Args:
            value: Value to sanitize.
            schema: Schema to sanitize against.
            
        Returns:
            Sanitized string value.
        """
        # Convert to string
        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception:
                value = ""
        
        # Trim whitespace
        value = value.strip()
        
        # Apply maxLength
        if "maxLength" in schema:
            value = value[:schema["maxLength"]]
        
        return value
    
    def _sanitize_number(self, value: Any, schema: Dict) -> Union[int, float]:
        """
        Sanitize a number value.
        
        Args:
            value: Value to sanitize.
            schema: Schema to sanitize against.
            
        Returns:
            Sanitized number value.
        """
        # Convert to number
        if isinstance(value, str):
            try:
                value = float(value)
                if schema.get("type") == "integer":
                    value = int(value)
            except Exception:
                value = 0
        elif not isinstance(value, (int, float)) or isinstance(value, bool):
            value = 0
        
        # Apply minimum
        if "minimum" in schema:
            value = max(value, schema["minimum"])
        
        # Apply maximum
        if "maximum" in schema:
            value = min(value, schema["maximum"])
        
        return value
    
    def _sanitize_boolean(self, value: Any) -> bool:
        """
        Sanitize a boolean value.
        
        Args:
            value: Value to sanitize.
            
        Returns:
            Sanitized boolean value.
        """
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "y", "t"]
        elif isinstance(value, (int, float)):
            return value != 0
        else:
            return bool(value)
    
    def _sanitize_object(self, value: Any, schema: Dict) -> Dict:
        """
        Sanitize an object value.
        
        Args:
            value: Value to sanitize.
            schema: Schema to sanitize against.
            
        Returns:
            Sanitized object value.
        """
        # Convert to object
        if not isinstance(value, dict):
            try:
                if isinstance(value, str):
                    value = json.loads(value)
                else:
                    value = {}
            except Exception:
                value = {}
        
        # Sanitize properties
        if "properties" in schema:
            for field, field_schema in schema["properties"].items():
                if field in value:
                    value[field] = self.sanitize_input(value[field], field_schema)
        
        # Add default values for missing required fields
        if "required" in schema and "properties" in schema:
            for field in schema["required"]:
                if field not in value and field in schema["properties"]:
                    field_schema = schema["properties"][field]
                    if "default" in field_schema:
                        value[field] = field_schema["default"]
                    else:
                        # Create a default value based on type
                        field_type = field_schema.get("type")
                        if field_type == "string":
                            value[field] = ""
                        elif field_type == "number" or field_type == "integer":
                            value[field] = 0
                        elif field_type == "boolean":
                            value[field] = False
                        elif field_type == "object":
                            value[field] = {}
                        elif field_type == "array":
                            value[field] = []
                        else:
                            value[field] = None
        
        return value
    
    def _sanitize_array(self, value: Any, schema: Dict) -> List:
        """
        Sanitize an array value.
        
        Args:
            value: Value to sanitize.
            schema: Schema to sanitize against.
            
        Returns:
            Sanitized array value.
        """
        # Convert to array
        if not isinstance(value, list):
            try:
                if isinstance(value, str):
                    value = json.loads(value)
                    if not isinstance(value, list):
                        value = [value]
                else:
                    value = [value] if value is not None else []
            except Exception:
                value = []
        
        # Sanitize items
        if "items" in schema:
            value = [self.sanitize_input(item, schema["items"]) for item in value]
        
        # Apply minItems
        if "minItems" in schema:
            while len(value) < schema["minItems"]:
                if "items" in schema:
                    # Create a default item based on the items schema
                    item_schema = schema["items"]
                    item_type = item_schema.get("type")
                    if item_type == "string":
                        value.append("")
                    elif item_type == "number" or item_type == "integer":
                        value.append(0)
                    elif item_type == "boolean":
                        value.append(False)
                    elif item_type == "object":
                        value.append({})
                    elif item_type == "array":
                        value.append([])
                    else:
                        value.append(None)
                else:
                    value.append(None)
        
        # Apply maxItems
        if "maxItems" in schema:
            value = value[:schema["maxItems"]]
        
        return value

