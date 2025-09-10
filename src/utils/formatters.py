"""
Discord embed formatting utilities for OSRS Discord Bot.

Provides consistent formatting for embeds, messages, and data display
with OSRS-themed styling and responsive layouts.
"""

import discord
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from math import ceil

from data.models.competition import Competition, CompetitionStatus
from data.models.user import User
from data.models.leaderboard import LeaderboardEntry, Achievement


class EmbedFormatter:
    """
    Utility class for creating consistently formatted Discord embeds.
    
    Provides methods for creating different types of embeds with
    OSRS-themed colors and formatting.
    """
    
    # Color scheme
    COLORS = {
        "success": discord.Color.green(),
        "error": discord.Color.red(),
        "warning": discord.Color.orange(),
        "info": discord.Color.blue(),
        "pending": discord.Color.yellow(),
        "active": discord.Color.green(),
        "completed": discord.Color.blue(),
        "cancelled": discord.Color.red(),
        "osrs_orange": discord.Color.from_rgb(255, 152, 31),  # OSRS UI orange
        "osrs_yellow": discord.Color.from_rgb(255, 255, 0),   # OSRS text yellow
        "osrs_red": discord.Color.from_rgb(255, 0, 0),        # OSRS red text
    }
    
    # Status emojis
    STATUS_EMOJIS = {
        "pending": "⏳",
        "active": "🟢",
        "completed": "✅",
        "cancelled": "❌",
        "paused": "⏸️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
    }
    
    # Competition type emojis
    COMPETITION_EMOJIS = {
        "skill_competition": "⚔️",
        "boss_competition": "👹",
        "trivia": "🧠",
        "race": "🏃",
        "speedrun": "⏱️",
    }
    
    @classmethod
    def create_basic_embed(cls, 
                          title: str, 
                          description: str = None,
                          color: Union[str, discord.Color] = "info",
                          emoji: str = None) -> discord.Embed:
        """
        Create a basic embed with consistent styling.
        
        Args:
            title: Embed title
            description: Embed description
            color: Color name or discord.Color object
            emoji: Optional emoji for title
            
        Returns:
            Formatted Discord embed
        """
        # Get color
        if isinstance(color, str):
            embed_color = cls.COLORS.get(color, cls.COLORS["info"])
        else:
            embed_color = color
        
        # Format title with emoji
        if emoji:
            formatted_title = f"{emoji} {title}"
        else:
            formatted_title = title
        
        embed = discord.Embed(
            title=formatted_title,
            description=description,
            color=embed_color,
            timestamp=datetime.utcnow()
        )
        
        return embed
    
    @classmethod
    def create_success_embed(cls, title: str, description: str = None) -> discord.Embed:
        """Create a success embed."""
        return cls.create_basic_embed(title, description, "success", cls.STATUS_EMOJIS["success"])
    
    @classmethod
    def create_error_embed(cls, title: str, description: str = None) -> discord.Embed:
        """Create an error embed."""
        return cls.create_basic_embed(title, description, "error", cls.STATUS_EMOJIS["error"])
    
    @classmethod
    def create_warning_embed(cls, title: str, description: str = None) -> discord.Embed:
        """Create a warning embed."""
        return cls.create_basic_embed(title, description, "warning", cls.STATUS_EMOJIS["warning"])
    
    @classmethod
    def create_competition_embed(cls, competition: Competition, detailed: bool = False) -> discord.Embed:
        """
        Create an embed for displaying competition information.
        
        Args:
            competition: Competition object
            detailed: Whether to include detailed information
            
        Returns:
            Formatted competition embed
        """
        # Get status color and emoji
        status_color = cls.COLORS.get(competition.status.value, cls.COLORS["info"])
        status_emoji = cls.STATUS_EMOJIS.get(competition.status.value, "❓")
        comp_emoji = cls.COMPETITION_EMOJIS.get(competition.type.value, "📝")
        
        # Create embed
        embed = discord.Embed(
            title=f"{comp_emoji} {competition.title}",
            description=competition.description if detailed else None,
            color=status_color,
            timestamp=datetime.utcnow()
        )
        
        # Basic information
        embed.add_field(
            name="Competition ID",
            value=f"`{competition.id}`",
            inline=True
        )
        
        embed.add_field(
            name="Type",
            value=competition.type.value.replace('_', ' ').title(),
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value=f"{status_emoji} {competition.status.value.title()}",
            inline=True
        )
        
        embed.add_field(
            name="Participants",
            value=f"{len(competition.participants)}/{competition.max_participants}",
            inline=True
        )
        
        # Time information
        if detailed:
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
            
            embed.add_field(
                name="Duration",
                value=f"{competition.get_duration_hours():.0f} hours",
                inline=True
            )
        
        # Winners if completed
        if competition.status == CompetitionStatus.COMPLETED and competition.winners:
            winner_text = []
            medals = ["🥇", "🥈", "🥉"]
            
            for i, winner_id in enumerate(competition.winners[:3]):
                medal = medals[i] if i < 3 else f"{i+1}."
                winner_text.append(f"{medal} <@{winner_id}>")
            
            embed.add_field(
                name="🏆 Winners",
                value="\n".join(winner_text),
                inline=False
            )
        
        return embed
    
    @classmethod
    def create_user_profile_embed(cls, user: User, discord_user: discord.User = None) -> discord.Embed:
        """
        Create an embed for displaying user profile.
        
        Args:
            user: User object
            discord_user: Optional Discord user object for avatar
            
        Returns:
            Formatted user profile embed
        """
        embed = discord.Embed(
            title=f"👤 {discord_user.display_name if discord_user else 'User'}'s Profile",
            color=cls.COLORS["osrs_orange"],
            timestamp=datetime.utcnow()
        )
        
        # Set thumbnail if Discord user provided
        if discord_user:
            embed.set_thumbnail(url=discord_user.display_avatar.url)
        
        # Basic information
        embed.add_field(
            name="Discord",
            value=f"<@{user.discord_id}>",
            inline=True
        )
        
        embed.add_field(
            name="OSRS Account",
            value=user.osrs_username if user.osrs_username else "Not linked",
            inline=True
        )
        
        join_timestamp = int(datetime.fromisoformat(user.join_date.replace('Z', '+00:00')).timestamp())
        embed.add_field(
            name="Member Since",
            value=f"<t:{join_timestamp}:D>",
            inline=True
        )
        
        # Competition statistics
        embed.add_field(
            name="📊 Competition Stats",
            value=f"**Participated:** {user.total_competitions}\n"
                  f"**Won:** {user.wins}\n"
                  f"**Win Rate:** {user.get_win_rate():.1f}%",
            inline=True
        )
        
        # Achievements
        embed.add_field(
            name="🏆 Achievements",
            value=f"{len(user.achievements)} earned",
            inline=True
        )
        
        # Last activity
        last_activity = int(datetime.fromisoformat(user.last_activity.replace('Z', '+00:00')).timestamp())
        embed.add_field(
            name="🕒 Last Active",
            value=f"<t:{last_activity}:R>",
            inline=True
        )
        
        return embed
    
    @classmethod
    def create_leaderboard_embed(cls, 
                                title: str,
                                entries: List[LeaderboardEntry], 
                                score_format: str = "points",
                                page: int = 1,
                                total_pages: int = 1) -> discord.Embed:
        """
        Create an embed for displaying leaderboard.
        
        Args:
            title: Leaderboard title
            entries: List of leaderboard entries
            score_format: Format for displaying scores
            page: Current page number
            total_pages: Total number of pages
            
        Returns:
            Formatted leaderboard embed
        """
        embed = discord.Embed(
            title=f"📈 {title}",
            color=cls.COLORS["osrs_yellow"],
            timestamp=datetime.utcnow()
        )
        
        if not entries:
            embed.description = "No entries found."
            return embed
        
        # Rank emojis for top 3
        rank_emojis = ["🥇", "🥈", "🥉"]
        
        # Format entries
        leaderboard_text = []
        for entry in entries:
            # Get rank emoji or number
            if entry.rank <= 3:
                rank_display = rank_emojis[entry.rank - 1]
            else:
                rank_display = f"**{entry.rank}.**"
            
            # Format score
            if score_format == "wins":
                score_text = f"{int(entry.score)} wins"
            elif score_format == "competitions":
                score_text = f"{int(entry.score)} competitions"
            elif score_format == "percentage":
                score_text = f"{entry.score:.1f}%"
            else:
                score_text = f"{entry.score:.1f} {score_format}"
            
            # User display
            user_display = entry.display_name or f"<@{entry.user_id}>"
            
            leaderboard_text.append(f"{rank_display} {user_display} - {score_text}")
        
        # Add entries to embed
        embed.description = "\n".join(leaderboard_text)
        
        # Add page information if multiple pages
        if total_pages > 1:
            embed.set_footer(text=f"Page {page}/{total_pages}")
        
        return embed
    
    @classmethod
    def create_achievement_embed(cls, achievement: Achievement, user_name: str = None) -> discord.Embed:
        """
        Create an embed for displaying achievement.
        
        Args:
            achievement: Achievement object
            user_name: Optional user name
            
        Returns:
            Formatted achievement embed
        """
        embed = discord.Embed(
            title="🏆 Achievement Unlocked!",
            color=cls.COLORS["osrs_yellow"],
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Achievement",
            value=achievement.achievement_id.replace('_', ' ').title(),
            inline=False
        )
        
        if user_name:
            embed.add_field(
                name="Earned By",
                value=user_name,
                inline=True
            )
        
        earned_timestamp = int(datetime.fromisoformat(achievement.earned_date.replace('Z', '+00:00')).timestamp())
        embed.add_field(
            name="Earned",
            value=f"<t:{earned_timestamp}:F>",
            inline=True
        )
        
        if achievement.competition_id:
            embed.add_field(
                name="Competition",
                value=f"`{achievement.competition_id}`",
                inline=True
            )
        
        return embed
    
    @classmethod
    def create_paginated_embed(cls,
                              title: str,
                              items: List[str],
                              items_per_page: int = 10,
                              page: int = 1,
                              color: Union[str, discord.Color] = "info") -> discord.Embed:
        """
        Create a paginated embed for large lists.
        
        Args:
            title: Embed title
            items: List of items to display
            items_per_page: Number of items per page
            page: Current page (1-indexed)
            color: Embed color
            
        Returns:
            Formatted paginated embed
        """
        total_pages = ceil(len(items) / items_per_page)
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_items = items[start_idx:end_idx]
        
        embed = cls.create_basic_embed(
            title=f"{title} (Page {page}/{total_pages})",
            color=color
        )
        
        if page_items:
            embed.description = "\n".join(page_items)
        else:
            embed.description = "No items found."
        
        if total_pages > 1:
            embed.set_footer(text=f"Page {page} of {total_pages} | {len(items)} total items")
        
        return embed
    
    @classmethod
    def create_help_embed(cls, command_name: str, description: str, 
                         usage: str = None, examples: List[str] = None) -> discord.Embed:
        """
        Create a help embed for commands.
        
        Args:
            command_name: Name of the command
            description: Command description
            usage: Usage syntax
            examples: List of usage examples
            
        Returns:
            Formatted help embed
        """
        embed = cls.create_basic_embed(
            title=f"📚 Help: {command_name}",
            description=description,
            color="info"
        )
        
        if usage:
            embed.add_field(
                name="Usage",
                value=f"`{usage}`",
                inline=False
            )
        
        if examples:
            example_text = "\n".join([f"`{example}`" for example in examples])
            embed.add_field(
                name="Examples",
                value=example_text,
                inline=False
            )
        
        return embed


