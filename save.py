from modelxml.xmlio import read_xml
from modelxml.selectors import geometry, masonry_materials, analysis_state, analysis_key

from extract_results import get_model_points_displacement, get_reactions

def save_scenario_info(scenario, file):
    root = read_xml(file)
    scenario['Geometry'] = geometry(root)
    scenario['Materials'] = masonry_materials(root)


def save_outputs(scenario, analysis, db_path, xml_file):
    xml_root = read_xml(xml_file)
    anls_key = int(analysis_key(xml_root, analysis))
    if 'Output' not in scenario:
        scenario['Output'] = {}
    scenario['Output'][analysis] = get_model_points_displacement(db_path, anls_key)
    scenario['Output'][analysis].update(get_reactions(db_path, anls_key))
    scenario['Output'][analysis].update(analysis_state(xml_root, analysis))