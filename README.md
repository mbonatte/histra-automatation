# HiStrA Automation Toolkit

## Overview

HiStrA Automation is a Python toolkit for generating HiStrA Bridges simulation outputs for historical masonry bridge models.

This repository is focused on model/scenario generation, XML mutation, solver execution, and extraction of solver outputs into machine-readable scenario data. Exploratory notebooks, dashboards, plots, and downstream result analysis belong in a separate output-analysis repository.

## Layout

- `histra_automation/`: scenario generation, solver orchestration, and output extraction helpers.
- `modelxml/`: XML selectors, mutations, and file operations for HiStrA model files.
- `notebooks/`: generation workflow notebooks.
- `histra_models/`: local HiStrA input models, ignored by Git.

## License

This project is provided for research and automation purposes with HiStrA.
Check your organization's HiStrA license terms before redistributing or automating solver executions.
