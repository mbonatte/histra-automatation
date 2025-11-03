import json
import numpy as np
import pandas as pd

# ---- (A) Optional: load/flatten your scenarios_results.json into a table
def load_scenarios_json(path):
    """
    Returns a DataFrame with one row per scenario.
    Columns include Uz and a flat set of numeric material properties with a
    <MaterialName>_<field> naming scheme (e.g., 'Damaged_Ehor', 'Piers_w', etc.).
    """
    with open(path, "r") as f:
        data = json.load(f)

    rows = []
    for scen in data:
        row = {}
        # Output(s)
        if "Output" in scen and "Vert" in scen["Output"] and "Uz" in scen["Output"]["Vert"]:
            row["Uz"] = scen["Output"]["Vert"]["Uz"]
        # Materials (flatten numerics)
        for m in scen.get("Materials", []):
            mname = (m.get("Name") or f"Key{m.get('Key','')}").strip().replace(" ", "_")
            for k, v in m.items():
                if k in ("Key", "Name"):
                    continue
                try:
                    row[f"{mname}_{k}"] = float(v)
                except Exception:
                    # non-numeric -> skip
                    pass
        rows.append(row)
    return pd.DataFrame(rows)


def _normalize_array(X: np.ndarray, scale: str = "zscore") -> np.ndarray:
    """Normalize a numeric array using z-score or min-max scaling."""
    mask_const = np.nanstd(X, axis=0) < 1e-12

    if scale == "zscore":
        mu, sd = np.nanmean(X, axis=0), np.nanstd(X, axis=0)
        sd[sd < 1e-12] = 1.0
        Z = (X - mu) / sd
    elif scale == "minmax":
        mn, mx = np.nanmin(X, axis=0), np.nanmax(X, axis=0)
        rng = mx - mn
        rng[rng < 1e-12] = 1.0
        Z = (X - mn) / rng
    else:
        raise ValueError("scale must be 'zscore' or 'minmax'")

    Z[:, mask_const] = 0.0
    return Z

def _find_neighbors(Z: np.ndarray, eps: float) -> list[list[int]]:
    """Find neighbors within a radius using cKDTree, sklearn, or fallback O(n^2)."""
    try:
        from scipy.spatial import cKDTree
        return cKDTree(Z).query_ball_point(Z, r=eps)
    except Exception:
        try:
            from sklearn.neighbors import NearestNeighbors
            nn = NearestNeighbors(radius=eps, algorithm="kd_tree").fit(Z)
            return nn.radius_neighbors(return_distance=False)
        except Exception:
            D = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(axis=2))
            return [list(np.where(D[i] <= eps)[0]) for i in range(Z.shape[0])]

def _build_clusters(order, neighbors_within):
    """Cluster points by proximity."""
    n = len(neighbors_within)
    kept = np.zeros(n, dtype=bool)
    removed = np.zeros(n, dtype=bool)
    seen = np.zeros(n, dtype=bool)
    clusters = []

    for i in order:
        if seen[i]:
            continue
        cluster = sorted(set(neighbors_within[i]) | {i})
        seen[cluster] = True
        kept[i] = True
        removed[[j for j in cluster if j != i]] = True
        clusters.append(cluster)

    return kept, removed, clusters

def normalized_distance_filter(
    df: pd.DataFrame,
    cols=None,
    scale: str = "zscore",   # 'zscore' or 'minmax'
    eps: float = 0.15,       # radius in normalized space for "too close"
    keep: str = "first",     # 'first' or 'random'
    random_state: int | None = None
):
    """
    Remove rows that are within 'eps' normalized Euclidean distance of each other.
    Returns (df_filtered, kept_index, removed_index, clusters)
    """
    if cols is None:
        cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    X = df[cols].to_numpy(dtype=float)

    Z = _normalize_array(X, scale)
    
    n = Z.shape[0]
    order = np.arange(n)
    if keep == "random":
        rng = np.random.default_rng(random_state)
        rng.shuffle(order)

    neighbors_within = _find_neighbors(Z, eps)
    kept, removed, clusters = _build_clusters(order, neighbors_within)
    
    df_filtered = df.iloc[kept].copy()

    return df_filtered, df.index[kept], df.index[removed], clusters

def normalized_close_pairs(df, cols=None, scale="zscore", eps=0.15):
    """Return list of (i, j) index pairs where normalized distance <= eps."""
    if cols is None:
        cols = df.select_dtypes(include=[np.number]).columns.tolist()
    Z = _normalize_array(df[cols].to_numpy(float), scale)
    neighbors = _find_neighbors(Z, eps)

    pairs = {(df.index[i], df.index[j]) for i, lst in enumerate(neighbors) for j in lst if j > i}
    return sorted(pairs)
