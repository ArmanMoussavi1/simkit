"""
Local job execution module for SimKit.

Handles creation of execution scripts for local (non-SLURM) runs.

Authors: Arman Moussavi, Zhenghao Wu
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from simkit import logger
from .project import Project
from .simulation import Simulation


class Local:
    """
    Manages local job execution for MD simulations (non-SLURM).
    
    Creates execution scripts for running simulations locally.
    """
    
    def __init__(self, project: Optional[Project] = None,
                 resources: Optional[Dict[str, Any]] = None):
        """
        Initialize local execution manager.
        
        Args:
            project: Project instance
            resources: Dictionary of execution parameters
                      (e.g., {'cores': 4, 'gpus': 1})
        """
        self.project = project
        self.resources = resources or {}
        
    def create_execution_file(self, sim: Simulation,
                            executable: Dict[str, str],
                            resources: Optional[Dict[str, Any]] = None) -> None:
        """
        Create execution script for local simulation run.
        
        Args:
            sim: Simulation instance
            executable: Dictionary with 'command' and 'dependency' keys
            resources: Execution resources (overrides instance resources)
        """
        resources = resources or self.resources
        
        if not resources:
            logger.warning("No resources specified, using defaults")
            resources = {'cores': 4}
            
        submission_dir = sim.taskpath / "simulations" / sim.sim_name / "submission_files"
        exec_file = submission_dir / f"{sim.simid}.sh"
        
        with open(exec_file, 'w') as f:
            f.write("#!/bin/bash -x\n\n")
            
            # Load modules/dependencies if specified
            if 'dependency' in executable and executable['dependency']:
                f.write("# Load required modules\n")
                f.write(f"module purge\n")
                f.write(f"module load {executable['dependency']}\n\n")
                
            # Build command with variables
            var_str = ""
            if sim.has_variables:
                var_str = " ".join(f"{key} {value}" for key, value in sim.variables.items())
                
            # File paths
            screen_path = f"./{sim.sim_name}/screen/{sim.simid}.screen"
            log_path = f"./{sim.sim_name}/log/{sim.simid}.log"
            input_file = os.path.basename(sim.input_file)
            
            # Execution command
            cores = resources.get('cores', 1)
            cmd = f"{executable['command']} ./simulation_inputs/{input_file}"
            
            if var_str:
                cmd += f" {var_str}"
            cmd += f" -log {log_path} > {screen_path}"
            
            f.write(f"# Execute simulation\n")
            f.write(f"cd {sim.taskpath}/simulations\n")
            f.write(cmd + "\n")
            
        # Make script executable
        os.chmod(exec_file, 0o755)
        logger.info(f"Created execution file: {exec_file}")
        
    def create_execution_script(self, sim: Simulation,
                               dependent_sim: Optional[Simulation] = None) -> None:
        """
        Create wrapper script to execute the simulation.
        
        Args:
            sim: Simulation instance
            dependent_sim: Optional simulation that should complete first
        """
        script_dir = sim.taskpath / "simulations" / "submission_scripts"
        script_file = script_dir / f"{sim.simid}_local.sh"
        
        with open(script_file, 'w') as f:
            f.write("#!/bin/bash -x\n")
            f.write(f"cd {sim.taskpath}/simulations\n\n")
            
            if dependent_sim is not None:
                f.write(f"# Wait for dependency: {dependent_sim.simid}\n")
                f.write(f"# Note: Manual coordination required for local runs\n\n")
                
            exec_file = f"./{sim.sim_name}/submission_files/{sim.simid}.sh"
            f.write(f"ExecFile={exec_file}\n")
            f.write("test -e ${ExecFile}\n")
            f.write('if [ "$?" -eq "0" ]; then\n')
            f.write("    bash ${ExecFile}\n")
            f.write("else\n")
            f.write("    echo 'Execution file not found'\n")
            f.write("    exit 1\n")
            f.write("fi\n")
            
        # Make script executable
        os.chmod(script_file, 0o755)
        logger.info(f"Created execution script: {script_file}")
        
    def execute(self, sim: Simulation, run: bool = False) -> None:
        """
        Execute the simulation locally.
        
        Args:
            sim: Simulation instance
            run: If True, actually execute; if False, just prepare
        """
        script_dir = sim.taskpath / "simulations" / "submission_scripts"
        script_file = f"{sim.simid}_local.sh"
        cmd = f"bash {script_dir}/{script_file}"
        
        if run:
            logger.info(f"Executing locally: {sim.simid}")
            result = os.system(cmd)
            if result == 0:
                logger.info(f"Execution completed successfully: {sim.simid}")
            else:
                logger.error(f"Execution failed with code {result}")
        else:
            logger.info(f"Dry run - would execute: {cmd}")
            
    def submit(self, sim: Simulation, run: bool = False,
              dependency: Optional[Simulation] = None,
              executable: Optional[Dict[str, str]] = None,
              resources: Optional[Dict[str, Any]] = None) -> None:
        """
        Complete execution workflow: create scripts and run locally.
        
        Args:
            sim: Simulation instance
            run: If True, actually execute; if False, just prepare
            dependency: Optional simulation dependency
            executable: Dictionary with 'command' and 'dependency' keys
            resources: Execution resources
        """
        if executable is None:
            raise ValueError("executable dictionary must be provided")
            
        self.create_execution_file(sim, executable, resources)
        self.create_execution_script(sim, dependent_sim=dependency)
        self.execute(sim, run=run)