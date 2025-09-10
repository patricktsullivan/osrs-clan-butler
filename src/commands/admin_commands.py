"""
Administrative commands for OSRS Discord Bot.

Provides commands for competition management, user administration,
and bot configuration. Requires administrator permissions.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from core.decorators import require_admin, handle_errors, defer_response, log_command_usage
from core.exceptions import CompetitionError, UserError
from utils.validators import InputValidator
from config.logging_config import get_logger


logger = get_logger(__name__)


class AdminCommands(commands.Cog):
    """
    Administrative commands cog.
    
    Provides competition management, user administration,
    and system maintenance commands for administrators.
    """
    
    def __init__(self, bot):
        """Initialize the admin commands cog."""
        self.bot = bot
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @app_commands.command(name="create_competition", description="Create a new competition")
    @app_commands.describe(
        competition_type="Type of competition to create",
        title="Competition title",
        description="Competition description",
        duration_hours="Duration in hours (1-168)",
        max_participants="Maximum number of participants (2-200)"
    )
    @app_commands.choices(competition_type=[
        app_commands.Choice(name="Skill Competition", value="skill_competition"),
        app_commands.Choice(name="Boss Competition", value="boss_competition"),
        app_commands.Choice(name="Trivia", value="trivia"),
        app_commands.Choice(name="Race", value="race"),
        app_commands.Choice(name="Speed Run", value="speedrun")
    ])
    @require_admin
    @handle_errors()
    @defer_response()
    @log_command_usage
    async def create_competition(
        self,
        interaction: discord.Interaction,
        competition_type: str,
        title: str,
        description: str,
        duration_hours: int = 24,
        max_participants: int = 50
    ):
        """Create a new competition."""
        # Validate inputs
        title = InputValidator.validate_competition_title(title)
        description = InputValidator.validate_competition_description(description)
        duration_hours = InputValidator.validate_duration_hours(duration_hours)
        max_participants = InputValidator.validate_participant_count(max_participants)
        
        try:
            # Get appropriate competition manager
            if competition_type not in self.bot.competition_managers:
                await interaction.followup.send(
                    f"❌ Competition type '{competition_type}' is not available.",
                    ephemeral=True
                )
                return
            
            manager = self.bot.competition_managers[competition_type]
            
            # Create competition
            competition_data = await manager.create_competition(
                title=title,
                description=description,
                duration_hours=duration_hours,
                max_participants=max_participants,
                created_by=interaction.user.id
            )
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Competition Created",
                description=f"Successfully created {competition_type.replace('_', ' ').title()}",
                color=discord.Color.green()
            )
            embed.add_field(name="Title", value=title, inline=False)
            embed.add_field(name="ID", value=competition_data["id"], inline=True)
            embed.add_field(name="Duration", value=f"{duration_hours} hours", inline=True)
            embed.add_field(name="Max Participants", value=str(max_participants), inline=True)
            embed.add_field(name="Status", value="Pending", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to create competition: {e}")
            await interaction.followup.send(
                f"❌ Failed to create competition: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="cancel_competition", description="Cancel a competition")
    @app_commands.describe(
        competition_id="ID of the competition to cancel",
        reason="Reason for cancellation"
    )
    @require_admin
    @handle_errors()
    @defer_response()
    @log_command_usage
    async def cancel_competition(
        self,
        interaction: discord.Interaction,
        competition_id: str,
        reason: str = "Cancelled by administrator"
    ):
        """Cancel a competition."""
        competition_id = InputValidator.sanitize_input(competition_id, max_length=100)
        reason = InputValidator.sanitize_input(reason, max_length=200)
        
        try:
            # Find the appropriate manager
            competition = await self.bot.competition_repo.get_by_id(competition_id, raise_if_not_found=False)
            if not competition:
                await interaction.followup.send(
                    f"❌ Competition '{competition_id}' not found.",
                    ephemeral=True
                )
                return
            
            manager = self.bot.competition_managers.get(competition.type.value)
            if not manager:
                await interaction.followup.send(
                    f"❌ No manager available for competition type '{competition.type.value}'.",
                    ephemeral=True
                )
                return
            
            # Cancel the competition
            await manager.cancel_competition(competition_id, reason)
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Competition Cancelled",
                description=f"Competition '{competition.title}' has been cancelled.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Competition ID", value=competition_id, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Participants", value=str(len(competition.participants)), inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to cancel competition: {e}")
            await interaction.followup.send(
                f"❌ Failed to cancel competition: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="bot_stats", description="View bot statistics and health")
    @require_admin
    @handle_errors()
    @defer_response()
    @log_command_usage
    async def bot_stats(self, interaction: discord.Interaction):
        """Display comprehensive bot statistics."""
        try:
            # Get bot statistics
            stats = await self.bot.get_bot_stats()
            
            # Create stats embed
            embed = discord.Embed(
                title="📊 Bot Statistics",
                color=discord.Color.blue()
            )
            
            # Basic stats
            embed.add_field(
                name="🤖 Bot Info",
                value=f"Uptime: {stats['uptime_formatted']}\n"
                      f"Latency: {stats['latency_ms']}ms\n"
                      f"Guilds: {stats['guild_count']}\n"
                      f"Users: {stats['user_count']}",
                inline=True
            )
            
            # Command stats
            embed.add_field(
                name="📈 Usage",
                value=f"Commands: {stats['command_count']}\n"
                      f"Errors: {stats['error_count']}\n"
                      f"Error Rate: {(stats['error_count'] / max(stats['command_count'], 1) * 100):.1f}%",
                inline=True
            )
            
            # Repository stats
            if 'user_repository' in stats:
                user_repo_stats = stats['user_repository']
                embed.add_field(
                    name="👥 Users",
                    value=f"File Size: {user_repo_stats.get('file_size_bytes', 0)} bytes\n"
                          f"Backups: {user_repo_stats.get('backup_count', 0)}",
                    inline=True
                )
            
            # Most used commands
            if stats['most_used_commands']:
                top_commands = "\n".join([
                    f"{cmd}: {count}" for cmd, count in stats['most_used_commands'][:3]
                ])
                embed.add_field(
                    name="🔥 Top Commands",
                    value=top_commands or "None",
                    inline=True
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to get bot stats: {e}")
            await interaction.followup.send(
                f"❌ Failed to retrieve bot statistics: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="force_sync", description="Force sync slash commands")
    @require_admin
    @handle_errors()
    @defer_response()
    @log_command_usage
    async def force_sync(self, interaction: discord.Interaction):
        """Force synchronization of slash commands."""
        try:
            guild = discord.Object(id=self.bot.guild_id)
            synced = await self.bot.tree.sync(guild=guild)
            
            embed = discord.Embed(
                title="✅ Commands Synced",
                description=f"Successfully synced {len(synced)} commands to the guild.",
                color=discord.Color.green()
            )
            
            if synced:
                command_list = "\n".join([f"• {cmd.name}" for cmd in synced[:10]])
                if len(synced) > 10:
                    command_list += f"\n... and {len(synced) - 10} more"
                embed.add_field(name="Commands", value=command_list, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")
            await interaction.followup.send(
                f"❌ Failed to sync commands: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="user_info", description="Get detailed information about a user")
    @app_commands.describe(user="User to get information about")
    @require_admin
    @handle_errors()
    @defer_response()
    @log_command_usage
    async def user_info(self, interaction: discord.Interaction, user: discord.User):
        """Get detailed information about a user."""
        try:
            # Get user from repository
            user_data = await self.bot.user_repo.get_user_by_discord_id(user.id)
            
            embed = discord.Embed(
                title=f"👤 User Information",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Discord User", value=f"{user.mention}\n{user.id}", inline=True)
            
            if user_data:
                embed.add_field(
                    name="OSRS Account",
                    value=user_data.osrs_username if user_data.osrs_username else "Not linked",
                    inline=True
                )
                embed.add_field(
                    name="Competition Stats",
                    value=f"Participated: {user_data.total_competitions}\n"
                          f"Won: {user_data.wins}\n"
                          f"Win Rate: {user_data.get_win_rate():.1f}%",
                    inline=True
                )
                embed.add_field(
                    name="Achievements",
                    value=f"{len(user_data.achievements)} earned",
                    inline=True
                )
                embed.add_field(
                    name="Joined",
                    value=f"<t:{int(user_data.join_date.timestamp())}:D>",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Status",
                    value="User not found in database",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to get user info: {e}")
            await interaction.followup.send(
                f"❌ Failed to get user information: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    """Setup function called by Discord.py to load the cog."""
    await bot.add_cog(AdminCommands(bot))