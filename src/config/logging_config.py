"""
Logging configuration for OSRS Discord Bot.

Provides structured logging with proper formatting, rotation,
and different output destinations for development and production.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging in production."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for structured logging."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname", 
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "getMessage"
            }:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for development console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console output."""
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Create colored level name
        colored_level = f"{log_color}{record.levelname:8}{reset_color}"
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Create the formatted message
        formatted_message = (
            f"{timestamp} | {colored_level} | "
            f"{record.name:20} | {record.getMessage()}"
        )
        
        # Add exception information if present
        if record.exc_info:
            formatted_message += f"\n{self.formatException(record.exc_info)}"
        
        return formatted_message


def setup_logging(settings: Optional[object] = None) -> None:
    """
    Setup comprehensive logging configuration.
    
    Args:
        settings: Configuration object with logging settings.
                 If None, uses environment variables or defaults.
    """
    # Import here to avoid circular imports
    if settings is None:
        from config.settings import Settings
        settings = Settings()
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set root logger level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Use colored formatter for development, JSON for production
    if settings.ENVIRONMENT == "development" or settings.DEBUG:
        console_formatter = ColoredFormatter()
    else:
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Setup file handler with rotation
    if settings.LOG_FILE:
        setup_file_logging(settings, log_level)
    
    # Setup specific loggers
    setup_component_loggers(settings, log_level)
    
    # Log the logging setup completion
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured - Level: {settings.LOG_LEVEL}, "
        f"Environment: {settings.ENVIRONMENT}, "
        f"File: {settings.LOG_FILE if settings.LOG_FILE else 'None'}"
    )


def setup_file_logging(settings: object, log_level: int) -> None:
    """Setup rotating file handler for persistent logging."""
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=settings.LOG_MAX_SIZE_MB * 1024 * 1024,  # Convert MB to bytes
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    
    # Always use JSON formatter for file output
    file_formatter = JSONFormatter()
    file_handler.setFormatter(file_formatter)
    
    # Add to root logger
    logging.getLogger().addHandler(file_handler)


def setup_component_loggers(settings: object, log_level: int) -> None:
    """Setup specific loggers for different components."""
    
    # Discord.py logger - reduce verbosity in production
    discord_logger = logging.getLogger('discord')
    if settings.ENVIRONMENT == "production":
        discord_logger.setLevel(logging.WARNING)
    else:
        discord_logger.setLevel(logging.INFO)
    
    # HTTP client logger
    http_logger = logging.getLogger('aiohttp')
    http_logger.setLevel(logging.WARNING)  # Reduce HTTP noise
    
    # Application component loggers
    component_loggers = [
        'core.bot',
        'events',
        'data.repositories',
        'external.wise_old_man',
        'commands',
        'utils'
    ]
    
    for logger_name in component_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with proper configuration.
    
    Args:
        name: Logger name, typically __name__ of the calling module
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capability to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for the class."""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")


def log_function_call(func):
    """Decorator to log function calls with parameters and execution time."""
    import functools
    import time
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        # Log function entry
        logger.debug(
            f"Entering {func.__name__}",
            extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
        )
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log successful completion
            logger.debug(
                f"Completed {func.__name__} in {execution_time:.3f}s",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                    "success": True
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log exception
            logger.error(
                f"Error in {func.__name__} after {execution_time:.3f}s: {e}",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                    "success": False,
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        # Log function entry
        logger.debug(
            f"Entering {func.__name__}",
            extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            }
        )
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log successful completion
            logger.debug(
                f"Completed {func.__name__} in {execution_time:.3f}s",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                    "success": True
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log exception
            logger.error(
                f"Error in {func.__name__} after {execution_time:.3f}s: {e}",
                extra={
                    "function": func.__name__,
                    "execution_time": execution_time,
                    "success": False,
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            raise
    
    # Return appropriate wrapper based on function type
    if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
        return async_wrapper
    else:
        return sync_wrapper