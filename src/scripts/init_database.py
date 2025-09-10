#!/usr/bin/env python3
"""
Database initialization script for OSRS Discord Bot.

Creates initial database files with proper structure and sample data.
Run this script before starting the bot for the first time.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the parent directory to the path to import bot modules
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import Settings
from data.repositories.user_repository import UserRepository
from data.repositories.competition_repository import CompetitionRepository
from data.repositories.leaderboard_repository import LeaderboardRepository


async def create_directory_structure(settings: Settings) -> None:
    """Create necessary directory structure."""
    print("Creating directory structure...")
    
    directories = [
        Path(settings.database.users_file).parent,
        Path(settings.database.competitions_file).parent,
        Path(settings.database.leaderboards_file).parent,
        Path(settings.database.trivia_questions_file).parent,
        Path(settings.LOG_FILE).parent,
        "logs",
        "backups"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created {directory}")


async def initialize_repositories(settings: Settings) -> None:
    """Initialize all repositories with default structure."""
    print("\nInitializing repositories...")
    
    # Initialize user repository
    print("  Initializing user repository...")
    user_repo = UserRepository(settings.database.users_file)
    await user_repo._initialize_file()
    print("  ✓ User repository initialized")
    
    # Initialize competition repository
    print("  Initializing competition repository...")
    comp_repo = CompetitionRepository(settings.database.competitions_file)
    await comp_repo._initialize_file()
    print("  ✓ Competition repository initialized")
    
    # Initialize leaderboard repository
    print("  Initializing leaderboard repository...")
    lb_repo = LeaderboardRepository(settings.database.leaderboards_file)
    await lb_repo._initialize_file()
    print("  ✓ Leaderboard repository initialized")


async def create_trivia_questions(settings: Settings) -> None:
    """Create initial trivia questions database."""
    print("\nCreating trivia questions database...")
    
    trivia_data = {
        "categories": {
            "general": {
                "name": "General OSRS Knowledge",
                "description": "General questions about Old School RuneScape"
            },
            "skills": {
                "name": "Skills",
                "description": "Questions about OSRS skills and training"
            },
            "quests": {
                "name": "Quests",
                "description": "Questions about OSRS quests and lore"
            },
            "combat": {
                "name": "Combat",
                "description": "Questions about combat, bosses, and PvP"
            },
            "items": {
                "name": "Items",
                "description": "Questions about items, equipment, and rewards"
            }
        },
        "questions": {
            "q001": {
                "id": "q001",
                "category": "general",
                "difficulty": "easy",
                "question": "What is the maximum combat level in Old School RuneScape?",
                "options": ["99", "120", "126", "138"],
                "correct_answer": 2,
                "explanation": "The maximum combat level is 126, achieved with 99 in all combat stats."
            },
            "q002": {
                "id": "q002",
                "category": "skills",
                "difficulty": "medium",
                "question": "Which skill is required to access the Woodcutting Guild?",
                "options": ["60 Woodcutting", "75 Woodcutting", "80 Woodcutting", "85 Woodcutting"],
                "correct_answer": 1,
                "explanation": "75 Woodcutting is required to access the Woodcutting Guild."
            },
            "q003": {
                "id": "q003",
                "category": "quests",
                "difficulty": "hard",
                "question": "What is the final boss in the Dragon Slayer II quest?",
                "options": ["Vorkath", "Galvek", "Zulrah", "Elvarg"],
                "correct_answer": 1,
                "explanation": "Galvek is the final boss in Dragon Slayer II quest."
            },
            "q004": {
                "id": "q004",
                "category": "combat",
                "difficulty": "medium",
                "question": "Which prayer increases your Attack and Strength by 15%?",
                "options": ["Ultimate Strength", "Incredible Reflexes", "Piety", "Chivalry"],
                "correct_answer": 2,
                "explanation": "Piety increases Attack, Strength, and Defence by 15%."
            },
            "q005": {
                "id": "q005",
                "category": "items",
                "difficulty": "easy",
                "question": "What color is a rune scimitar?",
                "options": ["Blue", "Green", "Red", "Purple"],
                "correct_answer": 0,
                "explanation": "Rune equipment has a distinctive blue color."
            }
        },
        "metadata": {
            "version": "1.0",
            "last_updated": datetime.utcnow().isoformat() + 'Z',
            "total_questions": 5,
            "total_categories": 5
        }
    }
    
    trivia_file = Path(settings.database.trivia_questions_file)
    trivia_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(trivia_file, 'w', encoding='utf-8') as f:
        json.dump(trivia_data, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Created trivia database with {len(trivia_data['questions'])} questions")


async def create_sample_data(settings: Settings) -> None:
    """Create sample data for testing (optional)."""
    print("\nWould you like to create sample data for testing? (y/N): ", end="")
    response = input().strip().lower()
    
    if response not in ['y', 'yes']:
        print("Skipping sample data creation.")
        return
    
    print("Creating sample data...")
    
    # Initialize repositories
    user_repo = UserRepository(settings.database.users_file)
    comp_repo = CompetitionRepository(settings.database.competitions_file)
    lb_repo = LeaderboardRepository(settings.database.leaderboards_file)
    
    # Create sample users
    sample_users = [
        {"discord_id": 123456789012345678, "osrs_username": "SampleUser1", "display_name": "Sample User 1"},
        {"discord_id": 123456789012345679, "osrs_username": "SampleUser2", "display_name": "Sample User 2"},
        {"discord_id": 123456789012345680, "osrs_username": "SampleUser3", "display_name": "Sample User 3"},
    ]
    
    for user_data in sample_users:
        try:
            user = await user_repo.create_user(**user_data)
            # Add some competition participation
            await user_repo.add_competition_participation(user.discord_id, won=True)
            await user_repo.add_competition_participation(user.discord_id, won=False)
            print(f"  ✓ Created sample user: {user_data['osrs_username']}")
        except Exception as e:
            print(f"  ⚠ Failed to create user {user_data['osrs_username']}: {e}")
    
    # Update leaderboards
    collection = await lb_repo.get_leaderboard_collection()
    for user_data in sample_users:
        await lb_repo.update_all_time_leaderboards(
            user_data["discord_id"], 
            "skill_competition", 
            won=True,
            display_name=user_data["display_name"]
        )
    
    print("  ✓ Sample data created successfully")


async def verify_setup(settings: Settings) -> None:
    """Verify that all files were created correctly."""
    print("\nVerifying setup...")
    
    files_to_check = [
        settings.database.users_file,
        settings.database.competitions_file,
        settings.database.leaderboards_file,
        settings.database.trivia_questions_file
    ]
    
    all_good = True
    for file_path in files_to_check:
        if Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"  ✓ {file_path} - Valid JSON")
            except json.JSONDecodeError:
                print(f"  ❌ {file_path} - Invalid JSON")
                all_good = False
        else:
            print(f"  ❌ {file_path} - File not found")
            all_good = False
    
    if all_good:
        print("\n🎉 Database initialization completed successfully!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your settings")
        print("2. Set your Discord bot token and guild ID")
        print("3. Configure admin roles and user IDs")
        print("4. Run the bot with: python main.py")
    else:
        print("\n❌ Setup verification failed. Please check the errors above.")
        sys.exit(1)


async def check_existing_data(settings: Settings) -> bool:
    """Check if database files already exist."""
    files_to_check = [
        settings.database.users_file,
        settings.database.competitions_file,
        settings.database.leaderboards_file
    ]
    
    existing_files = [f for f in files_to_check if Path(f).exists()]
    
    if existing_files:
        print("⚠ Warning: The following database files already exist:")
        for file_path in existing_files:
            print(f"  - {file_path}")
        
        print("\nContinuing will overwrite existing data. Are you sure? (y/N): ", end="")
        response = input().strip().lower()
        
        if response not in ['y', 'yes']:
            print("Initialization cancelled.")
            return False
    
    return True


def print_banner():
    """Print initialization banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║              OSRS Discord Bot - Database Setup              ║
║                                                              ║
║  This script will initialize the database files needed      ║
║  for the OSRS Discord Bot to function properly.             ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    """Main initialization function."""
    print_banner()
    
    try:
        # Load settings
        print("Loading configuration...")
        settings = Settings()
        print("✓ Configuration loaded")
        
        # Check for existing data
        if not await check_existing_data(settings):
            return
        
        # Create directory structure
        await create_directory_structure(settings)
        
        # Initialize repositories
        await initialize_repositories(settings)
        
        # Create trivia questions
        await create_trivia_questions(settings)
        
        # Optional sample data
        await create_sample_data(settings)
        
        # Verify setup
        await verify_setup(settings)
        
    except KeyboardInterrupt:
        print("\n\nInitialization cancelled by user.")
    except Exception as e:
        print(f"\n❌ An error occurred during initialization: {e}")
        print("Please check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    # Run the initialization
    asyncio.run(main())