"""
User repository implementation for OSRS Discord Bot.

Provides CRUD operations for user data with validation,
caching, and efficient querying capabilities.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from data.repositories.base_repository import BaseRepository
from data.models.user import User, UserPreferences
from core.exceptions import UserNotFoundError, UserError, ValidationError


class UserRepository(BaseRepository[User]):
    """
    Repository for managing user data with OSRS account integration.
    
    Provides specialized methods for user management, account linking,
    and competition participation tracking.
    """
    
    def __init__(self, file_path: str):
        """Initialize user repository."""
        super().__init__(file_path, User)
    
    def _get_default_structure(self) -> Dict[str, Any]:
        """Return the default JSON structure for users."""
        return {
            "users": {},
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat() + 'Z',
                "total_users": 0
            }
        }
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate the user data structure."""
        try:
            # Check required top-level keys
            if "users" not in data:
                self.logger.error("Missing 'users' key in data structure")
                return False
            
            if "metadata" not in data:
                self.logger.warning("Missing 'metadata' key, will be added automatically")
                data["metadata"] = {}
            
            # Validate each user entry
            for user_id, user_data in data["users"].items():
                try:
                    # Validate user ID format
                    int(user_id)
                    
                    # Validate user data by creating User object
                    User.from_dict(user_data)
                    
                except (ValueError, ValidationError) as e:
                    self.logger.error(f"Invalid user data for {user_id}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data validation error: {e}")
            return False
    
    async def create_user(self, discord_id: int, osrs_username: Optional[str] = None,
                         display_name: Optional[str] = None) -> User:
        """
        Create a new user.
        
        Args:
            discord_id: Discord user ID
            osrs_username: Optional OSRS username
            display_name: Optional display name
            
        Returns:
            Created user object
            
        Raises:
            UserError: If user already exists
        """
        # Check if user already exists
        existing_user = await self.get_user_by_discord_id(discord_id)
        if existing_user:
            raise UserError(
                f"User with Discord ID {discord_id} already exists",
                user_id=discord_id
            )
        
        # Create new user
        user = User(
            discord_id=discord_id,
            osrs_username=osrs_username,
            display_name=display_name
        )
        
        # Save to repository
        data = await self.load_data()
        data["users"][str(discord_id)] = user.to_dict()
        data["metadata"]["total_users"] = len(data["users"])
        await self.save_data(data)
        
        self.logger.info(
            f"Created new user: {discord_id}",
            extra={"discord_id": discord_id, "osrs_username": osrs_username}
        )
        
        return user
    
    async def get_user_by_discord_id(self, discord_id: int) -> Optional[User]:
        """
        Get user by Discord ID.
        
        Args:
            discord_id: Discord user ID
            
        Returns:
            User object or None if not found
        """
        data = await self.load_data()
        user_data = data["users"].get(str(discord_id))
        
        if user_data:
            return User.from_dict(user_data)
        return None
    
    async def get_user_by_osrs_username(self, osrs_username: str) -> Optional[User]:
        """
        Get user by OSRS username.
        
        Args:
            osrs_username: OSRS username (case-insensitive)
            
        Returns:
            User object or None if not found
        """
        data = await self.load_data()
        username_lower = osrs_username.lower()
        
        for user_data in data["users"].values():
            if (user_data.get("osrs_username") and 
                user_data["osrs_username"].lower() == username_lower):
                return User.from_dict(user_data)
        
        return None
    
    async def get_user_by_wise_old_man_id(self, wom_id: int) -> Optional[User]:
        """
        Get user by Wise Old Man ID.
        
        Args:
            wom_id: Wise Old Man player ID
            
        Returns:
            User object or None if not found
        """
        data = await self.load_data()
        
        for user_data in data["users"].values():
            if user_data.get("wise_old_man_id") == wom_id:
                return User.from_dict(user_data)
        
        return None
    
    async def update_user(self, user: User) -> None:
        """
        Update an existing user.
        
        Args:
            user: User object with updated data
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        data = await self.load_data()
        user_id_str = str(user.discord_id)
        
        if user_id_str not in data["users"]:
            raise UserNotFoundError(str(user.discord_id))
        
        # Update activity timestamp
        user.update_activity()
        
        # Save updated user data
        data["users"][user_id_str] = user.to_dict()
        await self.save_data(data)
        
        self.logger.debug(f"Updated user: {user.discord_id}")
    
    async def delete_user(self, discord_id: int) -> bool:
        """
        Delete a user.
        
        Args:
            discord_id: Discord user ID
            
        Returns:
            True if user was deleted, False if not found
        """
        data = await self.load_data()
        user_id_str = str(discord_id)
        
        if user_id_str in data["users"]:
            del data["users"][user_id_str]
            data["metadata"]["total_users"] = len(data["users"])
            await self.save_data(data)
            
            self.logger.info(f"Deleted user: {discord_id}")
            return True
        
        return False
    
    async def link_osrs_account(self, discord_id: int, osrs_username: str,
                               wise_old_man_id: Optional[int] = None) -> User:
        """
        Link an OSRS account to a user.
        
        Args:
            discord_id: Discord user ID
            osrs_username: OSRS username
            wise_old_man_id: Optional Wise Old Man player ID
            
        Returns:
            Updated user object
            
        Raises:
            UserNotFoundError: If user doesn't exist
            UserError: If OSRS username is already linked to another user
        """
        # Check if OSRS username is already linked
        existing_user = await self.get_user_by_osrs_username(osrs_username)
        if existing_user and existing_user.discord_id != discord_id:
            raise UserError(
                f"OSRS username '{osrs_username}' is already linked to another user",
                username=osrs_username
            )
        
        # Get the user
        user = await self.get_user_by_discord_id(discord_id)
        if not user:
            raise UserNotFoundError(str(discord_id))
        
        # Link the account
        user.link_osrs_account(osrs_username, wise_old_man_id)
        
        # Save changes
        await self.update_user(user)
        
        self.logger.info(
            f"Linked OSRS account for user {discord_id}: {osrs_username}",
            extra={"discord_id": discord_id, "osrs_username": osrs_username}
        )
        
        return user
    
    async def unlink_osrs_account(self, discord_id: int) -> User:
        """
        Unlink OSRS account from a user.
        
        Args:
            discord_id: Discord user ID
            
        Returns:
            Updated user object
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        user = await self.get_user_by_discord_id(discord_id)
        if not user:
            raise UserNotFoundError(str(discord_id))
        
        old_username = user.osrs_username
        user.unlink_osrs_account()
        
        await self.update_user(user)
        
        self.logger.info(
            f"Unlinked OSRS account for user {discord_id}: {old_username}",
            extra={"discord_id": discord_id, "old_username": old_username}
        )
        
        return user
    
    async def update_user_preferences(self, discord_id: int, 
                                    preferences: UserPreferences) -> User:
        """
        Update user preferences.
        
        Args:
            discord_id: Discord user ID
            preferences: New preferences
            
        Returns:
            Updated user object
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        user = await self.get_user_by_discord_id(discord_id)
        if not user:
            raise UserNotFoundError(str(discord_id))
        
        user.preferences = preferences
        await self.update_user(user)
        
        return user
    
    async def add_competition_participation(self, discord_id: int, won: bool = False) -> User:
        """
        Record competition participation for a user.
        
        Args:
            discord_id: Discord user ID
            won: Whether the user won the competition
            
        Returns:
            Updated user object
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        user = await self.get_user_by_discord_id(discord_id)
        if not user:
            raise UserNotFoundError(str(discord_id))
        
        user.add_competition_participation(won)
        await self.update_user(user)
        
        self.logger.info(
            f"Added competition participation for user {discord_id} (won: {won})",
            extra={"discord_id": discord_id, "won": won}
        )
        
        return user
    
    async def add_user_achievement(self, discord_id: int, achievement: str) -> bool:
        """
        Add an achievement to a user.
        
        Args:
            discord_id: Discord user ID
            achievement: Achievement identifier
            
        Returns:
            True if achievement was added, False if already exists
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        user = await self.get_user_by_discord_id(discord_id)
        if not user:
            raise UserNotFoundError(str(discord_id))
        
        added = user.add_achievement(achievement)
        if added:
            await self.update_user(user)
            self.logger.info(
                f"Added achievement '{achievement}' for user {discord_id}",
                extra={"discord_id": discord_id, "achievement": achievement}
            )
        
        return added
    
    async def get_all_users(self) -> List[User]:
        """
        Get all users.
        
        Returns:
            List of all user objects
        """
        data = await self.load_data()
        users = []
        
        for user_data in data["users"].values():
            try:
                users.append(User.from_dict(user_data))
            except Exception as e:
                self.logger.warning(f"Failed to load user data: {e}")
        
        return users
    
    async def get_users_by_achievement(self, achievement: str) -> List[User]:
        """
        Get all users who have a specific achievement.
        
        Args:
            achievement: Achievement identifier
            
        Returns:
            List of users with the achievement
        """
        users = await self.get_all_users()
        return [user for user in users if achievement in user.achievements]
    
    async def get_top_users_by_wins(self, limit: int = 10) -> List[User]:
        """
        Get top users by win count.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of users sorted by wins (descending)
        """
        users = await self.get_all_users()
        return sorted(users, key=lambda u: u.wins, reverse=True)[:limit]
    
    async def get_top_users_by_participation(self, limit: int = 10) -> List[User]:
        """
        Get top users by participation count.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of users sorted by total competitions (descending)
        """
        users = await self.get_all_users()
        return sorted(users, key=lambda u: u.total_competitions, reverse=True)[:limit]
    
    async def get_users_with_osrs_accounts(self) -> List[User]:
        """
        Get all users who have linked OSRS accounts.
        
        Returns:
            List of users with OSRS accounts linked
        """
        users = await self.get_all_users()
        return [user for user in users if user.is_osrs_linked()]
    
    async def search_users(self, query: str) -> List[User]:
        """
        Search users by username or display name.
        
        Args:
            query: Search query (case-insensitive)
            
        Returns:
            List of matching users
        """
        users = await self.get_all_users()
        query_lower = query.lower()
        
        matching_users = []
        for user in users:
            # Check OSRS username
            if (user.osrs_username and 
                query_lower in user.osrs_username.lower()):
                matching_users.append(user)
                continue
            
            # Check display name
            if (user.display_name and 
                query_lower in user.display_name.lower()):
                matching_users.append(user)
                continue
        
        return matching_users
    
    async def get_repository_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the user repository.
        
        Returns:
            Dictionary with various statistics
        """
        users = await self.get_all_users()
        
        if not users:
            return {
                "total_users": 0,
                "linked_accounts": 0,
                "total_competitions": 0,
                "total_wins": 0,
                "total_achievements": 0
            }
        
        linked_accounts = sum(1 for user in users if user.is_osrs_linked())
        total_competitions = sum(user.total_competitions for user in users)
        total_wins = sum(user.wins for user in users)
        total_achievements = sum(len(user.achievements) for user in users)
        
        # Calculate averages
        avg_competitions = total_competitions / len(users)
        avg_wins = total_wins / len(users)
        avg_win_rate = sum(user.get_win_rate() for user in users) / len(users)
        
        return {
            "total_users": len(users),
            "linked_accounts": linked_accounts,
            "link_rate": (linked_accounts / len(users)) * 100,
            "total_competitions": total_competitions,
            "total_wins": total_wins,
            "total_achievements": total_achievements,
            "avg_competitions_per_user": round(avg_competitions, 2),
            "avg_wins_per_user": round(avg_wins, 2),
            "avg_win_rate": round(avg_win_rate, 2),
            "most_active_user": max(users, key=lambda u: u.total_competitions).discord_id,
            "most_successful_user": max(users, key=lambda u: u.wins).discord_id
        }