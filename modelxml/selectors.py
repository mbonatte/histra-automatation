import math
import re

def interfaces(root):
    records = []
    for elem in root.iter("Interface"):
        data = elem.attrib
        if not data.get("Key"):
            continue
        
        record = {
            "Key": data.get("Key"),
            "NodeKey1": data.get("NodeKey1"),
            "NodeKey2": data.get("NodeKey2"),
            "Name": data.get("Name"),
            
            "MaterialKey": data.get("MaterialKey"),
            "ParentElementKey1": data.get("ParentElementKey1"),
            "ParentElementKey2": data.get("ParentElementKey2"),
            "ParentTypeElement1": data.get("ParentTypeElement1"),
            "ParentTypeElement2": data.get("ParentTypeElement2"),
            
            "Nspring": data.get("Nspring"),
            "Face1": data.get("Face1"),
            "Face2": data.get("Face2"),
            
            "IsPropertyModified": data.get("IsPropertyModified"),
            "VInt2D1": data.get("VInt2D1"),
            "VInt2D2": data.get("VInt2D2"),
            "VInt2D3": data.get("VInt2D3"),
            "VInt2D4": data.get("VInt2D4"),
            "VInt3D1": data.get("VInt3D1"),
            "VInt3D2": data.get("VInt3D2"),
            "VInt3D3": data.get("VInt3D3"),
            "VInt3D4": data.get("VInt3D4"),
            
        }
        records.append(record)
    return records

def quads(root):
    records = []
    for quad in root.iter("Quad"):
        data = quad.attrib
        record = {
            "Key": data.get("Key"),
            "Name": data.get("Name"),
            "MaterialKey": data.get("MaterialKey"),
            "LayerKey": data.get("LayerKey"),
            "G": data.get("G"),
            "NodeKey1": data.get("NodeKey1"),
            "NodeKey2": data.get("NodeKey2"),
            "NodeKey3": data.get("NodeKey3"),
            "NodeKey4": data.get("NodeKey4"),
        }
        records.append(record)
    return records

def masonry_materials(root):
    records = []
    for elem in root.iter("Template"):
        attrs = elem.attrib
        typeof = attrs.get("TypeOf", "")
        purpose = attrs.get("PurposeType", "")
        
        # Identify as masonry material
        if "MasonryMaterial" in typeof or "MasonryMaterial" in purpose:
            record = {
                "Key": attrs.get("Key"),
                "Name": attrs.get("Name"),

                "w": attrs.get("w"),
                "Ehor": attrs.get("Ehor"),
                
                "FtmHor": attrs.get("FtmHor"),
                "Gt": attrs.get("Gt"),

                "FmHor": attrs.get("FmHor"),
                "Gc": attrs.get("Gc"),
                
                "Gd": attrs.get("Gd"),
                "fvk0d": attrs.get("fvk0d"),
                "FrictionRatioShear": attrs.get("FrictionRatioShear"),
                "ShearMaxTensileRatio": attrs.get("ShearMaxTensileRatio"),
                "ShearPlasticStrain": attrs.get("ShearPlasticStrain"),
                "DuctilityShear": attrs.get("DuctilityShear"),
                "Bcacovic": attrs.get("Bcacovic"),
                
                
                "CohesionSlidingHor": attrs.get("CohesionSlidingHor"),
                "FrictionRatioSlidingHor": attrs.get("FrictionRatioSlidingHor"),
            }
            records.append(record)
    return records

def analysis_state(root, analysis_name):
    pattern = (
        r"displ\s*=\s*([\d.]+)\s*cm.*?"                  # displacement
        r"F\s*=\s*([\d.]+)\s*kN.*?"                      # force
        r"Load\s*multiplier\s*F/Fo\s*=\s*([\d.]+)\s*%?"  # load multiplier
        r"(?:.*?Fmax\s*=\s*([\d.]+)\s*kN)?$"             # optional Fmax
    )
    for elem in root.iter("Analysis"):
        if elem.attrib.get("Name") != analysis_name: continue
        states = elem.find("States")
        for state in states.findall("State"):
            displ = F = load_multiplier = Fmax = None
            match = re.search(pattern, state.attrib.get('ExitDescription', ''))
            if match:
                displ, F, load_multiplier, Fmax = [
                    float(v) if v is not None else None for v in match.groups()
                ]
            return {
                'Fo': state.attrib.get('Fo'),
                'State': state.attrib.get('State'),
                'Exit': state.attrib.get('Exit'),
                'ExitDescription': state.attrib.get('ExitDescription'),
                'displ': displ,
                'F': F,
                'Load_multiplier': load_multiplier,
                'Fmax': Fmax
            }
   
def analysis_key(root, analysis_name):
    for elem in root.iter("Analysis"):
        if elem.attrib.get("Name") == analysis_name:
            return elem.attrib.get("Key")
    raise KeyError(f"Analysis '{analysis_name}' not found.")

