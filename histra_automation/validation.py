import logging
from dataclasses import dataclass
from pathlib import Path

from modelxml.xmlio import read_xml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    message: str


class ModelValidationError(Exception):
    """Raised when a model preflight check finds a blocking issue."""

    def __init__(self, file_path, issues):
        self.file_path = file_path
        self.issues = issues
        messages = "\n".join(f"- [{issue.severity}] {issue.message}" for issue in issues)
        super().__init__(f"Model validation failed for {file_path}:\n{messages}")


def validate_model_file(file_path, analysis_names=None, strict=True):
    """Validate HRX consistency before running mesh/analyses."""
    root = read_xml(file_path)
    issues = validate_load_combinations(root, analysis_names=analysis_names)

    for issue in issues:
        if issue.severity == "error":
            logger.error(issue.message)
        else:
            logger.warning(issue.message)

    blocking = [issue for issue in issues if issue.severity == "error"]
    if strict and blocking:
        raise ModelValidationError(Path(file_path), blocking)

    return issues


def validate_load_combinations(root, analysis_names=None):
    analysis_filter = set(analysis_names or [])
    found_analysis_names = set()
    load_conditions = _load_conditions(root)
    load_condition_keys = set(load_conditions)
    load_condition_key_by_name = {
        attrs["Name"]: key
        for key, attrs in load_conditions.items()
        if attrs.get("Name")
    }
    combinations = {
        elem.get("Key"): elem
        for elem in root.iter("LoadCombination")
        if elem.get("Key")
    }

    issues = []

    for analysis in root.iter("Analysis"):
        analysis_name = analysis.get("Name", "")
        found_analysis_names.add(analysis_name)
        if analysis_filter and analysis_name not in analysis_filter:
            continue
        if analysis.get("TypeLoadDistribution") != "LoadCombination":
            continue

        combination_key = analysis.get("LoadCombinationKey")
        combination = combinations.get(combination_key)
        if combination is None:
            issues.append(ValidationIssue(
                "error",
                f"Analysis '{analysis_name}' references missing LoadCombination Key='{combination_key}'.",
            ))
            continue

        combination_name = combination.get("Name", "")
        row_columns = _load_combination_row_columns(combination)
        for row_key, columns in sorted(row_columns.items(), key=lambda item: _sort_key(item[0])):
            missing = sorted(load_condition_keys - columns, key=_sort_key)
            if missing:
                issues.append(ValidationIssue(
                    "error",
                    f"LoadCombination Key='{combination_key}' Name='{combination_name}' used by "
                    f"analysis '{analysis_name}' is missing ColumnKey(s) {', '.join(missing)} "
                    f"in RowKey='{row_key}'.",
                ))

        matching_condition_key = load_condition_key_by_name.get(combination_name)
        if matching_condition_key and not _has_active_column(combination, matching_condition_key):
            issues.append(ValidationIssue(
                "error",
                f"LoadCombination Key='{combination_key}' Name='{combination_name}' used by "
                f"analysis '{analysis_name}' has no active item for matching "
                f"ColumnKey='{matching_condition_key}'.",
            ))

    for missing_analysis in sorted(analysis_filter - found_analysis_names):
        issues.append(ValidationIssue(
            "error",
            f"Scenario references analysis '{missing_analysis}', but it is not present in the HRX file.",
        ))

    return issues


def _load_conditions(root):
    records = {}
    for elem in root.iter("LoadCondition"):
        key = elem.get("Id") or elem.get("Key")
        if key:
            records[key] = elem.attrib
    return records


def _load_combination_row_columns(load_combination):
    row_columns = {}
    for item in load_combination.iter():
        column_key = item.get("ColumnKey")
        if column_key is None:
            continue
        row_key = item.get("RowKey", "1")
        row_columns.setdefault(row_key, set()).add(column_key)
    return row_columns


def _has_active_column(load_combination, column_key):
    for item in load_combination.iter():
        if item.get("ColumnKey") != column_key:
            continue
        try:
            if float(item.get("Val", "0")) != 0:
                return True
        except ValueError:
            if item.get("Val"):
                return True
    return False


def _sort_key(value):
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value))
