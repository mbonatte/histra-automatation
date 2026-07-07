# Scenario Configuration

Scenarios are Python dictionaries that describe the model changes and analyses to run for one generated model copy.

## Analysis Order and Interface State

Foundation interface changes are persistent model-state changes. They are not local to a single analysis.

The HiStrA initial stress state controls the analysis dependency, but it does not automatically restore previous interface properties. If an interface change is made for a later scour phase, that interface state remains active until another interface update changes it.

For example, this order is unsafe:

```text
Scour_1
Scour_2
LiveLoad_1
LiveLoad_2
```

Even if `LiveLoad_1` uses `Scour_1` as its initial stress state, the interfaces have already been changed by `Scour_2`.

Prefer this order:

```text
Scour_1
LiveLoad_1
Modal_1
Scour_2
LiveLoad_2
Modal_2
```

All analyses that belong to a scour condition should run before changing the interfaces for the next scour condition.

In code, keep the `Analysis` dictionary ordered in the intended execution sequence:

```python
scenario = {
    "Analysis": {
        "Scour_1": {"pier_1": {"uniform": 0.20}},
        "LiveLoad_1": {},
        "Modal_1": {},
        "Scour_2": {"pier_1": {"uniform": 0.40}},
        "LiveLoad_2": {},
        "Modal_2": {},
    }
}
```

If an analysis must run with a specific interface condition, either place it immediately after the scour phase that sets that condition or repeat the same interface configuration for that analysis so the automation applies it again before running the solver.
