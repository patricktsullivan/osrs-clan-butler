"""
Rate limiting utilities for API calls and user commands.

Implements token bucket algorithm for rate limiting with
configurable rates and burst allowances.
"""

import asyncio
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

from config.logging_config import LoggerMixin


@dataclass
class RateLimitBucket:
    """
    Token bucket for rate limiting.
    
    Implements a token bucket algorithm where tokens are added
    at a constant rate and consumed when making requests.
    """
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Initialize bucket with full capacity."""
        if self.tokens == 0.0:
            self.tokens = float(self.capacity)
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were successfully consumed
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def time_until_available(self, tokens: int = 1) -> float:
        """
        Calculate time until requested tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time in seconds until tokens are available
        """
        self._refill()
        
        if self.tokens >= tokens:
            return 0.0
        
        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate
    
    def get_remaining_tokens(self) -> float:
        """Get number of remaining tokens."""
        self._refill()
        return self.tokens


class RateLimiter(LoggerMixin):
    """
    Comprehensive rate limiter with multiple bucket support.
    
    Supports different rate limits for different keys (users, APIs, etc.)
    with configurable rates and burst allowances.
    """
    
    def __init__(self, 
                 default_capacity: int = 10,
                 default_refill_rate: float = 1.0,
                 cleanup_interval: int = 3600):
        """
        Initialize rate limiter.
        
        Args:
            default_capacity: Default bucket capacity
            default_refill_rate: Default refill rate (tokens per second)
            cleanup_interval: Interval to cleanup old buckets (seconds)
        """
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self.cleanup_interval = cleanup_interval
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.bucket_configs: Dict[str, Dict[str, Any]] = {}
        self.last_cleanup = time.time()
        self._lock = asyncio.Lock()
    
    def configure_bucket(self, key_pattern: str, capacity: int, refill_rate: float) -> None:
        """
        Configure rate limiting for a specific key pattern.
        
        Args:
            key_pattern: Pattern to match keys (supports wildcards)
            capacity: Bucket capacity
            refill_rate: Refill rate (tokens per second)
        """
        self.bucket_configs[key_pattern] = {
            "capacity": capacity,
            "refill_rate": refill_rate
        }
        
        self.logger.info(f"Configured rate limit: {key_pattern} -> {capacity} tokens, {refill_rate}/s")
    
    def _get_bucket_config(self, key: str) -> Dict[str, Any]:
        """Get bucket configuration for a key."""
        # Check for exact matches first
        if key in self.bucket_configs:
            return self.bucket_configs[key]
        
        # Check for pattern matches
        for pattern, config in self.bucket_configs.items():
            if "*" in pattern:
                # Simple wildcard matching
                pattern_parts = pattern.split("*")
                if all(part in key for part in pattern_parts if part):
                    return config
        
        # Return default configuration
        return {
            "capacity": self.default_capacity,
            "refill_rate": self.default_refill_rate
        }
    
    def _get_bucket(self, key: str) -> RateLimitBucket:
        """Get or create bucket for a key."""
        if key not in self.buckets:
            config = self._get_bucket_config(key)
            self.buckets[key] = RateLimitBucket(
                capacity=config["capacity"],
                refill_rate=config["refill_rate"]
            )
        
        return self.buckets[key]
    
    async def acquire(self, key: str, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens for a key.
        
        Args:
            key: Rate limit key
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired successfully
        """
        async with self._lock:
            await self._cleanup_if_needed()
            bucket = self._get_bucket(key)
            return bucket.consume(tokens)
    
    async def wait_for_tokens(self, key: str, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Wait for tokens to become available.
        
        Args:
            key: Rate limit key
            tokens: Number of tokens needed
            timeout: Maximum time to wait (None for no timeout)
            
        Returns:
            True if tokens were acquired, False if timeout occurred
        """
        start_time = time.time()
        
        while True:
            if await self.acquire(key, tokens):
                return True
            
            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            # Calculate wait time
            async with self._lock:
                bucket = self._get_bucket(key)
                wait_time = bucket.time_until_available(tokens)
            
            # Wait for a short time or until tokens are available
            await asyncio.sleep(min(wait_time, 0.1))
    
    async def get_status(self, key: str) -> Dict[str, Any]:
        """
        Get rate limit status for a key.
        
        Args:
            key: Rate limit key
            
        Returns:
            Dictionary with rate limit status
        """
        async with self._lock:
            bucket = self._get_bucket(key)
            
            return {
                "key": key,
                "remaining_tokens": bucket.get_remaining_tokens(),
                "capacity": bucket.capacity,
                "refill_rate": bucket.refill_rate,
                "time_until_refill": bucket.time_until_available(1) if bucket.tokens < 1 else 0.0
            }
    
    async def reset_bucket(self, key: str) -> None:
        """Reset bucket for a key (refill to capacity)."""
        async with self._lock:
            if key in self.buckets:
                bucket = self.buckets[key]
                bucket.tokens = float(bucket.capacity)
                bucket.last_refill = time.time()
                
                self.logger.info(f"Reset rate limit bucket: {key}")
    
    async def _cleanup_if_needed(self) -> None:
        """Clean up old, unused buckets."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove buckets that haven't been used recently
        cutoff_time = now - self.cleanup_interval
        keys_to_remove = []
        
        for key, bucket in self.buckets.items():
            if bucket.last_refill < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.buckets[key]
        
        self.last_cleanup = now
        
        if keys_to_remove:
            self.logger.debug(f"Cleaned up {len(keys_to_remove)} rate limit buckets")


class APIRateLimiter(RateLimiter):
    """
    Specialized rate limiter for API calls.
    
    Provides additional features for API rate limiting including
    retry-after header support and adaptive rate limiting.
    """
    
    def __init__(self):
        """Initialize API rate limiter with sensible defaults."""
        super().__init__(
            default_capacity=60,  # 60 requests
            default_refill_rate=1.0,  # 1 request per second
            cleanup_interval=1800  # 30 minutes
        )
        
        # Configure default API rate limits
        self.configure_bucket("wise_old_man", 60, 1.0)  # 60 requests per minute
        self.configure_bucket("discord_api", 50, 1.0)   # 50 requests per minute
    
    async def handle_rate_limit_response(self, key: str, response_headers: Dict[str, str]) -> None:
        """
        Handle rate limit response from API.
        
        Args:
            key: API key
            response_headers: Response headers from API
        """
        retry_after = response_headers.get("Retry-After")
        if retry_after:
            try:
                # Pause rate limiting for the specified time
                retry_seconds = int(retry_after)
                
                async with self._lock:
                    bucket = self._get_bucket(key)
                    bucket.tokens = 0.0  # Drain bucket
                    bucket.last_refill = time.time() + retry_seconds
                
                self.logger.warning(
                    f"API rate limited for {key}, pausing for {retry_seconds} seconds",
                    extra={"api_key": key, "retry_after": retry_seconds}
                )
                
            except ValueError:
                self.logger.warning(f"Invalid Retry-After header: {retry_after}")
    
    async def adaptive_delay(self, key: str, success: bool) -> None:
        """
        Implement adaptive delays based on API response success.
        
        Args:
            key: API key
            success: Whether the last request was successful
        """
        if not success:
            # Add extra delay for failed requests
            await asyncio.sleep(0.5)
            
            # Temporarily reduce rate for this key
            async with self._lock:
                bucket = self._get_bucket(key)
                if bucket.refill_rate > 0.1:
                    bucket.refill_rate *= 0.8  # Reduce rate by 20%
                    
                    self.logger.info(
                        f"Reduced rate limit for {key} to {bucket.refill_rate:.2f}/s",
                        extra={"api_key": key, "new_rate": bucket.refill_rate}
                    )


class CommandRateLimiter:
    """
    Simple rate limiter for Discord commands.
    
    Tracks command usage per user with sliding window approach.
    """
    
    def __init__(self, default_limit: int = 5, window_seconds: int = 60):
        """
        Initialize command rate limiter.
        
        Args:
            default_limit: Default number of commands per window
            window_seconds: Time window in seconds
        """
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.user_commands: Dict[int, List[float]] = defaultdict(list)
        self.custom_limits: Dict[str, int] = {}
    
    def set_command_limit(self, command_name: str, limit: int) -> None:
        """Set custom limit for a specific command."""
        self.custom_limits[command_name] = limit
    
    def is_allowed(self, user_id: int, command_name: str = None) -> bool:
        """
        Check if user is allowed to execute a command.
        
        Args:
            user_id: Discord user ID
            command_name: Optional command name for custom limits
            
        Returns:
            True if command is allowed
        """
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Clean up old timestamps
        self.user_commands[user_id] = [
            timestamp for timestamp in self.user_commands[user_id]
            if timestamp > cutoff
        ]
        
        # Get limit for this command
        limit = self.custom_limits.get(command_name, self.default_limit)
        
        # Check if under limit
        if len(self.user_commands[user_id]) < limit:
            self.user_commands[user_id].append(now)
            return True
        
        return False
    
    def get_reset_time(self, user_id: int) -> float:
        """Get time until rate limit resets for user."""
        if user_id not in self.user_commands or not self.user_commands[user_id]:
            return 0.0
        
        oldest_timestamp = min(self.user_commands[user_id])
        reset_time = oldest_timestamp + self.window_seconds
        return max(0.0, reset_time - time.time())
    
    def reset_user(self, user_id: int) -> None:
        """Reset rate limit for a user."""
        if user_id in self.user_commands:
            del self.user_commands[user_id]


# Global instances for easy access
api_rate_limiter = APIRateLimiter()
command_rate_limiter = CommandRateLimiter()