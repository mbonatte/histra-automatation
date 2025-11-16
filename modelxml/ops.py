from .xmlio import mutate_file, read_xml, save_xml
from .mutations import (
    set_model_points,
    set_all_analysis_to_not_run,
    set_analysis_to_run,
    create_start_mesh_analysis,
    update_materials,
    update_foundation_interfaces,
)

def run_copy_paste(in_path: str, out_path: str | None = None):
    mutate_file(in_path, None, out_path)

def run_set_model_points(in_path: str, out_path: str | None = None):
    mutate_file(in_path, set_model_points, out_path)

def run_set_all_analyses_off(in_path: str, out_path: str | None = None):
    mutate_file(in_path, set_all_analysis_to_not_run, out_path)

def run_set_analysis_on(in_path: str, analysis: str, out_path: str | None = None):
    mutate_file(in_path, lambda r: set_analysis_to_run(r, analysis), out_path)

def run_create_start_mesh_analysis(in_path: str, out_path: str | None = None):
    mutate_file(in_path, create_start_mesh_analysis, out_path)

def run_update_material(in_path: str, materials: list, out_path: str | None = None):
    mutate_file(in_path, lambda r: update_materials(r, materials), out_path)

def run_update_foundation_ifaces(in_path: str, scenario: dict, out_path: str | None = None):
    mutate_file(in_path, lambda r: update_foundation_interfaces(r, scenario), out_path)
