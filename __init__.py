"""
SimKit - Automated Molecular Dynamics Simulation Setup

A Python package for automating the setup and submission of molecular dynamics
simulations on HPC clusters with SLURM scheduling.

Authors: Arman Moussavi, Zhenghao Wu
License: BSD License

This project is an updated and adapted version of AutoMD, originally created by
Zhenghao Wu. SimKit builds upon AutoMD with improvements to code structure,
error handling, and user experience.
"""

__author__ = "Arman Moussavi, Zhenghao Wu"
__license__ = "BSD License"
__version__ = "1.0.0"

import logging
import os
import json
from pathlib import Path

# Default output path
OUT_PATH = Path.home()

# Default logging configuration
LOG_CONFIG = {
    'ROOT_LEVEL': logging.INFO,
    'CONSOLE_LEVEL': logging.INFO,
    'FILE_LEVEL': logging.INFO,
    'TO_FILE': False
}


class _CleanFormatter(logging.Formatter):
    """Formatter that shows clean messages for INFO and prefixed for warnings/errors."""

    def format(self, record):
        if record.levelno == logging.INFO:
            return record.getMessage()
        elif record.levelno == logging.WARNING:
            return f"[WARNING] {record.getMessage()}"
        elif record.levelno >= logging.ERROR:
            return f"[ERROR] {record.getMessage()}"
        return record.getMessage()


def setup_logger(name: str = __name__, to_file: bool = LOG_CONFIG['TO_FILE'],
                 log_dir: Path = None) -> logging.Logger:
    """
    Set up and configure the package logger.

    Args:
        name: Logger name (typically __name__)
        to_file: Whether to log to file
        log_dir: Directory for log files (defaults to OUT_PATH)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_CONFIG['ROOT_LEVEL'])

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with clean formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_CONFIG['CONSOLE_LEVEL'])
    console_handler.setFormatter(_CleanFormatter())
    logger.addHandler(console_handler)

    # File handler (optional) — always use timestamped format in files
    if to_file:
        log_dir = log_dir or OUT_PATH
        log_file = log_dir / 'simkit.log'
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(LOG_CONFIG['FILE_LEVEL'])
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(file_handler)

    return logger


# Initialize package logger
logger = setup_logger()

# Import main classes
from .project import Project
from .simulation import Simulation
from .slurm import Slurm
from .local import Local
from .util import copy_file, retry, RetrySignal


def load_json(filename: str) -> dict:
    """
    Load data from a JSON file.
    
    Args:
        filename: Path to JSON file
        
    Returns:
        Parsed JSON data as dictionary
    """
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


__all__ = [
    'Project',
    'Simulation', 
    'Slurm',
    'Local',
    'logger',
    'load_json',
    'copy_file',
    'retry',
    'RetrySignal',
    'OUT_PATH',
    'LOG_CONFIG'
]