from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import bmat, csc_matrix, diags


@dataclass(frozen=True)
class RadialGeometry:
    radius_m: np.ndarray
    volumes_m3_per_m: np.ndarray
    interface_areas_m2_per_m: np.ndarray
    surface_area_m2_per_m: float
    dr_m: float

    @property
    def node_count(self) -> int:
        return int(self.radius_m.size)


def build_radial_geometry(radius_cm: float, dr_cm: float) -> RadialGeometry:
    if radius_cm <= 0.0 or dr_cm <= 0.0:
        raise ValueError("radius_cm and dr_cm must be positive")
    intervals = int(round(radius_cm / dr_cm))
    if intervals < 1 or not np.isclose(intervals * dr_cm, radius_cm, rtol=0.0, atol=1e-12):
        raise ValueError("radius_cm must be an integer multiple of dr_cm")
    radius_m = np.linspace(0.0, radius_cm / 100.0, intervals + 1)
    dr_m = dr_cm / 100.0
    left_faces = np.maximum(0.0, radius_m - dr_m / 2.0)
    right_faces = np.minimum(radius_m[-1], radius_m + dr_m / 2.0)
    volumes = np.pi * (right_faces**2 - left_faces**2)
    interface_areas = 2.0 * np.pi * (radius_m[:-1] + dr_m / 2.0)
    return RadialGeometry(
        radius_m=radius_m,
        volumes_m3_per_m=volumes,
        interface_areas_m2_per_m=interface_areas,
        surface_area_m2_per_m=float(2.0 * np.pi * radius_m[-1]),
        dr_m=dr_m,
    )


def harmonic_mean(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    denominator = left + right
    result = np.zeros(np.broadcast_shapes(left.shape, right.shape), dtype=float)
    np.divide(2.0 * left * right, denominator, out=result, where=denominator != 0.0)
    return result


def interface_values(node_values: np.ndarray, mean: str) -> np.ndarray:
    node_values = np.asarray(node_values, dtype=float)
    if mean == "harmonic":
        return harmonic_mean(node_values[:-1], node_values[1:])
    if mean == "arithmetic":
        return 0.5 * (node_values[:-1] + node_values[1:])
    raise ValueError("interface_mean must be 'harmonic' or 'arithmetic'")


def internal_flux_numerator(
    values: np.ndarray,
    interface_transport: np.ndarray,
    geometry: RadialGeometry,
) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    numerator = np.zeros_like(values)
    flux = (
        np.asarray(interface_transport, dtype=float)
        * geometry.interface_areas_m2_per_m
        * (values[1:] - values[:-1])
        / geometry.dr_m
    )
    numerator[:-1] += flux
    numerator[1:] -= flux
    return numerator


def build_coupled_jacobian_sparsity(node_count: int) -> csc_matrix:
    if node_count < 2:
        raise ValueError("node_count must be at least two")
    tri = diags(
        [np.ones(node_count - 1), np.ones(node_count), np.ones(node_count - 1)],
        offsets=[-1, 0, 1],
        shape=(node_count, node_count),
        format="csc",
    )
    return bmat([[tri, tri], [tri, tri]], format="csc")


def sample_profiles(
    internal_radius_cm: np.ndarray,
    output_radius_cm: np.ndarray,
    profiles: np.ndarray,
) -> np.ndarray:
    internal_radius_cm = np.asarray(internal_radius_cm, dtype=float)
    output_radius_cm = np.asarray(output_radius_cm, dtype=float)
    profiles = np.asarray(profiles, dtype=float)
    indices = np.rint(output_radius_cm / (internal_radius_cm[1] - internal_radius_cm[0])).astype(int)
    if np.allclose(internal_radius_cm[indices], output_radius_cm, rtol=0.0, atol=1e-12):
        return profiles[:, indices]
    return np.vstack([np.interp(output_radius_cm, internal_radius_cm, row) for row in profiles])
