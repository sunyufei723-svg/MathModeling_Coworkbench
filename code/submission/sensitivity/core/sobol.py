from __future__ import annotations

import numpy as np

try:
    from .pce import PCEModel, design_matrix, fit_pce, latin_hypercube, total_degree_indices
except ImportError:
    from pce import PCEModel, design_matrix, fit_pce, latin_hypercube, total_degree_indices  # type: ignore


def analytical_sobol(model: PCEModel) -> dict[str, object]:
    variance = float(np.sum(model.coefficients[1:] ** 2))
    if variance <= 0.0:
        raise ValueError("PCE variance must be positive")
    rows = []
    for index, name in enumerate(model.parameter_names):
        active = model.multi_indices > 0
        first_mask = active[:, index] & (np.sum(active, axis=1) == 1)
        total_mask = active[:, index]
        rows.append(
            {
                "parameter": name,
                "first_order": float(np.sum(model.coefficients[first_mask] ** 2) / variance),
                "total_order": float(np.sum(model.coefficients[total_mask] ** 2) / variance),
            }
        )
    interactions = []
    active = model.multi_indices > 0
    for left in range(len(model.parameter_names)):
        for right in range(left + 1, len(model.parameter_names)):
            mask = active[:, left] & active[:, right] & (np.sum(active, axis=1) == 2)
            value = float(np.sum(model.coefficients[mask] ** 2) / variance)
            interactions.append(
                {
                    "parameter_left": model.parameter_names[left],
                    "parameter_right": model.parameter_names[right],
                    "second_order": value,
                }
            )
    interactions.sort(key=lambda item: float(item["second_order"]), reverse=True)
    rows.sort(key=lambda item: float(item["total_order"]), reverse=True)
    return {
        "pce_variance_h2": variance,
        "rows": rows,
        "sum_first_order": float(sum(float(row["first_order"]) for row in rows)),
        "interactions": interactions,
    }


def saltelli_crosscheck(model: PCEModel, sample_count: int = 100000, seed: int = 20260914) -> dict[str, object]:
    dimension = len(model.parameter_names)
    a = latin_hypercube(sample_count, dimension, seed)
    b = latin_hypercube(sample_count, dimension, seed + 1)
    fa = model.predict(a)
    fb = model.predict(b)
    variance = float(np.var(np.concatenate([fa, fb]), ddof=1))
    rows = []
    for index, name in enumerate(model.parameter_names):
        ab = a.copy()
        ab[:, index] = b[:, index]
        fab = model.predict(ab)
        first = float(np.mean(fb * (fab - fa)) / variance)
        total = float(0.5 * np.mean((fa - fab) ** 2) / variance)
        rows.append({"parameter": name, "first_order": first, "total_order": total})
    return {"sample_count": sample_count, "rows": rows}


def bootstrap_sobol(
    train_points: np.ndarray,
    train_outputs: np.ndarray,
    parameter_names: tuple[str, ...],
    degree: int,
    repetitions: int = 500,
    seed: int = 20260915,
) -> dict[str, dict[str, list[float]]]:
    rng = np.random.default_rng(seed)
    multi_indices = total_degree_indices(len(parameter_names), degree)
    matrix = design_matrix(np.asarray(train_points, dtype=float), multi_indices)
    pseudo_inverse = np.linalg.pinv(matrix)
    base_model = PCEModel(
        parameter_names,
        degree,
        multi_indices,
        pseudo_inverse @ np.asarray(train_outputs, dtype=float),
    )
    fitted = base_model.predict(train_points)
    residuals = np.asarray(train_outputs, dtype=float) - fitted
    residuals = residuals - np.mean(residuals)
    first: dict[str, list[float]] = {name: [] for name in parameter_names}
    total: dict[str, list[float]] = {name: [] for name in parameter_names}
    for _ in range(repetitions):
        bootstrap_outputs = fitted + rng.choice(residuals, size=len(residuals), replace=True)
        model = PCEModel(
            parameter_names,
            degree,
            multi_indices,
            pseudo_inverse @ bootstrap_outputs,
        )
        result = analytical_sobol(model)
        for row in result["rows"]:
            name = str(row["parameter"])
            first[name].append(float(row["first_order"]))
            total[name].append(float(row["total_order"]))
    return {
        name: {
            "first_order_95_interval": [
                float(np.quantile(first[name], 0.025)),
                float(np.quantile(first[name], 0.975)),
            ],
            "total_order_95_interval": [
                float(np.quantile(total[name], 0.025)),
                float(np.quantile(total[name], 0.975)),
            ],
        }
        for name in parameter_names
    }


def merge_sobol_checks(
    analytical: dict[str, object],
    saltelli: dict[str, object],
) -> dict[str, object]:
    saltelli_by_name = {str(row["parameter"]): row for row in saltelli["rows"]}
    comparisons = []
    for row in analytical["rows"]:
        name = str(row["parameter"])
        numerical = saltelli_by_name[name]
        comparisons.append(
            {
                "parameter": name,
                "first_order_absolute_difference": abs(
                    float(row["first_order"]) - float(numerical["first_order"])
                ),
                "total_order_absolute_difference": abs(
                    float(row["total_order"]) - float(numerical["total_order"])
                ),
            }
        )
    maximum = max(
        max(item["first_order_absolute_difference"], item["total_order_absolute_difference"])
        for item in comparisons
    )
    return {
        "comparisons": comparisons,
        "maximum_absolute_difference": float(maximum),
        "passed": bool(maximum < 0.02),
    }
