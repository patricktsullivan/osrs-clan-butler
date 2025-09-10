"""
Decorators for permission checking, rate limiting, and common functionality.

Provides reusable decorators for Discord commands and bot methods
with proper error handling and user feedback.
"""

import functools
import asyncio
import time
from typing import Callable, Any, Optional, List, Union, Dict
from datetime import datetime, timedelta
import discord
from discord.ext import commands

from core.exceptions import PermissionError, ValidationError, OSRSBotException
from config.logging_config import get_logger


logger = get_logger(__name__)


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin permissions for command execution.
    
    Checks if the user has admin role or is in the admin user list
    as defined in the bot configuration.
    """
    @functools.wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        # Get admin configuration from bot settings
        admin_role_id = self.bot.settings.ADMIN_ROLE_ID
        admin_user_ids = self.bot.settings.ADMIN_USER_IDS
        
        # Check if user is in admin user list
        if interaction.user.id in admin_user_ids:
            logger.info(
                f"Admin command authorized for user {interaction.user.id}",
                extra={"user_id": interaction.user.id, "command": func.__name__}
            )
            return await func(self, interaction, *args, **kwargs)
        
        # Check if user has admin role
        if admin_role_id:
            user_roles = [role.id for role in interaction.user.roles]
            if admin_role_id in user_roles:
                logger.info(
                    f"Admin command authorized for role {admin_role_id}",
                    extra={"user_id": interaction.user.id, "command": func.__name__}
                )
                return await func(self, interaction, *args, **kwargs)
        
        # Permission denied
        logger.warning(
            f"Admin command denied for user {interaction.user.id}",
            extra={"user_id": interaction.user.id, "command": func.__name__}
        )
        
        raise PermissionError(
            required_permission="Administrator",
            user_id=interaction.user.id
        )
    
    return wrapper


def require_role(role_ids: Union[int, List[int]]) -> Callable:
    """
    Decorator to require specific role(s) for command execution.
    
    Args:
        role_ids: Single role ID or list of role IDs that are allowed
    """
    if isinstance(role_ids, int):
        role_ids = [role_ids]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            user_roles = [role.id for role in interaction.user.roles]
            
            # Check if user has any of the required roles
            if any(role_id in user_roles for role_id in role_ids):
                logger.debug(
                    f"Role check passed for user {interaction.user.id}",
                    extra={"user_id": interaction.user.id, "required_roles": role_ids}
                )
                return await func(self, interaction, *args, **kwargs)
            
            # Permission denied
            logger.warning(
                f"Role check failed for user {interaction.user.id}",
                extra={"user_id": interaction.user.id, "required_roles": role_ids}
            )
            
            raise PermissionError(
                required_permission=f"One of roles: {role_ids}",
                user_id=interaction.user.id
            )
        
        return wrapper
    return decorator


def validate_input(**validators) -> Callable:
    """
    Decorator to validate command inputs before execution.
    
    Args:
        **validators: Keyword arguments where keys are parameter names
                     and values are validation functions
    
    Example:
        @validate_input(username=lambda x: len(x) >= 3, level=lambda x: 1 <= x <= 99)
        async def some_command(self, interaction, username: str, level: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get function signature to map arguments
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate each specified parameter
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    try:
                        if not validator(value):
                            raise ValidationError(
                                f"Invalid value for {param_name}: {value}",
                                field_name=param_name,
                                field_value=value
                            )
                    except Exception as e:
                        if isinstance(e, ValidationError):
                            raise
                        raise ValidationError(
                            f"Validation error for {param_name}: {str(e)}",
                            field_name=param_name,
                            field_value=value
                        )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class RateLimiter:
    """Simple rate limiter for preventing command spam."""
    
    def __init__(self, calls: int = 5, period: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.call_times: Dict[int, List[float]] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make a call."""
        now = time.time()
        
        if user_id not in self.call_times:
            self.call_times[user_id] = []
        
        # Remove old calls outside the period
        self.call_times[user_id] = [
            call_time for call_time in self.call_times[user_id]
            if now - call_time < self.period
        ]
        
        # Check if under limit
        if len(self.call_times[user_id]) < self.calls:
            self.call_times[user_id].append(now)
            return True
        
        return False
    
    def time_until_reset(self, user_id: int) -> float:
        """Get time until user can make another call."""
        if user_id not in self.call_times or not self.call_times[user_id]:
            return 0.0
        
        oldest_call = min(self.call_times[user_id])
        return max(0.0, self.period - (time.time() - oldest_call))


def rate_limit(calls: int = 5, period: int = 60) -> Callable:
    """
    Decorator to rate limit command usage per user.
    
    Args:
        calls: Maximum number of calls allowed
        period: Time period in seconds
    """
    # Create a command-specific rate limiter
    limiter = CommandRateLimiter(default_limit=calls, window_seconds=period)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            user_id = interaction.user.id
            command_name = func.__name__
            
            if not limiter.is_allowed(user_id, command_name):
                wait_time = limiter.get_reset_time(user_id)
                logger.warning(
                    f"Rate limit exceeded for user {user_id}",
                    extra={
                        "user_id": user_id,
                        "command": command_name,
                        "wait_time": wait_time
                    }
                )
                
                await interaction.response.send_message(
                    f"You're using commands too quickly! Please wait {wait_time:.1f} seconds.",
                    ephemeral=True
                )
                return
            
            return await func(self, interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def handle_errors(send_to_user: bool = True) -> Callable:
    """
    Decorator to handle exceptions and provide user-friendly error messages.
    
    Args:
        send_to_user: Whether to send error messages to the user
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            try:
                return await func(self, interaction, *args, **kwargs)
            
            except OSRSBotException as e:
                # Log the error with context
                logger.error(
                    f"Bot error in {func.__name__}: {e}",
                    extra={
                        "user_id": interaction.user.id,
                        "command": func.__name__,
                        "error_data": e.to_dict()
                    }
                )
                
                if send_to_user:
                    try:
                        if interaction.response.is_done():
                            await interaction.followup.send(
                                f"❌ {e.user_message}",
                                ephemeral=True
                            )
                        else:
                            await interaction.response.send_message(
                                f"❌ {e.user_message}",
                                ephemeral=True
                            )
                    except Exception as send_error:
                        logger.error(f"Failed to send error message: {send_error}")
            
            except Exception as e:
                # Log unexpected errors
                logger.error(
                    f"Unexpected error in {func.__name__}: {e}",
                    extra={
                        "user_id": interaction.user.id,
                        "command": func.__name__
                    },
                    exc_info=True
                )
                
                if send_to_user:
                    try:
                        if interaction.response.is_done():
                            await interaction.followup.send(
                                "❌ An unexpected error occurred. Please try again later.",
                                ephemeral=True
                            )
                        else:
                            await interaction.response.send_message(
                                "❌ An unexpected error occurred. Please try again later.",
                                ephemeral=True
                            )
                    except Exception as send_error:
                        logger.error(f"Failed to send error message: {send_error}")
        
        return wrapper
    return decorator


def defer_response(ephemeral: bool = False) -> Callable:
    """
    Decorator to automatically defer Discord interaction responses.
    
    Args:
        ephemeral: Whether the response should be ephemeral
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=ephemeral)
            
            return await func(self, interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def log_command_usage(func: Callable) -> Callable:
    """Decorator to log command usage for analytics and debugging."""
    @functools.wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        start_time = time.time()
        
        # Log command start
        logger.info(
            f"Command {func.__name__} started",
            extra={
                "user_id": interaction.user.id,
                "username": str(interaction.user),
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
                "command": func.__name__
            }
        )
        
        try:
            result = await func(self, interaction, *args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log successful completion
            logger.info(
                f"Command {func.__name__} completed successfully",
                extra={
                    "user_id": interaction.user.id,
                    "command": func.__name__,
                    "execution_time": execution_time,
                    "success": True
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed completion
            logger.error(
                f"Command {func.__name__} failed",
                extra={
                    "user_id": interaction.user.id,
                    "command": func.__name__,
                    "execution_time": execution_time,
                    "success": False,
                    "error": str(e)
                }
            )
            
            raise
    
    return wrapper


def require_competition_active(func: Callable) -> Callable:
    """Decorator to ensure a competition is active before allowing operations."""
    @functools.wraps(func)
    async def wrapper(self, interaction: discord.Interaction, competition_id: str, *args, **kwargs):
        # This will be implemented once we have the competition repository
        # For now, it's a placeholder that shows the pattern
        try:
            competition = await self.bot.competition_repo.get_by_id(competition_id)
            if competition.status != "active":
                await interaction.response.send_message(
                    f"❌ Competition '{competition_id}' is not currently active.",
                    ephemeral=True
                )
                return
        except Exception as e:
            logger.error(f"Error checking competition status: {e}")
            await interaction.response.send_message(
                "❌ Could not verify competition status.",
                ephemeral=True
            )
            return
        
        return await func(self, interaction, competition_id, *args, **kwargs)
    
    return wrapper