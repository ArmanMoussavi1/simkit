#!/usr/bin/env python3
"""
SimKit: Multi-Stage LAMMPS Simulation Workflow

This script sets up and submits a two-stage molecular dynamics workflow:
1. Initial configuration generation
2. Mixing/equilibration using restart from step 1

Uses SimKit for project management and SLURM job submission.
"""

import sys
import logging

# Add custom module path
sys.path.append('/home/amp4121/')
from simkit import Project, Simulation, Slurm, logger

# Configure logging
logger.setLevel(logging.INFO)


# =============================================================================
# Configuration Parameters (User-Editable)
# =============================================================================

# System composition
num_unimers = 100        # Example values — set as needed
num_oligomers = 20
num_blocks_olig = 3
time_step = 0.001        # Time step in LAMMPS units

# SLURM Resource Configurations
NODES = 1
NTASKS = 16

resources_short = {
    "nodes": NODES,
    "ntasks": NTASKS,
    "partition": "short",
    "account": "p32439",
    "time": "1:30:00",
    "mem": "10G",
}

resources_normal = {
    "nodes": NODES,
    "ntasks": NTASKS,
    "partition": "normal",
    "account": "p32439",
    "time": "16:00:00",
    "mem": "60G",
}

# LAMMPS Executable
executable = {
    "command": "/home/amp4121/lammps2022Apr/build_quartic/lmp -i",
    "dependency": "mpi/openmpi-4.1.1-gcc.10.2.0 gcc/11.2.0 hdf5/1.10.8-openmpi-3.1.3-gcc-8.4.0"
}

# Force rebuild of directories (set to False to preserve existing)
FORCE_BUILD = True


# =============================================================================
# Main Simulation Workflow Function
# =============================================================================

def run_implicit_solvent_workflow():
    """Set up and submit a two-stage Pluronic simulation in implicit solvent."""
    
    print("\n" + "="*70)
    print("Starting Implicit Solvent Pluronic Simulation Workflow")
    print("="*70 + "\n")

    # -------------------------------------------------------------------------
    # Define project
    # -------------------------------------------------------------------------
    work_base = f"implicit_sol_pluronic_ABA_u{num_unimers}_olig{num_oligomers}_rp{num_blocks_olig}"
    project = Project(
        name='project',
        work_base=work_base,
        task='simulation'
    )

    # Create project structure (only if not exists or force=True)
    project.create(force=FORCE_BUILD, new_folder=True)
    print(f"Project created: {project.project_path}")

    # -------------------------------------------------------------------------
    # Initialize SLURM handler
    # -------------------------------------------------------------------------
    slurm = Slurm(project=project, resources=resources_short)

    # -------------------------------------------------------------------------
    # Stage 1: Generation Simulation
    # -------------------------------------------------------------------------
    print("\nSetting up Stage 1: Initial Configuration Generation")

    generation = Simulation(
        project=project,
        name='generation',
        input_file='./input_scripts/generation.inp',
        data='./input_scripts/initial_config.data',
        copy_input=True,
        copy_data=True
    )

    generation.load_variables({
        "-var datafile": "./simulation_inputs/initial_config.data",
        "-var info_save": "100000",
        "-var ts": "0.001",
        "-var steps": "1000000",
        "-var dump_file": "./generation/trajectory/dump.txt",
        "-var restart_data": "./generation/restart/restart.data"
    })

    generation.create(force=FORCE_BUILD, new_folder=True)
    print(f"  → Generation simulation prepared: {generation.sim_name}")

    # -------------------------------------------------------------------------
    # Stage 2: Mix Simulation (depends on generation restart)
    # -------------------------------------------------------------------------
    print("\nSetting up Stage 2: Mixing/Equilibration")

    mix = Simulation(
        project=project,
        name='mix',
        input_file='./input_scripts/mix.inp',
        copy_input=True,
        copy_data=False  # Uses restart from generation
    )

    mix.load_variables({
        "-var datafile": "./generation/restart/restart.data",
        "-var info_save": "200000",
        "-var ts": f"{time_step}",
        "-var steps": "2000000",
        "-var dump_file": "./mix/trajectory/dump.txt",
        "-var restart_data": "./mix/restart/restart.data"
    })

    mix.create(force=FORCE_BUILD, new_folder=True)
    print(f"  → Mix simulation prepared: {mix.sim_name}")

    # -------------------------------------------------------------------------
    # Submit Jobs with Dependency
    # -------------------------------------------------------------------------
    print("\nSubmitting jobs to SLURM...")

    # Submit generation job
    job_gen = slurm.submit(
        sim=generation,
        run=True,                    # Set to False to only prepare scripts
        dependency=None,
        executable=executable,
        resources=resources_short
    )

    # Submit mix job, dependent on generation completing first
    job_mix = slurm.submit(
        sim=mix,
        run=True,
        dependency=generation,
        executable=executable,
        resources=resources_normal
    )

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "="*70)
    print("Workflow Summary")
    print("="*70)
    print(f"Project Path: {project.project_path}")
    print(f"Simulation Directory: {project.simulations_path}")
    print("\nStages:")
    print(f"  1. {generation.sim_name} → Job ID: {job_gen}")
    print(f"  2. {mix.sim_name}       → Job ID: {job_mix} (after stage 1)")
    print("\nTo monitor: use `squeue -u $USER`")
    print("To cancel: `scancel <job_id>`")
    print("="*70 + "\n")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == '__main__':
    run_implicit_solvent_workflow()