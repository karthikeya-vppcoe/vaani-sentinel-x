"""
Centralized configuration management for Vaani Sentinel X.
Handles environment variables, validation, and default values.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """Database configuration."""
    sqlite_db_path: str = "data/vaani.db"
    scheduler_db_dir: str = "scheduler_db"
    analytics_db_dir: str = "analytics_db"


@dataclass  
class DirectoryConfig:
    """Directory paths configuration."""
    root_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    content_dir: str = "content"
    raw_dir: str = "content/raw" 
    structured_dir: str = "content/structured"
    multilingual_ready_dir: str = "content/multilingual_ready"
    content_ready_dir: str = "content/content_ready"
    content_final_dir: str = "content/content_final"
    logs_dir: str = "logs"
    archives_dir: str = "archives"
    scheduled_posts_dir: str = "scheduled_posts"
    config_dir: str = "config"


@dataclass
class SecurityConfig:
    """Security configuration."""
    jwt_secret: str = ""
    encryption_key: Optional[str] = None
    session_timeout: int = 3600  # 1 hour
    max_login_attempts: int = 5
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour


@dataclass
class APIConfig:
    """API keys and external service configuration."""
    groq_api_key: str = ""
    google_api_key: str = ""
    elevenlabs_api_key: str = ""
    openai_api_key: str = ""


@dataclass
class AgentConfig:
    """Agent-specific configuration."""
    default_languages: List[str] = field(default_factory=lambda: ["en"])
    supported_languages: List[str] = field(default_factory=lambda: [
        'en', 'hi', 'sa', 'mr', 'ta', 'te', 'kn', 'ml', 'bn', 'gu', 'pa',
        'es', 'fr', 'de', 'zh', 'ja', 'ru', 'ar', 'pt', 'it'
    ])
    default_sentiment: str = "neutral"
    supported_sentiments: List[str] = field(default_factory=lambda: [
        "uplifting", "neutral", "devotional"
    ])
    supported_platforms: List[str] = field(default_factory=lambda: [
        "twitter", "instagram", "linkedin", "sanatan"
    ])
    max_content_length: int = 4000
    pipeline_timeout: int = 300  # 5 minutes


@dataclass
class WebConfig:
    """Web UI configuration."""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    secret_key: str = ""


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - User: %(user)s - %(message)s"
    file_handler_enabled: bool = True
    console_handler_enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


class Config:
    """Main configuration class."""
    
    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration from environment variables."""
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to load from multiple possible locations
            for env_path in [".env", "config/.env", "../.env"]:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    break
        
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.database = self._init_database_config()
        self.directories = self._init_directory_config()
        self.security = self._init_security_config()
        self.apis = self._init_api_config()
        self.agents = self._init_agent_config()
        self.web = self._init_web_config()
        self.logging = self._init_logging_config()
        
        # Validate configuration
        self._validate_config()
        
        # Ensure directories exist
        self._create_directories()
    
    def _init_database_config(self) -> DatabaseConfig:
        """Initialize database configuration."""
        return DatabaseConfig(
            sqlite_db_path=os.getenv("SQLITE_DB_PATH", "data/vaani.db"),
            scheduler_db_dir=os.getenv("SCHEDULER_DB_DIR", "scheduler_db"),
            analytics_db_dir=os.getenv("ANALYTICS_DB_DIR", "analytics_db")
        )
    
    def _init_directory_config(self) -> DirectoryConfig:
        """Initialize directory configuration."""
        root_dir = Path(os.getenv("ROOT_DIR", Path(__file__).parent.parent))
        return DirectoryConfig(
            root_dir=root_dir,
            content_dir=os.getenv("CONTENT_DIR", "content"),
            raw_dir=os.getenv("RAW_DIR", "content/raw"),
            structured_dir=os.getenv("STRUCTURED_DIR", "content/structured"),
            multilingual_ready_dir=os.getenv("MULTILINGUAL_READY_DIR", "content/multilingual_ready"),
            content_ready_dir=os.getenv("CONTENT_READY_DIR", "content/content_ready"),
            content_final_dir=os.getenv("CONTENT_FINAL_DIR", "content/content_final"),
            logs_dir=os.getenv("LOGS_DIR", "logs"),
            archives_dir=os.getenv("ARCHIVES_DIR", "archives"),
            scheduled_posts_dir=os.getenv("SCHEDULED_POSTS_DIR", "scheduled_posts"),
            config_dir=os.getenv("CONFIG_DIR", "config")
        )
    
    def _init_security_config(self) -> SecurityConfig:
        """Initialize security configuration."""
        return SecurityConfig(
            jwt_secret=os.getenv("JWT_SECRET", ""),
            encryption_key=os.getenv("ENCRYPTION_KEY"),
            session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600")),
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
            rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
            rate_limit_window=int(os.getenv("RATE_LIMIT_WINDOW", "3600"))
        )
    
    def _init_api_config(self) -> APIConfig:
        """Initialize API configuration."""
        return APIConfig(
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", "")
        )
    
    def _init_agent_config(self) -> AgentConfig:
        """Initialize agent configuration."""
        default_languages = os.getenv("DEFAULT_LANGUAGES", "en").split(",")
        return AgentConfig(
            default_languages=[lang.strip() for lang in default_languages],
            default_sentiment=os.getenv("DEFAULT_SENTIMENT", "neutral"),
            max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "4000")),
            pipeline_timeout=int(os.getenv("PIPELINE_TIMEOUT", "300"))
        )
    
    def _init_web_config(self) -> WebConfig:
        """Initialize web configuration."""
        return WebConfig(
            host=os.getenv("WEB_HOST", "0.0.0.0"),
            port=int(os.getenv("WEB_PORT", "5000")),
            debug=os.getenv("WEB_DEBUG", "false").lower() == "true",
            secret_key=os.getenv("SECRET_KEY", "")
        )
    
    def _init_logging_config(self) -> LoggingConfig:
        """Initialize logging configuration."""
        return LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            file_handler_enabled=os.getenv("LOG_FILE_ENABLED", "true").lower() == "true",
            console_handler_enabled=os.getenv("LOG_CONSOLE_ENABLED", "true").lower() == "true",
            max_file_size=int(os.getenv("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))
        )
    
    def _validate_config(self) -> None:
        """Validate configuration and show warnings for missing required values."""
        warnings = []
        
        # Check required API keys for production
        if self.environment == "production":
            if not self.security.jwt_secret:
                warnings.append("JWT_SECRET is required for production")
            if not self.web.secret_key:
                warnings.append("SECRET_KEY is required for production")
            if not self.apis.groq_api_key:
                warnings.append("GROQ_API_KEY is recommended for production")
        
        # Check directory permissions
        try:
            os.makedirs(self.directories.logs_dir, exist_ok=True)
        except PermissionError:
            warnings.append(f"Cannot create logs directory: {self.directories.logs_dir}")
        
        # Log warnings
        if warnings:
            logger = logging.getLogger(__name__)
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
    
    def _create_directories(self) -> None:
        """Create required directories if they don't exist."""
        dirs_to_create = [
            self.directories.logs_dir,
            self.directories.content_dir,
            self.directories.raw_dir,
            self.directories.structured_dir,
            self.directories.multilingual_ready_dir,
            self.directories.content_ready_dir,
            self.directories.content_final_dir,
            self.directories.archives_dir,
            self.directories.scheduled_posts_dir,
            self.database.scheduler_db_dir,
            self.database.analytics_db_dir,
        ]
        
        for dir_path in dirs_to_create:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except OSError as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create directory {dir_path}: {e}")
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path based on root directory."""
        return self.directories.root_dir / relative_path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "environment": self.environment,
            "database": {
                "sqlite_db_path": self.database.sqlite_db_path,
                "scheduler_db_dir": self.database.scheduler_db_dir,
                "analytics_db_dir": self.database.analytics_db_dir,
            },
            "directories": {
                "root_dir": str(self.directories.root_dir),
                "content_dir": self.directories.content_dir,
                "logs_dir": self.directories.logs_dir,
            },
            "agents": {
                "default_languages": self.agents.default_languages,
                "supported_languages": self.agents.supported_languages,
                "default_sentiment": self.agents.default_sentiment,
                "supported_sentiments": self.agents.supported_sentiments,
                "supported_platforms": self.agents.supported_platforms,
            },
            "web": {
                "host": self.web.host,
                "port": self.web.port,
                "debug": self.web.debug,
            }
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config(env_file)
    return _config


def reload_config(env_file: Optional[str] = None) -> Config:
    """Reload the global configuration instance."""
    global _config
    _config = Config(env_file)
    return _config