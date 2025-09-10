"""
Main Discord bot class for OSRS Community Bot.

Handles Discord events, command registration, and provides the main
interface for all bot functionality.
"""

import discord
from discord.ext import commands, tasks
from typing import Dict, Any
from datetime import datetime, timezone

from config.settings import Settings
from config.logging_config import LoggerMixin
from core.exceptions import OSRSBotException, handle_exception


class OSRSBot(commands.Bot, LoggerMixin):
    """
    Main Discord bot class for OSRS community management.
    
    Provides event handling, command management, and integrates
    all bot components for a cohesive user experience.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the OSRS Discord bot.
        
        Args:
            settings: Configuration settings for the bot
        """
        # Configure Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        # Initialize bot with basic configuration
        super().__init__(
            command_prefix=settings.bot.command_prefix,
            intents=intents,
            help_command=None,  # We'll implement a custom help command
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        self.settings = settings
        self.start_time = datetime.now(timezone.utc)
        self.guild_id = settings.GUILD_ID
        
        # Component repositories (will be initialized in setup_hook)
        self.user_repo = None
        self.competition_repo = None
        self.leaderboard_repo = None
        
        # Competition managers (will be initialized in setup_hook)
        self.competition_managers: Dict[str, Any] = {}
        
        # Bot statistics
        self.command_stats: Dict[str, int] = {}
        self.error_count = 0
        
        # Background tasks
        self.background_tasks_started = False
    
    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is starting up.
        
        Initializes repositories, competition managers, and loads commands.
        """
        self.logger.info("Starting bot setup...")
        
        try:
            # Initialize repositories
            await self._initialize_repositories()
            
            # Initialize competition managers
            await self._initialize_competition_managers()
            
            # Load command extensions
            await self._load_extensions()
            
            # Sync slash commands if in development
            if self.settings.DEBUG:
                await self._sync_commands()
            
            # Start background tasks
            if not self.background_tasks_started:
                self._start_background_tasks()
                self.background_tasks_started = True
            
            self.logger.info("Bot setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup bot: {e}", exc_info=True)
            raise
    
    async def _initialize_repositories(self) -> None:
        """Initialize data repositories for the bot."""
        # Import here to avoid circular imports
        from data.repositories.user_repository import UserRepository
        from data.repositories.competition_repository import CompetitionRepository
        from data.repositories.leaderboard_repository import LeaderboardRepository
        
        self.user_repo = UserRepository(
            self.settings.database.users_file
        )
        
        self.competition_repo = CompetitionRepository(
            self.settings.database.competitions_file
        )
        
        self.leaderboard_repo = LeaderboardRepository(
            self.settings.database.leaderboards_file
        )
        
        self.logger.info("Repositories initialized")
    
    async def _initialize_competition_managers(self) -> None:
        """Initialize competition managers for different event types."""
        # Import here to avoid circular imports
        from events.factory import EventFactory
        
        # Initialize managers for each competition type
        manager_types = EventFactory.get_supported_types()
        
        for manager_type in manager_types:
            try:
                manager = EventFactory.create_manager(
                    manager_type,
                    self.competition_repo,
                    self.user_repo,
                    self.settings
                )
                self.competition_managers[manager_type] = manager
                self.logger.debug(f"Initialized {manager_type} manager")
            except Exception as e:
                self.logger.error(f"Failed to initialize {manager_type} manager: {e}")
        
        self.logger.info(f"Initialized {len(self.competition_managers)} competition managers")
    
    async def _load_extensions(self) -> None:
        """Load command extensions."""
        extensions = [
            'commands.admin_commands',
            'commands.participant_commands',
            'commands.view_commands'
        ]
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                self.logger.debug(f"Loaded extension: {extension}")
            except Exception as e:
                self.logger.error(f"Failed to load extension {extension}: {e}")
        
        self.logger.info(f"Loaded {len(extensions)} command extensions")
    
    async def _sync_commands(self) -> None:
        """Sync slash commands with Discord (development only)."""
        try:
            guild = discord.Object(id=self.guild_id)
            synced = await self.tree.sync(guild=guild)
            self.logger.info(f"Synced {len(synced)} commands to guild {self.guild_id}")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")
    
    def _start_background_tasks(self) -> None:
        """Start background tasks for maintenance and monitoring."""
        self.competition_monitor.start()
        self.cleanup_task.start()
        self.stats_update.start()
        
        self.logger.info("Background tasks started")
    
    async def on_ready(self) -> None:
        """Event handler for when the bot is ready."""
        self.logger.info(
            f"Bot is ready! Logged in as {self.user} (ID: {self.user.id})",
            extra={
                "bot_id": self.user.id,
                "guild_count": len(self.guilds),
                "latency": round(self.latency * 1000, 2)
            }
        )
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="OSRS competitions"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)
    
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Event handler for when the bot joins a guild."""
        self.logger.info(
            f"Joined guild: {guild.name} (ID: {guild.id})",
            extra={"guild_id": guild.id, "member_count": guild.member_count}
        )
    
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Event handler for when the bot leaves a guild."""
        self.logger.info(
            f"Left guild: {guild.name} (ID: {guild.id})",
            extra={"guild_id": guild.id}
        )
    
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Handle command errors."""
        self.error_count += 1
        
        # Convert to OSRSBotException if needed
        if not isinstance(error, OSRSBotException):
            error = handle_exception(error)
        
        self.logger.error(
            f"Command error in {ctx.command}: {error}",
            extra={
                "user_id": ctx.author.id,
                "command": str(ctx.command),
                "guild_id": ctx.guild.id if ctx.guild else None,
                "error_data": error.to_dict() if hasattr(error, 'to_dict') else {}
            }
        )
        
        # Send error message to user
        try:
            await ctx.send(f"❌ {error.user_message if hasattr(error, 'user_message') else str(error)}")
        except Exception as send_error:
            self.logger.error(f"Failed to send error message: {send_error}")
    
    async def on_application_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle slash command errors."""
        self.error_count += 1
        
        # Convert to OSRSBotException if needed
        if not isinstance(error, OSRSBotException):
            error = handle_exception(error)
        
        self.logger.error(
            f"Slash command error: {error}",
            extra={
                "user_id": interaction.user.id,
                "command": interaction.command.name if interaction.command else "unknown",
                "guild_id": interaction.guild_id,
                "error_data": error.to_dict() if hasattr(error, 'to_dict') else {}
            }
        )
        
        # Send error message to user
        try:
            error_message = error.user_message if hasattr(error, 'user_message') else "An error occurred"
            
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ {error_message}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {error_message}", ephemeral=True)
        except Exception as send_error:
            self.logger.error(f"Failed to send error message: {send_error}")
    
    async def on_command(self, ctx: commands.Context) -> None:
        """Track command usage statistics."""
        command_name = str(ctx.command)
        self.command_stats[command_name] = self.command_stats.get(command_name, 0) + 1
        
        self.logger.info(
            f"Command executed: {command_name}",
            extra={
                "user_id": ctx.author.id,
                "command": command_name,
                "guild_id": ctx.guild.id if ctx.guild else None
            }
        )
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Get comprehensive bot statistics."""
        uptime = datetime.now(timezone.utc) - self.start_time
        uptime = datetime.now(timezone.utc) - self.start_time
        stats = {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": str(uptime).split('.')[0],  # Remove microseconds
            "guild_count": len(self.guilds),
            "user_count": len(self.users),
            "command_count": sum(self.command_stats.values()),
            "error_count": self.error_count,
            "latency_ms": round(self.latency * 1000, 2),
            "most_used_commands": sorted(
                self.command_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
        
        # Add repository statistics if available
        if self.user_repo:
            try:
                user_stats = await self.user_repo.get_stats()
                stats["user_repository"] = user_stats
            except Exception as e:
                self.logger.error(f"Failed to get user repo stats: {e}")
        
        if self.competition_repo:
            try:
                comp_stats = await self.competition_repo.get_stats()
                stats["competition_repository"] = comp_stats
            except Exception as e:
                self.logger.error(f"Failed to get competition repo stats: {e}")
        
        return stats
    
    @tasks.loop(minutes=5)
    async def competition_monitor(self) -> None:
        """Monitor competitions for status changes and automatic transitions."""
        try:
            for manager in self.competition_managers.values():
                active_competitions = await manager.get_active_competitions()
                
                for competition in active_competitions:
                    # Check if competition should start
                    start_time = datetime.fromisoformat(competition['start_time'].replace('Z', '+00:00'))
                    if (competition['status'] == 'pending' and 
                        datetime.now(timezone.utc).replace(tzinfo=start_time.tzinfo) >= start_time):
                        await manager.start_competition(competition['id'])
                    
                    # Check if competition should end
                    end_time = datetime.fromisoformat(competition['end_time'].replace('Z', '+00:00'))
                    if (competition['status'] == 'active' and 
                        datetime.now(timezone.utc).replace(tzinfo=end_time.tzinfo) >= end_time):
                        await manager.end_competition(competition['id'])
        except Exception as e:
            self.logger.error(f"Error in competition monitor: {e}", exc_info=True)
    
    @tasks.loop(hours=1)
    async def cleanup_task(self) -> None:
        """Perform periodic cleanup tasks."""
        try:
            # Clean up old backup files
            if self.user_repo:
                await self.user_repo._cleanup_old_backups()
            if self.competition_repo:
                await self.competition_repo._cleanup_old_backups()
            if self.leaderboard_repo:
                await self.leaderboard_repo._cleanup_old_backups()
            
            self.logger.debug("Cleanup tasks completed")
        
        except Exception as e:
            self.logger.error(f"Error in cleanup task: {e}", exc_info=True)
    
    @tasks.loop(minutes=15)
    async def stats_update(self) -> None:
        """Update bot statistics and log system health."""
        try:
            stats = await self.get_bot_stats()
            
            self.logger.info(
                "Bot health check",
                extra={
                    "uptime_seconds": stats["uptime_seconds"],
                    "guild_count": stats["guild_count"],
                    "command_count": stats["command_count"],
                    "error_count": stats["error_count"],
                    "latency_ms": stats["latency_ms"]
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error in stats update: {e}", exc_info=True)
    
    async def close(self) -> None:
        """Clean shutdown of the bot."""
        self.logger.info("Starting bot shutdown...")
        
        # Stop background tasks
        if self.background_tasks_started:
            self.competition_monitor.cancel()
            self.cleanup_task.cancel()
            self.stats_update.cancel()
        
        # Close repositories if they exist
        # (Add any cleanup needed for repositories)
        
        # Call parent close
        await super().close()
        
        self.logger.info("Bot shutdown completed")