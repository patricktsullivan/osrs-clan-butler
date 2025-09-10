# OSRS Discord Bot

A comprehensive Discord bot for managing Old School RuneScape community competitions, leaderboards, and events.

## Features

### Phase 1 (Core Framework) ✅
- **Competition Management**: Create and manage different types of competitions
- **User System**: Link Discord accounts to OSRS usernames
- **Leaderboards**: Track wins, participation, and achievements
- **Data Persistence**: JSON-based storage with backup and recovery
- **Modular Architecture**: Extensible factory pattern for competition types
- **Comprehensive Logging**: Structured logging with rotation and monitoring
- **Error Handling**: Robust error handling with user-friendly messages
- **Permission System**: Role-based access control for administrative functions

### Planned Features (Future Phases)
- **Skill Competitions**: Weekly skill challenges with XP tracking
- **Boss Competitions**: Boss kill count competitions
- **Trivia System**: OSRS knowledge quizzes
- **Race Events**: Real-time racing competitions
- **Speed Run Challenges**: Timed challenge completions
- **Wise Old Man Integration**: Automatic stat tracking and verification
- **Advanced Statistics**: Detailed analytics and performance tracking

## Project Structure

```
osrs_discord_bot/
├── main.py                          # Application entry point
├── config/
│   ├── settings.py                  # Configuration management
│   └── logging_config.py            # Logging setup
├── core/
│   ├── bot.py                       # Main Discord bot class
│   ├── exceptions.py                # Custom exception definitions
│   └── decorators.py                # Permission and utility decorators
├── events/
│   ├── factory.py                   # Event factory for competition managers
│   ├── base_manager.py              # Abstract base competition manager
│   ├── skill_manager.py             # Skill competition management
│   ├── boss_manager.py              # Boss competition management
│   ├── trivia_manager.py            # Trivia system management
│   ├── race_manager.py              # Race event coordination
│   └── speedrun_manager.py          # Speed run challenge management
├── data/
│   ├── repositories/
│   │   ├── base_repository.py       # Abstract repository pattern
│   │   ├── user_repository.py       # User data management
│   │   ├── competition_repository.py # Competition data management
│   │   └── leaderboard_repository.py # Leaderboard and achievement management
│   └── models/
│       ├── user.py                  # User data model
│       ├── competition.py           # Competition data model
│       └── leaderboard.py           # Leaderboard and achievement models
├── external/
│   ├── wise_old_man.py             # Wise Old Man API client
│   └── api_exceptions.py           # API-specific exception handling
├── commands/
│   ├── admin_commands.py           # Administrative slash commands
│   ├── participant_commands.py     # User participation commands
│   └── view_commands.py            # Read-only viewing commands
├── utils/
│   ├── validators.py               # Input validation utilities
│   ├── rate_limiter.py             # API rate limiting implementation
│   └── formatters.py               # Discord embed formatting
├── database/                       # JSON data storage
│   ├── users.json                  # User profiles and accounts
│   ├── competitions.json           # Competition data
│   ├── leaderboards.json          # Rankings and achievements
│   └── trivia_questions.json      # Trivia question bank
└── logs/                           # Log files
    └── osrs_bot.log               # Application logs
```

## Installation

### Prerequisites
- Python 3.9 or higher
- Discord bot token
- Discord server with appropriate permissions

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd osrs_discord_bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Create necessary directories**
   ```bash
   mkdir -p database logs
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DISCORD_TOKEN` | Discord bot token | Yes | - |
| `GUILD_ID` | Discord server ID | Yes | - |
| `ADMIN_ROLE_ID` | Role ID for administrators | No | - |
| `ADMIN_USER_IDS` | Comma-separated admin user IDs | No | - |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No | INFO |
| `ENVIRONMENT` | Environment (development, production) | No | development |
| `MAX_CONCURRENT_COMPETITIONS` | Maximum active competitions | No | 5 |

### Discord Bot Setup

1. **Create Discord Application**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Navigate to "Bot" section
   - Create a bot and copy the token

2. **Set Bot Permissions**
   Required permissions:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History
   - Add Reactions
   - Manage Messages (for cleanup)

3. **Invite Bot to Server**
   Generate invite URL with required permissions and add to your server.

## Usage

### Administrative Commands

- `/create_competition` - Create a new competition
- `/cancel_competition` - Cancel an existing competition
- `/bot_stats` - View bot statistics and health
- `/force_sync` - Force sync slash commands
- `/user_info` - Get detailed user information

### User Commands

- `/link_account` - Link OSRS account to Discord
- `/unlink_account` - Unlink OSRS account
- `/join_competition` - Join an active competition
- `/leave_competition` - Leave a competition
- `/my_profile` - View your profile and stats
- `/my_competitions` - View competition history

### Viewing Commands

- `/competitions` - View active and upcoming competitions
- `/competition_info` - Get detailed competition information
- `/leaderboard` - View various leaderboards
- `/user_profile` - View another user's public profile

## Development

### Architecture Principles

The bot follows several architectural principles:

1. **Separation of Concerns**: Clear separation between Discord interactions, business logic, and data persistence
2. **Factory Pattern**: Extensible competition manager creation through EventFactory
3. **Repository Pattern**: Abstracted data access with consistent CRUD operations
4. **Dependency Injection**: Components receive dependencies through constructors
5. **Error Handling**: Comprehensive exception hierarchy with user-friendly messages
6. **Logging**: Structured logging for debugging and monitoring

### Adding New Competition Types

1. Create a new manager class extending `BaseCompetitionManager`
2. Implement required abstract methods
3. Register the manager in `EventFactory`
4. Add specific command handling if needed

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_user_repository.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Security Considerations

- Input validation on all user inputs
- SQL injection prevention (though using JSON storage)
- XSS prevention in text processing
- Rate limiting on commands
- Permission checking on administrative functions
- Secure configuration management

## Monitoring and Maintenance

### Logging

The bot provides comprehensive logging:
- **Console Output**: Colored logs for development
- **File Output**: JSON-structured logs for production
- **Log Rotation**: Automatic rotation with configurable size limits
- **Error Tracking**: Detailed error logging with context

### Data Backup

- Automatic backups before data modifications
- Configurable backup retention
- Backup verification and restoration capabilities

### Health Monitoring

- Bot uptime tracking
- Command usage statistics
- Error rate monitoring
- Repository health checks

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Include docstrings for classes and public methods
- Write tests for new functionality
- Update documentation as needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please:
1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
4. Join our Discord server (if available)

## Changelog

### Version 1.0.0 (Phase 1)
- Initial core framework implementation
- User management system
- Basic competition framework
- Leaderboard system
- Administrative commands
- JSON-based data persistence
- Comprehensive logging system