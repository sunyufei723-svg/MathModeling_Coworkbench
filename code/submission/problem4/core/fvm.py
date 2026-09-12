from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import bmat, csc_matrix, diags


@dataclass(frozen=True)
class ReferenceGeometry:
    xi: np.ndarray
    volumes_hat: np.ndarray
    interface_areas_hat: np.ndarray
    dxi: float

    @property
    def node_count(self) -> int:
        return int(self.xi.size)


def build_reference_geometry(node_count: int) -> ReferenceGeometry:
    if node_count < 2:
        raise ValueError("node_count must be at least two")
    xi = np.linspace(0.0, 1.0, node_count)
    dxi = 1.0 / (node_count - 1)
    left_faces = np.maximum(0.0, xi - 0.5 * dxi)
    right_faces = np.minimum(1.0, xi + 0.5 * dxi)
    volumes_hat = 0.5 * (right_faces**2 - left_faces**2)
    interface_areas_hat = xi[:-1] + 0.5 * dxi
    return ReferenceGeometry(xi, volumes_hat, interface_areas_hat, dxi)


def harmonic_mean(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    denominator = left + right
    result = np.zeros(np.broadcast_shapes(left.shape, right.shape), dtype=float)
    np.divide(2.0 * left * right, denominator, out=result, where=np.abs(denominator) > 0.0)
    return result


def interface_values(node_values: np.ndarray, mean: str) -> np.ndarray:
    values = np.asarray(node_values, dtype=float)
    if mean == "harmonic":
        return harmonic_mean(values[:-1], values[1:])
    if mean == "arithmetic":
        return 0.5 * (values[:-1] + values[1:])
    raise ValueError("mean must be 'harmonic' or 'arithmetic'")


def internal_flux_numerator(
    values: np.ndarray,
    interface_transport: np.ndarray,
    geometry: ReferenceGeometry,
) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    flux = (
        np.asarray(interface_transport, dtype=float)
        * geometry.interface_areas_hat
        * (values[1:] - values[:-1])
        / geometry.dxi
    )
    numerator = np.zeros_like(values)
    numerator[:-1] += flux
    numerator[1:] -= flux
    return numerator


def build_coupled_jacobian_sparsity(node_count: int) -> csc_matrix:
    if node_count < 2:
        raise ValueError("node_count must be at least two")
    tri = diags(
        [np.ones(node_count - 1), np.ones(node_count), np.ones(node_count - 1)],
        [-1, 0, 1],
        shape=(node_count, node_count),
        format="csc",
    )
    return bmat([[tri, tri], [tri, tri]], format="csc")


def sample_physical_profile(
    profile: np.ndarray,
    geometry: ReferenceGeometry,
    radius_cm: float,
    fixed_distances_cm: np.ndarray,
) -> np.ndarray:
    output = np.full(len(fixed_distances_cm) + 1, np.nan, dtype=float)
    for index, distance_cm in enumerate(fixed_distances_cm):
        if distance_cm <= radius_cm + 1.0e-12:
            output[index] = float(np.interp(distance_cm / radius_cm, geometry.xi, profile))
    output[-1] = float(profile[-1])
    return output
