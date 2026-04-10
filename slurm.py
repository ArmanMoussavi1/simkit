"""
SLURM job submission and management module for SimKit.

Handles creation of SLURM submission scripts and job submission.

Authors: Arman Moussavi, Zhenghao Wu
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from simkit import logger
from .project import Project
from .simulation import Simulation


class Slurm:
    """
    Manages SLURM job submission for MD simulations.
    
    Creates submission scripts and handles job dependencies.
    """
    
    def __init__(self, project: Optional[Project] = None, 
                 resources: Optional[Dict[str, Any]] = None):
        """
        Initialize SLURM manager.
        
        Args:
            project: Project instance
            resources: Dictionary of SLURM resource parameters
                      (e.g., {'nodes': 1, 'ntasks': 16, 'time': '24:00:00'})
        """
        self.project = project
        self.resources = resources or {}
        
    def detect_job_state(self, job_name: str, start_date: Optional[str] = None) -> int:
        """
        Detect the state of a SLURM job.
        
        Args:
            job_name: Name of the job to check
            start_date: Optional start date for sacct query
            
        Returns:
            0: RUNNING
            1: COMPLETED
            2: PENDING
            Exits on FAILED
        """
        date_str = start_date or ""
        cmd = f"sacct {date_str} --name {job_name} --format State"
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                shell=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error checking job state: {stderr}")
                return -1
                
            status = stdout.split()[2] if len(stdout.split()) > 2 else "UNKNOWN"
            
            status_map = {
                "RUNNING": 0,
                "COMPLETED": 1,
                "PENDING": 2
            }
            
            if status == "FAILED":
                logger.error(f"Job {job_name} FAILED!")
                sys.exit(1)
                
            return status_map.get(status, -1)
            
        except Exception as e:
            logger.error(f"Error detecting job state: {e}")
            return -1
            
    def create_submission_file(self, sim: Simulation, 
                              executable: Dict[str, str],
                              resources: Optional[Dict[str, Any]] = None) -> None:
        """
        Create SLURM submission script for a simulation.
        
        Args:
            sim: Simulation instance
            executable: Dictionary with 'command' and 'dependency' (module) keys
            resources: SLURM resources (overrides instance resources if provided)
        """
        resources = resources or self.resources
        
        if not resources:
            logger.warning("No SLURM resources specified, using defaults")
            resources = {'ntasks': 16, 'time': '24:00:00'}
            
        submission_dir = sim.taskpath / "simulations" / sim.sim_name / "submission_files"
        submission_file = submission_dir / f"{sim.simid}.sub"
        
        with open(submission_file, 'w') as f:
            # Shebang and SLURM directives
            f.write("#!/bin/bash -x\n")
            
            for key, value in resources.items():
                f.write(f"#SBATCH --{key} {value}\n")
                
            # Output and job name
            f.write(f"#SBATCH --output ./{sim.sim_name}/submission_files/cluster_out/out_{sim.simid}.o\n")
            f.write(f"#SBATCH --job-name {sim.simid}\n\n")
            
            # Module loading
            f.write("module purge\n")
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
            ntasks = resources.get('ntasks', 1)
            cmd = f"mpirun -np {ntasks} {executable['command']} ./simulation_inputs/{input_file}"
            
            if var_str:
                cmd += f" {var_str}"
            cmd += f" -log {log_path} > {screen_path}"
            
            f.write(cmd + "\n")
            
        logger.debug(f"Created submission file: {submission_file}")
        
    def _get_running_job_id(self, sim: Simulation) -> Optional[str]:
        """
        Query squeue for a currently running or pending job by name.

        Returns the job ID string if found, or None if the job is not in the
        queue (already completed, not yet submitted, etc.).
        """
        cmd = f"squeue --noheader --format=%i --name {sim.simid}"
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            job_id = result.stdout.strip().split('\n')[0].strip()
            return job_id if job_id else None
        except Exception as e:
            logger.debug(f"squeue query failed: {e}")
            return None

    def create_submission_script(self, sim: Simulation,
                                 dependent_sim: Optional[Simulation] = None) -> Optional[str]:
        """
        Create shell script to submit the job.

        The dependency job ID is resolved *now* via squeue.  If the dependency
        is not currently in the queue (already finished, or never submitted in
        this session), the script submits without a dependency rather than
        producing a broken ``--dependency=afterok:`` flag.

        Args:
            sim: Simulation instance
            dependent_sim: Optional simulation that must complete first

        Returns:
            The resolved dependency job ID if one was found, else None.
        """
        script_dir = sim.taskpath / "simulations" / "submission_scripts"
        script_file = script_dir / f"{sim.simid}.sh"

        # Resolve dependency at Python level — not inside the shell script
        dep_job_id: Optional[str] = None
        if dependent_sim is not None:
            dep_job_id = self._get_running_job_id(dependent_sim)
            if dep_job_id:
                logger.debug(
                    f"Dependency resolved: {dependent_sim.simid} → job {dep_job_id}"
                )
            else:
                logger.debug(
                    f"Dependency '{dependent_sim.simid}' not found in queue; "
                    "submitting without dependency"
                )

        with open(script_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f"cd {sim.taskpath}/simulations\n\n")

            sub_file = f"./{sim.sim_name}/submission_files/{sim.simid}.sub"
            f.write(f'SubFile="{sub_file}"\n')
            f.write('if [ ! -e "$SubFile" ]; then\n')
            f.write("    echo '[ERROR] Submission file not found: $SubFile'\n")
            f.write("    exit 1\n")
            f.write("fi\n\n")

            if dep_job_id:
                f.write(f"sbatch --dependency=afterok:{dep_job_id} ${{SubFile}}\n")
            else:
                f.write("sbatch ${SubFile}\n")

        os.chmod(script_file, 0o755)
        logger.debug(f"Created submission script: {script_file}")
        return dep_job_id
        
    def submit_job(self, sim: Simulation, run: bool = False) -> Optional[str]:
        """
        Submit the job to SLURM.

        Args:
            sim: Simulation instance
            run: If True, actually submit the job; if False, just prepare

        Returns:
            The SLURM job ID string on success, or None on dry-run / failure.
        """
        script_dir = sim.taskpath / "simulations" / "submission_scripts"
        script_file = f"{sim.simid}.sh"
        cmd = f"bash {script_dir}/{script_file}"

        if not run:
            logger.debug(f"Dry run — would execute: {cmd}")
            return None

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # sbatch prints: "Submitted batch job 12345"
            output = result.stdout.strip()
            job_id = output.split()[-1] if output else None
            logger.debug(f"sbatch output: {output}")
            return job_id
        else:
            logger.error(
                f"Job submission failed (exit {result.returncode}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
            return None
            
    def submit(self, sim: Simulation, run: bool = False,
              dependency: Optional[Simulation] = None,
              executable: Optional[Dict[str, str]] = None,
              resources: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Complete submission workflow: create scripts and submit job.

        Args:
            sim: Simulation instance
            run: If True, actually submit; if False, just prepare scripts only
            dependency: Optional simulation that must complete before this one
            executable: Dictionary with 'command' and 'dependency' keys
            resources: SLURM resources (overrides instance defaults)

        Returns:
            SLURM job ID string if submitted, None on dry-run or failure.
        """
        if executable is None:
            raise ValueError("executable dictionary must be provided")

        self.create_submission_file(sim, executable, resources)
        dep_job_id = self.create_submission_script(sim, dependent_sim=dependency)
        job_id = self.submit_job(sim, run=run)

        # Print a clean one-line submission summary
        if run:
            if job_id:
                dep_note = f"  (after job {dep_job_id})" if dep_job_id else ""
                print(f"  Submitted  {sim.sim_name:<20} → job {job_id}{dep_note}")
            else:
                print(f"  [ERROR] Submission failed for {sim.sim_name}")
        else:
            dep_note = f"  (would depend on job {dep_job_id})" if dep_job_id else ""
            print(f"  [dry-run]  {sim.sim_name:<20} → scripts prepared{dep_note}")

        return job_id