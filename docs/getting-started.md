# Getting Started with HiStrA Automation

This guide explains how to create a HiStrA Bridges model and prepare it to be executed through the HiStrA Automation Toolkit.

The workflow has four main stages:

1. Create and validate the base model in HiStrA Bridges.
2. Save the model as a reusable `.hrx` input file.
3. Configure the Python automation environment.
4. Define and run simulation scenarios.

---

## 1. Create the base model in HiStrA Bridges

Start by creating the structural model directly in HiStrA Bridges.

The base model should represent the reference bridge configuration before any automated parameter variation is applied. At this stage, the objective is not to create all scenarios manually, but to prepare a clean model that the automation can copy, modify, run, and post-process.

Before using the model in the automation workflow, check that:

* The geometry is complete.
* Materials are correctly assigned.
* Structural elements are correctly connected.
* Boundary conditions are defined.
* Loads and analyses are available.
* The model runs successfully inside HiStrA Bridges without automation.
* The names of materials, analyses, piers, layers, or other model entities are stable and easy to identify.

The automation modifies the model by searching and editing information inside the HiStrA model files. For that reason, clear and consistent naming is important.

---

## 2. Save the model file

After validating the model in HiStrA Bridges, save it as an `.hrx` file.

Place the model inside a local folder named:

```text
histra_models/
```

Example:

```text
histra_models/
  bridge_model.hrx
```

The `histra_models/` folder is intended for local model files and should not be committed to Git. This avoids storing large, private, or license-dependent HiStrA models inside the repository.

---

## 3. Configure the HiStrA solver path

The automation runs the HiStrA solver from Python.

Check the solver executable path in:

```text
histra_automation/run_program.py
```

The current structure expects a path similar to:

```python
EXE_PATH = r"C:\Program Files\Gruppo Sismica\HiStrA Bridges 2025.1.6\SolverHistra.exe"
```

Update this path if HiStrA Bridges is installed in a different location.

The toolkit can run the solver in two modes:

```python
mode="local"
```

or:

```python
mode="psexec"
```

Use `local` mode first unless there is a specific reason to use PsExec.

When using `psexec` mode, the terminal or Python environment may need to run with Administrator privileges.

---

## 4. Open the workflow notebook

Open the notebook:

```text
notebooks/run_model.ipynb
```

This notebook is the recommended starting point for running models while the project is still under development.

The notebook performs the following tasks:

* Sets the project root.
* Imports the automation functions.
* Defines unit conversions.
* Defines model parameters and scenarios.
* Calls the scenario runner.
* Executes the HiStrA solver for each scenario.

---

## 5. Define the input model path

In the notebook, define the path to the base `.hrx` model.

Example:

```python
input_path = r"histra_models/bridge_model.hrx"
```

The input model must be a valid HiStrA Bridges model file.

Before running automated scenarios, always test the base model manually in HiStrA Bridges.

---

## 6. Define scenario parameters

Scenarios are defined as Python dictionaries.

A scenario may include material changes, analysis definitions, scour conditions, or other model changes supported by the automation code.

Example structure:

```python
scenarios = [
    {
        "Analysis": {
            "Vert": {},
            "NewAnalysis": {}
        },
        "Materials": [
            {
                "Name": "Backfill",
                "fvk0d": 0.005,
                "CohesionSlidingHor": 0.005
            }
        ]
    }
]
```

In this example, the automation searches for the material named `Backfill` and modifies selected material properties before running the model.

The `Name` field must match the material name used in the HiStrA model.

### Analysis order and interface changes

Foundation interface changes are model-state changes. They are not stored only inside a single analysis.

This matters when running scour scenarios. For example, suppose `LiveLoad_1` has its initial stress state set from `Scour_1`. If the automation runs `Scour_2` before `LiveLoad_1`, the model interfaces have already been changed to the `Scour_2` condition. `LiveLoad_1` may still use the initial stress state from `Scour_1`, but the active interface properties in the model will be those left by `Scour_2`.

For that reason, run all analyses that belong to one scour condition before changing the interfaces for another scour condition. A safe order is:

```text
Scour_1
LiveLoad_1
Modal_1
Scour_2
LiveLoad_2
Modal_2
```

Avoid this order:

```text
Scour_1
Scour_2
LiveLoad_1
LiveLoad_2
```

The order of items in the scenario `Analysis` dictionary is therefore important. If an analysis must run with a specific scour/interface condition, place it immediately after that scour phase or repeat the same interface configuration for that analysis so it is applied again before the solver runs.

---

## 7. Generate multiple scenarios

