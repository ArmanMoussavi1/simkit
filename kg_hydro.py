# Import required libraries
import sys
import shutil
from random import randint
import numpy as np
import pandas as pd

# Append custom module path
sys.path.append('/home/amp4121/')
from simkit import Project, Simulation, Slurm, Local, logger
import logging

# Configure logging level if desired
logger.setLevel(logging.INFO)


# Define resource configurations for Slurm jobs

resources_short = {
    "nodes": f"{NODES}",
    "ntasks": f"{NTASKS}",
    "partition": "short",
    "account": "p32439",
    "time": "1:30:00",
    "mem": "10G",
}

resources_normal = {
    "nodes": f"{NODES}",
    "ntasks": f"{NTASKS}",
    "partition": "normal",
    "account": "p32439",
    "time": "16:00:00",
    "mem": "60G",
}

# Define executable configuration for LAMMPS
executable = {
    "command": "/home/amp4121/lammps2022Apr/build_quartic/lmp -i",
    "dependency": "mpi/openmpi-4.1.1-gcc.10.2.0 gcc/11.2.0 hdf5/1.10.8-openmpi-3.1.3-gcc-8.4.0"
}

# Main simulation function
def simulation(work_base):
    # Initialize project
    task = "simulation"
    project = Project(name='project', work_base=work_base, task=task)
    slurm = Slurm(project=project, resources=resources_short)

    ##############################################################################################################
    ##############################################################################################################

    # Initial condition equilibration simulations

    generation=Simulation(project=project,name='generation',input='./input_scripts/generation.inp',data=f'./input_scripts/initial_config.data')
    variables={
        "-var datafile": f'./simulation_inputs/initial_config.data',
        "-var info_save": '100000',
        "-var ts": f'0.001',
        "-var steps": '1000000',
        "-var dump_file": './generation/trajectory/dump.txt',
        "-var restart_data": "./generation/restart/restart.data"
    }
    generation.load_variables(variables)


    ##############################################################################################################
    ##############################################################################################################

    # Mix simulation
    mix = Simulation(project=project, name='mix', input='./input_scripts/mix.inp')
    mix.load_variables({
        "-var datafile": './generation/restart/restart.data',
        "-var info_save": '200000',
        "-var ts": f'{time_step}',
        "-var steps": '2000000',
        "-var dump_file": './mix/trajectory/dump.txt',
        "-var restart_data": "./mix/restart/restart.data"
    })




    ##############################################################################################################
    ##############################################################################################################
    ##############################################################################################################
    ##############################################################################################################
    ##############################################################################################################
    ##############################################################################################################
    
    # Submit jobs to Slurm
    force_build = True

    # project.create(new_folder=True)


    # # ##############################################################################################################


    # #-------------- SUBMIT: Generation ------------------#

    # generation.create(new_folder=True,force=force_build)
    # slurm.submit(generation,run=True,dependency=None,executable=executable, resources=resources_more_short)
    
    
    # # -------------- SUBMIT: Mix ------------------#
    
    # mix.create(new_folder=True, force=force_build)
    # slurm.submit(mix, run=True, dependency=generation, executable=executable, resources=resources_more_short)



#############################################################
#############################################################
# Run the simulation

simulation(f"implicit_sol_pluronic_ABA_u{num_unimers}_olig{num_oligomers}_rp{num_blocks_olig}")