def restrain(root):
    # === 3️⃣ Collect all restraint-like tags ===
    restraint_tags = ["Restraint", "GeometryLineRestraint", "SurfaceRestraint"]
    records = []

    for tag in restraint_tags:
        for elem in root.iter(tag):
            data = elem.attrib

            # Build a clean record for CSV
            record = {
                "Tag": tag,
                "ParentTypeElement": data.get("ParentTypeElement"),
                "Key": data.get("Key"),
                "Name": data.get("Name"),
                "Type": data.get("Type"),
                "NodeKey1": data.get("NodeKey1"),
                "NodeKey2": data.get("NodeKey2"),
                "U1mechBehaviourType": data.get("U1mechBehaviourType"),
                "U2mechBehaviourType": data.get("U2mechBehaviourType"),
                "U3mechBehaviourType": data.get("U3mechBehaviourType"),
                "R1mechBehaviourType": data.get("R1mechBehaviourType"),
                "R2mechBehaviourType": data.get("R2mechBehaviourType"),
                "R3mechBehaviourType": data.get("R3mechBehaviourType"),
                "K1": data.get("K1"),
                "K2": data.get("K2"),
                "K3": data.get("K3"),
                "Kr1": data.get("Kr1"),
                "Kr2": data.get("Kr2"),
                "Kr3": data.get("Kr3"),
                "G": data.get("G"),
                "Point1": data.get("Point1"),
                "Point2": data.get("Point2"),
                "Point3": data.get("Point3"),
                "Point4": data.get("Point4"),
                "ComputationalElementType": data.get("ComputationalElementType"),
                "ComputationalElementKey": data.get("ComputationalElementKey"),
            }
            records.append(record)
    return records

def foundation_interfaces(root):
    geo = geometry(root)
    inter = interfaces(root)

    restrains_interfaces = [i for i in inter if i['ParentTypeElement1'] == 'Restraint']

    foundation_locations = [
        (p["Origin"][0], p["B1f"] + p["b2"] + p["B3f"], -(p["H"] + p["Hf"]))
        for p in geo["Piers"]
    ]

    foundations_interfaces = {}

    for i, (x0, width, z0) in enumerate(foundation_locations):
        left, bottom, right = [], [], []
        for inter in restrains_interfaces:
            x, _, z = map(float, inter["VInt3D1"].split(";"))
            if x0 - width * 0.55 < x < x0 + width * 0.55:
                if abs(z - z0) < 1:
                    bottom.append(inter)
                elif x < x0:
                    left.append(inter)
                elif x > x0:
                    right.append(inter)
        foundations_interfaces[f"pier_{i+1}"] = (left, bottom, right)

    return foundations_interfaces

def nodes(root):
    records = []
    for node in root.iter("Node"):
        data = node.attrib

        # Base node info
        node_info = {
            "Key": data.get("Key"),
            "Name": data.get("Name"),
            "Point": data.get("Point"),
            "IsModelPoint": data.get("IsModelPoint"),
            "MasterElementKey": data.get("MasterElementKey"),
            "MasterElementType": data.get("MasterElementType"),
            "LayerKey": data.get("LayerKey"),
            "IsPropertyModified": data.get("IsPropertyModified"),
        }

        # --- Split Point into X, Y, Z numeric columns ---
        point = data.get("Point")
        if point:
            coords = [float(x) for x in point.split(";")]
            node_info["X"], node_info["Y"], node_info["Z"] = coords
        else:
            node_info["X"] = node_info["Y"] = node_info["Z"] = None

        records.append(node_info)
    return records

def _get_closest_node(nodes, x, y, z):
    closest_node = None
    min_distance = float('inf')

    for node in nodes:
        dx = node['X'] - x
        dy = node['Y'] - y
        dz = node['Z'] - z
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)

        if distance < min_distance:
            min_distance = distance
            closest_node = node

    return closest_node

def model_points_location_map(root):
    node_list = nodes(root)
    geometry_data = geometry(root)
    location_map = {}

    for i, pier in enumerate(geometry_data['Piers']):
        x = pier['Origin'][0]
        node = _get_closest_node(node_list, x, 0, 0)
        location_name = f"Pier_{i+1}_top"
        location_map[location_name] = {key: node[key] for key in ["Key", "X", "Y", "Z"]}

    for i, arch in enumerate(geometry_data['Spans']):
        if i == 0:
            x_pier = geometry_data['Piers'][i]['Origin'][0]
            x_pier -= geometry_data['Piers'][i]['b2'] / 2 
            x_arch = x_pier - arch['L'] / 2
        else:
            x_pier = geometry_data['Piers'][i-1]['Origin'][0]
            x_pier += geometry_data['Piers'][i-1]['b2'] / 2 
            x_arch = x_pier + arch['L'] / 2
        
        node = _get_closest_node(node_list, x_arch, 0, arch['f'])
        location_name = f"Arch_{i}_middle"
        location_map[location_name] = {key: node[key] for key in ["Key", "X", "Y", "Z"]}
    
    return location_map

