import logging

from modelxml.ops import (
    run_copy_paste,
    run_set_model_points,
    run_update_material, 
    run_set_all_analyses_off, 
    run_set_analysis_on, 
    run_create_start_mesh_analysis, 
    run_update_foundation_ifaces
)

from save import save_scenario_info, save_outputs

from run_program import run_program

# -------------------------------------------------------------------
# Configure logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------

def generate_mesh(file, mode="local", timeout_seconds=200, **kwargs):
    logger.info("Creating mesh analysis for file: %s", file.split('\\')[-1])
    try:
        run_create_start_mesh_analysis(file)
        run_set_all_analyses_off(file)
        run_set_analysis_on(file, "StartMesh")

        logger.info("Running mesh analysis for file: %s", file.split('\\')[-1])
        run_program(file, mode, timeout_seconds)

    except Exception as e:
        logger.exception("Error during mesh generation for %s: %s", file.split('\\')[-1], e)
        raise
    finally:
        run_set_all_analyses_off(file)
        logger.info("Mesh generation complete for file: %s", file.split('\\')[-1])

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
        logger.info("Copying input: %s → %s", input_path.split('\\')[-1], xml_file.split('\\')[-1])
        run_copy_paste(input_path, out_path=xml_file)

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

    for analysis_name, interfaces in scenario["Analysis"].items():
        try:
            logger.info("Updating foundation interfaces for index %s", index)
            run_update_foundation_ifaces(xml_file, interfaces)
            
            logger.info("Running analysis '%s' for index %s", analysis_name, index)
            run_set_analysis_on(xml_file, analysis_name)
            run_program(xml_file, mode, timeout)
        
        except Exception as e:
            logger.exception("Processing failed for %s - %s: %s", index, analysis_name, e)
            raise

    logger.info("Processing complete for index: %s", index)

def pos_processing(scenario, db_path, xml_file, **kwargs):
    logger.info("Starting post-processing for file: %s", xml_file.split('\\')[-1])

    for analysis_name, interfaces in scenario["Analysis"].items():
        try:
            logger.info("Saving outputs for analysis '%s'", analysis_name)
            save_outputs(scenario, analysis_name, db_path, xml_file, **kwargs)
        except Exception as e:
            logger.exception("Post-processing failed for %s - %s: %s", xml_file, analysis_name, e)
            raise

    logger.info("Post-processing complete for file: %s", xml_file.split('\\')[-1])