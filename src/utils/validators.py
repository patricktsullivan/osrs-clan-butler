"""
Input validation utilities for OSRS Discord Bot.

Provides comprehensive validation functions for user inputs,
OSRS-specific data formats, and common data types with
security-focused sanitization.
"""

import re
import html
from typing import Any, Optional, Union, List, Dict
from datetime import datetime, timedelta
from urllib.parse import urlparse

from core.exceptions import ValidationError


class InputValidator:
    """
    Comprehensive input validation with OSRS-specific validations.
    
    Provides static methods for validating various input types
    with proper error handling and security considerations.
    """
    
    # OSRS username validation pattern
    OSRS_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9 _-]{1,12}$')
    
    # Discord ID validation (snowflake format)
    DISCORD_ID_PATTERN = re.compile(r'^\d{17,19}$')
    
    # Common SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        re.compile(r'\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b', re.IGNORECASE),
        re.compile(r'[;\'"\\]'),
        re.compile(r'--'),
        re.compile(r'/\*|\*/')
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'<iframe[^>]*>', re.IGNORECASE)
    ]
    
    @staticmethod
    def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize user input to prevent injection attacks.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
            
        Raises:
            ValidationError: If input contains malicious content
        """
        if not isinstance(text, str):
            raise ValidationError(f"Expected string, got {type(text).__name__}")
        
        # Check for SQL injection patterns
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if pattern.search(text):
                raise ValidationError("Input contains potentially malicious content")
        
        # Check for XSS patterns
        for pattern in InputValidator.XSS_PATTERNS:
            if pattern.search(text):
                raise ValidationError("Input contains potentially malicious content")
        
        # HTML escape
        sanitized = html.escape(text.strip())
        
        # Validate length
        if max_length and len(sanitized) > max_length:
            raise ValidationError(f"Input too long (max {max_length} characters)")
        
        return sanitized
    
    @staticmethod
    def validate_osrs_username(username: str) -> str:
        """
        Validate and sanitize OSRS username.
        
        Args:
            username: OSRS username to validate
            
        Returns:
            Validated username
            
        Raises:
            ValidationError: If username is invalid
        """
        if not isinstance(username, str):
            raise ValidationError("Username must be a string")
        
        username = username.strip()
        
        if not username:
            raise ValidationError("Username cannot be empty")
        
        if len(username) > 12:
            raise ValidationError("OSRS username cannot exceed 12 characters")
        
        if not InputValidator.OSRS_USERNAME_PATTERN.match(username):
            raise ValidationError(
                "Invalid OSRS username. Only letters, numbers, spaces, hyphens, and underscores allowed"
            )
        
        # Check for reserved words or inappropriate content
        reserved_words = ['mod', 'admin', 'jagex', 'staff']
        if any(word in username.lower() for word in reserved_words):
            raise ValidationError("Username contains reserved words")
        
        return username
    
    @staticmethod
    def validate_discord_id(discord_id: Union[str, int]) -> int:
        """
        Validate Discord user/guild/channel ID.
        
        Args:
            discord_id: Discord ID to validate
            
        Returns:
            Validated Discord ID as integer
            
        Raises:
            ValidationError: If Discord ID is invalid
        """
        if isinstance(discord_id, int):
            discord_id_str = str(discord_id)
        elif isinstance(discord_id, str):
            discord_id_str = discord_id.strip()
        else:
            raise ValidationError(f"Discord ID must be string or int, got {type(discord_id).__name__}")
        
        if not InputValidator.DISCORD_ID_PATTERN.match(discord_id_str):
            raise ValidationError("Invalid Discord ID format")
        
        try:
            discord_id_int = int(discord_id_str)
        except ValueError:
            raise ValidationError("Discord ID must be numeric")
        
        # Basic range check (Discord IDs started around 2015)
        min_discord_id = 100000000000000000  # Approximate minimum valid Discord ID
        if discord_id_int < min_discord_id:
            raise ValidationError("Discord ID appears to be invalid")
        
        return discord_id_int
    
    @staticmethod
    def validate_competition_title(title: str) -> str:
        """
        Validate competition title.
        
        Args:
            title: Competition title to validate
            
        Returns:
            Validated title
            
        Raises:
            ValidationError: If title is invalid
        """
        title = InputValidator.sanitize_input(title, max_length=100)
        
        if len(title) < 3:
            raise ValidationError("Competition title must be at least 3 characters")
        
        # Check for reasonable content
        if title.isnumeric():
            raise ValidationError("Competition title cannot be only numbers")
        
        return title
    
    @staticmethod
    def validate_competition_description(description: str) -> str:
        """
        Validate competition description.
        
        Args:
            description: Competition description to validate
            
        Returns:
            Validated description
            
        Raises:
            ValidationError: If description is invalid
        """
        description = InputValidator.sanitize_input(description, max_length=1000)
        
        if len(description) < 10:
            raise ValidationError("Competition description must be at least 10 characters")
        
        return description
    
    @staticmethod
    def validate_duration_hours(duration: Union[str, int, float]) -> int:
        """
        Validate competition duration in hours.
        
        Args:
            duration: Duration to validate
            
        Returns:
            Validated duration as integer
            
        Raises:
            ValidationError: If duration is invalid
        """
        try:
            if isinstance(duration, str):
                duration = float(duration.strip())
            
            duration_int = int(duration)
            
        except (ValueError, TypeError):
            raise ValidationError("Duration must be a number")
        
        if duration_int < 1:
            raise ValidationError("Duration must be at least 1 hour")
        
        if duration_int > 168:  # 1 week
            raise ValidationError("Duration cannot exceed 168 hours (1 week)")
        
        return duration_int
    
    @staticmethod
    def validate_participant_count(count: Union[str, int]) -> int:
        """
        Validate maximum participant count.
        
        Args:
            count: Participant count to validate
            
        Returns:
            Validated count as integer
            
        Raises:
            ValidationError: If count is invalid
        """
        try:
            if isinstance(count, str):
                count = int(count.strip())
            
            count_int = int(count)
            
        except (ValueError, TypeError):
            raise ValidationError("Participant count must be a number")
        
        if count_int < 2:
            raise ValidationError("Must allow at least 2 participants")
        
        if count_int > 200:
            raise ValidationError("Cannot exceed 200 participants")
        
        return count_int
    
    @staticmethod
    def validate_skill_name(skill: str) -> str:
        """
        Validate OSRS skill name.
        
        Args:
            skill: Skill name to validate
            
        Returns:
            Validated skill name
            
        Raises:
            ValidationError: If skill name is invalid
        """
        skill = InputValidator.sanitize_input(skill)
        
        # OSRS skills list
        valid_skills = [
            'attack', 'defence', 'strength', 'hitpoints', 'ranged', 'prayer',
            'magic', 'cooking', 'woodcutting', 'fletching', 'fishing', 'firemaking',
            'crafting', 'smithing', 'mining', 'herblore', 'agility', 'thieving',
            'slayer', 'farming', 'runecrafting', 'hunter', 'construction'
        ]
        
        skill_lower = skill.lower()
        if skill_lower not in valid_skills:
            raise ValidationError(f"Invalid skill name: {skill}")
        
        return skill_lower
    
    @staticmethod
    def validate_boss_name(boss: str) -> str:
        """
        Validate OSRS boss name.
        
        Args:
            boss: Boss name to validate
            
        Returns:
            Validated boss name
            
        Raises:
            ValidationError: If boss name is invalid
        """
        boss = InputValidator.sanitize_input(boss)
        
        # Common OSRS bosses (not exhaustive, can be expanded)
        valid_bosses = [
            'zulrah', 'vorkath', 'alchemical hydra', 'cerberus', 'kraken',
            'abyssal sire', 'grotesque guardians', 'thermonuclear smoke devil',
            'chaos elemental', 'crazy archaeologist', 'scorpia', 'venenatis',
            'callisto', 'vet\'ion', 'chaos fanatic', 'king black dragon',
            'giant mole', 'deranged archaeologist', 'sarachnis', 'tempoross',
            'wintertodt', 'zalcano', 'gauntlet', 'corrupted gauntlet',
            'theatre of blood', 'chambers of xeric', 'tombs of amascut'
        ]
        
        boss_lower = boss.lower()
        if boss_lower not in valid_bosses:
            # Allow custom boss names but validate format
            if len(boss) < 2 or len(boss) > 50:
                raise ValidationError("Boss name must be 2-50 characters")
        
        return boss_lower
    
    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate URL format and safety.
        
        Args:
            url: URL to validate
            
        Returns:
            Validated URL
            
        Raises:
            ValidationError: If URL is invalid or unsafe
        """
        url = url.strip()
        
        if not url:
            raise ValidationError("URL cannot be empty")
        
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValidationError("Invalid URL format")
        
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError("URL must include protocol and domain")
        
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError("URL must use HTTP or HTTPS protocol")
        
        # Block potentially dangerous domains
        dangerous_domains = [
            'localhost', '127.0.0.1', '0.0.0.0', '::1'
        ]
        
        if any(domain in parsed.netloc.lower() for domain in dangerous_domains):
            raise ValidationError("URL points to potentially dangerous domain")
        
        return url
    
    @staticmethod
    def validate_date_string(date_str: str) -> datetime:
        """
        Validate ISO format date string.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Parsed datetime object
            
        Raises:
            ValidationError: If date format is invalid
        """
        try:
            # Handle both with and without timezone
            if date_str.endswith('Z'):
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(date_str)
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}")
    
    @staticmethod
    def validate_positive_integer(value: Union[str, int], 
                                field_name: str = "value",
                                min_value: int = 1,
                                max_value: Optional[int] = None) -> int:
        """
        Validate positive integer with optional bounds.
        
        Args:
            value: Value to validate
            field_name: Name of field for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Validated integer
            
        Raises:
            ValidationError: If value is invalid
        """
        try:
            if isinstance(value, str):
                value = int(value.strip())
            
            value_int = int(value)
            
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a number")
        
        if value_int < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")
        
        if max_value is not None and value_int > max_value:
            raise ValidationError(f"{field_name} cannot exceed {max_value}")
        
        return value_int
    
    @staticmethod
    def validate_choice(value: str, choices: List[str], 
                       field_name: str = "value",
                       case_sensitive: bool = False) -> str:
        """
        Validate that value is one of allowed choices.
        
        Args:
            value: Value to validate
            choices: List of allowed choices
            field_name: Name of field for error messages
            case_sensitive: Whether comparison is case-sensitive
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If value is not in choices
        """
        value = value.strip()
        
        if case_sensitive:
            if value not in choices:
                raise ValidationError(
                    f"Invalid {field_name}. Must be one of: {', '.join(choices)}"
                )
        else:
            value_lower = value.lower()
            choices_lower = [choice.lower() for choice in choices]
            if value_lower not in choices_lower:
                raise ValidationError(
                    f"Invalid {field_name}. Must be one of: {', '.join(choices)}"
                )
            # Return the original case from choices
            value = choices[choices_lower.index(value_lower)]
        
        return value
    
    @staticmethod
    def validate_json_object(obj: Any, required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate JSON object structure.
        
        Args:
            obj: Object to validate
            required_fields: List of required field names
            
        Returns:
            Validated dictionary
            
        Raises:
            ValidationError: If object is invalid
        """
        if not isinstance(obj, dict):
            raise ValidationError("Must be a JSON object")
        
        if required_fields:
            missing_fields = [field for field in required_fields if field not in obj]
            if missing_fields:
                raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        return obj
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe file operations.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            Sanitized filename
            
        Raises:
            ValidationError: If filename is invalid
        """
        if not isinstance(filename, str):
            raise ValidationError("Filename must be a string")
        
        filename = filename.strip()
        
        if not filename:
            raise ValidationError("Filename cannot be empty")
        
        # Remove dangerous characters
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in filename:
                raise ValidationError(f"Filename contains invalid character: {char}")
        
        # Limit length
        if len(filename) > 255:
            raise ValidationError("Filename too long")
        
        return filename