"""
Custom exception definitions for OSRS Discord Bot.

Provides a hierarchy of exceptions for different error scenarios
with proper error codes and context information.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(Enum):
    """Enumeration of error codes for categorizing exceptions."""
    
    # Configuration Errors (1000-1099)
    CONFIGURATION_ERROR = 1000
    MISSING_REQUIRED_CONFIG = 1001
    INVALID_CONFIG_VALUE = 1002
    
    # Database Errors (1100-1199)
    DATABASE_ERROR = 1100
    FILE_NOT_FOUND = 1101
    CORRUPTION_ERROR = 1102
    PERMISSION_DENIED = 1103
    BACKUP_ERROR = 1104
    
    # Competition Errors (1200-1299)
    COMPETITION_ERROR = 1200
    COMPETITION_NOT_FOUND = 1201
    COMPETITION_ALREADY_EXISTS = 1202
    COMPETITION_FULL = 1203
    COMPETITION_CLOSED = 1204
    INVALID_COMPETITION_TYPE = 1205
    PARTICIPANT_ALREADY_REGISTERED = 1206
    PARTICIPANT_NOT_REGISTERED = 1207
    
    # User Errors (1300-1399)
    USER_ERROR = 1300
    USER_NOT_FOUND = 1301
    USER_ALREADY_EXISTS = 1302
    INVALID_USERNAME = 1303
    USER_NOT_LINKED = 1304
    
    # API Errors (1400-1499)
    API_ERROR = 1400
    API_TIMEOUT = 1401
    API_RATE_LIMITED = 1402
    API_UNAUTHORIZED = 1403
    API_NOT_FOUND = 1404
    API_SERVER_ERROR = 1405
    
    # Discord Errors (1500-1599)
    DISCORD_ERROR = 1500
    PERMISSION_ERROR = 1501
    CHANNEL_NOT_FOUND = 1502
    GUILD_NOT_FOUND = 1503
    MESSAGE_TOO_LONG = 1504
    
    # Validation Errors (1600-1699)
    VALIDATION_ERROR = 1600
    INVALID_INPUT = 1601
    MISSING_REQUIRED_FIELD = 1602
    VALUE_OUT_OF_RANGE = 1603


class OSRSBotException(Exception):
    """
    Base exception class for all OSRS Bot specific exceptions.
    
    Provides error codes, context information, and user-friendly messages.
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Technical error message for logging
            error_code: Categorized error code
            context: Additional context information
            user_message: User-friendly error message
            original_exception: Original exception that caused this error
        """
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.user_message = user_message or "An error occurred. Please try again."
        self.original_exception = original_exception
    
    def __str__(self) -> str:
        """Return string representation of the exception."""
        return f"[{self.error_code.name}] {super().__str__()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code.value,
            "error_name": self.error_code.name,
            "message": str(self),
            "user_message": self.user_message,
            "context": self.context,
            "original_exception": str(self.original_exception) if self.original_exception else None
        }


class ConfigurationError(OSRSBotException):
    """Raised when there are configuration-related errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            context=context,
            user_message="Bot configuration error. Please contact an administrator.",
            **kwargs
        )


