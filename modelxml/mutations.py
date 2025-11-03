import copy
from xml.etree import ElementTree as ET
from .selectors import masonry_materials, quads, interfaces, foundation_interfaces

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

def update_foundation_interfaces(root, scenario: dict) -> None:
    # restr = [i for i in interfaces(root) if i["ParentTypeElement1"] == "Restraint"]
    # foundation_mk = _get_material_key(root, "Foundation")
    # foundation_quad_keys = [q["Key"] for q in quads(root) if q["MaterialKey"] == foundation_mk]
    # target_ifaces = {i["Key"] for i in restr if i["ParentElementKey2"] in foundation_quad_keys}
    found_inter = foundation_interfaces(root)
    for pier, material in scenario["Scour"].items():
        target_ifaces_keys = [f_i['Key'] for f_i in found_inter[pier][1]]
        mat_key = _get_material_key(root, material)
        set_material_to_interfaces(root, target_ifaces_keys, mat_key)