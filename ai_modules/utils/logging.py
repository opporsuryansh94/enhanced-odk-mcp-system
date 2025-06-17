"""
Logging utilities for AI modules in ODK MCP System.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ..config import AI_CONFIG


def setup_logger(name: str, level: int = None) -> logging.Logger:
    """
    Set up a logger with the specified name and level.
    
    Args:
        name: Logger name.
        level: Logging level. If None, uses the level from AI_CONFIG.
        
    Returns:
        Configured logger.
    """
    # Get logging configuration
    log_config = AI_CONFIG.get("logging", {})
    
    # Set default level if not provided
    if level is None:
        level_name = log_config.get("level", "INFO")
        level = getattr(logging, level_name)
    
    # Create logger
    logger = logging.getLogger(f"odk_mcp.ai.{name}")
    logger.setLevel(level)
    
    # Check if logger already has handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        log_config.get("date_format", "%Y-%m-%d %H:%M:%S")
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if enabled
    if log_config.get("file_logging_enabled", False):
        log_dir = log_config.get("log_dir", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"{name}.log"),
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_ai_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Log an AI event for monitoring and analysis.
    
    Args:
        event_type: Type of event.
        data: Event data.
    """
    # Get logging configuration
    log_config = AI_CONFIG.get("logging", {})
    
    # Check if AI event logging is enabled
    if not log_config.get("ai_event_logging_enabled", False):
        return
    
    # Create event logger
    event_logger = setup_logger("events", logging.INFO)
    
    # Create event data
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "data": data
    }
    
    # Log event
    event_logger.info(json.dumps(event))
    
    # Write to event log file if enabled
    if log_config.get("ai_event_file_logging_enabled", False):
        log_dir = log_config.get("log_dir", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        event_log_path = os.path.join(log_dir, "ai_events.jsonl")
        
        try:
            with open(event_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            event_logger.error(f"Error writing to event log file: {e}")


class AILogger:
    """
    Logger for AI modules with additional context.
    """
    
    def __init__(self, name: str, context: Dict[str, Any] = None):
        """
        Initialize the AI logger.
        
        Args:
            name: Logger name.
            context: Additional context to include in logs.
        """
        self.logger = setup_logger(name)
        self.context = context or {}
        self.name = name
    
    def _format_message(self, message: str) -> str:
        """
        Format message with context.
        
        Args:
            message: Log message.
            
        Returns:
            Formatted message.
        """
        if not self.context:
            return message
        
        context_str = " ".join(f"{k}={v}" for k, v in self.context.items())
        return f"{message} [{context_str}]"
    
    def debug(self, message: str, **kwargs) -> None:
        """
        Log a debug message.
        
        Args:
            message: Log message.
            **kwargs: Additional context for this log entry.
        """
        context = {**self.context, **kwargs}
        self.logger.debug(self._format_message(message), extra={"context": context})
    
    def info(self, message: str, **kwargs) -> None:
        """
        Log an info message.
        
        Args:
            message: Log message.
            **kwargs: Additional context for this log entry.
        """
        context = {**self.context, **kwargs}
        self.logger.info(self._format_message(message), extra={"context": context})
    
    def warning(self, message: str, **kwargs) -> None:
        """
        Log a warning message.
        
        Args:
            message: Log message.
            **kwargs: Additional context for this log entry.
        """
        context = {**self.context, **kwargs}
        self.logger.warning(self._format_message(message), extra={"context": context})
    
    def error(self, message: str, **kwargs) -> None:
        """
        Log an error message.
        
        Args:
            message: Log message.
            **kwargs: Additional context for this log entry.
        """
        context = {**self.context, **kwargs}
        self.logger.error(self._format_message(message), extra={"context": context})
    
    def critical(self, message: str, **kwargs) -> None:
        """
        Log a critical message.
        
        Args:
            message: Log message.
            **kwargs: Additional context for this log entry.
        """
        context = {**self.context, **kwargs}
        self.logger.critical(self._format_message(message), extra={"context": context})
    
    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Log an AI event.
        
        Args:
            event_type: Type of event.
            data: Event data.
        """
        # Add context to data
        event_data = {**data, "module": self.name, **self.context}
        
        # Log event
        log_ai_event(event_type, event_data)
    
    def with_context(self, **kwargs) -> 'AILogger':
        """
        Create a new logger with additional context.
        
        Args:
            **kwargs: Additional context.
            
        Returns:
            New logger with combined context.
        """
        new_context = {**self.context, **kwargs}
        return AILogger(self.name, new_context)

