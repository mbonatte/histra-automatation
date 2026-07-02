import numpy as np
from scipy.stats import qmc, norm

def build_scenarios(param_ranges, n_scenarios, analysis, correlations=None):
    if not param_ranges:
        return [{"Analysis": [analysis]} for _ in range(n_scenarios)]
    
    keys = list(param_ranges.keys())
    n_params = len(keys)
    key_index = {k: i for i, k in enumerate(keys)}

    # --- Build correlation matrix ---
    corr_matrix = np.eye(n_params)

    if correlations:
        for (a, b), rho in correlations.items():
            if a not in key_index or b not in key_index:
                raise KeyError(f"Unknown parameter(s): {a}, {b}")
            i, j = key_index[a], key_index[b]
            corr_matrix[i, j] = corr_matrix[j, i] = rho

    # Add a small jitter to diagonal to ensure positive definiteness
    corr_matrix += np.eye(n_params) * 1e-8
    
    
    # --- Latin Hypercube Sampling ---
    sampler = qmc.LatinHypercube(d=n_params)
    sample = sampler.random(n=n_scenarios)

    # Convert uniform [0,1] → normal (0,1)
    normal_sample = norm.ppf(sample)

    # Apply correlation
    L = np.linalg.cholesky(corr_matrix)
    correlated_normals = normal_sample @ L.T

    # Convert back to uniform [0,1]
    correlated_uniform = norm.cdf(correlated_normals)
    
    
    # --- Scale to parameter ranges ---
    l_bounds = [param_ranges[k][0] for k in keys]
    u_bounds = [param_ranges[k][1] for k in keys]
    scaled_sample = qmc.scale(correlated_uniform, l_bounds, u_bounds)

    # Helper to split "Material_Property"
    def parse_param_name(param):
        parts = param.split("_", 1)
        return parts if len(parts) == 2 else (parts[0], None)

    # --- Build scenarios ---
    scenarios = []
    for row in scaled_sample:
        material_values = dict(zip(keys, row))
        materials = {}
        for param, val in material_values.items():
            mat, prop = parse_param_name(param)
            if mat not in materials:
                materials[mat] = {"Name": mat}
            if prop:
                materials[mat][prop] = val
        scenarios.append({"Materials": list(materials.values()), "Analysis": [analysis]})
    
    return scenarios