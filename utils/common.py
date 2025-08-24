"""
Common utilities for Vaani Sentinel X agents.
Production-ready utilities with proper error handling and logging.
"""

import os
import sys
import json
import logging
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))
from settings import get_config


def setup_logger(
    name: str, 
    user_id: str = "system", 
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up a production-ready logger with rotation and proper formatting.
    
    Args:
        name: Logger name
        user_id: User ID for logging context
        log_file: Optional custom log file name
    
    Returns:
        Configured logger instance
    """
    config = get_config()
    logger = logging.getLogger(name)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Set logging level
    logger.setLevel(getattr(logging, config.logging.level))
    
    # Create formatter
    formatter = logging.Formatter(config.logging.format)
    
    # Console handler
    if config.logging.console_handler_enabled:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(lambda record: setattr(record, 'user', user_id) or True)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if config.logging.file_handler_enabled:
        log_filename = log_file or f"{name}.log"
        log_path = config.get_absolute_path(config.directories.logs_dir) / log_filename
        
        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=config.logging.max_file_size,
            backupCount=config.logging.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, config.logging.level))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(lambda record: setattr(record, 'user', user_id) or True)
        logger.addHandler(file_handler)
    
    return logger


def validate_input(
    data: Any, 
    expected_type: type, 
    field_name: str = "input",
    required: bool = True
) -> bool:
    """
    Validate input data type and requirements.
    
    Args:
        data: Data to validate
        expected_type: Expected data type
        field_name: Name of the field for error messages
        required: Whether the field is required
    
    Returns:
        True if valid, False otherwise
    
    Raises:
        ValueError: If validation fails and data is required
    """
    if data is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return True
    
    if not isinstance(data, expected_type):
        error_msg = f"{field_name} must be of type {expected_type.__name__}, got {type(data).__name__}"
        if required:
            raise ValueError(error_msg)
        return False
    
    return True


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input for security and consistency.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        raise ValueError("Text input must be a string")
    
    # Basic sanitization
    text = text.strip()
    
    # Remove null bytes and control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Limit length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip()
    
    return text


def safe_json_load(file_path: Union[str, Path]) -> Optional[Dict]:
    """
    Safely load JSON file with error handling.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        Loaded JSON data or None if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.getLogger(__name__).warning(f"JSON file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logging.getLogger(__name__).error(f"Invalid JSON in {file_path}: {e}")
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error loading JSON from {file_path}: {e}")
        return None


def safe_json_save(data: Dict, file_path: Union[str, Path], backup: bool = True) -> bool:
    """
    Safely save JSON file with error handling and optional backup.
    
    Args:
        data: Data to save
        file_path: Path to save JSON file
        backup: Whether to create backup of existing file
    
    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)
    
    try:
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if file exists and backup is requested
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(f'.bak.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            file_path.rename(backup_path)
        
        # Save new file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Error saving JSON to {file_path}: {e}")
        return False


def generate_content_id() -> str:
    """Generate a unique content ID."""
    return str(uuid.uuid4())


def generate_checksum(data: Union[str, bytes]) -> str:
    """
    Generate SHA-256 checksum for data integrity verification.
    
    Args:
        data: Data to generate checksum for
    
    Returns:
        Hexadecimal checksum string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def validate_language(language: str) -> bool:
    """
    Validate if language is supported.
    
    Args:
        language: Language code to validate
    
    Returns:
        True if supported, False otherwise
    """
    config = get_config()
    return language in config.agents.supported_languages


def validate_sentiment(sentiment: str) -> bool:
    """
    Validate if sentiment is supported.
    
    Args:
        sentiment: Sentiment to validate
    
    Returns:
        True if supported, False otherwise
    """
    config = get_config()
    return sentiment in config.agents.supported_sentiments


def validate_platform(platform: str) -> bool:
    """
    Validate if platform is supported.
    
    Args:
        platform: Platform to validate
    
    Returns:
        True if supported, False otherwise
    """
    config = get_config()
    return platform in config.agents.supported_platforms


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def safe_file_operation(operation: callable, *args, **kwargs) -> Any:
    """
    Safely execute file operations with error handling.
    
    Args:
        operation: File operation function to execute
        *args, **kwargs: Arguments for the operation
    
    Returns:
        Operation result or None if failed
    """
    try:
        return operation(*args, **kwargs)
    except PermissionError as e:
        logging.getLogger(__name__).error(f"Permission denied: {e}")
        return None
    except FileNotFoundError as e:
        logging.getLogger(__name__).error(f"File not found: {e}")
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"File operation failed: {e}")
        return None


class HealthChecker:
    """Health check utilities for agents and services."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.HealthChecker")
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if all required dependencies are available."""
        dependencies = {
            'requests': self._check_import('requests'),
            'textblob': self._check_import('textblob'),
            'langdetect': self._check_import('langdetect'),
            'groq': self._check_import('groq'),
            'gtts': self._check_import('gtts'),
            'cryptography': self._check_import('cryptography'),
            'better_profanity': self._check_import('better_profanity'),
        }
        return dependencies
    
    def check_directories(self) -> Dict[str, bool]:
        """Check if all required directories exist and are accessible."""
        config = get_config()
        directories = {}
        
        for attr_name in dir(config.directories):
            if not attr_name.startswith('_') and attr_name != 'root_dir':
                dir_path = getattr(config.directories, attr_name)
                full_path = config.get_absolute_path(dir_path)
                directories[attr_name] = full_path.exists() and full_path.is_dir()
        
        return directories
    
    def check_config_files(self) -> Dict[str, bool]:
        """Check if required configuration files exist."""
        config = get_config()
        config_files = {
            'user_profile.json': (config.get_absolute_path('config/user_profile.json')).exists(),
            'language_voice_map.json': (config.get_absolute_path('config/language_voice_map.json')).exists(),
        }
        return config_files
    
    def _check_import(self, module_name: str) -> bool:
        """Check if a module can be imported."""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def full_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        return {
            'timestamp': get_timestamp(),
            'dependencies': self.check_dependencies(),
            'directories': self.check_directories(),
            'config_files': self.check_config_files(),
        }