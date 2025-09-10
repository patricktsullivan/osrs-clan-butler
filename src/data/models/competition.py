"""
Competition data model with validation and state management.

Represents different types of competitions with participant tracking,
progress monitoring, and result calculation capabilities.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

from core.exceptions import ValidationError, CompetitionError


class CompetitionStatus(Enum):
    """Competition status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class CompetitionType(Enum):
    """Competition type enumeration."""
    SKILL_COMPETITION = "skill_competition"
    BOSS_COMPETITION = "boss_competition"
    TRIVIA = "trivia"
    RACE = "race"
    SPEEDRUN = "speedrun"


@dataclass
class ParticipantData:
    """Data for a single competition participant."""
    user_id: int
    registration_time: str
    starting_stats: Dict[str, Any] = field(default_factory=dict)
    current_progress: Dict[str, Any] = field(default_factory=dict)
    final_result: Optional[Dict[str, Any]] = None
    notes: str = ""
    
    def __post_init__(self):
        """Validate participant data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate participant data."""
        if not isinstance(self.user_id, int) or self.user_id <= 0:
            raise ValidationError(
                "User ID must be a positive integer",
                field_name="user_id",
                field_value=self.user_id
            )
        
        try:
            datetime.fromisoformat(self.registration_time.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError(
                "Invalid registration_time format",
                field_name="registration_time",
                field_value=self.registration_time
            )
    
    def update_progress(self, progress_data: Dict[str, Any]) -> None:
        """Update participant progress."""
        self.current_progress.update(progress_data)
    
    def set_final_result(self, result_data: Dict[str, Any]) -> None:
        """Set final competition result for participant."""
        self.final_result = result_data.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "registration_time": self.registration_time,
            "starting_stats": self.starting_stats.copy(),
            "current_progress": self.current_progress.copy(),
            "final_result": self.final_result.copy() if self.final_result else None,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParticipantData':
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            registration_time=data["registration_time"],
            starting_stats=data.get("starting_stats", {}),
            current_progress=data.get("current_progress", {}),
            final_result=data.get("final_result"),
            notes=data.get("notes", "")
        )


@dataclass
class CompetitionMetadata:
    """Metadata for competition tracking and analytics."""
    participant_count: int = 0
    completion_rate: float = 0.0
    created_version: str = "1.0"
    avg_completion_time: Optional[float] = None
    difficulty_rating: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "participant_count": self.participant_count,
            "completion_rate": self.completion_rate,
            "created_version": self.created_version,
            "avg_completion_time": self.avg_completion_time,
            "difficulty_rating": self.difficulty_rating,
            "tags": self.tags.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompetitionMetadata':
        """Create from dictionary."""
        return cls(
            participant_count=data.get("participant_count", 0),
            completion_rate=data.get("completion_rate", 0.0),
            created_version=data.get("created_version", "1.0"),
            avg_completion_time=data.get("avg_completion_time"),
            difficulty_rating=data.get("difficulty_rating"),
            tags=data.get("tags", [])
        )


