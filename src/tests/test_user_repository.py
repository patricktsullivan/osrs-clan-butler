"""
Example test file for UserRepository.

Demonstrates testing patterns for the OSRS Discord Bot
using pytest and asyncio.
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from data.repositories.user_repository import UserRepository
from data.models.user import User, UserPreferences, PrivacyLevel
from core.exceptions import UserNotFoundError, UserError, ValidationError


class TestUserRepository:
    """Test suite for UserRepository functionality."""
    
    @pytest.fixture
    async def temp_repo(self):
        """Create a temporary user repository for testing."""
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.close()
        
        # Initialize repository
        repo = UserRepository(temp_file.name)
        
        # Wait for initialization to complete
        await repo._initialize_file()
        
        yield repo
        
        # Cleanup
        try:
            os.unlink(temp_file.name)
        except FileNotFoundError:
            pass
    
    @pytest.fixture
    def sample_user_data(self):
        """Provide sample user data for testing."""
        return {
            "discord_id": 123456789012345678,
            "osrs_username": "TestPlayer",
            "display_name": "Test User"
        }
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, temp_repo, sample_user_data):
        """Test successful user creation."""
        user = await temp_repo.create_user(**sample_user_data)
        
        assert user.discord_id == sample_user_data["discord_id"]
        assert user.osrs_username == sample_user_data["osrs_username"]
        assert user.display_name == sample_user_data["display_name"]
        assert user.total_competitions == 0
        assert user.wins == 0
        assert len(user.achievements) == 0
    
    @pytest.mark.asyncio
    async def test_create_duplicate_user_fails(self, temp_repo, sample_user_data):
        """Test that creating duplicate user fails."""
        # Create first user
        await temp_repo.create_user(**sample_user_data)
        
        # Attempt to create duplicate should fail
        with pytest.raises(UserError):
            await temp_repo.create_user(**sample_user_data)
    
    @pytest.mark.asyncio
    async def test_get_user_by_discord_id(self, temp_repo, sample_user_data):
        """Test retrieving user by Discord ID."""
        # Create user
        created_user = await temp_repo.create_user(**sample_user_data)
        
        # Retrieve user
        retrieved_user = await temp_repo.get_user_by_discord_id(sample_user_data["discord_id"])
        
        assert retrieved_user is not None
        assert retrieved_user.discord_id == created_user.discord_id
        assert retrieved_user.osrs_username == created_user.osrs_username
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_none(self, temp_repo):
        """Test that getting non-existent user returns None."""
        user = await temp_repo.get_user_by_discord_id(999999999999999999)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_link_osrs_account(self, temp_repo, sample_user_data):
        """Test linking OSRS account to existing user."""
        # Create user without OSRS account
        discord_id = sample_user_data["discord_id"]
        await temp_repo.create_user(discord_id=discord_id)
        
        # Link OSRS account
        osrs_username = "NewPlayer"
        updated_user = await temp_repo.link_osrs_account(discord_id, osrs_username)
        
        assert updated_user.osrs_username == osrs_username
        assert updated_user.is_osrs_linked()
    
    @pytest.mark.asyncio
    async def test_link_duplicate_osrs_username_fails(self, temp_repo, sample_user_data):
        """Test that linking duplicate OSRS username fails."""
        # Create first user with OSRS account
        user1_discord_id = sample_user_data["discord_id"]
        osrs_username = sample_user_data["osrs_username"]
        await temp_repo.create_user(discord_id=user1_discord_id, osrs_username=osrs_username)
        
        # Create second user
        user2_discord_id = 987654321098765432
        await temp_repo.create_user(discord_id=user2_discord_id)
        
        # Attempt to link same OSRS username should fail
        with pytest.raises(UserError):
            await temp_repo.link_osrs_account(user2_discord_id, osrs_username)
    
    @pytest.mark.asyncio
    async def test_unlink_osrs_account(self, temp_repo, sample_user_data):
        """Test unlinking OSRS account."""
        # Create user with OSRS account
        user = await temp_repo.create_user(**sample_user_data)
        assert user.is_osrs_linked()
        
        # Unlink account
        updated_user = await temp_repo.unlink_osrs_account(user.discord_id)
        
        assert not updated_user.is_osrs_linked()
        assert updated_user.osrs_username is None
    
    @pytest.mark.asyncio
    async def test_add_competition_participation(self, temp_repo, sample_user_data):
        """Test adding competition participation."""
        # Create user
        user = await temp_repo.create_user(**sample_user_data)
        assert user.total_competitions == 0
        assert user.wins == 0
        
        # Add participation (loss)
        updated_user = await temp_repo.add_competition_participation(user.discord_id, won=False)
        assert updated_user.total_competitions == 1
        assert updated_user.wins == 0
        
        # Add participation (win)
        updated_user = await temp_repo.add_competition_participation(user.discord_id, won=True)
        assert updated_user.total_competitions == 2
        assert updated_user.wins == 1
        assert updated_user.get_win_rate() == 50.0
    
    @pytest.mark.asyncio
    async def test_add_achievement(self, temp_repo, sample_user_data):
        """Test adding achievements to user."""
        # Create user
        user = await temp_repo.create_user(**sample_user_data)
        assert len(user.achievements) == 0
        
        # Add achievement
        achievement = "first_win"
        added = await temp_repo.add_user_achievement(user.discord_id, achievement)
        
        assert added is True
        
        # Verify achievement was added
        updated_user = await temp_repo.get_user_by_discord_id(user.discord_id)
        assert achievement in updated_user.achievements
        
        # Try to add same achievement again
        added_again = await temp_repo.add_user_achievement(user.discord_id, achievement)
        assert added_again is False
    
    @pytest.mark.asyncio
    async def test_get_user_by_osrs_username(self, temp_repo, sample_user_data):
        """Test retrieving user by OSRS username."""
        # Create user
        await temp_repo.create_user(**sample_user_data)
        
        # Retrieve by OSRS username
        user = await temp_repo.get_user_by_osrs_username(sample_user_data["osrs_username"])
        
        assert user is not None
        assert user.osrs_username == sample_user_data["osrs_username"]
        
        # Test case insensitive search
        user_lower = await temp_repo.get_user_by_osrs_username(sample_user_data["osrs_username"].lower())
        assert user_lower is not None
    
    @pytest.mark.asyncio
    async def test_delete_user(self, temp_repo, sample_user_data):
        """Test deleting a user."""
        # Create user
        user = await temp_repo.create_user(**sample_user_data)
        
        # Verify user exists
        retrieved_user = await temp_repo.get_user_by_discord_id(user.discord_id)
        assert retrieved_user is not None
        
        # Delete user
        deleted = await temp_repo.delete_user(user.discord_id)
        assert deleted is True
        
        # Verify user no longer exists
        retrieved_user = await temp_repo.get_user_by_discord_id(user.discord_id)
        assert retrieved_user is None
        
        # Try to delete non-existent user
        deleted_again = await temp_repo.delete_user(user.discord_id)
        assert deleted_again is False
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self, temp_repo, sample_user_data):
        """Test updating user preferences."""
        # Create user
        user = await temp_repo.create_user(**sample_user_data)
        
        # Create new preferences
        new_preferences = UserPreferences(
            notifications=False,
            privacy_level=PrivacyLevel.PRIVATE,
            show_real_name=True
        )
        
        # Update preferences
        updated_user = await temp_repo.update_user_preferences(user.discord_id, new_preferences)
        
        assert updated_user.preferences.notifications is False
        assert updated_user.preferences.privacy_level == PrivacyLevel.PRIVATE
        assert updated_user.preferences.show_real_name is True
    
    @pytest.mark.asyncio
    async def test_get_repository_statistics(self, temp_repo):
        """Test getting repository statistics."""
        # Initially should have no users
        stats = await temp_repo.get_repository_statistics()
        assert stats["total_users"] == 0
        
        # Create some test users
        for i in range(3):
            await temp_repo.create_user(
                discord_id=123456789012345678 + i,
                osrs_username=f"Player{i}"
            )
            # Add some competition data
            await temp_repo.add_competition_participation(123456789012345678 + i, won=(i == 0))
        
        # Check updated statistics
        stats = await temp_repo.get_repository_statistics()
        assert stats["total_users"] == 3
        assert stats["linked_accounts"] == 3
        assert stats["total_competitions"] == 3
        assert stats["total_wins"] == 1
    
    @pytest.mark.asyncio
    async def test_data_persistence(self, temp_repo, sample_user_data):
        """Test that data persists across repository instances."""
        # Create user
        await temp_repo.create_user(**sample_user_data)
        
        # Create new repository instance with same file
        file_path = temp_repo.file_path
        new_repo = UserRepository(str(file_path))
        await new_repo._initialize_file()
        
        # Verify user still exists
        user = await new_repo.get_user_by_discord_id(sample_user_data["discord_id"])
        assert user is not None
        assert user.osrs_username == sample_user_data["osrs_username"]


# Integration test example
@pytest.mark.asyncio
async def test_user_workflow_integration():
    """Integration test for common user workflow."""
    # Create temporary repository
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.close()
    
    try:
        repo = UserRepository(temp_file.name)
        await repo._initialize_file()
        
        discord_id = 123456789012345678
        osrs_username = "IntegrationTest"
        
        # 1. Create user without OSRS account
        user = await repo.create_user(discord_id=discord_id)
        assert not user.is_osrs_linked()
        
        # 2. Link OSRS account
        user = await repo.link_osrs_account(discord_id, osrs_username)
        assert user.is_osrs_linked()
        
        # 3. Participate in competitions
        for i in range(5):
            won = i < 2  # Win first 2 competitions
            await repo.add_competition_participation(discord_id, won=won)
        
        # 4. Add achievements
        await repo.add_user_achievement(discord_id, "first_win")
        await repo.add_user_achievement(discord_id, "participation_5")
        
        # 5. Verify final state
        final_user = await repo.get_user_by_discord_id(discord_id)
        assert final_user.total_competitions == 5
        assert final_user.wins == 2
        assert final_user.get_win_rate() == 40.0
        assert len(final_user.achievements) == 2
        
    finally:
        try:
            os.unlink(temp_file.name)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    # Run tests if file is executed directly
    pytest.main([__file__, "-v"])