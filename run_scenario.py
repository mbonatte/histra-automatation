import os
import time
import glob

from run_program import SolverRunError

from processing_steps import pre_processing, processing, pos_processing

def delete_model_copies(file):
    """Delete all files that match '*_copy.*' in the file directory."""
    directory = os.path.dirname(file)
    base_name = file.split('\\')[-1].split('.')[0]
    pattern = os.path.join(directory, f"{base_name}.*")
    
    for path in glob.glob(pattern):
        try:
            os.remove(path)
        except Exception as e:
            print(f"Could not delete {path}: {e}")

def restart_scenario(file, scenario, i):
    print(f"Restarting scenario... {i+1}")
    delete_model_copies(file.replace(".hrx", f"_copy_{i+1}.hrx"))
    run_scenario(file, scenario, i)

def run_scenario(input_path, scenario, i, timeout=360):
    """Run a single scenario."""
    xml_file = input_path.replace(".hrx", f"_copy_{i+1}.hrx")
    db_path = input_path.replace(".hrx", f"_copy_{i+1}.Results")
    try:
        print(f"Pre-processing: {i+1}")
        pre_processing(input_path, scenario, xml_file)
        time.sleep(0.5)
        
        print(f"Processing: {i+1}")
        processing(xml_file, scenario, timeout=timeout)
        time.sleep(1)
        
        print(f"Pos-processing: {i+1}")
        pos_processing(scenario, db_path, xml_file)
        time.sleep(1)
        
        # delete_model_copies(xml_file)
    except SolverRunError as e:
        time.sleep(1)
        restart_scenario(input_path, scenario, i)