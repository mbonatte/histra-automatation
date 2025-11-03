import sqlite3
import pandas as pd
import gc
import time

def get_dataframe(db_path, table_name):
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table_name};", conn)
    df = df.copy()   # fully materialize
    del conn         # drop any lingering reference
    gc.collect()     # force cleanup of SQLite internals
    time.sleep(0.1)  # give Windows a moment to release file handle
    return df

def get_model_points_displacement(db_path, analysis_key, id_element=None, step=None):
    # id_element == Node Key
    sample = get_dataframe(db_path, "DisplModelPoints")
    
    if id_element:
        sample = sample[sample['IdElement'] == id_element]
    
    sample = sample[sample['AnalysisKey'] == analysis_key]
    
    if step is None:
        step = sample['Step'].max()
    sample = sample[sample['Step'] == step]
    sample = sample[['IdElement', 'Ux','Uy','Uz']]
    
    try:
        return {"Displacements": sample.to_dict('records')}
    except Exception as e:
        return None


def get_reactions(db_path, analysis_key, step=None):
    sample = get_dataframe(db_path, "ReactionSumStates")
    
    sample = sample[sample['AnalysisKey'] == analysis_key]
    
    if step is None:
        step = sample['Step'].max()
    sample = sample[sample['Step'] == step]
    sample = sample[['R1','R2','R3']]

    if sample.empty:
        return {"Reactions": {}}

    return {"Reactions": sample.to_dict('records')[0]}
    

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