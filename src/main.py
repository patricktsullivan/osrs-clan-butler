#!/usr/bin/env python3
"""
OSRS Discord Bot - Main Application Entry Point

This module initializes and runs the Discord bot with proper error handling,
graceful shutdown, and comprehensive logging setup.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from core.bot import OSRSBot
from config.settings import Settings
from config.logging_config import setup_logging


class BotRunner:
    """Manages the bot lifecycle with graceful startup and shutdown."""
    
    def __init__(self):
        self.bot: Optional[OSRSBot] = None
        self.logger = logging.getLogger(__name__)
        self._shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Initialize and start the Discord bot."""
        try:
            # Setup logging before any other operations
            setup_logging()
            self.logger.info("Starting OSRS Discord Bot...")
            
            # Load and validate configuration
            settings = Settings()
            if not settings.validate():
                self.logger.error("Configuration validation failed")
                sys.exit(1)
            
            # Initialize the bot
            self.bot = OSRSBot(settings)
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start the bot
            await self.bot.start(settings.DISCORD_TOKEN)
            
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}", exc_info=True)
            sys.exit(1)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the bot and cleanup resources."""
        self.logger.info("Initiating graceful shutdown...")
        
        if self.bot:
            try:
                await self.bot.close()
                self.logger.info("Bot connection closed successfully")
            except Exception as e:
                self.logger.error(f"Error during bot shutdown: {e}")
        
        # Cancel any remaining tasks
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        if tasks:
            self.logger.info(f"Cancelling {len(tasks)} pending tasks...")
            for task in tasks:
                task.cancel()
            
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info("Shutdown complete")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown on SIGINT/SIGTERM."""
        if sys.platform != "win32":
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig, lambda: asyncio.create_task(self._handle_shutdown())
                )
    
    async def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        self.logger.info("Shutdown signal received")
        self._shutdown_event.set()
        await self.shutdown()


async def main() -> None:
    """Main application entry point."""
    runner = BotRunner()
    
    try:
        await runner.start()
    except KeyboardInterrupt:
        await runner.shutdown()
    except Exception as e:
        logging.getLogger(__name__).error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)