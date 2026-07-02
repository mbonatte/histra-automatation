import logging
from typing import List, Tuple
import copy
import math
from xml.etree import ElementTree as ET
from .selectors import geometry, masonry_materials, nodes, model_points_location_map, quads, interfaces, get_foundation_locations, foundation_interfaces

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

DEFAULT_FOUNDATION_INTERFACE_MATERIALS = ("Foundation_Soil", "Soil")
SCOURED_FOUNDATION_INTERFACE_MATERIAL = "Damaged"


def set_all_analysis_to_not_run(root) -> None:
    for analysis in root.iter("Analysis"):
        states = analysis.find("States")
        if states is None: continue
        for state in states.findall("State"):
            state.set("State", "NotExecutedNotToBeExecuted")

def set_analysis_to_run(root, name) -> None:
    for analysis in root.iter("Analysis"):
        if analysis.get("Name") == name:
            states = analysis.find("States")
            if states is None: break
            for state in states.findall("State"):
                state.set("State", "NotExecutedToBeExecute")
            break

def _copy_analysis(root, copy_from):
    analysis = None
    last_key = 0

    for elem in root.findall("Analysis"):
        last_key = max(last_key, int(elem.get("Key")))
        if elem.get("Name") == copy_from:
            analysis = elem
    
    if not analysis:
        raise ValueError(f"No '{copy_from}' analysis found in XML")
            
    return last_key, copy.deepcopy(analysis)

def update_node_to_model_point(root, node_key):
    # Find the Node with the given Key
    node = root.find(f".//Node[@Key='{node_key}']")
    if node is None:
        raise ValueError(f"Node with Key={node_key} not found")
    
    # Update the Node to be a ModelPoint
    node.set("IsModelPoint", "True")

    
    # Check if ModelPoint already exists for this Node
    existing_mp = root.find(f".//ModelPoint[@IdElement='{node_key}']") \
               or root.find(f".//ModelPoint[@ElementKey='{node_key}']")
    if existing_mp is not None:
        return 
    
    # Find the max Key among existing ModelPoints
    model_points = root.findall(".//ModelPoint")
    existing_keys = [
        int(mp.get("Key")) for mp in model_points
        if mp.get("Key") and mp.get("Key").isdigit()
    ]
    next_key = max(existing_keys) + 1 if existing_keys else 1
    
    # Create the new ModelPoint element
    model_point = ET.Element("ModelPoint")
    
    # Populate auto-generated and node-related fields
    model_point_data = {
        "Key": str(next_key),
        "Name": str(next_key),
        "ParentKey": str(next_key),
        "IdElement": str(node_key),
        "ElementKey": str(node_key),
        "ElementType": "Node",
        "Point": node.get("Point"),
        "Description": f"Point in ({node.get('Point')})",
    }

    # Assign all attributes to the new ModelPoint
    for key, value in model_point_data.items():
        model_point.set(key, str(value))

    # Append the new ModelPoint to the root (or specific parent if needed)
    root.append(model_point)

def set_model_points(root):
    location_map = model_points_location_map(root)
    for point in location_map.values():
        update_node_to_model_point(root, point['Key'])

def create_start_mesh(root):
    key, analysis_mesh = _copy_analysis(root, "Vert")
    analysis_mesh.set("Name", "StartMesh")
    analysis_mesh.set("Key", f"{key + 1}")

    for state in analysis_mesh.find("States").findall("State"):
        state.set("Key", f"{key + 1}")

    root.append(analysis_mesh)

def create_start_mesh_analysis(root):    
    if 'StartMesh' not in [elem.attrib.get("Name") for elem in root.iter("Analysis")]:
        create_start_mesh(root)
    
    setpairs = {
        "Mult": "0",
    }
    
    for elem in root.iter("Analysis"):
        if elem.attrib.get("Name") == 'StartMesh':
            for k,v in setpairs.items():
                elem.set(k, v)
            break

def update_materials(root, materials):
    for material in materials:
        update_material(root, material)

def update_material(root, mat) -> None:
    for tmpl in root.iter("Template"):
        if tmpl.get("Name") == mat["Name"]:
            for k, v in mat.items():
                if k != "Name":
                    tmpl.set(k, str(v))
            return
    raise KeyError(f"Material '{mat['Name']}' not found.")

def set_material_to_interfaces(root, iface_keys, material_key) -> None:
    for iface in root.iter("Interface"):
        k = iface.get("Key")
        if k and k in iface_keys:
            iface.set("MaterialKey", material_key)
            iface.set("IsPropertyModified", "True")

def _get_material_key(root: ET.Element, material_name: str) -> str:
    for m in masonry_materials(root):
        if m["Name"] == material_name:
            return m["Key"]
    raise KeyError(f"Material '{material_name}' not found.")


def _get_first_material_key(root: ET.Element, material_names: Tuple[str, ...]) -> str:
    for material_name in material_names:
        try:
            return _get_material_key(root, material_name)
        except KeyError:
            continue
    raise KeyError(f"None of the materials were found: {', '.join(material_names)}")


def _compute_interface_x_center(interface: dict) -> float:
    x_values = [float(interface[f"VInt3D{i}"].split(';')[0]) for i in range(1, 5)]
    return sum(x_values) / 4.0

def _select_outside_delta_interfaces(
    interfaces: List[dict],
    location: Tuple[float, float, float],
    delta: float
) -> List[str]:
    x0, width, _ = location
    half_zone = ((1-delta) * width) / 2

    min_x = x0 - half_zone
    max_x = x0 + half_zone

    logging.debug(f"min_x='{min_x}', max_x='{max_x}'")

    selected_keys = []

    for iface in interfaces:
        x_center = _compute_interface_x_center(iface)
        if x_center < min_x or x_center > max_x:
            logging.debug(f"x_center='{x_center}'")
            selected_keys.append(iface["Key"])

    return selected_keys

def set_default_interface(root, interfaces):
    interfaces_keys = [f_i['Key'] for f_i in interfaces]
    mat_key = _get_first_material_key(root, DEFAULT_FOUNDATION_INTERFACE_MATERIALS)
    set_material_to_interfaces(root, interfaces_keys, mat_key)


def update_foundation_interfaces(root, interfaces: dict) -> None:
    if not interfaces:
        logging.debug("No interfaces provided. Nothing to update.")
        return

    foundation_locations = get_foundation_locations(root)
    found_inter = foundation_interfaces(root)

    for pier, delta in interfaces.items():
        logging.debug(f"Processing pier='{pier}', delta='{delta}'")

        if pier not in found_inter:
            logging.warning(f"Pier '{pier}' not found in foundation interfaces. Skipping.")
            continue

        bottom_interfaces = found_inter[pier][1]
        if not bottom_interfaces:
            logging.warning(f"No bottom foundation interfaces found for pier '{pier}'. Skipping.")
            continue

        set_default_interface(root, bottom_interfaces)

        target_interface_keys = _select_outside_delta_interfaces(
            bottom_interfaces,
            foundation_locations[pier],
            delta
        )

        mat_key = _get_material_key(root, material_name=SCOURED_FOUNDATION_INTERFACE_MATERIAL)
        set_material_to_interfaces(root, target_interface_keys, mat_key)