class MessageFormatter:
    """
    Utility class for formatting plain text messages and responses.
    
    Provides consistent text formatting for non-embed messages.
    """
    
    @staticmethod
    def format_time_remaining(seconds: float) -> str:
        """
        Format time remaining in a human-readable format.
        
        Args:
            seconds: Time remaining in seconds
            
        Returns:
            Formatted time string
        """
        if seconds <= 0:
            return "Ended"
        
        time_delta = timedelta(seconds=int(seconds))
        days = time_delta.days
        hours, remainder = divmod(time_delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "Less than 1 minute"
    
    @staticmethod
    def format_number(number: Union[int, float], precision: int = 1) -> str:
        """
        Format large numbers with appropriate suffixes.
        
        Args:
            number: Number to format
            precision: Decimal precision for formatted number
            
        Returns:
            Formatted number string
        """
        if number < 1000:
            return str(int(number))
        elif number < 1_000_000:
            return f"{number/1000:.{precision}f}K"
        elif number < 1_000_000_000:
            return f"{number/1_000_000:.{precision}f}M"
        else:
            return f"{number/1_000_000_000:.{precision}f}B"
    
    @staticmethod
    def format_percentage(value: float, total: float) -> str:
        """
        Format a percentage with proper handling of edge cases.
        
        Args:
            value: Value to calculate percentage for
            total: Total value
            
        Returns:
            Formatted percentage string
        """
        if total == 0:
            return "0.0%"
        
        percentage = (value / total) * 100
        return f"{percentage:.1f}%"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Truncate text to a maximum length with optional suffix.
        
        Args:
            text: Text to truncate
            max_length: Maximum length including suffix
            suffix: Suffix to add if truncated
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        truncated_length = max_length - len(suffix)
        return text[:truncated_length] + suffix
    
    @staticmethod
    def format_competition_status(competition: Competition) -> str:
        """
        Format competition status with emoji and time information.
        
        Args:
            competition: Competition object
            
        Returns:
            Formatted status string
        """
        status_emoji = EmbedFormatter.STATUS_EMOJIS.get(competition.status.value, "❓")
        status_text = competition.status.value.title()
        
        if competition.status == CompetitionStatus.PENDING:
            start_time = datetime.fromisoformat(competition.start_time.replace('Z', '+00:00'))
            time_until_start = (start_time - datetime.utcnow()).total_seconds()
            time_str = MessageFormatter.format_time_remaining(time_until_start)
            return f"{status_emoji} {status_text} (starts in {time_str})"
        
        elif competition.status == CompetitionStatus.ACTIVE:
            time_remaining = competition.get_time_remaining_hours()
            if time_remaining is not None:
                time_str = MessageFormatter.format_time_remaining(time_remaining * 3600)
                return f"{status_emoji} {status_text} ({time_str} remaining)"
        
        return f"{status_emoji} {status_text}"