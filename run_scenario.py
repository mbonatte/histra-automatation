import os
import time
import glob
import traceback

from run_program import SolverRunError
from processing_steps import pre_processing, processing, pos_processing

def delete_model_copies(file_path):
    """Delete all files that match '*_copy.*' in the file directory."""
    directory = os.path.dirname(file_path)
    base_name = os.path.basename(file_path).split('.')[0]
    pattern = os.path.join(directory, f"{base_name}.*")
    
    for path in glob.glob(pattern):
        try:
            os.remove(path)
        except Exception as e:
            print(f"[WARN] Could not delete {path}: {e}")

def restart_scenario(input_path, scenario, i, retries_left=2):
    """Retry a failed scenario, deleting old copies first."""
    if retries_left <= 0:
        print(f"[ERROR] Scenario {i+1} failed permanently after retries.")
        return
    print(f"[INFO] Restarting scenario {i+1}... ({retries_left} retries left)")
    xml_file = input_path.replace(".hrx", f"_copy_{i+1}.hrx")
    delete_model_copies(xml_file)
    time.sleep(1)

    try:
        run_scenario(input_path, scenario, i)
    except SolverRunError:
        restart_scenario(input_path, scenario, i, retries_left=retries_left-1)

def run_scenario(input_path, scenario, i, mode='local', timeout=360, **kwargs):
    """Run a single scenario."""
    xml_file = input_path.replace(".hrx", f"_copy_{i+1}.hrx")
    db_path = input_path.replace(".hrx", f"_copy_{i+1}.Results")
    
    try:
        pre_processing(input_path, scenario, xml_file, **kwargs)
        time.sleep(0.5)
        
        processing(xml_file, scenario, mode, timeout, **kwargs)
        time.sleep(1)
        
        pos_processing(scenario, db_path, xml_file, **kwargs)
        time.sleep(1)
        
        print(f"[SUCCESS] Scenario {i+1} finished successfully and saved.\n")
    
    except SolverRunError as e:
        print(f"[ERROR] SolverRunError in scenario {i+1}: {e}")
        # restart_scenario(input_path, scenario, i)
    except Exception as e:
        print(f"[FATAL] Unexpected error in scenario {i+1}: {e}")
        traceback.print_exc()
    finally:
        time.sleep(1)
        print(f"[CLEANUP] Deleting temporary files for scenario {i+1}")
        delete_model_copies(xml_file)