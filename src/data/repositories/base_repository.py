"""
Base repository pattern for JSON file operations.

Provides abstract base class with common CRUD operations,
file locking, backup functionality, and error handling.
"""

import json
import asyncio
import aiofiles
import aiofiles.os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, TypeVar, Generic, Type
from datetime import datetime
import shutil
import fcntl
import tempfile

from core.exceptions import DatabaseError, ValidationError
from config.logging_config import LoggerMixin


T = TypeVar('T')


class BaseRepository(ABC, LoggerMixin, Generic[T]):
    """
    Abstract base repository for JSON-based data persistence.
    
    Provides common functionality for CRUD operations, file locking,
    backup management, and data validation.
    """
    
    def __init__(self, file_path: str, model_class: Type[T]):
        """
        Initialize the repository.
        
        Args:
            file_path: Path to the JSON file
            model_class: Class used for data validation and serialization
        """
        self.file_path = Path(file_path)
        self.model_class = model_class
        self.backup_dir = self.file_path.parent / "backups"
        self._lock = asyncio.Lock()
        
        # Ensure directories exist
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize file if it doesn't exist
        asyncio.create_task(self._initialize_file())
    
    async def _initialize_file(self) -> None:
        """Initialize the JSON file with default structure if it doesn't exist."""
        if not self.file_path.exists():
            try:
                default_data = self._get_default_structure()
                await self._write_file(default_data)
                self.logger.info(f"Initialized new data file: {self.file_path}")
            except Exception as e:
                raise DatabaseError(
                    f"Failed to initialize file {self.file_path}",
                    operation="initialize",
                    file_path=str(self.file_path),
                    original_exception=e
                )
    
    @abstractmethod
    def _get_default_structure(self) -> Dict[str, Any]:
        """Return the default JSON structure for the repository."""
        pass
    
    @abstractmethod
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate the data structure and content."""
        pass
    
    async def _read_file(self) -> Dict[str, Any]:
        """
        Read and parse the JSON file with file locking.
        
        Returns:
            Parsed JSON data
            
        Raises:
            DatabaseError: If file operations fail
        """
        try:
            async with aiofiles.open(self.file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
                if not content.strip():
                    return self._get_default_structure()
                return json.loads(content)
        
        except FileNotFoundError:
            self.logger.warning(f"File not found: {self.file_path}, using defaults")
            return self._get_default_structure()
        
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in {self.file_path}: {e}")
            # Try to restore from backup
            backup_data = await self._restore_from_backup()
            if backup_data:
                return backup_data
            raise DatabaseError(
                f"Corrupted JSON file: {self.file_path}",
                operation="read",
                file_path=str(self.file_path),
                original_exception=e
            )
        
        except Exception as e:
            raise DatabaseError(
                f"Failed to read file: {self.file_path}",
                operation="read",
                file_path=str(self.file_path),
                original_exception=e
            )
    
    async def _write_file(self, data: Dict[str, Any]) -> None:
        """
        Write data to JSON file with atomic operations and backup.
        
        Args:
            data: Data to write to file
            
        Raises:
            DatabaseError: If file operations fail
        """
        # Validate data before writing
        if not self._validate_data(data):
            raise ValidationError("Data validation failed before write operation")
        
        # Update metadata
        data.setdefault('metadata', {})
        data['metadata']['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
        try:
            # Create backup before writing
            await self._create_backup()
            
            # Write to temporary file first for atomic operation
            temp_file = self.file_path.with_suffix('.tmp')
            
            async with aiofiles.open(temp_file, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(data, indent=2, ensure_ascii=False))
                await file.flush()
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: temp_file.rename(self.file_path)
                )
            
            self.logger.debug(f"Successfully wrote data to {self.file_path}")
        
        except Exception as e:
            # Clean up temporary file if it exists
            if temp_file.exists():
                await aiofiles.os.remove(temp_file)
            
            raise DatabaseError(
                f"Failed to write file: {self.file_path}",
                operation="write",
                file_path=str(self.file_path),
                original_exception=e
            )
    
    async def _create_backup(self) -> None:
        """Create a timestamped backup of the current file."""
        if not self.file_path.exists():
            return
        
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{self.file_path.stem}_{timestamp}.json"
            
            await asyncio.get_event_loop().run_in_executor(
                None, shutil.copy2, str(self.file_path), str(backup_file)
            )
            
            # Clean up old backups
            await self._cleanup_old_backups()
            
            self.logger.debug(f"Created backup: {backup_file}")
        
        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")
            # Don't raise exception for backup failures
    
    async def _cleanup_old_backups(self, max_backups: int = 10) -> None:
        """Remove old backup files, keeping only the most recent ones."""
        try:
            backup_files = sorted(
                self.backup_dir.glob(f"{self.file_path.stem}_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backup_files[max_backups:]:
                await aiofiles.os.remove(old_backup)
                self.logger.debug(f"Removed old backup: {old_backup}")
        
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old backups: {e}")
    
    async def _restore_from_backup(self) -> Optional[Dict[str, Any]]:
        """
        Attempt to restore data from the most recent backup.
        
        Returns:
            Restored data if successful, None otherwise
        """
        try:
            backup_files = sorted(
                self.backup_dir.glob(f"{self.file_path.stem}_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if not backup_files:
                self.logger.warning("No backup files found for restoration")
                return None
            
            latest_backup = backup_files[0]
            self.logger.info(f"Attempting to restore from backup: {latest_backup}")
            
            async with aiofiles.open(latest_backup, 'r', encoding='utf-8') as file:
                content = await file.read()
                data = json.loads(content)
                
                if self._validate_data(data):
                    # Copy backup to main file
                    await asyncio.get_event_loop().run_in_executor(
                        None, shutil.copy2, str(latest_backup), str(self.file_path)
                    )
                    self.logger.info(f"Successfully restored from backup: {latest_backup}")
                    return data
                else:
                    self.logger.error(f"Backup file validation failed: {latest_backup}")
                    return None
        
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
            return None
    
    async def load_data(self) -> Dict[str, Any]:
        """
        Load all data from the repository.
        
        Returns:
            Complete data structure from the JSON file
        """
        async with self._lock:
            return await self._read_file()
    
    async def save_data(self, data: Dict[str, Any]) -> None:
        """
        Save complete data structure to the repository.
        
        Args:
            data: Complete data structure to save
        """
        async with self._lock:
            await self._write_file(data)
    
    async def update_field(self, field_path: str, value: Any) -> None:
        """
        Update a specific field in the data structure.
        
        Args:
            field_path: Dot-separated path to the field (e.g., "users.123.username")
            value: New value for the field
        """
        async with self._lock:
            data = await self._read_file()
            
            # Navigate to the field and update it
            keys = field_path.split('.')
            current = data
            
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            current[keys[-1]] = value
            await self._write_file(data)
    
    async def delete_field(self, field_path: str) -> bool:
        """
        Delete a specific field from the data structure.
        
        Args:
            field_path: Dot-separated path to the field
            
        Returns:
            True if field was deleted, False if not found
        """
        async with self._lock:
            data = await self._read_file()
            
            keys = field_path.split('.')
            current = data
            
            # Navigate to parent of target field
            for key in keys[:-1]:
                if key not in current:
                    return False
                current = current[key]
            
            # Delete the field if it exists
            target_key = keys[-1]
            if target_key in current:
                del current[target_key]
                await self._write_file(data)
                return True
            
            return False
    
    async def get_metadata(self) -> Dict[str, Any]:
        """Get metadata information about the repository."""
        data = await self.load_data()
        return data.get('metadata', {})
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistical information about the repository."""
        try:
            file_stats = self.file_path.stat()
            data = await self.load_data()
            
            return {
                "file_size_bytes": file_stats.st_size,
                "last_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                "data_version": data.get('metadata', {}).get('version', 'unknown'),
                "last_updated": data.get('metadata', {}).get('last_updated', 'unknown'),
                "backup_count": len(list(self.backup_dir.glob(f"{self.file_path.stem}_*.json")))
            }
        except Exception as e:
            self.logger.error(f"Failed to get repository stats: {e}")
            return {}
    
    async def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the repository data.
        
        Returns:
            Dictionary with integrity check results
        """
        results = {
            "file_exists": self.file_path.exists(),
            "file_readable": False,
            "json_valid": False,
            "data_valid": False,
            "backup_available": False,
            "errors": []
        }
        
        try:
            # Check if file is readable
            data = await self._read_file()
            results["file_readable"] = True
            results["json_valid"] = True
            
            # Check data validation
            results["data_valid"] = self._validate_data(data)
            
            # Check if backups are available
            backup_files = list(self.backup_dir.glob(f"{self.file_path.stem}_*.json"))
            results["backup_available"] = len(backup_files) > 0
            results["backup_count"] = len(backup_files)
            
        except Exception as e:
            results["errors"].append(str(e))
        
        return results