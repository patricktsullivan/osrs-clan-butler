"""
Leaderboard data model for ranking and achievement tracking.

Manages different types of leaderboards, achievement systems,
and statistical analysis for competition performance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from core.exceptions import ValidationError


class LeaderboardType(Enum):
    """Types of leaderboards supported."""
    ALL_TIME_WINS = "all_time_wins"
    MONTHLY_WINS = "monthly_wins"
    PARTICIPATION = "participation"
    WIN_RATE = "win_rate"
    SKILL_COMPETITIONS = "skill_competitions"
    BOSS_COMPETITIONS = "boss_competitions"
    TRIVIA_COMPETITIONS = "trivia_competitions"
    RACE_COMPETITIONS = "race_competitions"
    SPEEDRUN_COMPETITIONS = "speedrun_competitions"


class AchievementType(Enum):
    """Types of achievements available."""
    FIRST_WIN = "first_win"
    MULTIPLE_WINS = "multiple_wins"
    PARTICIPATION_MILESTONE = "participation_milestone"
    WIN_STREAK = "win_streak"
    COMPETITION_SPECIFIC = "competition_specific"
    SEASONAL = "seasonal"
    SPECIAL = "special"


@dataclass
class LeaderboardEntry:
    """Individual entry in a leaderboard."""
    user_id: int
    rank: int
    score: float
    display_name: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate entry data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate leaderboard entry data."""
        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValidationError(
                "User ID must be a positive integer",
                field_name="user_id",
                field_value=self.user_id
            )
        
        if not isinstance(self.rank, int) or self.rank <= 0:
            raise ValidationError(
                "Rank must be a positive integer",
                field_name="rank",
                field_value=self.rank
            )
        
        if not isinstance(self.score, (int, float)):
            raise ValidationError(
                "Score must be a number",
                field_name="score",
                field_value=self.score
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "rank": self.rank,
            "score": self.score,
            "display_name": self.display_name,
            "additional_data": self.additional_data.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LeaderboardEntry':
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            rank=data["rank"],
            score=data["score"],
            display_name=data.get("display_name"),
            additional_data=data.get("additional_data", {})
        )


