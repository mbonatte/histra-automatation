# HiStrA Automation Toolkit

## Overview

HiStrA Automation is a Python toolkit for generating HiStrA Bridges simulation outputs for historical masonry bridge models.

This repository is focused on model/scenario generation, XML mutation, solver execution, and extraction of solver outputs into machine-readable scenario data. Exploratory notebooks, dashboards, plots, and downstream result analysis belong in a separate output-analysis repository.

## Start here

- [Getting started](docs/getting-started.md)
- [HiStrA model requirements](docs/histra-model-requirements.md)
- [Scenario configuration](docs/scenario-configuration.md)
- [Running simulations](docs/running-simulations.md)
- [Troubleshooting](docs/troubleshooting.md)

## Repository layout

- `histra_automation/`: scenario generation, solver orchestration, and output extraction.
- `modelxml/`: XML selectors, mutations, and file operations for HiStrA model files.
- `notebooks/`: example workflow notebooks.
- `histra_models/`: local HiStrA input models, ignored by Git.

## License

This project is provided for research and automation purposes with HiStrA.
Check your organization's HiStrA license terms before redistributing or automating solver executions.
