import logging
import time
from collections import OrderedDict
from datetime import datetime

from modelxml.ops import (
    run_copy_paste,
    run_set_model_points,
    run_update_material, 
    run_set_all_analyses_off, 
    run_set_analysis_on, 
    run_create_start_mesh_analysis, 
    run_update_foundation_ifaces,
    run_add_line_load,
    run_activate_line_load_condition,
)
from modelxml.xmlio import read_xml

from .save import save_scenario_info, save_outputs

from .run_program import run_program
from .validation import validate_model_file

# -------------------------------------------------------------------
# Configure logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)
LOAD_POSITION_KEY = "load_pos"

# -------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------

def generate_mesh(file, mode="local", timeout=200, **kwargs):
    file_name = file.split('\\')[-1]

    logger.info("Creating mesh analysis for file: %s", file_name)

    try:
        run_create_start_mesh_analysis(file)
        run_set_all_analyses_off(file)
        run_set_analysis_on(file, "StartMesh")

        logger.info("Running mesh analysis for file: %s", file_name)
        run_program(file, mode, timeout)

    except Exception as e:
        logger.exception("Error during mesh generation for %s: %s", file_name, e)
        raise
    else:
        logger.info("Mesh generation complete for file: %s", file_name)
    finally:
        try:
            run_set_all_analyses_off(file)
            logger.info("Analyses turned off after mesh step for file: %s", file_name)
        except Exception as cleanup_error:
            logger.exception(
                "Failed to turn analyses off after mesh step for %s: %s",
                file_name,
                cleanup_error,
            )

def prepare_model(file):
    logger.info("Preparing model for file: %s", file.split('\\')[-1])
    try:
        run_set_model_points(file)
    except Exception as e:
        logger.exception("Error while preparing model for %s: %s", file.split('\\')[-1], e)
        raise
    logger.info("Model preparation complete for file: %s", file.split('\\')[-1])

def pre_processing(input_path, scenario, xml_file, **kwargs):
    index = xml_file.split("_")[-1].split(".")[0]
    logger.info("Starting pre-processing for scenario index: %s", index)

    try:
        # Validate scenario metadata before mutating the copied model.
        _expand_analysis_requests(scenario["Analysis"])

        logger.info("Copying input: %s → %s", input_path.split('\\')[-1], xml_file.split('\\')[-1])
        run_copy_paste(input_path, out_path=xml_file)

        _add_requested_load_positions(xml_file, scenario["Analysis"])

        logger.info("Validating model file: %s", xml_file.split('\\')[-1])
        validate_model_file(xml_file, analysis_names=_scenario_analysis_names(scenario))

        logger.info("Updating materials for index %s", index)
        run_update_material(xml_file, scenario.get("Materials", []))

        generate_mesh(xml_file, **kwargs)

        save_scenario_info(scenario, xml_file)
        logger.info("Pre-processing finished for index %s", index)

    except Exception as e:
        logger.exception("Pre-processing failed for %s: %s", xml_file, e)
        raise

def processing(xml_file, scenario, mode="local", timeout=360, **kwargs):
    index = xml_file.split("_")[-1].split(".")[0]
    logger.info("Starting processing for index: %s", index)

    requested_analyses = _expand_analysis_requests(scenario["Analysis"])
    processing_started = time.perf_counter()
    timing = scenario.setdefault("Timing", {})
    timing["Analysis_Date"] = datetime.now().astimezone().isoformat(timespec="seconds")
    timing["Per_Analysis_Seconds"] = {}

    for analysis_name, interfaces in _analysis_run_queue(xml_file, requested_analyses):
        try:
            logger.info("Updating foundation interfaces for index %s", index)
            run_update_foundation_ifaces(xml_file, interfaces)
            
            logger.info("Running analysis '%s' for index %s", analysis_name, index)
            run_set_analysis_on(xml_file, analysis_name)
            analysis_started = time.perf_counter()
            run_program(xml_file, mode, timeout)
            timing["Per_Analysis_Seconds"][analysis_name] = round(
                time.perf_counter() - analysis_started, 3
            )
        
        except Exception as e:
            logger.exception("Processing failed for %s - %s: %s", index, analysis_name, e)
            raise

    timing["Total_Analysis_Seconds"] = round(time.perf_counter() - processing_started, 3)
    logger.info("Processing complete for index: %s", index)


def _analysis_run_queue(xml_file, requested_analyses):
    queue = OrderedDict()

    for analysis_name, interfaces in requested_analyses.items():
        root = read_xml(xml_file)
        for required_name in _missing_required_analyses(root, analysis_name):
            if required_name not in requested_analyses:
                logger.warning(
                    "Analysis '%s' was set to run because it is required by "
                    "analysis '%s', even though the user did not request it.",
                    required_name,
                    analysis_name,
                )
            queue.setdefault(required_name, requested_analyses.get(required_name, {}))

        queue.setdefault(analysis_name, interfaces)

    return queue.items()


