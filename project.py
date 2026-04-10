"""
Project management module for SimKit.

Handles creation and organization of project directory structures.

Authors: Arman Moussavi, Zhenghao Wu
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Optional

from simkit import logger


class Project:
    """
    Manages project directory structure for MD simulations.
    
    Creates hierarchical directory structure: name/work_base/task/simulations/
    """
    
    def __init__(self, name: str = 'test', work_base: Optional[str] = None, 
                 task: Optional[str] = None):
        """
        Initialize a Project.
        
        Args:
            name: Project name
            work_base: Work base directory (defaults to name)
            task: Task directory (defaults to name)
        """
        self.name = name
        self.work_base = work_base or name
        self.task = task or name
        
    @property
    def taskpath(self) -> Path:
        """Get the full path to the task directory."""
        return Path.cwd() / self.name / self.work_base / self.task

    @property
    def project_path(self) -> Path:
        """Alias for taskpath — full path to the project task directory."""
        return self.taskpath

    @property
    def simulations_path(self) -> Path:
        """Path to the simulations subdirectory."""
        return self.taskpath / "simulations"
    
    def create(self, force: bool = False, new_folder: bool = True) -> None:
        """
        Create project directory structure.
        
        Args:
            force: If True, automatically delete existing directories
            new_folder: If True, create new directory structure
        """
        if not new_folder:
            logger.info(f"Restarting project: {self.name}")
            return
            
        path = self.taskpath
        
        if path.exists():
            response = 'y' if force else self._prompt_user_for_deletion(path)
            
            if response.lower() in ['y', 'yes']:
                self._remove_directory(path)
                self._create_directory_structure(path)
            elif response.lower() in ['n', 'no']:
                logger.warning(f"Project path already exists: {path}")
                logger.info("Exiting to avoid overwriting existing data")
                sys.exit(0)
            else:
                logger.error("Invalid input. Please enter 'y' or 'n'")
                sys.exit(1)
        else:
            self._create_directory_structure(path)
            
    def _prompt_user_for_deletion(self, path: Path) -> str:
        """Prompt user to confirm directory deletion."""
        return input(f"{path} already exists. Delete and create new? (y/n): ")
    
    def _remove_directory(self, path: Path) -> None:
        """Safely remove directory and wait for completion."""
        logger.info(f"Removing directory: {path}")
        shutil.rmtree(path)
        time.sleep(1)  # Brief wait to ensure filesystem sync
        
    def _create_directory_structure(self, path: Path) -> None:
        """Create the full directory structure for simulations."""
        logger.info(f"Creating project structure: {path}")
        
        # Create main directories
        path.mkdir(parents=True, exist_ok=True)
        
        # Create simulation subdirectories
        sim_path = path / "simulations"
        (sim_path / "simulation_inputs").mkdir(parents=True, exist_ok=True)
        (sim_path / "submission_scripts").mkdir(parents=True, exist_ok=True)
        
        logger.debug("Project structure created successfully")
        
    def __repr__(self) -> str:
        return f"Project(name='{self.name}', work_base='{self.work_base}', task='{self.task}')"