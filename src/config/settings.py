"""
Configuration management for OSRS Discord Bot.

Handles environment variables, validation, and provides
centralized access to all configuration settings.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """Database-related configuration settings."""
    users_file: str = "database/users.json"
    competitions_file: str = "database/competitions.json"
    leaderboards_file: str = "database/leaderboards.json"
    trivia_questions_file: str = "database/trivia_questions.json"
    backup_interval_hours: int = 6
    max_backup_files: int = 10


@dataclass
class APIConfig:
    """External API configuration settings."""
    wise_old_man_base_url: str = "https://api.wiseoldman.net/v2"
    wise_old_man_rate_limit: int = 60  # requests per minute
    request_timeout: int = 10  # seconds
    max_retries: int = 3
    backoff_factor: float = 2.0


@dataclass
class BotConfig:
    """Discord bot behavior configuration."""
    command_prefix: str = "!"
    max_concurrent_competitions: int = 5
    default_competition_duration_hours: int = 168  # 1 week
    max_participants_per_competition: int = 100
    trivia_question_time_limit: int = 30  # seconds
    race_registration_time_limit: int = 300  # 5 minutes


class Settings:
    """
    Centralized configuration management with environment variable support.
    
    Loads settings from environment variables with fallback defaults,
    validates configuration, and provides type-safe access to settings.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Discord Configuration (Required)
        self.DISCORD_TOKEN = self._get_env_var("DISCORD_TOKEN", required=True)
        self.GUILD_ID = self._get_env_var("GUILD_ID", required=True, var_type=int)
        
        # Admin Configuration
        self.ADMIN_ROLE_ID = self._get_env_var("ADMIN_ROLE_ID", var_type=int)
        self.ADMIN_USER_IDS = self._get_env_list("ADMIN_USER_IDS", var_type=int)
        
        # Logging Configuration
        self.LOG_LEVEL = self._get_env_var("LOG_LEVEL", default="INFO")
        self.LOG_FILE = self._get_env_var("LOG_FILE", default="logs/osrs_bot.log")
        self.LOG_MAX_SIZE_MB = self._get_env_var("LOG_MAX_SIZE_MB", default=10, var_type=int)
        self.LOG_BACKUP_COUNT = self._get_env_var("LOG_BACKUP_COUNT", default=5, var_type=int)
        
        # Development/Production Environment
        self.ENVIRONMENT = self._get_env_var("ENVIRONMENT", default="development")
        self.DEBUG = self._get_env_var("DEBUG", default=False, var_type=bool)
        
        # Component Configurations
        self.database = DatabaseConfig()
        self.api = APIConfig()
        self.bot = BotConfig()
        
        # Override component configs from environment if provided
        self._load_component_configs()
        
        # Ensure required directories exist
        self._ensure_directories()
    
    def _get_env_var(self, name: str, default: Any = None, 
                     required: bool = False, var_type: type = str) -> Any:
        """
        Get environment variable with type conversion and validation.
        
        Args:
            name: Environment variable name
            default: Default value if not found
            required: Whether the variable is required
            var_type: Type to convert the value to
            
        Returns:
            The environment variable value converted to the specified type
            
        Raises:
            ValueError: If required variable is missing or type conversion fails
        """
        value = os.getenv(name)
        
        if value is None:
            if required:
                raise ValueError(f"Required environment variable {name} is not set")
            return default
        
        try:
            if var_type == bool:
                return value.lower() in ("true", "1", "yes", "on")
            elif var_type == int:
                return int(value)
            elif var_type == float:
                return float(value)
            elif var_type == list:
                return [item.strip() for item in value.split(",") if item.strip()]
            else:
                return value
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to convert {name}='{value}' to {var_type.__name__}: {e}")
    
    def _get_env_list(self, name: str, default: Optional[List] = None, 
                      var_type: type = str) -> List[Any]:
        """Get comma-separated environment variable as a list."""
        value = os.getenv(name)
        if value is None:
            return default or []
        
        try:
            items = [item.strip() for item in value.split(",") if item.strip()]
            if var_type != str:
                items = [var_type(item) for item in items]
            return items
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Failed to parse {name} as list: {e}")
            return default or []
    
    def _load_component_configs(self) -> None:
        """Load component-specific configurations from environment variables."""
        # Database config overrides
        self.database.users_file = self._get_env_var(
            "DB_USERS_FILE", default=self.database.users_file
        )
        self.database.competitions_file = self._get_env_var(
            "DB_COMPETITIONS_FILE", default=self.database.competitions_file
        )
        self.database.leaderboards_file = self._get_env_var(
            "DB_LEADERBOARDS_FILE", default=self.database.leaderboards_file
        )
        self.database.backup_interval_hours = self._get_env_var(
            "DB_BACKUP_INTERVAL_HOURS", 
            default=self.database.backup_interval_hours, 
            var_type=int
        )
        
        # API config overrides
        self.api.wise_old_man_base_url = self._get_env_var(
            "WOM_BASE_URL", default=self.api.wise_old_man_base_url
        )
        self.api.wise_old_man_rate_limit = self._get_env_var(
            "WOM_RATE_LIMIT", 
            default=self.api.wise_old_man_rate_limit, 
            var_type=int
        )
        self.api.request_timeout = self._get_env_var(
            "API_TIMEOUT", default=self.api.request_timeout, var_type=int
        )
        
        # Bot config overrides
        self.bot.max_concurrent_competitions = self._get_env_var(
            "MAX_CONCURRENT_COMPETITIONS",
            default=self.bot.max_concurrent_competitions,
            var_type=int
        )
        self.bot.default_competition_duration_hours = self._get_env_var(
            "DEFAULT_COMPETITION_DURATION_HOURS",
            default=self.bot.default_competition_duration_hours,
            var_type=int
        )
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        directories = [
            Path(self.LOG_FILE).parent,
            Path(self.database.users_file).parent,
            Path(self.database.competitions_file).parent,
            Path(self.database.leaderboards_file).parent,
            Path(self.database.trivia_questions_file).parent,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> bool:
        """
        Validate all configuration settings.
        
        Returns:
            True if all settings are valid, False otherwise
        """
        errors = []
        
        # Validate required Discord settings
        if not self.DISCORD_TOKEN or len(self.DISCORD_TOKEN) < 50:
            errors.append("Invalid or missing DISCORD_TOKEN")
        
        if not self.GUILD_ID or self.GUILD_ID <= 0:
            errors.append("Invalid or missing GUILD_ID")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            errors.append(f"Invalid LOG_LEVEL: {self.LOG_LEVEL}")
        
        # Validate numeric settings
        if self.api.wise_old_man_rate_limit <= 0:
            errors.append("WOM_RATE_LIMIT must be positive")
        
        if self.api.request_timeout <= 0:
            errors.append("API_TIMEOUT must be positive")
        
        if self.bot.max_concurrent_competitions <= 0:
            errors.append("MAX_CONCURRENT_COMPETITIONS must be positive")
        
        # Log validation results
        if errors:
            for error in errors:
                self.logger.error(f"Configuration validation error: {error}")
            return False
        
        self.logger.info("Configuration validation passed")
        return True
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information for debugging/monitoring."""
        return {
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "log_level": self.LOG_LEVEL,
            "guild_id": self.GUILD_ID,
            "admin_role_configured": self.ADMIN_ROLE_ID is not None,
            "admin_users_count": len(self.ADMIN_USER_IDS),
            "database_files": {
                "users": self.database.users_file,
                "competitions": self.database.competitions_file,
                "leaderboards": self.database.leaderboards_file,
                "trivia": self.database.trivia_questions_file,
            },
            "api_config": {
                "wom_base_url": self.api.wise_old_man_base_url,
                "rate_limit": self.api.wise_old_man_rate_limit,
                "timeout": self.api.request_timeout,
            }
        }