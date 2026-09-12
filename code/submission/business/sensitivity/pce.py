from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
from numpy.polynomial.legendre import legval


def latin_hypercube(n: int, dimension: int, seed: int) -> np.ndarray:
    if n < 1 or dimension < 1:
        raise ValueError("n and dimension must be positive")
    rng = np.random.default_rng(seed)
    sample = np.empty((n, dimension), dtype=float)
    for column in range(dimension):
        sample[:, column] = (rng.permutation(n) + rng.random(n)) / n
    return sample


def total_degree_indices(dimension: int, degree: int) -> np.ndarray:
    if dimension < 1 or degree < 0:
        raise ValueError("invalid PCE dimension or degree")
    return np.asarray(
        [values for values in product(range(degree + 1), repeat=dimension) if sum(values) <= degree],
        dtype=int,
    )


def normalized_legendre(degree: int, unit_values: np.ndarray) -> np.ndarray:
    coefficients = np.zeros(degree + 1, dtype=float)
    coefficients[-1] = 1.0
    return np.sqrt(2.0 * degree + 1.0) * legval(2.0 * np.asarray(unit_values) - 1.0, coefficients)


def design_matrix(unit_points: np.ndarray, multi_indices: np.ndarray) -> np.ndarray:
    unit_points = np.asarray(unit_points, dtype=float)
    if unit_points.ndim != 2 or multi_indices.ndim != 2:
        raise ValueError("PCE points and indices must be two-dimensional")
    if unit_points.shape[1] != multi_indices.shape[1]:
        raise ValueError("PCE point and multi-index dimensions differ")
    maximum_degree = int(np.max(multi_indices, initial=0))
    basis = np.empty((unit_points.shape[1], maximum_degree + 1, unit_points.shape[0]), dtype=float)
    for dimension in range(unit_points.shape[1]):
        for degree in range(maximum_degree + 1):
            basis[dimension, degree] = normalized_legendre(degree, unit_points[:, dimension])
    matrix = np.ones((unit_points.shape[0], multi_indices.shape[0]), dtype=float)
    for term_index, alpha in enumerate(multi_indices):
        for dimension, degree in enumerate(alpha):
            matrix[:, term_index] *= basis[dimension, degree]
    return matrix


@dataclass(frozen=True)
class PCEModel:
    parameter_names: tuple[str, ...]
    degree: int
    multi_indices: np.ndarray
    coefficients: np.ndarray

    def predict(self, unit_points: np.ndarray) -> np.ndarray:
        return design_matrix(np.asarray(unit_points, dtype=float), self.multi_indices) @ self.coefficients

    def as_dict(self) -> dict[str, object]:
        return {
            "parameter_names": list(self.parameter_names),
            "degree": int(self.degree),
            "multi_indices": self.multi_indices.tolist(),
            "coefficients": self.coefficients.tolist(),
        }


def fit_pce(
    unit_points: np.ndarray,
    outputs: np.ndarray,
    parameter_names: tuple[str, ...],
    degree: int,
) -> PCEModel:
    points = np.asarray(unit_points, dtype=float)
    outputs = np.asarray(outputs, dtype=float)
    indices = total_degree_indices(points.shape[1], degree)
    matrix = design_matrix(points, indices)
    if points.shape[0] < indices.shape[0]:
        raise ValueError("PCE is underdetermined")
    coefficients, _, rank, _ = np.linalg.lstsq(matrix, outputs, rcond=None)
    if rank < indices.shape[0]:
        raise RuntimeError("PCE design matrix is rank deficient")
    return PCEModel(parameter_names, degree, indices, coefficients)


def validation_metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    observed = np.asarray(observed, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    errors = predicted - observed
    residual_sum = float(np.sum(errors**2))
    total_sum = float(np.sum((observed - np.mean(observed)) ** 2))
    output_range = float(np.ptp(observed))
    rmse = float(np.sqrt(np.mean(errors**2)))
    r_squared = 1.0 - residual_sum / max(total_sum, 1.0e-30)
    return {
        "r_squared": float(r_squared),
        "q_squared_independent": float(r_squared),
        "rmse_h": rmse,
        "mae_h": float(np.mean(np.abs(errors))),
        "maximum_absolute_error_h": float(np.max(np.abs(errors))),
        "normalized_rmse_by_range": rmse / max(output_range, 1.0e-30),
        "observed_range_h": output_range,
    }


def validation_passed(metrics: dict[str, float]) -> bool:
    return bool(
        metrics["q_squared_independent"] >= 0.99
        and metrics["normalized_rmse_by_range"] <= 0.02
        and metrics["maximum_absolute_error_h"] <= 0.1
    )
