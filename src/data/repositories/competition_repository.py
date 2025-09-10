"""
Competition repository implementation for OSRS Discord Bot.

Provides CRUD operations for competition data with filtering,
status management, and performance tracking capabilities.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

from data.repositories.base_repository import BaseRepository
from data.models.competition import Competition, CompetitionStatus, CompetitionType
from core.exceptions import CompetitionNotFoundError, CompetitionError, ValidationError


class CompetitionRepository(BaseRepository[Competition]):
    """
    Repository for managing competition data and lifecycle.
    
    Provides specialized methods for competition management, participant
    tracking, and status transitions with comprehensive querying capabilities.
    """
    
    def __init__(self, file_path: str):
        """Initialize competition repository."""
        super().__init__(file_path, Competition)
    
    def _get_default_structure(self) -> Dict[str, Any]:
        """Return the default JSON structure for competitions."""
        return {
            "competitions": {},
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.now(timezone.utc).isoformat() + 'Z',
                "total_competitions": 0,
                "active_competitions": 0
            }
        }
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate the competition data structure."""
        try:
            # Check required top-level keys
            if "competitions" not in data:
                self.logger.error("Missing 'competitions' key in data structure")
                return False
            
            if "metadata" not in data:
                self.logger.warning("Missing 'metadata' key, will be added automatically")
                data["metadata"] = {}
            
            # Validate each competition entry
            for comp_id, comp_data in data["competitions"].items():
                try:
                    # Validate competition data by creating Competition object
                    Competition.from_dict(comp_data)
                    
                except (ValueError, ValidationError) as e:
                    self.logger.error(f"Invalid competition data for {comp_id}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data validation error: {e}")
            return False
    
    async def create_competition(self, competition: Competition) -> Competition:
        """
        Create a new competition.
        
        Args:
            competition: Competition object to create
            
        Returns:
            Created competition object
            
        Raises:
            CompetitionError: If competition already exists
        """
        # Check if competition already exists
        existing_comp = await self.get_by_id(competition.id, raise_if_not_found=False)
        if existing_comp:
            raise CompetitionError(
                f"Competition with ID {competition.id} already exists",
                competition_id=competition.id
            )
        
        # Save to repository
        data = await self.load_data()
        data["competitions"][competition.id] = competition.to_dict()
        data["metadata"]["total_competitions"] = len(data["competitions"])
        await self._update_active_count(data)
        await self.save_data(data)
        
        self.logger.info(
            f"Created new competition: {competition.id}",
            extra={
                "competition_id": competition.id,
                "type": competition.type.value,
                "created_by": competition.created_by
            }
        )
        
        return competition
    
    async def get_by_id(self, competition_id: str, 
                       raise_if_not_found: bool = True) -> Optional[Competition]:
        """
        Get competition by ID.
        
        Args:
            competition_id: Competition identifier
            raise_if_not_found: Whether to raise exception if not found
            
        Returns:
            Competition object or None if not found
            
        Raises:
            CompetitionNotFoundError: If competition doesn't exist and raise_if_not_found is True
        """
        data = await self.load_data()
        comp_data = data["competitions"].get(competition_id)
        
        if comp_data:
            return Competition.from_dict(comp_data)
        elif raise_if_not_found:
            raise CompetitionNotFoundError(competition_id)
        
        return None
    
    async def update_competition(self, competition: Competition) -> None:
        """
        Update an existing competition.
        
        Args:
            competition: Competition object with updated data
            
        Raises:
            CompetitionNotFoundError: If competition doesn't exist
        """
        data = await self.load_data()
        
        if competition.id not in data["competitions"]:
            raise CompetitionNotFoundError(competition.id)
        
        # Save updated competition data
        data["competitions"][competition.id] = competition.to_dict()
        await self._update_active_count(data)
        await self.save_data(data)
        
        self.logger.debug(f"Updated competition: {competition.id}")
    
    async def delete_competition(self, competition_id: str) -> bool:
        """
        Delete a competition.
        
        Args:
            competition_id: Competition identifier
            
        Returns:
            True if competition was deleted, False if not found
        """
        data = await self.load_data()
        
        if competition_id in data["competitions"]:
            del data["competitions"][competition_id]
            data["metadata"]["total_competitions"] = len(data["competitions"])
            await self._update_active_count(data)
            await self.save_data(data)
            
            self.logger.info(f"Deleted competition: {competition_id}")
            return True
        
        return False
    
    async def get_competitions_by_status(self, status: CompetitionStatus) -> List[Competition]:
        """
        Get all competitions with a specific status.
        
        Args:
            status: Competition status to filter by
            
        Returns:
            List of competitions with the specified status
        """
        data = await self.load_data()
        competitions = []
        
        for comp_data in data["competitions"].values():
            if comp_data.get("status") == status.value:
                try:
                    competitions.append(Competition.from_dict(comp_data))
                except Exception as e:
                    self.logger.warning(f"Failed to load competition data: {e}")
        
        return competitions
    
    async def get_competitions_by_type(self, competition_type: CompetitionType) -> List[Competition]:
        """
        Get all competitions of a specific type.
        
        Args:
            competition_type: Competition type to filter by
            
        Returns:
            List of competitions of the specified type
        """
        data = await self.load_data()
        competitions = []
        
        for comp_data in data["competitions"].values():
            if comp_data.get("type") == competition_type.value:
                try:
                    competitions.append(Competition.from_dict(comp_data))
                except Exception as e:
                    self.logger.warning(f"Failed to load competition data: {e}")
        
        return competitions
    
    async def get_competitions_by_creator(self, creator_id: int) -> List[Competition]:
        """
        Get all competitions created by a specific user.
        
        Args:
            creator_id: Discord user ID of the creator
            
        Returns:
            List of competitions created by the user
        """
        data = await self.load_data()
        competitions = []
        
        for comp_data in data["competitions"].values():
            if comp_data.get("created_by") == creator_id:
                try:
                    competitions.append(Competition.from_dict(comp_data))
                except Exception as e:
                    self.logger.warning(f"Failed to load competition data: {e}")
        
        return competitions
    
    async def get_active_competitions(self) -> List[Competition]:
        """
        Get all active competitions (pending or active status).
        
        Returns:
            List of active competitions
        """
        active_statuses = [CompetitionStatus.PENDING, CompetitionStatus.ACTIVE]
        active_competitions = []
        
        for status in active_statuses:
            competitions = await self.get_competitions_by_status(status)
            active_competitions.extend(competitions)
        
        return active_competitions
    
    async def get_user_competitions(self, user_id: int) -> List[Competition]:
        """
        Get all competitions where a user is a participant.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of competitions the user has participated in
        """
        data = await self.load_data()
        competitions = []
        user_id_str = str(user_id)
        
        for comp_data in data["competitions"].values():
            if user_id_str in comp_data.get("participants", {}):
                try:
                    competitions.append(Competition.from_dict(comp_data))
                except Exception as e:
                    self.logger.warning(f"Failed to load competition data: {e}")
        
        return competitions
    
    async def get_competitions_in_date_range(self, start_date: datetime, 
                                           end_date: datetime) -> List[Competition]:
        """
        Get competitions within a specific date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of competitions in the date range
        """
        data = await self.load_data()
        competitions = []
        
        for comp_data in data["competitions"].values():
            try:
                comp_start = datetime.fromisoformat(comp_data["start_time"].replace('Z', '+00:00'))
                comp_end = datetime.fromisoformat(comp_data["end_time"].replace('Z', '+00:00'))
                
                # Check if competition overlaps with date range
                if (comp_start <= end_date and comp_end >= start_date):
                    competitions.append(Competition.from_dict(comp_data))
                    
            except Exception as e:
                self.logger.warning(f"Failed to process competition date: {e}")
        
        return competitions
    
    async def get_recent_competitions(self, days: int = 7) -> List[Competition]:
        """
        Get competitions from recent days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of recent competitions
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        return await self.get_competitions_in_date_range(start_date, end_date)
    
    async def get_upcoming_competitions(self, days: int = 7) -> List[Competition]:
        """
        Get upcoming competitions.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of upcoming competitions
        """
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days)
        
        competitions = await self.get_competitions_in_date_range(start_date, end_date)
        
        # Filter to only pending/active competitions
        return [comp for comp in competitions 
                if comp.status in [CompetitionStatus.PENDING, CompetitionStatus.ACTIVE]]
    
    async def update_competition_status(self, competition_id: str, 
                                      new_status: CompetitionStatus) -> Competition:
        """
        Update competition status.
        
        Args:
            competition_id: Competition identifier
            new_status: New status to set
            
        Returns:
            Updated competition object
            
        Raises:
            CompetitionNotFoundError: If competition doesn't exist
        """
        competition = await self.get_by_id(competition_id)
        old_status = competition.status
        
        competition.status = new_status
        
        # Update timestamps based on status change
        now = datetime.utcnow().isoformat() + 'Z'
        if new_status == CompetitionStatus.ACTIVE and old_status == CompetitionStatus.PENDING:
            competition.start_time = now
        elif new_status == CompetitionStatus.COMPLETED:
            competition.end_time = now
        
        await self.update_competition(competition)
        
        self.logger.info(
            f"Updated competition {competition_id} status: {old_status.value} -> {new_status.value}",
            extra={"competition_id": competition_id, "old_status": old_status.value, "new_status": new_status.value}
        )
        
        return competition
    
    async def add_participant(self, competition_id: str, user_id: int,
                            starting_stats: Optional[Dict[str, Any]] = None) -> Competition:
        """
        Add a participant to a competition.
        
        Args:
            competition_id: Competition identifier
            user_id: Discord user ID
            starting_stats: Optional starting statistics
            
        Returns:
            Updated competition object
            
        Raises:
            CompetitionNotFoundError: If competition doesn't exist
            CompetitionError: If registration fails
        """
        competition = await self.get_by_id(competition_id)
        competition.add_participant(user_id, starting_stats)
        await self.update_competition(competition)
        
        self.logger.info(
            f"Added participant {user_id} to competition {competition_id}",
            extra={"competition_id": competition_id, "user_id": user_id}
        )
        
        return competition
    
    async def remove_participant(self, competition_id: str, user_id: int) -> Competition:
        """
        Remove a participant from a competition.
        
        Args:
            competition_id: Competition identifier
            user_id: Discord user ID
            
        Returns:
            Updated competition object
            
        Raises:
            CompetitionNotFoundError: If competition doesn't exist
        """
        competition = await self.get_by_id(competition_id)
        removed = competition.remove_participant(user_id)
        
        if removed:
            await self.update_competition(competition)
            self.logger.info(
                f"Removed participant {user_id} from competition {competition_id}",
                extra={"competition_id": competition_id, "user_id": user_id}
            )
        
        return competition
    
    async def update_participant_progress(self, competition_id: str, user_id: int,
                                        progress_data: Dict[str, Any]) -> Competition:
        """
        Update participant progress in a competition.
        
        Args:
            competition_id: Competition identifier
            user_id: Discord user ID
            progress_data: Progress information
            
        Returns:
            Updated competition object
            
        Raises:
            CompetitionNotFoundError: If competition doesn't exist
        """
        competition = await self.get_by_id(competition_id)
        updated = competition.update_participant_progress(user_id, progress_data)
        
        if updated:
            await self.update_competition(competition)
            self.logger.debug(
                f"Updated progress for participant {user_id} in competition {competition_id}",
                extra={"competition_id": competition_id, "user_id": user_id}
            )
        
        return competition
    
    async def search_competitions(self, query: str) -> List[Competition]:
        """
        Search competitions by title or description.
        
        Args:
            query: Search query (case-insensitive)
            
        Returns:
            List of matching competitions
        """
        data = await self.load_data()
        competitions = []
        query_lower = query.lower()
        
        for comp_data in data["competitions"].values():
            try:
                title = comp_data.get("title", "").lower()
                description = comp_data.get("description", "").lower()
                
                if query_lower in title or query_lower in description:
                    competitions.append(Competition.from_dict(comp_data))
                    
            except Exception as e:
                self.logger.warning(f"Failed to process competition in search: {e}")
        
        return competitions
    
    async def get_competitions_requiring_attention(self) -> List[Competition]:
        """
        Get competitions that require attention (starting, ending, etc.).
        
        Returns:
            List of competitions requiring attention
        """
        now = datetime.utcnow()
        competitions_needing_attention = []
        
        active_competitions = await self.get_active_competitions()
        
        for competition in active_competitions:
            try:
                start_time = datetime.fromisoformat(competition.start_time.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(competition.end_time.replace('Z', '+00:00'))
                
                # Check if competition should start
                if (competition.status == CompetitionStatus.PENDING and 
                    now >= start_time):
                    competitions_needing_attention.append(competition)
                
                # Check if competition should end
                elif (competition.status == CompetitionStatus.ACTIVE and 
                      now >= end_time):
                    competitions_needing_attention.append(competition)
                    
            except Exception as e:
                self.logger.warning(f"Failed to check competition {competition.id}: {e}")
        
        return competitions_needing_attention
    
    async def _update_active_count(self, data: Dict[str, Any]) -> None:
        """Update the active competition count in metadata."""
        active_count = 0
        for comp_data in data["competitions"].values():
            status = comp_data.get("status")
            if status in [CompetitionStatus.PENDING.value, CompetitionStatus.ACTIVE.value]:
                active_count += 1
        
        data["metadata"]["active_competitions"] = active_count
    
    async def get_repository_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the competition repository.
        
        Returns:
            Dictionary with various statistics
        """
        data = await self.load_data()
        competitions = []
        
        # Load all competitions
        for comp_data in data["competitions"].values():
            try:
                competitions.append(Competition.from_dict(comp_data))
            except Exception as e:
                self.logger.warning(f"Failed to load competition for stats: {e}")
        
        if not competitions:
            return {
                "total_competitions": 0,
                "active_competitions": 0,
                "completed_competitions": 0,
                "cancelled_competitions": 0,
                "total_participants": 0,
                "avg_participants_per_competition": 0.0
            }
        
        # Calculate statistics
        status_counts = {}
        type_counts = {}
        total_participants = 0
        
        for competition in competitions:
            # Count by status
            status = competition.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by type
            comp_type = competition.type.value
            type_counts[comp_type] = type_counts.get(comp_type, 0) + 1
            
            # Count participants
            total_participants += len(competition.participants)
        
        avg_participants = total_participants / len(competitions) if competitions else 0
        
        # Find most popular competition type
        most_popular_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        
        return {
            "total_competitions": len(competitions),
            "active_competitions": status_counts.get("active", 0) + status_counts.get("pending", 0),
            "completed_competitions": status_counts.get("completed", 0),
            "cancelled_competitions": status_counts.get("cancelled", 0),
            "total_participants": total_participants,
            "avg_participants_per_competition": round(avg_participants, 2),
            "competitions_by_type": type_counts,
            "competitions_by_status": status_counts,
            "most_popular_type": most_popular_type
        }