@dataclass
class Competition:
    """
    Competition model representing any type of competition.
    
    Handles competition lifecycle, participant management, and result tracking
    with type-specific parameter support through the parameters field.
    """
    id: str
    type: CompetitionType
    title: str
    description: str
    status: CompetitionStatus = CompetitionStatus.PENDING
    created_by: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    end_time: str = field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')
    max_participants: int = 50
    participants: Dict[str, ParticipantData] = field(default_factory=dict)
    winners: List[int] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: CompetitionMetadata = field(default_factory=CompetitionMetadata)
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[str] = None
    
    def __post_init__(self):
        """Validate competition data after initialization."""
        # Convert string enums to proper enum types if needed
        if isinstance(self.type, str):
            self.type = CompetitionType(self.type)
        if isinstance(self.status, str):
            self.status = CompetitionStatus(self.status)
        if isinstance(self.metadata, dict):
            self.metadata = CompetitionMetadata.from_dict(self.metadata)
        
        # Convert participant dictionaries to ParticipantData objects
        for user_id, participant in self.participants.items():
            if isinstance(participant, dict):
                self.participants[user_id] = ParticipantData.from_dict(participant)
        
        self.validate()
    
    def validate(self) -> None:
        """
        Validate competition data integrity.
        
        Raises:
            ValidationError: If competition data is invalid
        """
        # Validate ID
        if not isinstance(self.id, str) or len(self.id.strip()) == 0:
            raise ValidationError(
                "Competition ID cannot be empty",
                field_name="id",
                field_value=self.id
            )
        
        # Validate title and description
        if not isinstance(self.title, str) or len(self.title.strip()) < 3:
            raise ValidationError(
                "Competition title must be at least 3 characters",
                field_name="title",
                field_value=self.title
            )
        
        if len(self.title) > 100:
            raise ValidationError(
                "Competition title cannot exceed 100 characters",
                field_name="title",
                field_value=self.title
            )
        
        if not isinstance(self.description, str) or len(self.description.strip()) < 10:
            raise ValidationError(
                "Competition description must be at least 10 characters",
                field_name="description",
                field_value=self.description
            )
        
        if len(self.description) > 1000:
            raise ValidationError(
                "Competition description cannot exceed 1000 characters",
                field_name="description",
                field_value=self.description
            )
        
        # Validate creator
        if not isinstance(self.created_by, int) or self.created_by <= 0:
            raise ValidationError(
                "Created by must be a positive integer",
                field_name="created_by",
                field_value=self.created_by
            )
        
        # Validate max participants
        if not isinstance(self.max_participants, int) or self.max_participants < 2:
            raise ValidationError(
                "Max participants must be at least 2",
                field_name="max_participants",
                field_value=self.max_participants
            )
        
        if self.max_participants > 200:
            raise ValidationError(
                "Max participants cannot exceed 200",
                field_name="max_participants",
                field_value=self.max_participants
            )
        
        # Validate dates
        try:
            created_dt = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
            start_dt = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
            
            if start_dt >= end_dt:
                raise ValidationError(
                    "End time must be after start time",
                    field_name="end_time",
                    field_value=f"start: {self.start_time}, end: {self.end_time}"
                )
                
        except ValueError as e:
            raise ValidationError(
                f"Invalid date format: {e}",
                field_name="dates"
            )
        
        # Validate participant count doesn't exceed maximum
        if len(self.participants) > self.max_participants:
            raise ValidationError(
                f"Participant count ({len(self.participants)}) exceeds maximum ({self.max_participants})",
                field_name="participants"
            )
        
        # Validate winners are participants
        for winner_id in self.winners:
            if str(winner_id) not in self.participants:
                raise ValidationError(
                    f"Winner {winner_id} is not a participant",
                    field_name="winners",
                    field_value=winner_id
                )
    
    def add_participant(self, user_id: int, starting_stats: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a participant to the competition.
        
        Args:
            user_id: Discord user ID
            starting_stats: Initial statistics for the participant
            
        Returns:
            True if participant was added successfully
            
        Raises:
            CompetitionError: If competition is full or user already registered
        """
        user_id_str = str(user_id)
        
        # Check if already registered
        if user_id_str in self.participants:
            raise CompetitionError(
                f"User {user_id} is already registered for competition {self.id}",
                competition_id=self.id
            )
        
        # Check if competition is full
        if len(self.participants) >= self.max_participants:
            raise CompetitionError(
                f"Competition {self.id} is full ({self.max_participants} participants)",
                competition_id=self.id
            )
        
        # Check if competition allows registration
        if self.status not in [CompetitionStatus.PENDING, CompetitionStatus.ACTIVE]:
            raise CompetitionError(
                f"Cannot register for competition with status {self.status.value}",
                competition_id=self.id
            )
        
        # Add participant
        participant = ParticipantData(
            user_id=user_id,
            registration_time=datetime.utcnow().isoformat() + 'Z',
            starting_stats=starting_stats or {}
        )
        
        self.participants[user_id_str] = participant
        self.metadata.participant_count = len(self.participants)
        
        return True
    
    def remove_participant(self, user_id: int) -> bool:
        """
        Remove a participant from the competition.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if participant was removed
        """
        user_id_str = str(user_id)
        
        if user_id_str in self.participants:
            del self.participants[user_id_str]
            self.metadata.participant_count = len(self.participants)
            
            # Remove from winners list if present
            if user_id in self.winners:
                self.winners.remove(user_id)
            
            return True
        
        return False
    
    def update_participant_progress(self, user_id: int, progress_data: Dict[str, Any]) -> bool:
        """
        Update progress for a participant.
        
        Args:
            user_id: Discord user ID
            progress_data: Progress information
            
        Returns:
            True if progress was updated
        """
        user_id_str = str(user_id)
        
        if user_id_str in self.participants:
            self.participants[user_id_str].update_progress(progress_data)
            return True
        
        return False
    
    def set_participant_result(self, user_id: int, result_data: Dict[str, Any]) -> bool:
        """
        Set final result for a participant.
        
        Args:
            user_id: Discord user ID
            result_data: Final result information
            
        Returns:
            True if result was set
        """
        user_id_str = str(user_id)
        
        if user_id_str in self.participants:
            self.participants[user_id_str].set_final_result(result_data)
            return True
        
        return False
    
    def get_participant(self, user_id: int) -> Optional[ParticipantData]:
        """Get participant data for a user."""
        return self.participants.get(str(user_id))
    
    def is_participant(self, user_id: int) -> bool:
        """Check if a user is a participant."""
        return str(user_id) in self.participants
    
    def is_full(self) -> bool:
        """Check if competition is at maximum capacity."""
        return len(self.participants) >= self.max_participants
    
    def can_register(self) -> bool:
        """Check if new participants can register."""
        return (self.status in [CompetitionStatus.PENDING, CompetitionStatus.ACTIVE] and 
                not self.is_full())
    
    def get_duration_hours(self) -> float:
        """Get competition duration in hours."""
        start_dt = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        return (end_dt - start_dt).total_seconds() / 3600
    
    def get_time_remaining_hours(self) -> Optional[float]:
        """Get remaining time in hours, None if completed."""
        if self.status == CompetitionStatus.COMPLETED:
            return None
        
        end_dt = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        now = datetime.utcnow().replace(tzinfo=end_dt.tzinfo)
        
        if now >= end_dt:
            return 0.0
        
        return (end_dt - now).total_seconds() / 3600
    
    def get_completion_rate(self) -> float:
        """Calculate completion rate based on participants with final results."""
        if not self.participants:
            return 0.0
        
        completed = sum(1 for p in self.participants.values() if p.final_result is not None)
        return completed / len(self.participants)
    
    def set_winners(self, winner_ids: List[int]) -> None:
        """
        Set competition winners.
        
        Args:
            winner_ids: List of winner user IDs
        """
        # Validate that all winners are participants
        for winner_id in winner_ids:
            if not self.is_participant(winner_id):
                raise CompetitionError(
                    f"Winner {winner_id} is not a participant",
                    competition_id=self.id
                )
        
        self.winners = winner_ids.copy()
    
    def cancel(self, reason: str = "Cancelled by administrator") -> None:
        """
        Cancel the competition.
        
        Args:
            reason: Reason for cancellation
        """
        self.status = CompetitionStatus.CANCELLED
        self.cancellation_reason = reason
        self.cancelled_at = datetime.utcnow().isoformat() + 'Z'
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert competition to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the competition
        """
        participants_dict = {}
        for user_id, participant in self.participants.items():
            participants_dict[user_id] = participant.to_dict()
        
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "max_participants": self.max_participants,
            "participants": participants_dict,
            "winners": self.winners.copy(),
            "parameters": self.parameters.copy(),
            "metadata": self.metadata.to_dict(),
            "cancellation_reason": self.cancellation_reason,
            "cancelled_at": self.cancelled_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Competition':
        """
        Create Competition instance from dictionary.
        
        Args:
            data: Dictionary containing competition data
            
        Returns:
            Competition instance
            
        Raises:
            ValidationError: If data is invalid
        """
        try:
            return cls(
                id=data["id"],
                type=CompetitionType(data["type"]),
                title=data["title"],
                description=data["description"],
                status=CompetitionStatus(data.get("status", "pending")),
                created_by=data["created_by"],
                created_at=data.get("created_at", datetime.utcnow().isoformat() + 'Z'),
                start_time=data["start_time"],
                end_time=data["end_time"],
                max_participants=data.get("max_participants", 50),
                participants=data.get("participants", {}),
                winners=data.get("winners", []),
                parameters=data.get("parameters", {}),
                metadata=data.get("metadata", {}),
                cancellation_reason=data.get("cancellation_reason"),
                cancelled_at=data.get("cancelled_at")
            )
        except KeyError as e:
            raise ValidationError(f"Missing required field: {e}")
        except Exception as e:
            raise ValidationError(f"Failed to create Competition from data: {e}")
    
    def __str__(self) -> str:
        """String representation of the competition."""
        return f"Competition({self.title}, {self.type.value}, {self.status.value}, {len(self.participants)} participants)"
    
    def __repr__(self) -> str:
        """Detailed string representation of the competition."""
        return (f"Competition(id='{self.id}', type={self.type.value}, title='{self.title}', "
                f"status={self.status.value}, participants={len(self.participants)})")