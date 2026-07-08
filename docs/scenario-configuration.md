# Scenario Configuration

Scenarios are Python dictionaries that describe the model changes and analyses to run for one generated model copy.

## Scour Direction Modes

Foundation scour is configured inside each analysis entry, grouped by pier. Each pier can use one or more scour direction modes:

```python
scenario = {
    "Analysis": {
        "Scour_1": {
            "pier_1": {
                "left": 0.20,
                "upstream": 0.10,
            }
        }
    }
}
```

Supported modes are:

* `uniform`: removes the same total proportion from both length ends of the foundation.
* `left`: removes the selected proportion from the left-bank side along the foundation length.
* `right`: removes the selected proportion from the right-bank side along the foundation length.
* `upstream`: removes the selected proportion from the upstream side across the foundation width.
* `downstream`: removes the selected proportion from the downstream side across the foundation width.

The value must be between `0` and `1`. For example, `0.20` means 20 percent of the relevant foundation dimension.

For backward compatibility, a direct numeric value is treated as `uniform` scour:

```python
scenario = {
    "Analysis": {
        "Scour_1": {
            "pier_1": 0.20
        }
    }
}
```

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
