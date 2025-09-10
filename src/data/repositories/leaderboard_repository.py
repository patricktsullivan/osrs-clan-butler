"""
Leaderboard repository implementation for OSRS Discord Bot.

Provides management for leaderboards, achievements, and ranking systems
with efficient querying and statistical analysis capabilities.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from data.repositories.base_repository import BaseRepository
from data.models.leaderboard import (
    LeaderboardCollection, Leaderboard, LeaderboardType, 
    Achievement, AchievementType, LeaderboardEntry
)
from core.exceptions import ValidationError


class LeaderboardRepository(BaseRepository[LeaderboardCollection]):
    """
    Repository for managing leaderboards and achievements.
    
    Provides specialized methods for ranking management, achievement
    tracking, and statistical analysis of user performance.
    """
    
    def __init__(self, file_path: str):
        """Initialize leaderboard repository."""
        super().__init__(file_path, LeaderboardCollection)
    
    def _get_default_structure(self) -> Dict[str, Any]:
        """Return the default JSON structure for leaderboards."""
        return {
            "leaderboards": {},
            "user_achievements": {},
            "achievement_definitions": {
                "first_win": {
                    "name": "First Victory",
                    "description": "Win your first competition",
                    "type": "first_win",
                    "icon": "🏆"
                },
                "participation_10": {
                    "name": "Active Participant",
                    "description": "Participate in 10 competitions",
                    "type": "participation_milestone",
                    "icon": "🎯"
                },
                "participation_50": {
                    "name": "Competition Veteran",
                    "description": "Participate in 50 competitions",
                    "type": "participation_milestone",
                    "icon": "⭐"
                },
                "win_streak_3": {
                    "name": "Hat Trick",
                    "description": "Win 3 competitions in a row",
                    "type": "win_streak",
                    "icon": "🔥"
                },
                "multiple_wins_5": {
                    "name": "Champion",
                    "description": "Win 5 competitions",
                    "type": "multiple_wins",
                    "icon": "👑"
                },
                "multiple_wins_10": {
                    "name": "Legend",
                    "description": "Win 10 competitions",
                    "type": "multiple_wins",
                    "icon": "🌟"
                }
            },
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat() + 'Z',
                "total_leaderboards": 0,
                "total_achievements_awarded": 0
            }
        }
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate the leaderboard data structure."""
        try:
            # Check required top-level keys
            required_keys = ["leaderboards", "user_achievements", "achievement_definitions"]
            for key in required_keys:
                if key not in data:
                    self.logger.error(f"Missing '{key}' key in data structure")
                    return False
            
            if "metadata" not in data:
                self.logger.warning("Missing 'metadata' key, will be added automatically")
                data["metadata"] = {}
            
            # Validate leaderboard data
            for lb_key, lb_data in data["leaderboards"].items():
                try:
                    Leaderboard.from_dict(lb_data)
                except Exception as e:
                    self.logger.error(f"Invalid leaderboard data for {lb_key}: {e}")
                    return False
            
            # Validate user achievements
            for user_id, achievements in data["user_achievements"].items():
                try:
                    int(user_id)  # Validate user ID format
                    for achievement_data in achievements:
                        Achievement.from_dict(achievement_data)
                except Exception as e:
                    self.logger.error(f"Invalid achievement data for user {user_id}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data validation error: {e}")
            return False
    
    async def get_leaderboard_collection(self) -> LeaderboardCollection:
        """
        Get the complete leaderboard collection.
        
        Returns:
            LeaderboardCollection instance
        """
        data = await self.load_data()
        return LeaderboardCollection.from_dict(data)
    
    async def save_leaderboard_collection(self, collection: LeaderboardCollection) -> None:
        """
        Save the complete leaderboard collection.
        
        Args:
            collection: LeaderboardCollection to save
        """
        data = collection.to_dict()
        data["metadata"]["total_leaderboards"] = len(data["leaderboards"])
        data["metadata"]["total_achievements_awarded"] = sum(
            len(achievements) for achievements in data["user_achievements"].values()
        )
        await self.save_data(data)
    
    async def get_leaderboard(self, leaderboard_type: LeaderboardType,
                            period: Optional[str] = None) -> Optional[Leaderboard]:
        """
        Get a specific leaderboard.
        
        Args:
            leaderboard_type: Type of leaderboard
            period: Optional period identifier
            
        Returns:
            Leaderboard instance or None if not found
        """
        collection = await self.get_leaderboard_collection()
        return collection.get_leaderboard(leaderboard_type, period)
    
    async def create_leaderboard(self, leaderboard_type: LeaderboardType,
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
        collection = await self.get_leaderboard_collection()
        leaderboard = collection.create_leaderboard(
            leaderboard_type, period, period_start, period_end
        )
        await self.save_leaderboard_collection(collection)
        
        self.logger.info(
            f"Created leaderboard: {leaderboard_type.value}" + 
            (f" (period: {period})" if period else ""),
            extra={"leaderboard_type": leaderboard_type.value, "period": period}
        )
        
        return leaderboard
    
    async def update_user_score(self, leaderboard_type: LeaderboardType, user_id: int,
                              score: float, period: Optional[str] = None,
                              display_name: Optional[str] = None,
                              additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Update user score in a leaderboard.
        
        Args:
            leaderboard_type: Type of leaderboard
            user_id: Discord user ID
            score: User's score
            period: Optional period identifier
            display_name: Optional display name
            additional_data: Additional data for the entry
        """
        collection = await self.get_leaderboard_collection()
        collection.update_user_score(
            leaderboard_type, user_id, score, period, display_name, additional_data
        )
        await self.save_leaderboard_collection(collection)
        
        self.logger.debug(
            f"Updated score for user {user_id} in {leaderboard_type.value}: {score}",
            extra={
                "user_id": user_id,
                "leaderboard_type": leaderboard_type.value,
                "score": score,
                "period": period
            }
        )
    
    async def award_achievement(self, user_id: int, achievement_id: str,
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
        collection = await self.get_leaderboard_collection()
        awarded = collection.award_achievement(
            user_id, achievement_id, achievement_type, competition_id, metadata
        )
        
        if awarded:
            await self.save_leaderboard_collection(collection)
            self.logger.info(
                f"Awarded achievement '{achievement_id}' to user {user_id}",
                extra={
                    "user_id": user_id,
                    "achievement_id": achievement_id,
                    "achievement_type": achievement_type.value
                }
            )
        
        return awarded
    
    async def get_user_achievements(self, user_id: int) -> List[Achievement]:
        """
        Get all achievements for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of user's achievements
        """
        collection = await self.get_leaderboard_collection()
        return collection.get_user_achievements(user_id)
    
    async def get_user_leaderboard_positions(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get user's position across all leaderboards.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary mapping leaderboard names to position data
        """
        collection = await self.get_leaderboard_collection()
        return collection.get_user_leaderboard_positions(user_id)
    
    async def get_top_users(self, leaderboard_type: LeaderboardType,
                          limit: int = 10, period: Optional[str] = None) -> List[LeaderboardEntry]:
        """
        Get top users from a leaderboard.
        
        Args:
            leaderboard_type: Type of leaderboard
            limit: Maximum number of entries to return
            period: Optional period identifier
            
        Returns:
            List of top leaderboard entries
        """
        leaderboard = await self.get_leaderboard(leaderboard_type, period)
        if leaderboard:
            return leaderboard.get_top_entries(limit)
        return []
    
    async def get_user_rank(self, leaderboard_type: LeaderboardType, user_id: int,
                          period: Optional[str] = None) -> Optional[int]:
        """
        Get user's rank in a specific leaderboard.
        
        Args:
            leaderboard_type: Type of leaderboard
            user_id: Discord user ID
            period: Optional period identifier
            
        Returns:
            User's rank or None if not found
        """
        leaderboard = await self.get_leaderboard(leaderboard_type, period)
        if leaderboard:
            return leaderboard.get_user_rank(user_id)
        return None
    
    async def update_all_time_leaderboards(self, user_id: int, competition_type: str,
                                         won: bool = False, display_name: Optional[str] = None) -> None:
        """
        Update all-time leaderboards for a user after competition participation.
        
        Args:
            user_id: Discord user ID
            competition_type: Type of competition participated in
            won: Whether the user won the competition
            display_name: Optional display name
        """
        collection = await self.get_leaderboard_collection()
        
        # Update participation leaderboard
        participation_lb = collection.get_leaderboard(LeaderboardType.PARTICIPATION)
        if not participation_lb:
            participation_lb = collection.create_leaderboard(LeaderboardType.PARTICIPATION)
        
        current_entry = participation_lb.get_entry(user_id)
        new_participation_score = (current_entry.score if current_entry else 0) + 1
        collection.update_user_score(
            LeaderboardType.PARTICIPATION, user_id, new_participation_score, display_name=display_name
        )
        
        # Update wins leaderboard if user won
        if won:
            wins_lb = collection.get_leaderboard(LeaderboardType.ALL_TIME_WINS)
            if not wins_lb:
                wins_lb = collection.create_leaderboard(LeaderboardType.ALL_TIME_WINS)
            
            current_wins_entry = wins_lb.get_entry(user_id)
            new_wins_score = (current_wins_entry.score if current_wins_entry else 0) + 1
            collection.update_user_score(
                LeaderboardType.ALL_TIME_WINS, user_id, new_wins_score, display_name=display_name
            )
            
            # Update competition-type specific leaderboard
            type_leaderboard_map = {
                "skill_competition": LeaderboardType.SKILL_COMPETITIONS,
                "boss_competition": LeaderboardType.BOSS_COMPETITIONS,
                "trivia": LeaderboardType.TRIVIA_COMPETITIONS,
                "race": LeaderboardType.RACE_COMPETITIONS,
                "speedrun": LeaderboardType.SPEEDRUN_COMPETITIONS
            }
            
            if competition_type in type_leaderboard_map:
                type_lb_type = type_leaderboard_map[competition_type]
                type_lb = collection.get_leaderboard(type_lb_type)
                if not type_lb:
                    type_lb = collection.create_leaderboard(type_lb_type)
                
                current_type_entry = type_lb.get_entry(user_id)
                new_type_score = (current_type_entry.score if current_type_entry else 0) + 1
                collection.update_user_score(
                    type_lb_type, user_id, new_type_score, display_name=display_name
                )
        
        await self.save_leaderboard_collection(collection)
    
    async def update_monthly_leaderboards(self, user_id: int, won: bool = False,
                                        display_name: Optional[str] = None) -> None:
        """
        Update monthly leaderboards for a user.
        
        Args:
            user_id: Discord user ID
            won: Whether the user won the competition
            display_name: Optional display name
        """
        current_month = datetime.utcnow().strftime("%Y-%m")
        collection = await self.get_leaderboard_collection()
        
        # Update monthly participation
        monthly_participation_lb = collection.get_leaderboard(
            LeaderboardType.PARTICIPATION, current_month
        )
        if not monthly_participation_lb:
            start_of_month = datetime.utcnow().replace(day=1).isoformat() + 'Z'
            monthly_participation_lb = collection.create_leaderboard(
                LeaderboardType.PARTICIPATION, current_month, period_start=start_of_month
            )
        
        current_entry = monthly_participation_lb.get_entry(user_id)
        new_score = (current_entry.score if current_entry else 0) + 1
        collection.update_user_score(
            LeaderboardType.PARTICIPATION, user_id, new_score, 
            period=current_month, display_name=display_name
        )
        
        # Update monthly wins if user won
        if won:
            monthly_wins_lb = collection.get_leaderboard(
                LeaderboardType.MONTHLY_WINS, current_month
            )
            if not monthly_wins_lb:
                start_of_month = datetime.utcnow().replace(day=1).isoformat() + 'Z'
                monthly_wins_lb = collection.create_leaderboard(
                    LeaderboardType.MONTHLY_WINS, current_month, period_start=start_of_month
                )
            
            current_wins_entry = monthly_wins_lb.get_entry(user_id)
            new_wins_score = (current_wins_entry.score if current_wins_entry else 0) + 1
            collection.update_user_score(
                LeaderboardType.MONTHLY_WINS, user_id, new_wins_score,
                period=current_month, display_name=display_name
            )
        
        await self.save_leaderboard_collection(collection)
    
    async def check_and_award_achievements(self, user_id: int, wins: int, 
                                         total_competitions: int,
                                         competition_id: Optional[str] = None) -> List[str]:
        """
        Check and award achievements based on user statistics.
        
        Args:
            user_id: Discord user ID
            wins: Total wins
            total_competitions: Total competitions participated in
            competition_id: Optional current competition ID
            
        Returns:
            List of newly awarded achievement IDs
        """
        awarded_achievements = []
        
        # Check first win achievement
        if wins == 1:
            awarded = await self.award_achievement(
                user_id, "first_win", AchievementType.FIRST_WIN, competition_id
            )
            if awarded:
                awarded_achievements.append("first_win")
        
        # Check participation milestones
        participation_milestones = [10, 25, 50, 100]
        for milestone in participation_milestones:
            if total_competitions == milestone:
                achievement_id = f"participation_{milestone}"
                awarded = await self.award_achievement(
                    user_id, achievement_id, AchievementType.PARTICIPATION_MILESTONE
                )
                if awarded:
                    awarded_achievements.append(achievement_id)
        
        # Check win milestones
        win_milestones = [5, 10, 25, 50]
        for milestone in win_milestones:
            if wins == milestone:
                achievement_id = f"multiple_wins_{milestone}"
                awarded = await self.award_achievement(
                    user_id, achievement_id, AchievementType.MULTIPLE_WINS
                )
                if awarded:
                    awarded_achievements.append(achievement_id)
        
        return awarded_achievements
    
    async def get_leaderboard_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about all leaderboards.
        
        Returns:
            Dictionary with leaderboard statistics
        """
        collection = await self.get_leaderboard_collection()
        
        stats = {
            "total_leaderboards": len(collection.leaderboards),
            "total_users_with_achievements": len(collection.user_achievements),
            "total_achievements_awarded": sum(
                len(achievements) for achievements in collection.user_achievements.values()
            ),
            "leaderboard_entries_count": {},
            "most_popular_achievement": None,
            "achievement_distribution": {}
        }
        
        # Count entries per leaderboard
        for lb_key, leaderboard in collection.leaderboards.items():
            stats["leaderboard_entries_count"][lb_key] = len(leaderboard.entries)
        
        # Analyze achievement distribution
        achievement_counts = {}
        for achievements in collection.user_achievements.values():
            for achievement in achievements:
                achievement_id = achievement.achievement_id
                achievement_counts[achievement_id] = achievement_counts.get(achievement_id, 0) + 1
        
        if achievement_counts:
            stats["most_popular_achievement"] = max(achievement_counts.items(), key=lambda x: x[1])
            stats["achievement_distribution"] = achievement_counts
        
        return stats
    
    async def cleanup_old_monthly_leaderboards(self, months_to_keep: int = 12) -> int:
        """
        Clean up old monthly leaderboards to save space.
        
        Args:
            months_to_keep: Number of recent months to keep
            
        Returns:
            Number of leaderboards cleaned up
        """
        collection = await self.get_leaderboard_collection()
        current_date = datetime.utcnow()
        
        # Calculate cutoff date
        cutoff_year = current_date.year
        cutoff_month = current_date.month - months_to_keep
        
        while cutoff_month <= 0:
            cutoff_month += 12
            cutoff_year -= 1
        
        cutoff_date_str = f"{cutoff_year:04d}-{cutoff_month:02d}"
        
        # Find leaderboards to remove
        leaderboards_to_remove = []
        for lb_key in collection.leaderboards.keys():
            # Check if it's a monthly leaderboard
            if "_" in lb_key and lb_key.split("_")[-1].count("-") == 1:
                period = lb_key.split("_")[-1]
                if period < cutoff_date_str:
                    leaderboards_to_remove.append(lb_key)
        
        # Remove old leaderboards
        for lb_key in leaderboards_to_remove:
            del collection.leaderboards[lb_key]
        
        if leaderboards_to_remove:
            await self.save_leaderboard_collection(collection)
            self.logger.info(f"Cleaned up {len(leaderboards_to_remove)} old monthly leaderboards")
        
        return len(leaderboards_to_remove)