class DatabaseError(OSRSBotException):
    """Raised when database operations fail."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        file_path: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if operation:
            context['operation'] = operation
        if file_path:
            context['file_path'] = file_path
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            context=context,
            user_message="Database error occurred. Please try again later.",
            **kwargs
        )


class CompetitionError(OSRSBotException):
    """Raised when competition-related operations fail."""
    
    def __init__(
        self,
        message: str,
        competition_id: Optional[str] = None,
        competition_type: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if competition_id:
            context['competition_id'] = competition_id
        if competition_type:
            context['competition_type'] = competition_type
        
        super().__init__(
            message=message,
            error_code=ErrorCode.COMPETITION_ERROR,
            context=context,
            user_message="Competition operation failed. Please check the competition details.",
            **kwargs
        )


class CompetitionNotFoundError(CompetitionError):
    """Raised when a requested competition cannot be found."""
    
    def __init__(self, competition_id: str, **kwargs):
        super().__init__(
            message=f"Competition not found: {competition_id}",
            error_code=ErrorCode.COMPETITION_NOT_FOUND,
            competition_id=competition_id,
            user_message=f"Competition '{competition_id}' was not found.",
            **kwargs
        )


class CompetitionFullError(CompetitionError):
    """Raised when trying to join a full competition."""
    
    def __init__(self, competition_id: str, max_participants: int, **kwargs):
        super().__init__(
            message=f"Competition {competition_id} is full ({max_participants} participants)",
            error_code=ErrorCode.COMPETITION_FULL,
            competition_id=competition_id,
            context={'max_participants': max_participants},
            user_message=f"Competition is full (maximum {max_participants} participants).",
            **kwargs
        )


class UserError(OSRSBotException):
    """Raised when user-related operations fail."""
    
    def __init__(
        self,
        message: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if user_id:
            context['user_id'] = user_id
        if username:
            context['username'] = username
        
        super().__init__(
            message=message,
            error_code=ErrorCode.USER_ERROR,
            context=context,
            user_message="User operation failed. Please check your information.",
            **kwargs
        )


class UserNotFoundError(UserError):
    """Raised when a requested user cannot be found."""
    
    def __init__(self, identifier: str, **kwargs):
        super().__init__(
            message=f"User not found: {identifier}",
            error_code=ErrorCode.USER_NOT_FOUND,
            user_message=f"User '{identifier}' was not found.",
            **kwargs
        )


class APIError(OSRSBotException):
    """Raised when external API operations fail."""
    
    def __init__(
        self,
        message: str,
        api_name: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if api_name:
            context['api_name'] = api_name
        if status_code:
            context['status_code'] = status_code
        
        super().__init__(
            message=message,
            error_code=ErrorCode.API_ERROR,
            context=context,
            user_message="External service temporarily unavailable. Please try again later.",
            **kwargs
        )


class APIRateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(
        self,
        api_name: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if retry_after:
            context['retry_after'] = retry_after
        
        super().__init__(
            message=f"Rate limit exceeded for {api_name}",
            error_code=ErrorCode.API_RATE_LIMITED,
            api_name=api_name,
            context=context,
            user_message=f"Too many requests. Please try again in {retry_after or 60} seconds.",
            **kwargs
        )


class DiscordError(OSRSBotException):
    """Raised when Discord-related operations fail."""
    
    def __init__(
        self,
        message: str,
        guild_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if guild_id:
            context['guild_id'] = guild_id
        if channel_id:
            context['channel_id'] = channel_id
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DISCORD_ERROR,
            context=context,
            user_message="Discord operation failed. Please try again.",
            **kwargs
        )


class PermissionError(DiscordError):
    """Raised when user lacks required permissions."""
    
    def __init__(
        self,
        required_permission: str,
        user_id: Optional[int] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        context['required_permission'] = required_permission
        if user_id:
            context['user_id'] = user_id
        
        super().__init__(
            message=f"Permission denied: {required_permission} required",
            error_code=ErrorCode.PERMISSION_ERROR,
            context=context,
            user_message=f"You don't have permission to perform this action. Required: {required_permission}",
            **kwargs
        )


class ValidationError(OSRSBotException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        **kwargs
    ):
        context = kwargs.get('context', {})
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = str(field_value)
        
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            context=context,
            user_message="Invalid input provided. Please check your data and try again.",
            **kwargs
        )


def handle_exception(exc: Exception) -> OSRSBotException:
    """
    Convert generic exceptions to OSRSBotException for consistent handling.
    
    Args:
        exc: The original exception
        
    Returns:
        OSRSBotException with appropriate error code and context
    """
    if isinstance(exc, OSRSBotException):
        return exc
    
    # Map common exception types to our custom exceptions
    exception_mapping = {
        FileNotFoundError: (ErrorCode.FILE_NOT_FOUND, DatabaseError),
        PermissionError: (ErrorCode.PERMISSION_DENIED, DatabaseError),
        ValueError: (ErrorCode.VALIDATION_ERROR, ValidationError),
        KeyError: (ErrorCode.MISSING_REQUIRED_FIELD, ValidationError),
        ConnectionError: (ErrorCode.API_ERROR, APIError),
        TimeoutError: (ErrorCode.API_TIMEOUT, APIError),
    }
    
    error_code, exception_class = exception_mapping.get(
        type(exc), 
        (ErrorCode.CONFIGURATION_ERROR, OSRSBotException)
    )
    
    return exception_class(
        message=str(exc),
        error_code=error_code,
        original_exception=exc
    )