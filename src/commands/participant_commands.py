"""
Participant commands for OSRS Discord Bot.

Provides commands for user registration, competition participation,
and account management for regular users.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from core.decorators import handle_errors, defer_response, log_command_usage, rate_limit
from core.exceptions import UserError, CompetitionError
from utils.validators import InputValidator
from config.logging_config import get_logger


logger = get_logger(__name__)


class ParticipantCommands(commands.Cog):
    """
    Participant commands cog.
    
    Provides commands for user account management, competition
    participation, and profile viewing for regular users.
    """
    
    def __init__(self, bot):
        """Initialize the participant commands cog."""
        self.bot = bot
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @app_commands.command(name="link_account", description="Link your OSRS account to Discord")
    @app_commands.describe(osrs_username="Your OSRS username")
    @handle_errors()
    @defer_response()
    @rate_limit(calls=3, period=300)  # 3 calls per 5 minutes
    @log_command_usage
    async def link_account(self, interaction: discord.Interaction, osrs_username: str):
        """Link OSRS account to Discord profile."""
        try:
            # Validate OSRS username
            osrs_username = InputValidator.validate_osrs_username(osrs_username)
            
            # Check if user already exists
            existing_user = await self.bot.user_repo.get_user_by_discord_id(interaction.user.id)
            
            if existing_user:
                # Update existing user with OSRS account
                await self.bot.user_repo.link_osrs_account(
                    interaction.user.id, 
                    osrs_username
                )
                action = "updated"
            else:
                # Create new user with OSRS account
                await self.bot.user_repo.create_user(
                    discord_id=interaction.user.id,
                    osrs_username=osrs_username,
                    display_name=interaction.user.display_name
                )
                action = "linked"
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Account Linked",
                description=f"Successfully {action} your OSRS account link!",
                color=discord.Color.green()
            )
            embed.add_field(name="Discord", value=interaction.user.mention, inline=True)
            embed.add_field(name="OSRS Username", value=osrs_username, inline=True)
            embed.add_field(
                name="Next Steps",
                value="You can now participate in competitions and view your stats!",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except UserError as e:
            await interaction.followup.send(f"❌ {e.user_message}", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Failed to link account: {e}")
            await interaction.followup.send(
                "❌ Failed to link account. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="unlink_account", description="Unlink your OSRS account")
    @handle_errors()
    @defer_response()
    @rate_limit(calls=2, period=300)  # 2 calls per 5 minutes
    @log_command_usage
    async def unlink_account(self, interaction: discord.Interaction):
        """Unlink OSRS account from Discord profile."""
        try:
            # Check if user exists
            user = await self.bot.user_repo.get_user_by_discord_id(interaction.user.id)
            if not user:
                await interaction.followup.send(
                    "❌ You don't have a linked account to unlink.",
                    ephemeral=True
                )
                return
            
            if not user.is_osrs_linked():
                await interaction.followup.send(
                    "❌ You don't have an OSRS account linked.",
                    ephemeral=True
                )
                return
            
            old_username = user.osrs_username
            
            # Unlink the account
            await self.bot.user_repo.unlink_osrs_account(interaction.user.id)
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Account Unlinked",
                description="Successfully unlinked your OSRS account.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Previous OSRS Username", value=old_username, inline=True)
            embed.add_field(
                name="Note",
                value="Your competition history and achievements are preserved.",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to unlink account: {e}")
            await interaction.followup.send(
                "❌ Failed to unlink account. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="join_competition", description="Join an active competition")
    @app_commands.describe(competition_id="ID of the competition to join")
    @handle_errors()
    @defer_response()
    @rate_limit(calls=5, period=60)  # 5 calls per minute
    @log_command_usage
    async def join_competition(self, interaction: discord.Interaction, competition_id: str):
        """Join an active competition."""
        try:
            competition_id = InputValidator.sanitize_input(competition_id, max_length=100)
            
            # Check if user has linked account
            user = await self.bot.user_repo.get_user_by_discord_id(interaction.user.id)
            if not user:
                await interaction.followup.send(
                    "❌ You need to link your OSRS account first. Use `/link_account`.",
                    ephemeral=True
                )
                return
            
            # Get competition
            competition = await self.bot.competition_repo.get_by_id(competition_id, raise_if_not_found=False)
            if not competition:
                await interaction.followup.send(
                    f"❌ Competition '{competition_id}' not found.",
                    ephemeral=True
                )
                return
            
            # Check if competition allows registration
            if not competition.can_register():
                status_msg = {
                    "completed": "already completed",
                    "cancelled": "been cancelled",
                    "paused": "currently paused"
                }.get(competition.status.value, f"in {competition.status.value} status")
                
                await interaction.followup.send(
                    f"❌ Cannot join competition - it has {status_msg}.",
                    ephemeral=True
                )
                return
            
            # Check if already registered
            if competition.is_participant(interaction.user.id):
                await interaction.followup.send(
                    "❌ You are already registered for this competition.",
                    ephemeral=True
                )
                return
            
            # Get appropriate manager and register participant
            manager = self.bot.competition_managers.get(competition.type.value)
            if not manager:
                await interaction.followup.send(
                    f"❌ Competition type '{competition.type.value}' is not available.",
                    ephemeral=True
                )
                return
            
            # Register participant
            registration_data = await manager.register_participant(
                interaction.user.id,
                competition_id
            )
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Registered for Competition",
                description=f"Successfully joined '{competition.title}'!",
                color=discord.Color.green()
            )
            embed.add_field(name="Competition ID", value=competition_id, inline=True)
            embed.add_field(name="Type", value=competition.type.value.replace('_', ' ').title(), inline=True)
            embed.add_field(name="Participants", value=f"{len(competition.participants) + 1}/{competition.max_participants}", inline=True)
            
            # Add competition-specific information
            if competition.start_time:
                embed.add_field(
                    name="Starts",
                    value=f"<t:{int(competition.start_time.timestamp())}:F>",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except CompetitionError as e:
            await interaction.followup.send(f"❌ {e.user_message}", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Failed to join competition: {e}")
            await interaction.followup.send(
                "❌ Failed to join competition. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="leave_competition", description="Leave a competition you've joined")
    @app_commands.describe(competition_id="ID of the competition to leave")
    @handle_errors()
    @defer_response()
    @rate_limit(calls=3, period=60)  # 3 calls per minute
    @log_command_usage
    async def leave_competition(self, interaction: discord.Interaction, competition_id: str):
        """Leave a competition."""
        try:
            competition_id = InputValidator.sanitize_input(competition_id, max_length=100)
            
            # Get competition
            competition = await self.bot.competition_repo.get_by_id(competition_id, raise_if_not_found=False)
            if not competition:
                await interaction.followup.send(
                    f"❌ Competition '{competition_id}' not found.",
                    ephemeral=True
                )
                return
            
            # Check if user is registered
            if not competition.is_participant(interaction.user.id):
                await interaction.followup.send(
                    "❌ You are not registered for this competition.",
                    ephemeral=True
                )
                return
            
            # Check if competition has started
            if competition.status.value == "active":
                await interaction.followup.send(
                    "❌ Cannot leave an active competition. Contact an administrator if needed.",
                    ephemeral=True
                )
                return
            
            # Remove participant
            await self.bot.competition_repo.remove_participant(competition_id, interaction.user.id)
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Left Competition",
                description=f"Successfully left '{competition.title}'.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Competition ID", value=competition_id, inline=True)
            embed.add_field(name="Remaining Participants", value=str(len(competition.participants) - 1), inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to leave competition: {e}")
            await interaction.followup.send(
                "❌ Failed to leave competition. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="my_profile", description="View your profile and statistics")
    @handle_errors()
    @defer_response()
    @rate_limit(calls=5, period=60)  # 5 calls per minute
    @log_command_usage
    async def my_profile(self, interaction: discord.Interaction):
        """Display user's profile and statistics."""
        try:
            # Get user data
            user = await self.bot.user_repo.get_user_by_discord_id(interaction.user.id)
            if not user:
                embed = discord.Embed(
                    title="👤 Your Profile",
                    description="You haven't linked your OSRS account yet!",
                    color=discord.Color.yellow()
                )
                embed.add_field(
                    name="Get Started",
                    value="Use `/link_account <osrs_username>` to get started.",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create profile embed
            embed = discord.Embed(
                title="👤 Your Profile",
                color=discord.Color.blue()
            )
            
            # Basic info
            embed.add_field(
                name="Discord",
                value=f"{interaction.user.mention}\n{interaction.user.id}",
                inline=True
            )
            embed.add_field(
                name="OSRS Account",
                value=user.osrs_username if user.osrs_username else "Not linked",
                inline=True
            )
            embed.add_field(
                name="Member Since",
                value=f"<t:{int(user.join_date.timestamp())}:D>",
                inline=True
            )
            
            # Competition stats
            embed.add_field(
                name="📊 Competition Stats",
                value=f"Participated: {user.total_competitions}\n"
                      f"Won: {user.wins}\n"
                      f"Win Rate: {user.get_win_rate():.1f}%",
                inline=True
            )
            
            # Achievements
            embed.add_field(
                name="🏆 Achievements",
                value=f"{len(user.achievements)} earned",
                inline=True
            )
            
            # Recent activity
            embed.add_field(
                name="🕒 Last Active",
                value=f"<t:{int(user.last_activity.timestamp())}:R>",
                inline=True
            )
            
            # Get leaderboard positions (if available)
            try:
                positions = await self.bot.leaderboard_repo.get_user_leaderboard_positions(interaction.user.id)
                if positions:
                    rank_info = []
                    for lb_name, position in positions.items():
                        if 'all_time_wins' in lb_name:
                            rank_info.append(f"Wins: #{position['rank']}")
                        elif 'participation' in lb_name and 'monthly' not in lb_name:
                            rank_info.append(f"Participation: #{position['rank']}")
                    
                    if rank_info:
                        embed.add_field(
                            name="📈 Rankings",
                            value="\n".join(rank_info[:3]),
                            inline=True
                        )
            except Exception as e:
                self.logger.warning(f"Failed to get leaderboard positions: {e}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to get profile: {e}")
            await interaction.followup.send(
                "❌ Failed to retrieve profile. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="my_competitions", description="View your competition history")
    @handle_errors()
    @defer_response()
    @rate_limit(calls=3, period=60)  # 3 calls per minute
    @log_command_usage
    async def my_competitions(self, interaction: discord.Interaction):
        """Display user's competition history."""
        try:
            # Get user competitions
            competitions = await self.bot.competition_repo.get_user_competitions(interaction.user.id)
            
            if not competitions:
                embed = discord.Embed(
                    title="📋 Your Competitions",
                    description="You haven't participated in any competitions yet!",
                    color=discord.Color.yellow()
                )
                embed.add_field(
                    name="Get Started",
                    value="Look for active competitions with `/competitions` and join with `/join_competition`.",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Sort competitions by creation date (most recent first)
            competitions.sort(key=lambda c: c.created_at, reverse=True)
            
            # Create embed
            embed = discord.Embed(
                title="📋 Your Competition History",
                description=f"Showing {min(len(competitions), 10)} most recent competitions",
                color=discord.Color.blue()
            )
            
            # Add competition entries
            for i, competition in enumerate(competitions[:10]):
                # Determine status emoji
                status_emojis = {
                    "pending": "⏳",
                    "active": "🟢",
                    "completed": "✅",
                    "cancelled": "❌",
                    "paused": "⏸️"
                }
                status_emoji = status_emojis.get(competition.status.value, "❓")
                
                # Check if user won
                won_indicator = "🏆" if interaction.user.id in competition.winners else ""
                
                # Format entry
                competition_info = (
                    f"{status_emoji} **{competition.title}** {won_indicator}\n"
                    f"Type: {competition.type.value.replace('_', ' ').title()}\n"
                    f"Status: {competition.status.value.title()}\n"
                    f"Participants: {len(competition.participants)}"
                )
                
                embed.add_field(
                    name=f"#{i+1} - {competition.id[:20]}...",
                    value=competition_info,
                    inline=True
                )
                
                # Add separator every 3 competitions
                if (i + 1) % 3 == 0 and i < len(competitions) - 1:
                    embed.add_field(name="\u200b", value="\u200b", inline=False)
            
            if len(competitions) > 10:
                embed.set_footer(text=f"... and {len(competitions) - 10} more competitions")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to get competitions: {e}")
            await interaction.followup.send(
                "❌ Failed to retrieve competition history. Please try again later.",
                ephemeral=True
            )


async def setup(bot):
    """Setup function called by Discord.py to load the cog."""
    await bot.add_cog(ParticipantCommands(bot))