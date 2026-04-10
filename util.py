"""
Utility functions for SimKit package.

Provides file handling and retry functionality.

Authors: Arman Moussavi, Zhenghao Wu
"""

import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Callable, Union, Optional, Type

from simkit import logger


class RetrySignal(Exception):
    """Exception to signal that a function should be retried."""
    pass


def copy_file(src: str, dest: str, backup_existing: bool = True) -> None:
    """
    Copy a file from source to destination with optional backup.
    
    Args:
        src: Source file path
        dest: Destination file path
        backup_existing: If True, backup existing destination file with timestamp
        
    Raises:
        FileNotFoundError: If source file doesn't exist
    """
    if not os.path.isfile(src):
        logger.error(f"Source file does not exist: {src}")
        raise FileNotFoundError(f"Source file not found: {src}")
        
    # Backup existing file if requested
    if backup_existing and os.path.exists(dest):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = Path(dest)
        backup_name = f"{dest_path.stem}_{timestamp}{dest_path.suffix}"
        backup_path = dest_path.parent / backup_name
        
        logger.info(f"Backing up existing file: {dest} -> {backup_path}")
        shutil.move(dest, backup_path)
        
    # Copy the file
    shutil.copy2(src, dest)
    logger.debug(f"Copied file: {src} -> {dest}")


def retry(max_retry: int = 3,
         sleep_time: Union[int, float] = 60,
         catch_exception: Type[BaseException] = RetrySignal) -> Callable:
    """
    Decorator to retry a function on failure.
    
    Args:
        max_retry: Maximum number of retry attempts (must be > 0)
        sleep_time: Time to sleep between retries in seconds
        catch_exception: Exception type to catch and retry on
        
    Returns:
        Decorated function that retries on specified exception
        
    Example:
        >>> @retry(max_retry=3, sleep_time=60, catch_exception=RetrySignal)
        ... def unstable_function():
        ...     # Function that might fail
        ...     if some_condition:
        ...         raise RetrySignal("Temporary failure")
        ...     return result
    """
    if max_retry <= 0:
        raise ValueError("max_retry must be greater than 0")
        
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            errors = []
            
            for attempt in range(max_retry):
                try:
                    return func(*args, **kwargs)
                    
                except catch_exception as e:
                    errors.append(e)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retry} failed for {func.__name__}: {e}"
                    )
                    
                    if attempt < max_retry - 1:  # Don't sleep after last attempt
                        logger.info(f"Sleeping {sleep_time}s before retry...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"All {max_retry} attempts failed for {func.__name__}")
                        
            # If we get here, all retries failed
            raise RuntimeError(
                f"Failed to execute {func.__name__} after {max_retry} attempts"
            ) from errors[-1]
            
        return wrapper
    return decorator


def create_directory_structure(base_path: Path, structure: dict) -> None:
    """
    Create a nested directory structure from a dictionary.
    
    Args:
        base_path: Base path for directory creation
        structure: Dictionary representing directory structure
                  Keys are directory names, values are subdirectories (dict) or None
                  
    Example:
        >>> structure = {
        ...     'data': {
        ...         'raw': None,
        ...         'processed': None
        ...     },
        ...     'results': None
        ... }
        >>> create_directory_structure(Path('/project'), structure)
    """
    for name, subdirs in structure.items():
        dir_path = base_path / name
        dir_path.mkdir(parents=True, exist_ok=True)
        
        if subdirs is not None and isinstance(subdirs, dict):
            create_directory_structure(dir_path, subdirs)


def find_files(directory: Path, pattern: str = "*", recursive: bool = True) -> list:
    """
    Find files matching a pattern in a directory.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern to match (default: all files)
        recursive: If True, search recursively
        
    Returns:
        List of Path objects matching the pattern
    """
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def validate_executable(executable: dict) -> bool:
    """
    Validate that an executable dictionary has required keys.
    
    Args:
        executable: Dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_keys = ['command', 'dependency']
    
    if not isinstance(executable, dict):
        logger.error("Executable must be a dictionary")
        return False
        
    for key in required_keys:
        if key not in executable:
            logger.error(f"Executable missing required key: {key}")
            return False
            
    return True