The function `build_scenarios()` can be used to generate multiple scenarios from parameter ranges.

Example:

```python
from histra_automation.build_scenarios import build_scenarios

param_ranges = {
    "Masonry_Ehor": (1.0, 30.0),
    "Masonry_FmHor": (1.0, 40.0),
}

n_scenarios = 10

scenarios = build_scenarios(
    param_ranges=param_ranges,
    n_scenarios=n_scenarios,
    analysis="NewAnalysis"
)
```

Parameter names follow this structure:

```text
MaterialName_PropertyName
```

Example:

```text
Masonry_Ehor
Backfill_fvk0d
Foundation_Ehor
```

The part before the first underscore is interpreted as the material name. The part after the first underscore is interpreted as the property name.

---

## 8. Run the scenarios

Import the runner:

```python
from histra_automation.run_scenario import run_scenario
```

A simple loop can run all scenarios:

```python
for i, scenario in enumerate(scenarios):
    run_scenario(
        input_path=input_path,
        scenario=scenario,
        i=i,
        mode="local",
        timeout=360
    )
```

Each scenario creates a temporary copy of the base model, modifies it, runs the HiStrA solver, extracts the results, and then deletes the temporary files.

To inspect the generated model files after a run, disable cleanup:

```python
run_scenario(
    input_path=input_path,
    scenario=scenario,
    i=0,
    mode="local",
    timeout=360,
    cleanup=False
)
```

Cleanup is enabled by default. Use `cleanup=False` only when you want to keep the generated scenario model and results files for debugging.

---

## 9. Run scenarios in parallel

The notebook also shows a parallel execution pattern using `ThreadPoolExecutor`.

Example:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from histra_automation.processing_steps import prepare_model
from histra_automation.run_scenario import run_scenario

def run_model(input_path, scenarios, mode="local", timeout=360, max_workers=4, **kwargs):
    prepare_model(input_path)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        for i, scenario in enumerate(scenarios):
            futures.append(
                executor.submit(
                    run_scenario,
                    input_path,
                    scenario,
                    i,
                    mode,
                    timeout,
                    **kwargs
                )
            )

        for future in as_completed(futures):
            future.result()
```

Use parallel execution carefully. The recommended number of workers depends on:

* the size of the model,
* available CPU and RAM,
* the HiStrA license behavior,
* solver stability,
* and whether multiple solver instances can run safely on the same machine.

Start with:

```python
max_workers = 1
```

Then increase gradually.

---

## 10. Check outputs

After each scenario, the automation should extract the solver results into machine-readable data.

The exact output format depends on the current implementation of the post-processing functions.

Typical information to check after a run includes:

* whether the solver completed successfully,
* whether the temporary `.hrx` copy was deleted or intentionally kept with `cleanup=False`,
* whether the `.Results` folder was generated,
* whether the expected result files were extracted,
* and whether the scenario data was saved.

---

## 11. Troubleshooting

### Model not found

Check that the input path points to an existing `.hrx` file.

```python
input_path = r"histra_models/bridge_model.hrx"
```

### Solver path is wrong

Check `EXE_PATH` in:

```text
histra_automation/run_program.py
```

Update it to match the installed HiStrA Bridges version.

### PsExec requires Administrator privileges

If using:

```python
mode="psexec"
```

run VS Code, Jupyter, or the terminal as Administrator.

Alternatively, use:

```python
mode="local"
```

### Scenario runs manually but fails in automation

Check that the names used in the scenario dictionary match the names inside the HiStrA model.

For example, this scenario requires a material named `Backfill`:

```python
{
    "Materials": [
        {
            "Name": "Backfill",
            "fvk0d": 0.005
        }
    ]
}
```

If the material is named differently in the HiStrA model, the automation may not find it.

### Solver timeout

Increase the timeout:

```python
run_scenario(
    input_path=input_path,
    scenario=scenario,
    i=0,
    mode="local",
    timeout=900
)
```

### Temporary files remain after a failed run

The automation attempts to delete temporary model copies after each scenario. If files remain, close HiStrA Bridges and delete temporary files manually from the model folder.

---

## Recommended workflow

For a new model, follow this order:

1. Create the model in HiStrA Bridges.
2. Run it manually in HiStrA Bridges.
3. Save the model as `.hrx`.
4. Copy it to `histra_models/`.
5. Open `notebooks/run_model.ipynb`.
6. Set `input_path`.
7. Define one simple scenario.
8. Run with `max_workers=1`.
9. Check the result.
10. Add more parameters.
11. Increase the number of scenarios.
12. Use parallel execution only after the single-scenario workflow is stable.