def nodec(root):
    # === 3️⃣ Coletar todos os nós ===
    node_tags = ["NodeC", "GeometryNodeC"]  # cobre as variações possíveis
    records = []

    for tag in node_tags:
        for node in root.iter(tag):
            data = node.attrib
            node_info  = {
                "Tag": tag,
                "NodeKey": data.get("NodeKey"),
                "Key": data.get("Key"),
                "Name": data.get("Name"),
                "IsIndipendent": data.get("IsIndipendent"),
                "MasterElementKey": data.get("MasterElementKey"),
                "MasterElementType": data.get("MasterElementType"),
                "LayerKey": data.get("LayerKey"),
                "IsPropertyModified": data.get("IsPropertyModified"),            
            }
            # --- MasterElements ---
            master_elements = []
            master_block = node.find("MasterElements")
            if master_block is not None:
                for m in master_block.findall("MasterElement"):
                    master_elements.append(f"{m.attrib.get('Value')}:{m.attrib.get('Key')}")
            node_info["MasterElements"] = "; ".join(master_elements) if master_elements else None

            # --- SlaveElements ---
            slave_elements = []
            slave_block = node.find("SlaveElements")
            if slave_block is not None:
                for s in slave_block.findall("SlaveElement"):
                    slave_elements.append(f"{s.attrib.get('Value')}:{s.attrib.get('Key')}")
            node_info["SlaveElements"] = "; ".join(slave_elements) if slave_elements else None
            
            records.append(node_info)
    return records
     
def geometry(root):
    def parse_vector(v):
        return [float(x) for x in v.split(';')] if v else None
    
    geometry = {
        "BridgeDefinition": {},
        "Abutments": [],
        "Piers": [],
        "Spans": []
    }

    bridge_def = root.find(".//BridgeDefinition")
    geometry["BridgeDefinition"] = {
        "Width": float(bridge_def.get("Width", 0)),
        "Slope": float(bridge_def.get("Slope", 0)),
        "InclinationAngle": float(bridge_def.get("InclinationAngle", 0)),
        "Zlevel": float(bridge_def.get("Zlevel", 0)),
        "ThicknessBallast": float(bridge_def.get("ThicknessBallast", 0)),
        "ThicknessRiempimento": float(bridge_def.get("ThicknessRiempimento", 0)),
    }

    for ab in root.findall(".//Abutment"):
        ref = ab.find("ReferenceSystem")
        geometry["Abutments"].append({
            "AbutmentKind": ab.get("AbutmentKind", ""),
            "b2": float(ab.get("b2", 0)),
            "w2": float(ab.get("w2", 0)),
            "Kz": float(ab.get("Kz", 0)),
            "Hsp1": float(ab.get("Hsp1", 0)),
            "Hsp2": float(ab.get("Hsp2", 0)),
            "Origin": parse_vector(ref.get("Origin", "0;0;0"))
        })
    

    for pier in root.findall(".//Pier"):
        ref = pier.find("ReferenceSystem")
        geometry["Piers"].append({
            "H": float(pier.get("H", 0)),
            "b2": float(pier.get("b2", 0)),
            "w2": float(pier.get("w2", 0)),
            "Hsp1": float(pier.get("Hsp1", 0)),
            "Hsp2": float(pier.get("Hsp2", 0)),

            "Hf": float(pier.get("Hf", 0)),
            "B1f": float(pier.get("B1f", 0)),
            "B3f": float(pier.get("B3f", 0)),
            "W1f": float(pier.get("W1f", 0)),
            "W3f": float(pier.get("W3f", 0)),
            "Kz": float(pier.get("Kz", 0)),
            
            "Origin": parse_vector(ref.get("Origin", "0;0;0"))
        })

    for span in root.findall(".//Span"):
        geometry["Spans"].append({
            "L": float(span.get("L", 0)),
            "W": float(span.get("W", 0)),
            "f": float(span.get("f", 0)),
            "Tb": float(span.get("Tb", 0)),
            "Tt": float(span.get("Tt", 0)),
        })

    elevations_node = root.find(".//Elevations")
    elevations_data = {
        "Elevations": [],
    }

    # Extract <Elevation> elements
    for e in elevations_node.findall(".//Elevation"):
        elevations_data["Elevations"].append({
            "X": float(e.get("X", 0)),
            "H1": float(e.get("H1", 0)),
            "H2": float(e.get("H2", 0)),
            "H3": float(e.get("H3", 0))
        })

    geometry["Elevations"] = elevations_data
    
    return geometry