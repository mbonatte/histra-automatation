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
SCOURED_FOUNDATION_INTERFACE_MATERIAL = "Soil_removed"

def set_analysis_state(analysis, new_state: str) -> None:
    analysis_name = analysis.get("Name")
    analysis_key = analysis.get("Key")

    logging.debug(
        "Setting analysis '%s' [Key=%s] states to '%s'",
        analysis_name,
        analysis_key,
        new_state,
    )

    states = analysis.find("States")
    if states is None:
        logging.debug(
            "Analysis '%s' [Key=%s] has no States element",
            analysis_name,
            analysis_key,
        )
        return

    for state in states.findall("State"):
        logging.debug(
            "Analysis '%s' [Key=%s], state Id=%s before was '%s'",
            analysis_name,
            analysis_key,
            state.get("Id"),
            state.get("State"),
        )

        state.set("State", new_state)

        logging.debug(
            "Analysis '%s' [Key=%s], state Id=%s after is '%s'",
            analysis_name,
            analysis_key,
            state.get("Id"),
            state.get("State"),
        )

def set_all_analysis_to_not_run(root) -> None:
    for analysis in root.iter("Analysis"):
        set_analysis_state(analysis, "NotExecutedNotToBeExecuted")

def set_analysis_to_run(root, name) -> None:
    for analysis in root.iter("Analysis"):
        if analysis.get("Name") == name:
            set_analysis_state(analysis, "NotExecutedToBeExecute")
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
    logging.debug(f"Node {node_key} set to ModelPoint {next_key}.")
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

def create_load_condition(root):
    last_load_condition = root.findall("LoadCondition")[-1]
    load_condition = copy.deepcopy(last_load_condition)
    number = int(last_load_condition.get("Name").split("_")[-1]) + 1

    load_condition.set("Id", str(int(last_load_condition.get("Id")) + 1))
    load_condition.set("Name", f"Load_Condition_{number}")
    load_condition.set("Description", f"Load_Condition_{number}")

    root.insert(list(root).index(last_load_condition) + 1, load_condition)
    return load_condition.get("Id")

def add_line_load_definition(root):
    load_condition_id = create_load_condition(root)
    last_line_load = [
        template for template in root.iter("Template")
        if template.get("Name", "").startswith("VERTICAL_APPLIED_LOAD")
    ][-1]
    line_load = copy.deepcopy(last_line_load)
    key = str(max(int(template.get("Key")) for template in root.iter("Template")) + 1)
    number = int(last_line_load.get("Name").split("_")[-1]) + 1

    line_load.set("Key", key)
    line_load.set("Name", f"VERTICAL_APPLIED_LOAD_{number}")

    for item in line_load.iter("LoadTemplateItem"):
        item.set("IdLoadTemplate", key)
        item.set("IdLoadCondition", load_condition_id)

    root.insert(list(root).index(list(root.iter("Template"))[-1]) + 1, line_load)
    return key

def create_load_combination(root):
    last_load_combination = [
        combination for combination in root.iter("LoadCombination")
        if combination.get("Name", "").startswith("User_combination")
    ][-1]
    load_combination = copy.deepcopy(last_load_combination)
    key = str(int(last_load_combination.get("Key")) + 1)
    number = int(last_load_combination.get("Name").split("_")[-1]) + 1

    load_combination.set("Key", key)
    load_combination.set("Name", f"User_combination_{number}")

    for item in load_combination.iter("Item"):
        item.set("LoadCombinationKey", key)

    root.insert(list(root).index(last_load_combination) + 1, load_combination)
    return key

