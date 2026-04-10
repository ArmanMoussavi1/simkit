"""
Simulation management module for SimKit.

Handles creation and configuration of individual MD simulations.

Authors: Arman Moussavi, Zhenghao Wu
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import Optional, Dict, Union

from .project import Project
from .util import copy_file
from simkit import logger


class Simulation:
    """
    Manages individual MD simulation setup and configuration.
    
    Creates simulation-specific directories and handles input file management.
    """
    
    def __init__(self, project: Project, name: str, input_file: Optional[str] = None,
                 copy_input: bool = True, data: Optional[str] = None,
                 copy_data: bool = True, **kwargs):
        """
        Initialize a Simulation.

        Args:
            project: Parent Project instance
            name: Simulation name
            input_file: Path to input file for simulation (also accepted as ``input``)
            copy_input: Whether to copy input file to simulation directory
            data: Optional data file path
            copy_data: Whether to copy data file to simulation directory
        """
        # Support legacy ``input`` keyword used in older scripts
        if input_file is None and 'input' in kwargs:
            input_file = kwargs.pop('input')
        if kwargs:
            raise TypeError(f"Unexpected keyword arguments: {list(kwargs)}")
        if input_file is None:
            raise TypeError("input_file (or 'input') is required")

        if not isinstance(project, Project):
            raise TypeError("project must be a Project instance")
            
        self.project = project
        self.sim_name = name
        self.input_file = input_file
        self.data = data
        self.copy_input = copy_input
        self.copy_data = copy_data
        
        # Paths
        self.taskpath = project.taskpath
        self.simpath = self.taskpath / "simulations" / self.sim_name
        
        # Generate unique simulation ID
        self.simid = f"{self.sim_name}_{project.name}_{project.work_base}_{project.task}"
        
        # Variables for parameterized simulations
        self.variables: Dict[str, Union[str, int, float]] = {}
        self.has_variables = False
        
    def load_variables(self, variables: Dict[str, Union[str, int, float]]) -> None:
        """
        Load variables for parameterized simulations.
        
        Args:
            variables: Dictionary of variable names and values
        """
        self.variables = variables
        self.has_variables = len(self.variables) > 0
        logger.debug(f"Loaded {len(self.variables)} variables for {self.sim_name}")
        
    def _copy_simulation_input(self, filename: str) -> None:
        """
        Copy a file to the simulation inputs directory.
        
        Args:
            filename: Path to file to copy
        """
        if not os.path.isfile(filename):
            logger.error(f"Input file does not exist: {filename}")
            raise FileNotFoundError(f"Input file not found: {filename}")
            
        dest_file = os.path.basename(filename)
        dest_path = self.taskpath / "simulations" / "simulation_inputs" / dest_file
        copy_file(filename, str(dest_path))
        logger.debug(f"Copied input file: {filename} -> {dest_path}")
        
    def load_inputs(self, input_files: Union[str, list]) -> None:
        """
        Load and copy input files to simulation directory.
        
        Args:
            input_files: Single file path or list of file paths
        """
        if isinstance(input_files, list):
            logger.warning("List of input files not fully supported, using first file only")
            if input_files:
                self._copy_simulation_input(input_files[0])
        elif isinstance(input_files, str):
            self._copy_simulation_input(input_files)
        else:
            raise TypeError("input_files must be a string or list")
            
    def _create_simulation_directories(self) -> None:
        """Create all required subdirectories for the simulation."""
        directories = [
            "log",
            "restart", 
            "screen",
            "submission_files/cluster_out",
            "trajectory"
        ]
        
        for dir_name in directories:
            dir_path = self.simpath / dir_name
            dir_path.mkdir(parents=True, exist_ok=False)
            logger.debug(f"Created directory: {dir_path}")
            
        # Copy input files if requested
        if self.copy_input:
            self.load_inputs(self.input_file)
            
        if self.copy_data and self.data is not None:
            self.load_inputs(self.data)
            
    def create(self, force: bool = False, new_folder: bool = True) -> None:
        """
        Create simulation directory structure.
        
        Args:
            force: If True, automatically delete existing directories
            new_folder: If True, create new directory structure
        """
        if not new_folder:
            logger.info(f"Restarting simulation: {self.sim_name}")
            if self.copy_input:
                self.load_inputs(self.input_file)
            if self.copy_data and self.data is not None:
                self.load_inputs(self.data)
            return
            
        # Check if project directory exists
        if not self.taskpath.exists():
            logger.error("Project directories not created. Create project first.")
            raise RuntimeError("Project must be created before simulations")
            
        # Handle existing simulation directory
        if self.simpath.exists():
            response = 'y' if force else self._prompt_user_for_deletion()
            
            if response.lower() in ['y', 'yes']:
                logger.info(f"Removing existing simulation: {self.simpath}")
                shutil.rmtree(self.simpath)
                time.sleep(1)
                self._create_simulation_directories()
            elif response.lower() in ['n', 'no']:
                logger.warning(f"Simulation already exists: {self.simpath}")
                sys.exit(0)
            else:
                logger.error("Invalid input. Please enter 'y' or 'n'")
                sys.exit(1)
        else:
            self._create_simulation_directories()
            
        logger.debug(f"Simulation created successfully: {self.sim_name}")
        
    def _prompt_user_for_deletion(self) -> str:
        """Prompt user to confirm directory deletion."""
        return input(f"{self.simpath} already exists. Delete and create new? (y/n): ")
        
    def __repr__(self) -> str:
        return f"Simulation(name='{self.sim_name}', id='{self.simid}')"