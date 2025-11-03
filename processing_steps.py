from modelxml.ops import (
    run_copy_paste,
    run_update_material, 
    run_set_all_analyses_off, 
    run_set_analysis_on, 
    run_create_start_mesh_analysis, 
    run_update_foundation_ifaces
)

from save import save_scenario_info, save_outputs

from run_program import run_program

def generate_mesh(file):
    print("Creating mesh analysis")
    run_create_start_mesh_analysis(file)
    run_set_all_analyses_off(file)
    run_set_analysis_on(file, "StartMesh")
    print("Running mesh analysis")
    run_program(file, timeout_seconds=200, mode="local")
    run_set_all_analyses_off(file)

def prepare_model(file):
    generate_mesh(file)
    

def pre_processing(input_path, scenario, xml_file):
    index = xml_file.split("_")[-1].split(".")[0]
    print(f"Copying: {index}")
    run_copy_paste(input_path, out_path=xml_file)
    print(f"Updating materials: {index}")
    run_update_material(xml_file, scenario.get("Materials", []))
    print(f"Updating foundation interfaces: {index}")
    run_update_foundation_ifaces(xml_file, scenario)
    print(f"Pre-processing finished: {index}")
    save_scenario_info(scenario, xml_file)

def processing(xml_file, scenario, timeout=360):
    index = xml_file.split("_")[-1].split(".")[0]
    for analysis in ["Vert"]+scenario["Analysis"]:
        run_set_analysis_on(xml_file, analysis)
        print(f"Running: {index} - {analysis}")
        run_program(xml_file, timeout_seconds=timeout, mode="local")

def pos_processing(scenario, db_path, xml_file):
    for analysis in ["Vert"]+scenario["Analysis"]:
        save_outputs(scenario, analysis, db_path, xml_file)