def _add_requested_load_positions(xml_file, requested_analyses):
    """Create the requested positioned copies before the model is validated/meshed."""
    for analysis_name, config in requested_analyses.items():
        for position in _load_positions(config, analysis_name):
            if not position:
                logger.info("Activating the existing load condition for '%s'", analysis_name)
                run_activate_line_load_condition(xml_file, analysis_name)
                continue
            x = position.get("x")
            if x is not None:
                logger.info("Adding positioned copy of '%s' at X=%s", analysis_name, x)
                run_add_line_load(xml_file, x, analysis_name)


def _expand_analysis_requests(requested_analyses):
    """Replace load-position metadata with concrete analysis names, preserving order."""
    expanded = OrderedDict()
    for analysis_name, config in requested_analyses.items():
        positions = _load_positions(config, analysis_name)
        interface_config = _interface_config(config, analysis_name)

        if not positions:
            expanded[analysis_name] = interface_config
            continue

        for position in positions:
            if not position:
                expanded.setdefault(analysis_name, interface_config)
                continue
            x = position["x"]
            positioned_name = f"{analysis_name}_Pos_{x}"
            if positioned_name in expanded:
                raise ValueError(
                    f"Analysis '{analysis_name}' has duplicate load position X={x}."
                )
            expanded[positioned_name] = {}
    return expanded


def _load_positions(config, analysis_name):
    if isinstance(config, list):
        # Accept the original shorthand: "LiveLoad_0": [{}, {"x": 660}].
        positions = config
    elif isinstance(config, dict) and LOAD_POSITION_KEY in config:
        positions = config[LOAD_POSITION_KEY]
    else:
        return []

    if not isinstance(positions, list) or not positions:
        raise ValueError(
            f"Analysis '{analysis_name}' load_pos must be a non-empty list of {{}} or {{'x': value}} entries."
        )
    for position in positions:
        if not isinstance(position, dict) or set(position) - {"x"}:
            raise ValueError(
                f"Analysis '{analysis_name}' load_pos entries must be {{}} or {{'x': value}}."
            )
        if position and position["x"] is None:
            raise ValueError(f"Analysis '{analysis_name}' load_pos x cannot be None.")
    return positions


def _interface_config(config, analysis_name):
    if isinstance(config, list):
        return {}
    if not isinstance(config, dict):
        raise ValueError(f"Analysis '{analysis_name}' configuration must be a dictionary.")
    return {key: value for key, value in config.items() if key != LOAD_POSITION_KEY}


def _missing_required_analyses(root, analysis_name):
    required = []
    analysis_by_name, analysis_by_key = _analysis_indexes(root)
    seen_keys = set()

    def visit(current_name):
        analysis = analysis_by_name.get(current_name)
        if analysis is None:
            raise KeyError(f"Analysis '{current_name}' not found.")

        initial_key = analysis.get("InitialAnalysisKey")
        if not initial_key or initial_key == "-100":
            return
        if initial_key in seen_keys:
            raise ValueError(
                f"Circular InitialAnalysisKey dependency detected at Key='{initial_key}'."
            )
        seen_keys.add(initial_key)

        required_analysis = analysis_by_key.get(initial_key)
        if required_analysis is None:
            raise KeyError(
                f"Analysis '{current_name}' requires missing InitialAnalysisKey='{initial_key}'."
            )

        required_name = required_analysis.get("Name")
        visit(required_name)
        if not _analysis_is_completed(required_analysis):
            required.append(required_name)

    visit(analysis_name)
    return required


def _analysis_indexes(root):
    by_name = {}
    by_key = {}
    for analysis in root.iter("Analysis"):
        name = analysis.get("Name")
        key = analysis.get("Key")
        if name:
            by_name[name] = analysis
        if key:
            by_key[key] = analysis
    return by_name, by_key


def _analysis_is_completed(analysis):
    states = analysis.find("States")
    if states is None:
        return False
    analysis_states = states.findall("State")
    return bool(analysis_states) and all(
        state.get("State") == "ExecutedCompleted"
        for state in analysis_states
    )


def _scenario_analysis_names(scenario):
    return _expand_analysis_requests(scenario.get("Analysis", {})).keys()


def pos_processing(scenario, db_path, xml_file, **kwargs):
    logger.info("Starting post-processing for file: %s", xml_file.split('\\')[-1])

    for analysis_name in _expand_analysis_requests(scenario["Analysis"]):
        try:
            logger.info("Saving outputs for analysis '%s'", analysis_name)
            save_outputs(scenario, analysis_name, db_path, xml_file, **kwargs)
        except Exception as e:
            logger.exception("Post-processing failed for %s - %s: %s", xml_file, analysis_name, e)
            raise

    logger.info("Post-processing complete for file: %s", xml_file.split('\\')[-1])
