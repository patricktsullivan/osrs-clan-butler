"""
User data model with validation and serialization.

Represents a Discord user with OSRS account linkage,
competition history, and preference management.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from core.exceptions import ValidationError


class PrivacyLevel(Enum):
    """User privacy level options."""
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


@dataclass
class UserPreferences:
    """User preference settings."""
    notifications: bool = True
    privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC
    show_real_name: bool = False
    auto_register_competitions: bool = False
    preferred_time_zone: str = "UTC"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "notifications": self.notifications,
            "privacy_level": self.privacy_level.value,
            "show_real_name": self.show_real_name,
            "auto_register_competitions": self.auto_register_competitions,
            "preferred_time_zone": self.preferred_time_zone
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create from dictionary."""
        return cls(
            notifications=data.get("notifications", True),
            privacy_level=PrivacyLevel(data.get("privacy_level", "public")),
            show_real_name=data.get("show_real_name", False),
            auto_register_competitions=data.get("auto_register_competitions", False),
            preferred_time_zone=data.get("preferred_time_zone", "UTC")
        )


@dataclass
class User:
    """
    User model representing a Discord user with OSRS account integration.
    
    Handles user data validation, serialization, and business logic
    for user management within the bot ecosystem.
    """
    discord_id: int
    osrs_username: Optional[str] = None
    wise_old_man_id: Optional[int] = None
    join_date: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    total_competitions: int = 0
    wins: int = 0
    preferences: UserPreferences = field(default_factory=UserPreferences)
    achievements: List[str] = field(default_factory=list)
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    display_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate user data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate user data integrity.
        
        Raises:
            ValidationError: If user data is invalid
        """
        # Validate Discord ID
        if not isinstance(self.discord_id, int) or self.discord_id <= 0:
            raise ValidationError(
                "Discord ID must be a positive integer",
                field_name="discord_id",
                field_value=self.discord_id
            )
        
        # Validate OSRS username if provided
        if self.osrs_username is not None:
            if not isinstance(self.osrs_username, str) or len(self.osrs_username.strip()) == 0:
                raise ValidationError(
                    "OSRS username cannot be empty",
                    field_name="osrs_username",
                    field_value=self.osrs_username
                )
            
            # OSRS username validation rules
            username = self.osrs_username.strip()
            if len(username) < 1 or len(username) > 12:
                raise ValidationError(
                    "OSRS username must be 1-12 characters",
                    field_name="osrs_username",
                    field_value=username
                )
            
            # Only alphanumeric, spaces, hyphens, and underscores allowed
            allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_")
            if not all(c in allowed_chars for c in username):
                raise ValidationError(
                    "OSRS username contains invalid characters",
                    field_name="osrs_username",
                    field_value=username
                )
        
        # Validate Wise Old Man ID if provided
        if self.wise_old_man_id is not None:
            if not isinstance(self.wise_old_man_id, int) or self.wise_old_man_id <= 0:
                raise ValidationError(
                    "Wise Old Man ID must be a positive integer",
                    field_name="wise_old_man_id",
                    field_value=self.wise_old_man_id
                )
        
        # Validate competition stats
        if not isinstance(self.total_competitions, int) or self.total_competitions < 0:
            raise ValidationError(
                "Total competitions must be a non-negative integer",
                field_name="total_competitions",
                field_value=self.total_competitions
            )
        
        if not isinstance(self.wins, int) or self.wins < 0:
            raise ValidationError(
                "Wins must be a non-negative integer",
                field_name="wins",
                field_value=self.wins
            )
        
        if self.wins > self.total_competitions:
            raise ValidationError(
                "Wins cannot exceed total competitions",
                field_name="wins",
                field_value=f"{self.wins}/{self.total_competitions}"
            )
        
        # Validate date formats
        try:
            datetime.fromisoformat(self.join_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError(
                "Invalid join_date format",
                field_name="join_date",
                field_value=self.join_date
            )
        
        try:
            datetime.fromisoformat(self.last_activity.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError(
                "Invalid last_activity format",
                field_name="last_activity",
                field_value=self.last_activity
            )
        
        # Validate achievements list
        if not isinstance(self.achievements, list):
            raise ValidationError(
                "Achievements must be a list",
                field_name="achievements",
                field_value=type(self.achievements).__name__
            )
        
        # Validate display name if provided
        if self.display_name is not None:
            if not isinstance(self.display_name, str) or len(self.display_name.strip()) == 0:
                raise ValidationError(
                    "Display name cannot be empty",
                    field_name="display_name",
                    field_value=self.display_name
                )
            
            if len(self.display_name) > 32:
                raise ValidationError(
                    "Display name cannot exceed 32 characters",
                    field_name="display_name",
                    field_value=self.display_name
                )
    
    def update_activity(self) -> None:
        """Update the last activity timestamp to current time."""
        self.last_activity = datetime.utcnow().isoformat() + 'Z'
    
    def link_osrs_account(self, username: str, wise_old_man_id: Optional[int] = None) -> None:
        """
        Link an OSRS account to this user.
        
        Args:
            username: OSRS username
            wise_old_man_id: Optional Wise Old Man player ID
        """
        self.osrs_username = username.strip()
        self.wise_old_man_id = wise_old_man_id
        self.update_activity()
        self.validate()  # Ensure the new data is valid
    
    def unlink_osrs_account(self) -> None:
        """Remove OSRS account linkage."""
        self.osrs_username = None
        self.wise_old_man_id = None
        self.update_activity()
    
    def add_competition_participation(self, won: bool = False) -> None:
        """
        Record participation in a competition.
        
        Args:
            won: Whether the user won the competition
        """
        self.total_competitions += 1
        if won:
            self.wins += 1
        self.update_activity()
    
    def add_achievement(self, achievement: str) -> bool:
        """
        Add an achievement to the user's profile.
        
        Args:
            achievement: Achievement identifier
            
        Returns:
            True if achievement was added, False if already exists
        """
        if achievement not in self.achievements:
            self.achievements.append(achievement)
            self.update_activity()
            return True
        return False
    
    def remove_achievement(self, achievement: str) -> bool:
        """
        Remove an achievement from the user's profile.
        
        Args:
            achievement: Achievement identifier
            
        Returns:
            True if achievement was removed, False if not found
        """
        if achievement in self.achievements:
            self.achievements.remove(achievement)
            self.update_activity()
            return True
        return False
    
    def get_win_rate(self) -> float:
        """
        Calculate the user's win rate.
        
        Returns:
            Win rate as a percentage (0.0 to 100.0)
        """
        if self.total_competitions == 0:
            return 0.0
        return (self.wins / self.total_competitions) * 100
    
    def is_osrs_linked(self) -> bool:
        """Check if user has linked an OSRS account."""
        return self.osrs_username is not None
    
    def get_public_profile(self) -> Dict[str, Any]:
        """
        Get user profile data based on privacy settings.
        
        Returns:
            Dictionary with user data respecting privacy preferences
        """
        if self.preferences.privacy_level == PrivacyLevel.PRIVATE:
            return {
                "discord_id": self.discord_id,
                "display_name": self.display_name,
                "privacy_level": "private"
            }
        
        profile = {
            "discord_id": self.discord_id,
            "display_name": self.display_name,
            "osrs_username": self.osrs_username if self.is_osrs_linked() else None,
            "total_competitions": self.total_competitions,
            "wins": self.wins,
            "win_rate": round(self.get_win_rate(), 1),
            "achievements": self.achievements.copy(),
            "join_date": self.join_date,
            "privacy_level": self.preferences.privacy_level.value
        }
        
        if self.preferences.privacy_level == PrivacyLevel.FRIENDS:
            # In a real implementation, you'd check if the requester is a friend
            # For now, we include all data for FRIENDS level
            pass
        
        return profile
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert user to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the user
        """
        return {
            "discord_id": self.discord_id,
            "osrs_username": self.osrs_username,
            "wise_old_man_id": self.wise_old_man_id,
            "join_date": self.join_date,
            "total_competitions": self.total_competitions,
            "wins": self.wins,
            "preferences": self.preferences.to_dict(),
            "achievements": self.achievements.copy(),
            "last_activity": self.last_activity,
            "display_name": self.display_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create User instance from dictionary.
        
        Args:
            data: Dictionary containing user data
            
        Returns:
            User instance
            
        Raises:
            ValidationError: If data is invalid
        """
        try:
            preferences_data = data.get("preferences", {})
            preferences = UserPreferences.from_dict(preferences_data)
            
            return cls(
                discord_id=data["discord_id"],
                osrs_username=data.get("osrs_username"),
                wise_old_man_id=data.get("wise_old_man_id"),
                join_date=data.get("join_date", datetime.utcnow().isoformat() + 'Z'),
                total_competitions=data.get("total_competitions", 0),
                wins=data.get("wins", 0),
                preferences=preferences,
                achievements=data.get("achievements", []),
                last_activity=data.get("last_activity", datetime.utcnow().isoformat() + 'Z'),
                display_name=data.get("display_name")
            )
        except KeyError as e:
            raise ValidationError(f"Missing required field: {e}")
        except Exception as e:
            raise ValidationError(f"Failed to create User from data: {e}")
    
    def __str__(self) -> str:
        """String representation of the user."""
        name = self.display_name or self.osrs_username or f"User#{self.discord_id}"
        return f"User({name}, {self.total_competitions} competitions, {self.wins} wins)"
    
    def __repr__(self) -> str:
        """Detailed string representation of the user."""
        return (f"User(discord_id={self.discord_id}, osrs_username='{self.osrs_username}', "
                f"total_competitions={self.total_competitions}, wins={self.wins})")