def create_line_load_analyses(root, x, load_combination_key):
    live_loads = [
        analysis for analysis in root.iter("Analysis")
        if analysis.get("Name") == "LiveLoad_1"
    ]
    key = max(int(analysis.get("Key")) for analysis in root.iter("Analysis"))
    load_function_key = max(
        int(analysis.get("LoadFunctionKey")) for analysis in root.iter("Analysis")
    )
    analysis_index = list(root).index(list(root.iter("Analysis"))[-1]) + 1
    load_function_item_key = max(
        int(item.get("key")) for item in root.iter("LoadFunctionItem")
    )

    for analysis in live_loads:
        key += 1
        load_function_key += 1
        line_load_analysis = copy.deepcopy(analysis)
        line_load_analysis.set("Key", str(key))
        line_load_analysis.set("Name", f"{analysis.get('Name')}_Pos_{x}")
        line_load_analysis.set(
            "Description",
            f"Copy of analysis {analysis.get('Name')} that runs at X={x}",
        )
        line_load_analysis.set("LoadFunctionKey", str(load_function_key))
        line_load_analysis.set("LoadCombinationKey", load_combination_key)

        for state in line_load_analysis.find("States").findall("State"):
            state.set("Key", str(key))
        for phase in line_load_analysis.iter("AdapticPhase"):
            phase.set("ParentKey", str(key))

        root.insert(analysis_index, line_load_analysis)
        analysis_index += 1

        load_function = ET.Element(
            "LoadFunction",
            {"key": str(load_function_key), "typeDiscr": "false", "DiscrVal": "0.2"},
        )
        root.insert(list(root).index(list(root.iter("LoadFunction"))[-1]) + 1, load_function)

        for pseudo_time, multiplier in [("0", "0"), ("1", "1")]:
            load_function_item_key += 1
            load_function_item = ET.Element(
                "LoadFunctionItem",
                {
                    "key": str(load_function_item_key),
                    "loadFunctionKey": str(load_function_key),
                    "pseudoTime": pseudo_time,
                    "multiplier": multiplier,
                },
            )
            root.insert(
                list(root).index(list(root.iter("LoadFunctionItem"))[-1]) + 1,
                load_function_item,
            )

def add_line_load(root, x):
    load_template_id = add_line_load_definition(root)
    load_combination_key = create_load_combination(root)
    create_line_load_analyses(root, x, load_combination_key)
    last_line_load = [
        load for load in root.iter("LoadElement")
        if load.get("TypeOf") == "HiStrA.Objects.LineLoadElement"
    ][-1]
    line_load = copy.deepcopy(last_line_load)
    point1 = last_line_load.get("Point1").split(";")
    point2 = last_line_load.get("Point2").split(";")
    x_value = float(x)
    quad = min(
        root.iter("Quad"),
        key=lambda quad: (
            (float(quad.get("G").split(";")[0]) - x_value) ** 2
            + (float(quad.get("G").split(";")[2]) - float(point1[2])) ** 2
        ),
    )

    line_load.set("Key", str(int(last_line_load.get("Key")) + 1))
    line_load.set("ElementKey", quad.get("Key"))
    line_load.set("IdLoadTemplate", load_template_id)
    line_load.set("Point1", f"{x};{point1[1]};{point1[2]}")
    line_load.set("Point2", f"{x};{point2[1]};{point2[2]}")

    root.insert(list(root).index(last_line_load) + 1, line_load)

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


def _compute_interface_xyz_center(interface: dict) -> Tuple[float, float, float]:
    x_values = [float(interface[f"VInt3D{i}"].split(';')[0]) for i in range(1, 5)]
    y_values = [float(interface[f"VInt3D{i}"].split(';')[1]) for i in range(1, 5)]
    z_values = [float(interface[f"VInt3D{i}"].split(';')[2]) for i in range(1, 5)]

    return (
        sum(x_values) / 4.0,
        sum(y_values) / 4.0,
        sum(z_values) / 4.0,
    )


