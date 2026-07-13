import sqlite3
import pandas as pd
import gc
import time

def get_dataframe(db_path, table_name):
    conn = None
    try:
        # Explicitly open in read-only mode
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        df = pd.read_sql_query(f"SELECT * FROM {table_name};", conn)
        df = df.copy()  # fully materialize in memory
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            del conn
            gc.collect()     # force cleanup of SQLite internals
    
    return df

def get_model_points_displacement(db_path, analysis_key, id_element=None, step=None, all_steps=False, **kwargs):
    # id_element == Node Key
    sample = get_dataframe(db_path, "DisplModelPoints")
    sample = sample[sample['AnalysisKey'] == analysis_key]
    
    if id_element:
        sample = sample[sample['IdElement'] == id_element]
    
    if not all_steps:
        if step is None:
            step = sample['Step'].max()
        sample = sample[sample['Step'] == step]
        sample = sample[['IdElement', 'ParentKey', 'Step', 'Ux','Uy','Uz']]
        try:
            return {"Displacements": sample.to_dict('records')}
        except Exception as e:
            return None
    else:
        # Return all steps with reactions
        sample = sample[['IdElement', 'Step', 'Ux','Uy','Uz']]
        # Sort by step for clarity (optional)
        sample = sample.sort_values(by="Step")
        return {"Displacements": sample.to_dict('records')}
    

def get_reactions(db_path, analysis_key, step=None, all_steps=False, **kwargs):
    sample = get_dataframe(db_path, "ReactionSumStates")
    sample = sample[sample['AnalysisKey'] == analysis_key]

    if sample.empty:
        return {"Reactions": {}}
    
    if not all_steps:
        if step is None:
            step = sample['Step'].max()
        sample = sample[sample['Step'] == step]
        sample = sample[['Step', 'R1', 'R2', 'R3']]
        return {"Reactions": sample.to_dict('records')}
    else:
        # Return all steps with reactions
        sample = sample[['Step', 'R1', 'R2', 'R3']]
        # Sort by step for clarity (optional)
        sample = sample.sort_values(by="Step")
        return {"Reactions": sample.to_dict('records')}
    

def get_main_modal_contributions(db_path, analysis_key, top_n=1, **kwargs):
    """
    Get the modes with the main modal mass participation in X, Y, and Z.
    top_n : Number of dominant modes to return per direction.
    """

    df = get_dataframe(db_path, "ModalValues")

    df = df[df["AnalysisKey"] == analysis_key]

    if df.empty:
        return {
            "ModalContributions": {
                "X": [],
                "Y": [],
                "Z": [],
                "Cumulative": {}
            }
        }

    # Columns that are useful to understand each mode
    base_cols = [
        "Step", "Fn",
        # "GammaX", "GammaY", "GammaZ",
        # "MassaX", "MassaY", "MassaZ",
        # "MTotX", "MTotY", "MTotZ",
        "Mx_pcent", "My_pcent", "Mz_pcent",
        # "UMaxX", "UMaxY", "UMaxZ"
    ]

    # Keep only columns that actually exist
    base_cols = [c for c in base_cols if c in df.columns]

    def top_modes(direction_col):
        return (
            df.sort_values(by=direction_col, ascending=False)
              .head(top_n)[base_cols]
              .to_dict("records")
        )

    result = {
        "ModalContributions": {
            "X": top_modes("Mx_pcent"),
            "Y": top_modes("My_pcent"),
            "Z": top_modes("Mz_pcent"),
            "Cumulative": {
                "Mx_pcent": float(df["Mx_pcent"].sum()),
                "My_pcent": float(df["My_pcent"].sum()),
                "Mz_pcent": float(df["Mz_pcent"].sum())
            }
        }
    }

    return result

# tables_to_check = [
#     "DisplModelPoints",
#     "NodeCStates", "QuadStates", 
#     "RestraintStates", "ReactionSumStates",
#     "InterfaceStates",
#     "SpringStates"
# ]

# for t in tables_to_check:
#     try:
#         print(f"\n=== {t} ===")
#         # info = pd.read_sql_query(f"PRAGMA table_info({t});", conn)
#         # print(info[['name', 'type']])
#         sample = pd.read_sql_query(f"SELECT * FROM {t};", conn)
#         sample.to_csv(f"Result_{t}.csv", index=False)
#     except Exception as e:
#         print(f"⚠️ Could not read {t}: {e}")