@dataclass
class Achievement:
    """Individual achievement earned by a user."""
    achievement_type: AchievementType
    achievement_id: str
    earned_date: str
    competition_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate achievement data after initialization."""
        if isinstance(self.achievement_type, str):
            self.achievement_type = AchievementType(self.achievement_type)
        self.validate()
    
    def validate(self) -> None:
        """Validate achievement data."""
        if not isinstance(self.achievement_id, str) or len(self.achievement_id.strip()) == 0:
            raise ValidationError(
                "Achievement ID cannot be empty",
                field_name="achievement_id",
                field_value=self.achievement_id
            )
        
        try:
            datetime.fromisoformat(self.earned_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError(
                "Invalid earned_date format",
                field_name="earned_date",
                field_value=self.earned_date
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "achievement_type": self.achievement_type.value,
            "achievement_id": self.achievement_id,
            "earned_date": self.earned_date,
            "competition_id": self.competition_id,
            "metadata": self.metadata.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Achievement':
        """Create from dictionary."""
        return cls(
            achievement_type=AchievementType(data["achievement_type"]),
            achievement_id=data["achievement_id"],
            earned_date=data["earned_date"],
            competition_id=data.get("competition_id"),
            metadata=data.get("metadata", {})
        )


@dataclass
class Leaderboard:
    """
    Leaderboard model for tracking and displaying user rankings.
    
    Supports different types of leaderboards with configurable
    scoring and ranking systems.
    """
    leaderboard_type: LeaderboardType
    entries: List[LeaderboardEntry] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize leaderboard with proper validation."""
        if isinstance(self.leaderboard_type, str):
            self.leaderboard_type = LeaderboardType(self.leaderboard_type)
        
        # Convert dict entries to LeaderboardEntry objects
        for i, entry in enumerate(self.entries):
            if isinstance(entry, dict):
                self.entries[i] = LeaderboardEntry.from_dict(entry)
        
        self.validate()
    
    def validate(self) -> None:
        """Validate leaderboard data."""
        try:
            datetime.fromisoformat(self.last_updated.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError(
                "Invalid last_updated format",
                field_name="last_updated",
                field_value=self.last_updated
            )
        
        if self.period_start:
            try:
                datetime.fromisoformat(self.period_start.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError(
                    "Invalid period_start format",
                    field_name="period_start",
                    field_value=self.period_start
                )
        
        if self.period_end:
            try:
                datetime.fromisoformat(self.period_end.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError(
                    "Invalid period_end format",
                    field_name="period_end",
                    field_value=self.period_end
                )
    
    def add_or_update_entry(self, user_id: int, score: float, 
                           display_name: Optional[str] = None,
                           additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new entry or update existing entry for a user.
        
        Args:
            user_id: Discord user ID
            score: Score for the leaderboard
            display_name: Optional display name
            additional_data: Additional data for the entry
        """
        # Find existing entry
        existing_entry = None
        for entry in self.entries:
            if entry.user_id == user_id:
                existing_entry = entry
                break
        
        if existing_entry:
            # Update existing entry
            existing_entry.score = score
            if display_name:
                existing_entry.display_name = display_name
            if additional_data:
                existing_entry.additional_data.update(additional_data)
        else:
            # Add new entry
            new_entry = LeaderboardEntry(
                user_id=user_id,
                rank=0,  # Will be calculated in recalculate_ranks
                score=score,
                display_name=display_name,
                additional_data=additional_data or {}
            )
            self.entries.append(new_entry)
        
        # Recalculate ranks
        self.recalculate_ranks()
        self.last_updated = datetime.utcnow().isoformat() + 'Z'
    
    def remove_entry(self, user_id: int) -> bool:
        """
        Remove an entry from the leaderboard.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if entry was removed
        """
        for i, entry in enumerate(self.entries):
            if entry.user_id == user_id:
                del self.entries[i]
                self.recalculate_ranks()
                self.last_updated = datetime.utcnow().isoformat() + 'Z'
                return True
        return False
    
    def get_entry(self, user_id: int) -> Optional[LeaderboardEntry]:
        """Get entry for a specific user."""
        for entry in self.entries:
            if entry.user_id == user_id:
                return entry
        return None
    
    def get_user_rank(self, user_id: int) -> Optional[int]:
        """Get rank for a specific user."""
        entry = self.get_entry(user_id)
        return entry.rank if entry else None
    
    def get_top_entries(self, limit: int = 10) -> List[LeaderboardEntry]:
        """
        Get top N entries from the leaderboard.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of top entries
        """
        return sorted(self.entries, key=lambda x: x.rank)[:limit]
    
    def recalculate_ranks(self) -> None:
        """Recalculate ranks based on scores."""
        # Sort entries by score (descending for most leaderboard types)
        if self.leaderboard_type in [LeaderboardType.WIN_RATE]:
            # For win rate, higher is better
            sorted_entries = sorted(self.entries, key=lambda x: x.score, reverse=True)
        else:
            # For most other types, higher score is better
            sorted_entries = sorted(self.entries, key=lambda x: x.score, reverse=True)
        
        # Assign ranks, handling ties
        current_rank = 1
        for i, entry in enumerate(sorted_entries):
            if i > 0 and sorted_entries[i-1].score != entry.score:
                current_rank = i + 1
            entry.rank = current_rank
        
        # Update the entries list to maintain sorted order
        self.entries = sorted_entries
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistical information about the leaderboard."""
        if not self.entries:
            return {
                "total_entries": 0,
                "average_score": 0.0,
                "highest_score": 0.0,
                "lowest_score": 0.0
            }
        
        scores = [entry.score for entry in self.entries]
        
        return {
            "total_entries": len(self.entries),
            "average_score": sum(scores) / len(scores),
            "highest_score": max(scores),
            "lowest_score": min(scores),
            "median_score": sorted(scores)[len(scores) // 2] if scores else 0.0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "leaderboard_type": self.leaderboard_type.value,
            "entries": [entry.to_dict() for entry in self.entries],
            "last_updated": self.last_updated,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "metadata": self.metadata.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Leaderboard':
        """Create from dictionary."""
        return cls(
            leaderboard_type=LeaderboardType(data["leaderboard_type"]),
            entries=data.get("entries", []),
            last_updated=data.get("last_updated", datetime.utcnow().isoformat() + 'Z'),
            period_start=data.get("period_start"),
            period_end=data.get("period_end"),
            metadata=data.get("metadata", {})
        )


@dataclass
class LeaderboardCollection:
    """
    Collection of multiple leaderboards with achievement tracking.
    
    Manages all leaderboards and user achievements in a unified system.
    """
    leaderboards: Dict[str, Leaderboard] = field(default_factory=dict)
    user_achievements: Dict[int, List[Achievement]] = field(default_factory=dict)
    achievement_definitions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_leaderboard(self, leaderboard_type: LeaderboardType, 
                       period: Optional[str] = None) -> Optional[Leaderboard]:
        """
        Get a specific leaderboard.
        
        Args:
            leaderboard_type: Type of leaderboard
            period: Optional period identifier (e.g., "2024-01" for monthly)
            
        Returns:
            Leaderboard instance or None if not found
        """
        key = f"{leaderboard_type.value}"
        if period:
            key += f"_{period}"
        
        return self.leaderboards.get(key)
    
    def create_leaderboard(self, leaderboard_type: LeaderboardType,
                          period: Optional[str] = None,
                          period_start: Optional[str] = None,
                          period_end: Optional[str] = None) -> Leaderboard:
        """
        Create a new leaderboard.
        
        Args:
            leaderboard_type: Type of leaderboard
            period: Optional period identifier
            period_start: Optional period start date
            period_end: Optional period end date
            
        Returns:
            Created leaderboard
        """
        key = f"{leaderboard_type.value}"
        if period:
            key += f"_{period}"
        
        leaderboard = Leaderboard(
            leaderboard_type=leaderboard_type,
            period_start=period_start,
            period_end=period_end
        )
        
        self.leaderboards[key] = leaderboard
        return leaderboard
    
    def update_user_score(self, leaderboard_type: LeaderboardType, user_id: int, 
                         score: float, period: Optional[str] = None,
                         display_name: Optional[str] = None,
                         additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Update user score in a specific leaderboard.
        
        Args:
            leaderboard_type: Type of leaderboard
            user_id: Discord user ID
            score: New score
            period: Optional period identifier
            display_name: Optional display name
            additional_data: Additional data for the entry
        """
        leaderboard = self.get_leaderboard(leaderboard_type, period)
        if not leaderboard:
            leaderboard = self.create_leaderboard(leaderboard_type, period)
        
        leaderboard.add_or_update_entry(user_id, score, display_name, additional_data)
    
    def award_achievement(self, user_id: int, achievement_id: str, 
                         achievement_type: AchievementType,
                         competition_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Award an achievement to a user.
        
        Args:
            user_id: Discord user ID
            achievement_id: Achievement identifier
            achievement_type: Type of achievement
            competition_id: Optional competition ID
            metadata: Optional achievement metadata
            
        Returns:
            True if achievement was awarded (not already earned)
        """
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = []
        
        # Check if user already has this achievement
        for achievement in self.user_achievements[user_id]:
            if achievement.achievement_id == achievement_id:
                return False  # Already earned
        
        # Award the achievement
        new_achievement = Achievement(
            achievement_type=achievement_type,
            achievement_id=achievement_id,
            earned_date=datetime.utcnow().isoformat() + 'Z',
            competition_id=competition_id,
            metadata=metadata or {}
        )
        
        self.user_achievements[user_id].append(new_achievement)
        return True
    
    def get_user_achievements(self, user_id: int) -> List[Achievement]:
        """Get all achievements for a user."""
        return self.user_achievements.get(user_id, [])
    
    def get_user_leaderboard_positions(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get user's position across all leaderboards.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary mapping leaderboard names to position data
        """
        positions = {}
        
        for lb_key, leaderboard in self.leaderboards.items():
            entry = leaderboard.get_entry(user_id)
            if entry:
                positions[lb_key] = {
                    "rank": entry.rank,
                    "score": entry.score,
                    "total_entries": len(leaderboard.entries),
                    "percentile": (1 - (entry.rank - 1) / len(leaderboard.entries)) * 100
                }
        
        return positions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        leaderboards_dict = {}
        for key, leaderboard in self.leaderboards.items():
            leaderboards_dict[key] = leaderboard.to_dict()
        
        achievements_dict = {}
        for user_id, achievements in self.user_achievements.items():
            achievements_dict[user_id] = [achievement.to_dict() for achievement in achievements]
        
        return {
            "leaderboards": leaderboards_dict,
            "user_achievements": achievements_dict,
            "achievement_definitions": self.achievement_definitions.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LeaderboardCollection':
        """Create from dictionary."""
        collection = cls()
        
        # Load leaderboards
        leaderboards_data = data.get("leaderboards", {})
        for key, lb_data in leaderboards_data.items():
            collection.leaderboards[key] = Leaderboard.from_dict(lb_data)
        
        # Load user achievements
        achievements_data = data.get("user_achievements", {})
        for user_id_str, user_achievements in achievements_data.items():
            user_id = int(user_id_str)
            collection.user_achievements[user_id] = [
                Achievement.from_dict(achievement_data) 
                for achievement_data in user_achievements
            ]
        
        # Load achievement definitions
        collection.achievement_definitions = data.get("achievement_definitions", {})
        
        return collection