def _select_outside_delta_interfaces(
    interfaces: List[dict],
    location: Tuple[float, float, float, float, float],
    delta: float,
    mode: str = "uniform",
) -> List[str]:
    x0, y0, length, width, _z0 = location
    delta = float(delta)

    if not 0 <= delta <= 1:
        raise ValueError(f"delta must be between 0 and 1. Got: {delta}")
    
    left_bank_x = x0 - length / 2
    right_bank_x = x0 + length / 2

    upstream_y = y0 - width / 2
    downstream_y = y0 + width / 2

    mode = mode.lower()

    if mode == "uniform":
        # delta=0.2 means remove/select 20% total,
        # split equally between left and right.
        half_zone = ((1 - delta) * length) / 2

        min_x = x0 - half_zone
        max_x = x0 + half_zone

        logging.debug(
            "Uniform scour: x0='%s', length='%s', delta='%s', min_x='%s', max_x='%s'",
            x0,
            length,
            delta,
            min_x,
            max_x,
        )

        def should_select(xyz_center: Tuple[float, float, float]) -> bool:
            x_center = xyz_center[0]
            return x_center < min_x or x_center > max_x

    elif mode == "left":
        # delta=0.2 means select the left 20% of the foundation length.
        limit_x = left_bank_x + delta * length

        logging.debug(
            "Left scour: x0='%s', length='%s', delta='%s', left_bank_x='%s', limit_x='%s'",
            x0,
            length,
            delta,
            left_bank_x,
            limit_x,
        )

        def should_select(xyz_center: Tuple[float, float, float]) -> bool:
            x_center = xyz_center[0]
            return x_center < limit_x
    
    elif mode == "right":
        # delta=0.2 means select the right 20% of the foundation length.
        limit_x = right_bank_x - delta * length

        logging.debug(
            "Right scour: x0='%s', length='%s', delta='%s', limit_x='%s', right_bank_x='%s'",
            x0,
            length,
            delta,
            limit_x,
            right_bank_x,
        )

        def should_select(xyz_center: Tuple[float, float, float]) -> bool:
            x_center = xyz_center[0]
            return x_center > limit_x
        
    elif mode == "upstream":
        # delta=0.2 means select the upstream 20% of the foundation width.
        limit_y = upstream_y + delta * width

        logging.debug(
            "Upstream scour: y0='%s', width='%s', delta='%s', upstream_y='%s', limit_y='%s'",
            y0,
            width,
            delta,
            upstream_y,
            limit_y,
        )

        def should_select(xyz_center: Tuple[float, float, float]) -> bool:
            y_center = xyz_center[1]
            return y_center < limit_y

    elif mode == "downstream":
        # delta=0.2 means select the downstream 20% of the foundation width.
        limit_y = downstream_y - delta * width

        logging.debug(
            "Downstream scour: y0='%s', width='%s', delta='%s', limit_y='%s', downstream_y='%s'",
            y0,
            width,
            delta,
            limit_y,
            downstream_y,
        )

        def should_select(xyz_center: Tuple[float, float, float]) -> bool:
            y_center = xyz_center[1]
            return y_center > limit_y

    else:
        raise ValueError(
            f"Unsupported scour mode '{mode}'. Expected 'left', 'right', "
            "'uniform', 'upstream', or 'downstream'."
        )
    
    selected_keys = []

    for iface in interfaces:
        xyz_center = _compute_interface_xyz_center(iface)

        logging.debug(
            "Interface Key='%s', xyz_center='%s'",
            iface.get("Key"),
            xyz_center,
        )

        if should_select(xyz_center):
            logging.debug(
                "Selected interface Key='%s', xyz_center='%s', mode='%s', delta='%s'",
                iface.get("Key"),
                xyz_center,
                mode,
                delta,
            )
            selected_keys.append(iface["Key"])

    logging.debug(
        "Selected %s interface(s) for mode='%s', delta='%s': %s",
        len(selected_keys),
        mode,
        delta,
        selected_keys,
    )

    return selected_keys

def set_default_interface(root, interfaces):
    interfaces_keys = [f_i['Key'] for f_i in interfaces]
    mat_key = _get_first_material_key(root, DEFAULT_FOUNDATION_INTERFACE_MATERIALS)
    set_material_to_interfaces(root, interfaces_keys, mat_key)


def update_foundation_interfaces(root, interface_scenario: dict) -> None:
    if not interface_scenario:
        logging.debug("No interfaces provided. Nothing to update.")
        return

    foundation_locations = get_foundation_locations(root)
    found_inter = foundation_interfaces(root)

    mat_key = _get_material_key(
        root,
        material_name=SCOURED_FOUNDATION_INTERFACE_MATERIAL,
    )

    for pier, scour_config in interface_scenario.items():
        logging.debug("Processing pier='%s', scour_config='%s'", pier, scour_config)

        if pier not in found_inter:
            logging.warning("Pier '%s' not found in foundation interfaces. Skipping.", pier)
            continue

        if pier not in foundation_locations:
            logging.warning("Pier '%s' not found in foundation locations. Skipping.", pier)
            continue

        bottom_interfaces = found_inter[pier][1]
        if not bottom_interfaces:
            logging.warning(f"No bottom foundation interfaces found for pier '{pier}'. Skipping.")
            continue

        set_default_interface(root, bottom_interfaces)

        # Backward compatibility:
        # allow "pier_1": 0.2 and treat it as uniform.
        if isinstance(scour_config, dict):
            scour_items = scour_config.items()
        else:
            scour_items = [("uniform", scour_config)]

        for mode, delta in scour_items:
            logging.debug(
                "Processing pier='%s', mode='%s', delta='%s'",
                pier,
                mode,
                delta,
            )

            target_interface_keys = _select_outside_delta_interfaces(
                bottom_interfaces,
                foundation_locations[pier],
                delta,
                mode=mode,
            )

            set_material_to_interfaces(root, target_interface_keys, mat_key)
