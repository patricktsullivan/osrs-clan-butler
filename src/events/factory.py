"""
Event factory for creating competition manager instances.

Implements the factory pattern to create appropriate competition managers
based on competition type with dependency injection and proper error handling.
"""

from typing import Dict, Type, List, Any
import importlib
import inspect

from events.base_manager import BaseCompetitionManager, CompetitionType
from core.exceptions import CompetitionError, ValidationError
from config.logging_config import LoggerMixin


class EventFactory(LoggerMixin):
    """
    Factory class for creating competition manager instances.
    
    Uses dynamic imports and type checking to create appropriate
    competition managers with proper dependency injection.
    """
    
    # Static mapping of competition types to manager classes
    _manager_classes: Dict[str, Type[BaseCompetitionManager]] = {}
    _initialized = False
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize the factory by registering all manager classes."""
        if cls._initialized:
            return
        
        # Register manager classes
        cls._register_manager_classes()
        cls._initialized = True
        
        logger = cls._get_logger()
        logger.info(f"EventFactory initialized with {len(cls._manager_classes)} manager types")
    
    @classmethod
    def _get_logger(cls):
        """Get logger instance for the factory."""
        import logging
        return logging.getLogger(f"{cls.__module__}.{cls.__name__}")
    
    @classmethod
    def _register_manager_classes(cls) -> None:
        """Register all competition manager classes."""
        manager_configs = [
            {
                "type": "skill_competition",
                "module": "events.skill_manager",
                "class": "SkillCompetitionManager"
            },
            {
                "type": "boss_competition", 
                "module": "events.boss_manager",
                "class": "BossCompetitionManager"
            },
            {
                "type": "trivia",
                "module": "events.trivia_manager", 
                "class": "TriviaManager"
            },
            {
                "type": "race",
                "module": "events.race_manager",
                "class": "RaceManager" 
            },
            {
                "type": "speedrun",
                "module": "events.speedrun_manager",
                "class": "SpeedRunManager"
            }
        ]
        
        logger = cls._get_logger()
        
        for config in manager_configs:
            try:
                # For Phase 1, we'll create placeholder classes since the actual
                # manager implementations will be created in later phases
                cls._manager_classes[config["type"]] = cls._create_placeholder_manager(
                    config["type"], config["class"]
                )
                logger.debug(f"Registered manager: {config['type']}")
                
            except Exception as e:
                logger.warning(f"Failed to register manager {config['type']}: {e}")
    
    @classmethod
    def _create_placeholder_manager(cls, manager_type: str, class_name: str) -> Type[BaseCompetitionManager]:
        """Create a placeholder manager class for Phase 1 implementation."""
        
        class PlaceholderManager(BaseCompetitionManager):
            """Placeholder competition manager for Phase 1."""
            
            @property
            def competition_type(self) -> CompetitionType:
                """Return the competition type this manager handles."""
                type_mapping = {
                    "skill_competition": CompetitionType.SKILL_COMPETITION,
                    "boss_competition": CompetitionType.BOSS_COMPETITION,
                    "trivia": CompetitionType.TRIVIA,
                    "race": CompetitionType.RACE,
                    "speedrun": CompetitionType.SPEEDRUN
                }
                return type_mapping[manager_type]
            
            async def create_competition(self, **kwargs) -> Dict[str, Any]:
                """Create a new competition instance."""
                # Extract common parameters
                title = kwargs.get("title", "")
                description = kwargs.get("description", "")
                duration_hours = kwargs.get("duration_hours", 24)
                max_participants = kwargs.get("max_participants", 50)
                created_by = kwargs.get("created_by", 0)
                
                # Validate parameters
                await self.validate_competition_parameters(**kwargs)
                
                # Create competition using base method
                return await self._create_base_competition(
                    title=title,
                    description=description,
                    duration_hours=duration_hours,
                    max_participants=max_participants,
                    created_by=created_by,
                    **{k: v for k, v in kwargs.items() 
                       if k not in ["title", "description", "duration_hours", "max_participants", "created_by"]}
                )
            
            async def validate_competition_parameters(self, **kwargs) -> bool:
                """Validate competition-specific parameters."""
                # Base validation - specific managers will override
                required_params = ["title", "description", "created_by"]
                for param in required_params:
                    if param not in kwargs:
                        raise ValidationError(f"Missing required parameter: {param}")
                return True
            
            async def register_participant(self, user_id: int, competition_id: str, **kwargs) -> Dict[str, Any]:
                """Register a user for the competition."""
                competition = await self.get_competition(competition_id)
                
                # Add participant with basic starting stats
                starting_stats = kwargs.get("starting_stats", {})
                competition.add_participant(user_id, starting_stats)
                
                # Update competition in repository
                await self.competition_repo.update_competition(competition)
                
                return {
                    "user_id": user_id,
                    "competition_id": competition_id,
                    "registration_time": competition.participants[str(user_id)].registration_time,
                    "starting_stats": starting_stats
                }
            
            async def update_progress(self, user_id: int, competition_id: str, 
                                   progress_data: Dict[str, Any]) -> Dict[str, Any]:
                """Update participant progress."""
                competition = await self.get_competition(competition_id)
                
                # Update progress
                updated = competition.update_participant_progress(user_id, progress_data)
                if updated:
                    await self.competition_repo.update_competition(competition)
                
                return {
                    "user_id": user_id,
                    "competition_id": competition_id,
                    "updated": updated,
                    "progress_data": progress_data
                }
            
            async def calculate_rankings(self, competition_id: str) -> List[Dict[str, Any]]:
                """Calculate current rankings."""
                competition = await self.get_competition(competition_id)
                
                rankings = []
                rank = 1
                
                # Basic ranking by participation time (placeholder logic)
                sorted_participants = sorted(
                    competition.participants.items(),
                    key=lambda x: x[1].registration_time
                )
                
                for user_id_str, participant in sorted_participants:
                    rankings.append({
                        "rank": rank,
                        "user_id": int(user_id_str),
                        "score": participant.current_progress.get("score", 0),
                        "progress": participant.current_progress,
                        "final_result": participant.final_result
                    })
                    rank += 1
                
                return rankings
        
        # Set the class name for better debugging
        PlaceholderManager.__name__ = class_name
        PlaceholderManager.__qualname__ = class_name
        
        return PlaceholderManager
    
    @classmethod
    def create_manager(cls, event_type: str, competition_repo, user_repo, 
                      settings, **kwargs) -> BaseCompetitionManager:
        """
        Create and return appropriate competition manager instance.
        
        Args:
            event_type: Type of competition event
            competition_repo: Competition repository instance
            user_repo: User repository instance  
            settings: Bot configuration settings
            **kwargs: Additional arguments for manager initialization
            
        Returns:
            Competition manager instance
            
        Raises:
            CompetitionError: If event type is not supported
            ValidationError: If required dependencies are missing
        """
        # Initialize factory if not done already
        if not cls._initialized:
            cls.initialize()
        
        logger = cls._get_logger()
        
        # Validate event type
        if event_type not in cls._manager_classes:
            supported_types = list(cls._manager_classes.keys())
            raise CompetitionError(
                f"Unsupported event type: {event_type}. Supported types: {supported_types}",
                competition_type=event_type
            )
        
        # Validate required dependencies
        cls._validate_dependencies(competition_repo, user_repo, settings)
        
        try:
            # Get manager class
            manager_class = cls._manager_classes[event_type]
            
            # Create manager instance with dependency injection
            manager = manager_class(
                competition_repo=competition_repo,
                user_repo=user_repo,
                settings=settings,
                **kwargs
            )
            
            logger.info(
                f"Created {event_type} manager",
                extra={"event_type": event_type, "manager_class": manager_class.__name__}
            )
            
            return manager
            
        except Exception as e:
            logger.error(f"Failed to create manager for {event_type}: {e}")
            raise CompetitionError(
                f"Failed to create competition manager for {event_type}: {str(e)}",
                competition_type=event_type,
                original_exception=e
            )
    
    @classmethod
    def _validate_dependencies(cls, competition_repo, user_repo, settings) -> None:
        """Validate that required dependencies are provided."""
        if competition_repo is None:
            raise ValidationError("competition_repo is required")
        
        if user_repo is None:
            raise ValidationError("user_repo is required")
        
        if settings is None:
            raise ValidationError("settings is required")
        
        # Check that repositories have required methods
        required_competition_methods = ["get_by_id", "update_competition", "create_competition"]
        for method_name in required_competition_methods:
            if not hasattr(competition_repo, method_name):
                raise ValidationError(f"competition_repo missing required method: {method_name}")
        
        required_user_methods = ["get_user_by_discord_id", "update_user"]
        for method_name in required_user_methods:
            if not hasattr(user_repo, method_name):
                raise ValidationError(f"user_repo missing required method: {method_name}")
        
        # Check settings has required attributes
        if not hasattr(settings, 'bot'):
            raise ValidationError("settings missing bot configuration")
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """
        Return list of supported competition types.
        
        Returns:
            List of supported event type strings
        """
        if not cls._initialized:
            cls.initialize()
        
        return list(cls._manager_classes.keys())
    
    @classmethod
    def is_supported_type(cls, event_type: str) -> bool:
        """
        Check if an event type is supported.
        
        Args:
            event_type: Event type to check
            
        Returns:
            True if the event type is supported
        """
        return event_type in cls.get_supported_types()
    
    @classmethod
    def get_manager_info(cls, event_type: str) -> Dict[str, Any]:
        """
        Get information about a specific manager type.
        
        Args:
            event_type: Event type to get info for
            
        Returns:
            Dictionary with manager information
            
        Raises:
            CompetitionError: If event type is not supported
        """
        if not cls.is_supported_type(event_type):
            raise CompetitionError(f"Unsupported event type: {event_type}")
        
        manager_class = cls._manager_classes[event_type]
        
        return {
            "event_type": event_type,
            "class_name": manager_class.__name__,
            "module": manager_class.__module__,
            "competition_type": None,  # Will be available once manager is instantiated
            "description": manager_class.__doc__ or "No description available"
        }
    
    @classmethod
    def get_all_manager_info(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all supported manager types.
        
        Returns:
            Dictionary mapping event types to manager information
        """
        info = {}
        for event_type in cls.get_supported_types():
            try:
                info[event_type] = cls.get_manager_info(event_type)
            except Exception as e:
                logger = cls._get_logger()
                logger.warning(f"Failed to get info for {event_type}: {e}")
        
        return info
    
    @classmethod
    def register_custom_manager(cls, event_type: str, 
                              manager_class: Type[BaseCompetitionManager]) -> None:
        """
        Register a custom competition manager.
        
        Args:
            event_type: Event type identifier
            manager_class: Manager class that extends BaseCompetitionManager
            
        Raises:
            ValidationError: If manager class is invalid
        """
        # Validate manager class
        if not issubclass(manager_class, BaseCompetitionManager):
            raise ValidationError(
                f"Manager class must extend BaseCompetitionManager: {manager_class}"
            )
        
        # Check required methods are implemented
        required_methods = [
            "competition_type", "create_competition", "validate_competition_parameters",
            "register_participant", "update_progress", "calculate_rankings"
        ]
        
        for method_name in required_methods:
            if not hasattr(manager_class, method_name):
                raise ValidationError(f"Manager class missing required method: {method_name}")
        
        # Register the manager
        cls._manager_classes[event_type] = manager_class
        
        logger = cls._get_logger()
        logger.info(f"Registered custom manager: {event_type} -> {manager_class.__name__}")
    
    @classmethod
    def unregister_manager(cls, event_type: str) -> bool:
        """
        Unregister a competition manager.
        
        Args:
            event_type: Event type to unregister
            
        Returns:
            True if manager was unregistered
        """
        if event_type in cls._manager_classes:
            del cls._manager_classes[event_type]
            
            logger = cls._get_logger()
            logger.info(f"Unregistered manager: {event_type}")
            return True
        
        return False
    
    @classmethod
    def reset_factory(cls) -> None:
        """Reset the factory to initial state (useful for testing)."""
        cls._manager_classes.clear()
        cls._initialized = False
        
        logger = cls._get_logger()
        logger.info("EventFactory reset")


# Initialize the factory when module is imported
EventFactory.initialize()