# SimKit - Automated Molecular Dynamics Setup

A Python package for automating the setup and submission of molecular dynamics simulations on HPC clusters with SLURM scheduling or local execution.

**Authors:** Arman Moussavi, Zhenghao Wu

---

## About

**SimKit** is an updated and modernized version of [AutoMD](https://github.com/zwu27/automd), originally created by Zhenghao Wu. This project builds upon AutoMD's foundation with significant improvements to:

- Code structure and organization
- Error handling and validation
- Type hints and documentation
- Path handling (using `pathlib`)
- Logging system
- User experience

We are grateful to Zhenghao Wu for creating AutoMD and providing the foundation for this work.

---

## Features

- **Project Management**: Hierarchical directory structure organization
- **Simulation Setup**: Automated creation of simulation directories and input file management
- **SLURM Integration**: Generate and submit SLURM job scripts with dependencies
- **Local Execution**: Run simulations on local machines without SLURM
- **Parameterized Runs**: Easy setup of parameter sweeps
- **Workflow Management**: Chain simulations with dependencies
- **Error Handling**: Robust error checking and logging

## Installation

```bash
# Clone or copy the package
cd /path/to/your/packages
git clone <repository-url> simkit

# Or install in development mode
pip install -e /path/to/simkit
```

## Quick Start

```python
from simkit import Project, Simulation, Slurm

# 1. Create a project
project = Project(
    name='my_simulation',
    work_base='production',
    task='equilibration'
)
project.create()

# 2. Create a simulation
sim = Simulation(
    project=project,
    name='nvt_300K',
    input_file='/path/to/input.in',
    data='/path/to/data.data'
)
sim.create()

# 3. Submit to SLURM
slurm = Slurm(
    project=project,
    resources={
        'nodes': 1,
        'ntasks': 16,
        'time': '24:00:00'
    }
)

executable = {
    'command': 'lmp_mpi',
    'dependency': 'lammps/2023.08.02'
}

slurm.submit(sim, run=True, executable=executable)
```

## Directory Structure

SimKit creates the following directory structure:

```
project_name/
└── work_base/
    └── task/
        └── simulations/
            ├── simulation_inputs/      # Input files
            ├── submission_scripts/     # Job submission scripts
            └── simulation_name/
                ├── log/                # Log files
                ├── restart/            # Restart files
                ├── screen/             # Screen output
                ├── trajectory/         # Trajectory files
                └── submission_files/
                    └── cluster_out/    # SLURM output files
```

## Core Classes

### Project

Manages the overall project directory structure.

```python
project = Project(
    name='project_name',
    work_base='work_directory',  # Optional, defaults to name
    task='task_name'              # Optional, defaults to name
)
project.create(force=False, new_folder=True)
```

### Simulation

Manages individual simulation setup.

```python
sim = Simulation(
    project=project,
    name='simulation_name',
    input_file='/path/to/input.in',
    copy_input=True,
    data='/path/to/data.data',  # Optional
    copy_data=True
)
sim.create(force=False, new_folder=True)

# Add variables for parameterized runs
sim.load_variables({'-var': 'temperature', '300': ''})
```

### Slurm

Handles SLURM job submission.

```python
slurm = Slurm(
    project=project,
    resources={
        'nodes': 1,
        'ntasks': 16,
        'time': '24:00:00',
        'partition': 'standard',
        'mem': '32GB',
        'gres': 'gpu:1'  # For GPU jobs
    }
)

executable = {
    'command': 'lmp_mpi',           # Executable command
    'dependency': 'lammps/2023.08'  # Module to load
}

slurm.submit(
    sim=sim,
    run=False,              # Set True to actually submit
    dependency=None,        # Optional: another Simulation object
    executable=executable,
    resources=None          # Optional: override default resources
)
```

### Local

Handles local (non-SLURM) execution.

```python
local = Local(
    project=project,
    resources={'cores': 4}
)

local.submit(
    sim=sim,
    run=False,
    executable=executable
)
```

## Common Use Cases

### 1. Parameter Sweep

```python
project = Project(name='temp_sweep')
project.create()

temperatures = [250, 275, 300, 325, 350]
slurm = Slurm(project=project, resources={...})

for temp in temperatures:
    sim = Simulation(
        project=project,
        name=f'nvt_{temp}K',
        input_file='template.in'
    )
    sim.load_variables({'-var': 'temp', str(temp): ''})
    sim.create()
    slurm.submit(sim, run=True, executable=executable)
```

### 2. Workflow with Dependencies

```python
project = Project(name='workflow')
project.create()

# Create simulations
sim1 = Simulation(project=project, name='minimize', input_file='min.in')
sim2 = Simulation(project=project, name='equilibrate', input_file='eq.in')
sim3 = Simulation(project=project, name='production', input_file='prod.in')

for sim in [sim1, sim2, sim3]:
    sim.create()

slurm = Slurm(project=project, resources={...})

# Submit with dependencies
slurm.submit(sim1, run=True, executable=executable)
slurm.submit(sim2, run=True, dependency=sim1, executable=executable)
slurm.submit(sim3, run=True, dependency=sim2, executable=executable)
```

### 3. Restart Existing Simulation

```python
# Restart mode - doesn't recreate directories
project = Project(name='existing_project')
project.create(new_folder=False)

sim = Simulation(
    project=project,
    name='existing_sim',
    input_file='restart.in',
    copy_input=True
)
sim.create(new_folder=False)  # Copies new input, keeps directories
```

## Configuration

### Logging

```python
from simkit import logger
import logging

# Set logging level
logger.setLevel(logging.DEBUG)

# Enable file logging
from simkit import setup_logger
logger = setup_logger(to_file=True, log_dir='/path/to/logs')
```

### SLURM Resources

Common resource specifications:

```python
resources = {
    'nodes': 1,              # Number of nodes
    'ntasks': 16,            # Number of tasks/cores
    'ntasks-per-node': 16,   # Tasks per node
    'time': '24:00:00',      # Wall time (HH:MM:SS)
    'partition': 'standard', # Partition/queue name
    'mem': '32GB',           # Memory
    'mem-per-cpu': '2GB',    # Memory per CPU
    'gres': 'gpu:2',         # Generic resources (e.g., GPUs)
    'constraint': 'haswell', # Node constraints
    'account': 'project123'  # Account/allocation
}
```

## Best Practices

1. **Test First**: Use `run=False` to generate scripts without submitting
2. **Check Paths**: Verify input file paths exist before creating simulations
3. **Use Force Carefully**: `force=True` will delete existing directories
4. **Monitor Jobs**: Use `squeue` and `sacct` to check job status
5. **Organize Projects**: Use meaningful names for project/work_base/task hierarchy

## Troubleshooting

### Common Issues

**Input file not found**
```python
# Ensure full path or correct relative path
sim = Simulation(
    project=project,
    name='test',
    input_file=os.path.abspath('input.in')  # Use absolute path
)
```

**Module not available**
```python
# Check available modules: module avail
executable = {
    'command': 'lmp_mpi',
    'dependency': 'lammps/2023.08.02'  # Verify this exists
}
```

**Job not submitting**
```python
# Check SLURM resources match your cluster
# Run manually to debug:
cd /path/to/project/simulations
sh submission_scripts/sim_id.sh
```

## API Reference

See `example_usage.py` for comprehensive examples of all features.

## Acknowledgments

SimKit is built upon the excellent work of Zhenghao Wu's [AutoMD](https://github.com/zwu27/automd). We thank him for creating the original framework and making it available to the community.

## License

BSD License

## Authors

- **Arman Moussavi** - Primary author of SimKit updates
- **Zhenghao Wu** - Original author of AutoMD

## Contributing

Contributions welcome! Please ensure code follows the existing style and includes appropriate logging and type hints.
