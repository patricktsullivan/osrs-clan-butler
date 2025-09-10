"""
Abstract base class for competition managers.

Defines the interface and common functionality for all competition types
including participant management, progress tracking, and ranking calculation.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import uuid

from core.exceptions import (
    CompetitionError, CompetitionNotFoundError, CompetitionFullError,
    UserNotFoundError, ValidationError
)
from config.logging_config import LoggerMixin


class CompetitionStatus(Enum):
    """Enumeration of possible competition statuses."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class CompetitionType(Enum):
    """Enumeration of competition types."""
    SKILL_COMPETITION = "skill_competition"
    BOSS_COMPETITION = "boss_competition"
    TRIVIA = "trivia"
    RACE = "race"
    SPEEDRUN = "speedrun"


class BaseCompetitionManager(ABC, LoggerMixin):
    """
    Abstract base class for all competition type managers.
    
    Provides common functionality for competition lifecycle management,
    participant handling, and progress tracking.
    """
    
    def __init__(self, competition_repo, user_repo, settings):
        """
        Initialize the competition manager.
        
        Args:
            competition_repo: Repository for competition data
            user_repo: Repository for user data
            settings: Bot configuration settings
        """
        self.competition_repo = competition_repo
        self.user_repo = user_repo
        self.settings = settings
        self._active_competitions: Set[str] = set()
    
    @property
    @abstractmethod
    def competition_type(self) -> CompetitionType:
        """Return the competition type this manager handles."""
        pass
    
    @abstractmethod
    async def create_competition(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new competition instance with specified parameters.
        
        Returns:
            Dictionary containing competition data
        """
        pass
    
    @abstractmethod
    async def validate_competition_parameters(self, **kwargs) -> bool:
        """
        Validate competition-specific parameters.
        
        Returns:
            True if parameters are valid
            
        Raises:
            ValidationError: If parameters are invalid
        """
        pass
    
    @abstractmethod
    async def register_participant(self, user_id: int, competition_id: str, 
                                 **kwargs) -> Dict[str, Any]:
        """
        Register a user for the specified competition.
        
        Args:
            user_id: Discord user ID
            competition_id: Competition identifier
            **kwargs: Additional registration parameters
            
        Returns:
            Registration data
        """
        pass
    
    @abstractmethod
    async def update_progress(self, user_id: int, competition_id: str, 
                            progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update participant progress in the competition.
        
        Args:
            user_id: Discord user ID
            competition_id: Competition identifier
            progress_data: Progress information
            
        Returns:
            Updated progress data
        """
        pass
    
    @abstractmethod
    async def calculate_rankings(self, competition_id: str) -> List[Dict[str, Any]]:
        """
        Calculate current rankings for the competition.
        
        Args:
            competition_id: Competition identifier
            
        Returns:
            List of participants sorted by ranking
        """
        pass
    
    async def _generate_competition_id(self, title: str) -> str:
        """Generate a unique competition ID."""
        # Create a readable ID based on title and timestamp
        safe_title = "".join(c.lower() if c.isalnum() else "_" for c in title)[:20]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
        unique_suffix = str(uuid.uuid4())[:8]
        
        return f"{self.competition_type.value}_{safe_title}_{timestamp}_{unique_suffix}"
    
    async def _validate_common_parameters(self, title: str, description: str,
                                        duration_hours: int, max_participants: int,
                                        created_by: int) -> None:
        """Validate common competition parameters."""
        if not title or len(title) < 3:
            raise ValidationError("Competition title must be at least 3 characters")
        
        if len(title) > 100:
            raise ValidationError("Competition title cannot exceed 100 characters")
        
        if not description or len(description) < 10:
            raise ValidationError("Competition description must be at least 10 characters")
        
        if len(description) > 1000:
            raise ValidationError("Competition description cannot exceed 1000 characters")
        
        if duration_hours < 1 or duration_hours > 168:  # 1 hour to 1 week
            raise ValidationError("Competition duration must be between 1 and 168 hours")
        
        if max_participants < 2 or max_participants > self.settings.bot.max_participants_per_competition:
            raise ValidationError(
                f"Max participants must be between 2 and "
                f"{self.settings.bot.max_participants_per_competition}"
            )
        
        # Verify creator exists in user repository
        user_data = await self.user_repo.load_data()
        if str(created_by) not in user_data.get('users', {}):
            raise UserNotFoundError(str(created_by))
    
    async def _create_base_competition(self, title: str, description: str,
                                     duration_hours: int, max_participants: int,
                                     created_by: int, **specific_params) -> Dict[str, Any]:
        """Create base competition structure with common fields."""
        await self._validate_common_parameters(
            title, description, duration_hours, max_participants, created_by
        )
        
        # Check if we have too many active competitions
        active_count = await self._count_active_competitions()
        if active_count >= self.settings.bot.max_concurrent_competitions:
            raise CompetitionError(
                f"Maximum number of active competitions reached "
                f"({self.settings.bot.max_concurrent_competitions})"
            )
        
        competition_id = await self._generate_competition_id(title)
        start_time = datetime.utcnow() + timedelta(minutes=5)  # 5-minute registration period
        end_time = start_time + timedelta(hours=duration_hours)
        
        competition_data = {
            "id": competition_id,
            "type": self.competition_type.value,
            "title": title,
            "description": description,
            "status": CompetitionStatus.PENDING.value,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat() + 'Z',
            "start_time": start_time.isoformat() + 'Z',
            "end_time": end_time.isoformat() + 'Z',
            "max_participants": max_participants,
            "participants": {},
            "winners": [],
            "parameters": specific_params,
            "metadata": {
                "participant_count": 0,
                "completion_rate": 0.0,
                "created_version": "1.0"
            }
        }
        
        # Save to repository
        competitions_data = await self.competition_repo.load_data()
        competitions_data.setdefault('competitions', {})[competition_id] = competition_data
        await self.competition_repo.save_data(competitions_data)
        
        # Track active competition
        self._active_competitions.add(competition_id)
        
        self.logger.info(
            f"Created {self.competition_type.value} competition: {competition_id}",
            extra={
                "competition_id": competition_id,
                "created_by": created_by,
                "title": title
            }
        )
        
        return competition_data
    
    async def get_competition(self, competition_id: str) -> Dict[str, Any]:
        """
        Retrieve competition data by ID.
        
        Args:
            competition_id: Competition identifier
            
        Returns:
            Competition data
            
        Raises:
            CompetitionNotFoundError: If competition doesn't exist
        """
        competitions_data = await self.competition_repo.load_data()
        competitions = competitions_data.get('competitions', {})
        
        if competition_id not in competitions:
            raise CompetitionNotFoundError(competition_id)
        
        return competitions[competition_id]
    
    async def start_competition(self, competition_id: str) -> Dict[str, Any]:
        """
        Start a pending competition.
        
        Args:
            competition_id: Competition identifier
            
        Returns:
            Updated competition data
        """
        competition = await self.get_competition(competition_id)
        
        if competition['status'] != CompetitionStatus.PENDING.value:
            raise CompetitionError(
                f"Competition {competition_id} cannot be started (status: {competition['status']})",
                competition_id=competition_id
            )
        
        # Update status and start time
        competition['status'] = CompetitionStatus.ACTIVE.value
        competition['start_time'] = datetime.utcnow().isoformat() + 'Z'
        
        # Save changes
        await self.competition_repo.update_field(
            f"competitions.{competition_id}",
            competition
        )
        
        self.logger.info(
            f"Started competition: {competition_id}",
            extra={"competition_id": competition_id}
        )
        
        return competition
    
    async def end_competition(self, competition_id: str) -> Dict[str, Any]:
        """
        End an active competition and determine winners.
        
        Args:
            competition_id: Competition identifier
            
        Returns:
            Competition results with final rankings
        """
        competition = await self.get_competition(competition_id)
        
        if competition['status'] not in [CompetitionStatus.ACTIVE.value, CompetitionStatus.PAUSED.value]:
            raise CompetitionError(
                f"Competition {competition_id} cannot be ended (status: {competition['status']})",
                competition_id=competition_id
            )
        
        # Calculate final rankings
        final_rankings = await self.calculate_rankings(competition_id)
        
        # Determine winners (top 3)
        winners = [participant['user_id'] for participant in final_rankings[:3]]
        
        # Update competition
        competition['status'] = CompetitionStatus.COMPLETED.value
        competition['end_time'] = datetime.utcnow().isoformat() + 'Z'
        competition['winners'] = winners
        competition['metadata']['completion_rate'] = self._calculate_completion_rate(competition)
        
        # Save changes
        await self.competition_repo.update_field(
            f"competitions.{competition_id}",
            competition
        )
        
        # Remove from active competitions
        self._active_competitions.discard(competition_id)
        
        self.logger.info(
            f"Ended competition: {competition_id} with {len(winners)} winners",
            extra={
                "competition_id": competition_id,
                "winners": winners,
                "participant_count": len(competition['participants'])
            }
        )
        
        return {
            "competition": competition,
            "final_rankings": final_rankings,
            "winners": winners
        }
    
    async def cancel_competition(self, competition_id: str, reason: str = "Cancelled by administrator") -> None:
        """
        Cancel a competition.
        
        Args:
            competition_id: Competition identifier
            reason: Reason for cancellation
        """
        competition = await self.get_competition(competition_id)
        
        competition['status'] = CompetitionStatus.CANCELLED.value
        competition['cancellation_reason'] = reason
        competition['cancelled_at'] = datetime.utcnow().isoformat() + 'Z'
        
        await self.competition_repo.update_field(
            f"competitions.{competition_id}",
            competition
        )
        
        self._active_competitions.discard(competition_id)
        
        self.logger.info(
            f"Cancelled competition: {competition_id}",
            extra={"competition_id": competition_id, "reason": reason}
        )
    
    async def get_participant_data(self, competition_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get participant data for a specific user in a competition."""
        competition = await self.get_competition(competition_id)
        return competition['participants'].get(str(user_id))
    
    async def is_participant_registered(self, competition_id: str, user_id: int) -> bool:
        """Check if a user is registered for a competition."""
        participant_data = await self.get_participant_data(competition_id, user_id)
        return participant_data is not None
    
    async def get_active_competitions(self) -> List[Dict[str, Any]]:
        """Get all active competitions managed by this manager."""
        competitions_data = await self.competition_repo.load_data()
        competitions = competitions_data.get('competitions', {})
        
        active_competitions = []
        for comp_id, comp_data in competitions.items():
            if (comp_data['type'] == self.competition_type.value and 
                comp_data['status'] in [CompetitionStatus.PENDING.value, CompetitionStatus.ACTIVE.value]):
                active_competitions.append(comp_data)
        
        return active_competitions
    
    async def _count_active_competitions(self) -> int:
        """Count the number of active competitions."""
        active_competitions = await self.get_active_competitions()
        return len(active_competitions)
    
    def _calculate_completion_rate(self, competition: Dict[str, Any]) -> float:
        """Calculate the completion rate for a competition."""
        total_participants = len(competition['participants'])
        if total_participants == 0:
            return 0.0
        
        completed_participants = sum(
            1 for participant in competition['participants'].values()
            if participant.get('final_result') is not None
        )
        
        return completed_participants / total_participants
    
    async def get_competition_statistics(self, competition_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a competition."""
        competition = await self.get_competition(competition_id)
        
        total_participants = len(competition['participants'])
        active_participants = sum(
            1 for participant in competition['participants'].values()
            if participant.get('current_progress') is not None
        )
        
        return {
            "competition_id": competition_id,
            "type": competition['type'],
            "status": competition['status'],
            "total_participants": total_participants,
            "active_participants": active_participants,
            "completion_rate": self._calculate_completion_rate(competition),
            "duration_hours": self._calculate_duration_hours(competition),
            "time_remaining": self._calculate_time_remaining(competition)
        }
    
    def _calculate_duration_hours(self, competition: Dict[str, Any]) -> float:
        """Calculate the duration of a competition in hours."""
        start_time = datetime.fromisoformat(competition['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(competition['end_time'].replace('Z', '+00:00'))
        return (end_time - start_time).total_seconds() / 3600
    
    def _calculate_time_remaining(self, competition: Dict[str, Any]) -> Optional[float]:
        """Calculate time remaining in competition (hours), None if completed."""
        if competition['status'] == CompetitionStatus.COMPLETED.value:
            return None
        
        end_time = datetime.fromisoformat(competition['end_time'].replace('Z', '+00:00'))
        now = datetime.utcnow().replace(tzinfo=end_time.tzinfo)
        
        if now >= end_time:
            return 0.0
        
        return (end_time - now).total_seconds() / 3600