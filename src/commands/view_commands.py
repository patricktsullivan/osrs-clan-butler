"""
View commands for OSRS Discord Bot.

Provides commands for viewing leaderboards, competition information,
and public statistics accessible to all users.
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from datetime import datetime

from core.decorators import handle_errors, defer_response, log_command_usage, rate_limit
from utils.validators import InputValidator
from data.models.leaderboard import LeaderboardType
from data.models.competition import CompetitionStatus
from config.logging_config import get_logger


logger = get_logger(__name__)


class ViewCommands(commands.Cog):
    """
    View commands cog.
    
    Provides read-only commands for viewing leaderboards,
    competition information, and public statistics.
    """
    
    def __init__(self, bot):
        """Initialize the view commands cog."""
        self.bot = bot
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @app_commands.command(name="competitions", description="View active and upcoming competitions")
    @app_commands.describe(status="Filter by competition status")
    @app_commands.choices(status=[
        app_commands.Choice(name="Active", value="active"),
        app_commands.Choice(name="Pending", value="pending"),
        app_commands.Choice(name="All", value="all")
    ])
    @handle_errors()
    @defer_response()
    @rate_limit(calls=10, period=60)  # 10 calls per minute
    @log_command_usage
    async def competitions(self, interaction: discord.Interaction, status: str = "active"):
        """Display active and upcoming competitions."""
        try:
            # Get competitions based on status filter
            if status == "all":
                active_comps = await self.bot.competition_repo.get_competitions_by_status(CompetitionStatus.ACTIVE)
                pending_comps = await self.bot.competition_repo.get_competitions_by_status(CompetitionStatus.PENDING)
                competitions = active_comps + pending_comps
            elif status == "active":
                competitions = await self.bot.competition_repo.get_competitions_by_status(CompetitionStatus.ACTIVE)
            elif status == "pending":
                competitions = await self.bot.competition_repo.get_competitions_by_status(CompetitionStatus.PENDING)
            else:
                competitions = await self.bot.competition_repo.get_active_competitions()
            
            if not competitions:
                embed = discord.Embed(
                    title="📅 Competitions",
                    description="No competitions found matching your criteria.",
                    color=discord.Color.yellow()
                )
                embed.add_field(
                    name="Want to Create One?",
                    value="Administrators can create competitions using `/create_competition`.",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Sort by start time
            competitions.sort(key=lambda c: c.start_time)
            
            # Create embed
            embed = discord.Embed(
                title="📅 Competitions",
                description=f"Showing {len(competitions)} competition(s)",
                color=discord.Color.green()
            )
            
            # Add competition entries
            for i, competition in enumerate(competitions[:10]):  # Limit to 10
                # Status indicator
                status_emojis = {
                    "pending": "⏳ Pending",
                    "active": "🟢 Active",
                    "completed": "✅ Completed",
                    "cancelled": "❌ Cancelled",
                    "paused": "⏸️ Paused"
                }
                status_text = status_emojis.get(competition.status.value, competition.status.value.title())
                
                # Calculate time info
                now = datetime.utcnow()
                start_time = datetime.fromisoformat(competition.start_time.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(competition.end_time.replace('Z', '+00:00'))
                
                if competition.status.value == "pending":
                    time_info = f"Starts: <t:{int(start_time.timestamp())}:R>"
                elif competition.status.value == "active":
                    time_info = f"Ends: <t:{int(end_time.timestamp())}:R>"
                else:
                    time_info = f"Duration: {competition.get_duration_hours():.0f}h"
                
                # Format competition info
                comp_info = (
                    f"**{competition.title}**\n"
                    f"Type: {competition.type.value.replace('_', ' ').title()}\n"
                    f"Status: {status_text}\n"
                    f"Participants: {len(competition.participants)}/{competition.max_participants}\n"
                    f"{time_info}"
                )
                
                embed.add_field(
                    name=f"ID: {competition.id[:20]}{'...' if len(competition.id) > 20 else ''}",
                    value=comp_info,
                    inline=True
                )
                
                # Add separator every 2 competitions
                if (i + 1) % 2 == 0 and i < len(competitions) - 1:
                    embed.add_field(name="\u200b", value="\u200b", inline=False)
            
            if len(competitions) > 10:
                embed.set_footer(text=f"... and {len(competitions) - 10} more competitions")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to get competitions: {e}")
            await interaction.followup.send(
                "❌ Failed to retrieve competitions. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="competition_info", description="Get detailed information about a competition")
    @app_commands.describe(competition_id="ID of the competition to view")
    @handle_errors()
    @defer_response()
    @rate_limit(calls=10, period=60)  # 10 calls per minute
    @log_command_usage
    async def competition_info(self, interaction: discord.Interaction, competition_id: str):
        """Display detailed information about a specific competition."""
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
            
            # Create detailed embed
            embed = discord.Embed(
                title=f"📋 {competition.title}",
                description=competition.description,
                color=discord.Color.blue()
            )
            
            # Basic info
            embed.add_field(
                name="Competition ID",
                value=competition.id,
                inline=True
            )
            embed.add_field(
                name="Type",
                value=competition.type.value.replace('_', ' ').title(),
                inline=True
            )
            embed.add_field(
                name="Status",
                value=competition.status.value.title(),
                inline=True
            )
            
            # Participation info
            embed.add_field(
                name="Participants",
                value=f"{len(competition.participants)}/{competition.max_participants}",
                inline=True
            )
            
            # Time info
            start_time = datetime.fromisoformat(competition.start_time.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(competition.end_time.replace('Z', '+00:00'))
            
            embed.add_field(
                name="Start Time",
                value=f"<t:{int(start_time.timestamp())}:F>",
                inline=True
            )
            embed.add_field(
                name="End Time",
                value=f"<t:{int(end_time.timestamp())}:F>",
                inline=True
            )
            
            # Duration
            embed.add_field(
                name="Duration",
                value=f"{competition.get_duration_hours():.0f} hours",
                inline=True
            )
            
            # Creator info
            try:
                creator = await self.bot.fetch_user(competition.created_by)
                embed.add_field(
                    name="Created By",
                    value=creator.mention if creator else f"User ID: {competition.created_by}",
                    inline=True
                )
            except:
                embed.add_field(
                    name="Created By",
                    value=f"User ID: {competition.created_by}",
                    inline=True
                )
            
            # Competition-specific parameters
            if competition.parameters:
                param_text = []
                for key, value in competition.parameters.items():
                    if key in ['skill_name', 'boss_name', 'category']:
                        param_text.append(f"{key.replace('_', ' ').title()}: {value}")
                
                if param_text:
                    embed.add_field(
                        name="Parameters",
                        value="\n".join(param_text),
                        inline=False
                    )
            
            # Winners (if completed)
            if competition.status.value == "completed" and competition.winners:
                winner_mentions = []
                for winner_id in competition.winners[:3]:  # Top 3
                    try:
                        user = await self.bot.fetch_user(winner_id)
                        winner_mentions.append(user.mention if user else f"User ID: {winner_id}")
                    except:
                        winner_mentions.append(f"User ID: {winner_id}")
                
                embed.add_field(
                    name="🏆 Winners",
                    value="\n".join([f"{i+1}. {mention}" for i, mention in enumerate(winner_mentions)]),
                    inline=False
                )
            
            # Recent participants (if not too many)
            if len(competition.participants) <= 20:
                participant_list = []
                for user_id_str in list(competition.participants.keys())[:10]:
                    try:
                        user_id = int(user_id_str)
                        user = await self.bot.fetch_user(user_id)
                        participant_list.append(user.mention if user else f"User ID: {user_id}")
                    except:
                        participant_list.append(f"User ID: {user_id_str}")
                
                if participant_list:
                    embed.add_field(
                        name="👥 Participants",
                        value="\n".join(participant_list),
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to get competition info: {e}")
            await interaction.followup.send(
                "❌ Failed to retrieve competition information. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="leaderboard", description="View leaderboards")
    @app_commands.describe(
        board_type="Type of leaderboard to view",
        limit="Number of entries to show (1-25)"
    )
    @app_commands.choices(board_type=[
        app_commands.Choice(name="All-Time Wins", value="all_time_wins"),
        app_commands.Choice(name="Monthly Wins", value="monthly_wins"),
        app_commands.Choice(name="Participation", value="participation"),
        app_commands.Choice(name="Skill Competitions", value="skill_competitions"),
        app_commands.Choice(name="Boss Competitions", value="boss_competitions"),
        app_commands.Choice(name="Trivia", value="trivia_competitions")
    ])
    @handle_errors()
    @defer_response()
    @rate_limit(calls=5, period=60)  # 5 calls per minute
    @log_command_usage
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        board_type: str = "all_time_wins",
        limit: int = 10
    ):
        """Display leaderboard rankings."""
        try:
            # Validate limit
            limit = max(1, min(limit, 25))
            
            # Get leaderboard type
            try:
                lb_type = LeaderboardType(board_type)
            except ValueError:
                await interaction.followup.send(
                    f"❌ Invalid leaderboard type: {board_type}",
                    ephemeral=True
                )
                return
            
            # For monthly leaderboards, get current month
            period = None
            if board_type == "monthly_wins":
                period = datetime.utcnow().strftime("%Y-%m")
            
            # Get leaderboard data
            leaderboard = await self.bot.leaderboard_repo.get_leaderboard(lb_type, period)
            
            if not leaderboard or not leaderboard.entries:
                embed = discord.Embed(
                    title="📈 Leaderboard",
                    description=f"No data available for {board_type.replace('_', ' ').title()} leaderboard.",
                    color=discord.Color.yellow()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get top entries
            top_entries = leaderboard.get_top_entries(limit)
            
            # Create embed
            board_name = board_type.replace('_', ' ').title()
            if period:
                board_name += f" ({period})"
            
            embed = discord.Embed(
                title=f"📈 {board_name} Leaderboard",
                description=f"Top {len(top_entries)} participants",
                color=discord.Color.gold()
            )
            
            # Add entries
            rank_emojis = ["🥇", "🥈", "🥉"]
            leaderboard_text = []
            
            for i, entry in enumerate(top_entries):
                # Get emoji for rank
                if i < 3:
                    rank_emoji = rank_emojis[i]
                else:
                    rank_emoji = f"**{entry.rank}.**"
                
                # Try to get user mention
                try:
                    user = await self.bot.fetch_user(entry.user_id)
                    user_display = user.mention if user else entry.display_name or f"User {entry.user_id}"
                except:
                    user_display = entry.display_name or f"User {entry.user_id}"
                
                # Format score based on leaderboard type
                if board_type in ["all_time_wins", "monthly_wins", "skill_competitions", "boss_competitions", "trivia_competitions"]:
                    score_text = f"{int(entry.score)} wins"
                elif board_type == "participation":
                    score_text = f"{int(entry.score)} competitions"
                else:
                    score_text = f"{entry.score:.1f}"
                
                leaderboard_text.append(f"{rank_emoji} {user_display} - {score_text}")
            
            # Split into chunks if too long
            text_chunks = []
            current_chunk = []
            current_length = 0
            
            for line in leaderboard_text:
                if current_length + len(line) > 1000 and current_chunk:
                    text_chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_length = len(line)
                else:
                    current_chunk.append(line)
                    current_length += len(line) + 1
            
            if current_chunk:
                text_chunks.append("\n".join(current_chunk))
            
            # Add fields
            for i, chunk in enumerate(text_chunks):
                field_name = "Rankings" if i == 0 else f"Rankings (continued {i+1})"
                embed.add_field(name=field_name, value=chunk, inline=False)
            
            # Add statistics
            stats = leaderboard.get_statistics()
            if stats["total_entries"] > 0:
                embed.add_field(
                    name="📊 Statistics",
                    value=f"Total Entries: {stats['total_entries']}\n"
                          f"Average Score: {stats['average_score']:.1f}\n"
                          f"Highest Score: {stats['highest_score']:.1f}",
                    inline=True
                )
            
            # Add timestamp
            embed.set_footer(text=f"Last updated: {leaderboard.last_updated}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to get leaderboard: {e}")
            await interaction.followup.send(
                "❌ Failed to retrieve leaderboard. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="user_profile", description="View another user's public profile")
    @app_commands.describe(user="User whose profile to view")
    @handle_errors()
    @defer_response()
    @rate_limit(calls=10, period=60)  # 10 calls per minute
    @log_command_usage
    async def user_profile(self, interaction: discord.Interaction, user: discord.User):
        """Display another user's public profile."""
        try:
            # Get user data
            user_data = await self.bot.user_repo.get_user_by_discord_id(user.id)
            
            if not user_data:
                embed = discord.Embed(
                    title=f"👤 {user.display_name}'s Profile",
                    description="This user hasn't linked their OSRS account yet.",
                    color=discord.Color.yellow()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Get public profile data (respects privacy settings)
            public_data = user_data.get_public_profile()
            
            if public_data.get("privacy_level") == "private":
                embed = discord.Embed(
                    title=f"👤 {user.display_name}'s Profile",
                    description="This user's profile is set to private.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create profile embed
            embed = discord.Embed(
                title=f"👤 {user.display_name}'s Profile",
                color=discord.Color.blue()
            )
            
            # Basic info
            embed.add_field(
                name="Discord",
                value=f"{user.mention}",
                inline=True
            )
            
            if public_data.get("osrs_username"):
                embed.add_field(
                    name="OSRS Account",
                    value=public_data["osrs_username"],
                    inline=True
                )
            
            embed.add_field(
                name="Member Since",
                value=f"<t:{int(datetime.fromisoformat(public_data['join_date'].replace('Z', '+00:00')).timestamp())}:D>",
                inline=True
            )
            
            # Competition stats
            if "total_competitions" in public_data:
                embed.add_field(
                    name="📊 Competition Stats",
                    value=f"Participated: {public_data['total_competitions']}\n"
                          f"Won: {public_data['wins']}\n"
                          f"Win Rate: {public_data['win_rate']:.1f}%",
                    inline=True
                )
            
            # Achievements
            if "achievements" in public_data:
                embed.add_field(
                    name="🏆 Achievements",
                    value=f"{len(public_data['achievements'])} earned",
                    inline=True
                )
            
            # Get leaderboard positions (if available and not private)
            try:
                positions = await self.bot.leaderboard_repo.get_user_leaderboard_positions(user.id)
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
                self.logger.warning(f"Failed to get leaderboard positions for user profile: {e}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            await interaction.followup.send(
                "❌ Failed to retrieve user profile. Please try again later.",
                ephemeral=True
            )


async def setup(bot):
    """Setup function called by Discord.py to load the cog."""
    await bot.add_cog(ViewCommands(bot))