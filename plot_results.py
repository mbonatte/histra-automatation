import pandas as pd


def flat_data(data):
    rows = []
    
    for idx, s in enumerate(data):
        if "Output" not in s or not s["Output"]:
            continue

        for analysis, output_data in s["Output"].items():
            displacements = output_data.get("Displacements", [])

            row = {
                "_source_index": idx,
                "Analysis": analysis,
                "Fmax": output_data.get("Fmax", 0),
                "Exit": output_data.get("Exit", ""),
            }

            # Dynamically extract all materials and their properties
            for material in s.get("Materials", []):
                mat_name = material.get("Name", "Unknown")
                for prop_name, prop_value in material.items():
                    if prop_name == "Name":
                        continue
                    # Create column names like "Damaged_Ehor" or "Arches_w"
                    key = f"{mat_name}_{prop_name}"
                    try:
                        row[key] = float(prop_value)
                    except (ValueError, TypeError):
                        row[key] = prop_value  # keep non-numeric values as-is
            
            if not displacements:
                continue

            for disp in displacements:
                try:
                    id_elem = disp.get("IdElement")
                    row[f"Ux_{id_elem}"] = float(disp.get("Ux", 0))
                    row[f"Uy_{id_elem}"] = float(disp.get("Uy", 0))
                    row[f"Uz_{id_elem}"] = float(disp.get("Uz", 0))
                except (TypeError, ValueError):
                    continue
            
            try:
                row['R1'] = output_data['Reactions']['R1']
                row['R2'] = output_data['Reactions']['R2']
                row['R3'] = output_data['Reactions']['R3']
            except:
                pass

            
            rows.append(row)
    
    return pd.DataFrame(rows)