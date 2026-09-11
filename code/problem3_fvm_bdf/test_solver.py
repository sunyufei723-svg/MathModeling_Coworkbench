import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fvm import (
    build_coupled_jacobian_sparsity,
    build_radial_geometry,
    harmonic_mean,
    interface_values,
    internal_flux_numerator,
)
from model import EnvironmentSeries, PostBoundary, moisture_diffusivity
from solver_bdf import SolverConfig, build_coupled_rhs, drying_event_value, solve_problem3_bdf
from solver_be import BESolverConfig, coupled_backward_euler_step


class Problem3ImprovedTests(unittest.TestCase):
    def setUp(self):
        self.environment = EnvironmentSeries(
            np.array([0.0, 10.0]),
            np.array([50.0, 50.0]),
            np.array([0.05, 0.05]),
        )

    def test_appendix3_diffusivity_uses_division_and_kelvin(self):
        expected = 2.4e-3 * np.exp(-0.45 / 2.55) * np.exp(-3850.0 / (50.0 + 273.15))
        actual = float(moisture_diffusivity(np.array([2.55]), np.array([50.0]))[0])
        self.assertAlmostEqual(actual, expected, places=18)

    def test_geometry_volumes_sum_to_cylinder_cross_section(self):
        geometry = build_radial_geometry(2.0, 0.025)
        self.assertAlmostEqual(
            float(np.sum(geometry.volumes_m3_per_m)),
            np.pi * (0.02**2),
            places=15,
        )
        self.assertAlmostEqual(float(geometry.radius_m[0]), 0.0)
        self.assertAlmostEqual(float(geometry.radius_m[-1]), 0.02)

    def test_geometry_rejects_noninteger_radius_ratio(self):
        with self.assertRaises(ValueError):
            build_radial_geometry(2.0, 0.03)

    def test_harmonic_mean_and_zero_denominator(self):
        result = harmonic_mean(np.array([1.0, 0.0]), np.array([3.0, 0.0]))
        np.testing.assert_allclose(result, np.array([1.5, 0.0]))
        arithmetic = interface_values(np.array([1.0, 3.0]), "arithmetic")
        np.testing.assert_allclose(arithmetic, np.array([2.0]))

    def test_internal_fluxes_cancel_exactly(self):
        geometry = build_radial_geometry(2.0, 0.1)
        values = np.linspace(2.0, 0.1, geometry.node_count)
        numerator = internal_flux_numerator(values, np.ones(geometry.node_count - 1), geometry)
        self.assertAlmostEqual(float(np.sum(numerator)), 0.0, places=15)

    def test_closed_surface_rhs_conserves_total_moisture(self):
        geometry = build_radial_geometry(2.0, 0.1)
        config = replace(SolverConfig(), internal_dr_cm=0.1, mass_transfer_m_s=0.0)
        state = np.concatenate(
            [np.linspace(28.0, 50.0, geometry.node_count), np.linspace(2.55, 0.5, geometry.node_count)]
        )
        rhs = build_coupled_rhs(geometry, self.environment, PostBoundary(50.0, 0.05), config)
        moisture_rate = rhs(5.0, state)[geometry.node_count:]
        self.assertAlmostEqual(
            float(np.sum(moisture_rate * geometry.volumes_m3_per_m)),
            0.0,
            places=15,
        )

    def test_event_uses_full_profile_maximum(self):
        state = np.array([40.0, 40.0, 40.0, 0.10, 0.16, 0.08])
        self.assertAlmostEqual(drying_event_value(state, 3, 0.15), 0.01)

    def test_jacobian_has_four_nearest_neighbour_blocks(self):
        pattern = build_coupled_jacobian_sparsity(5)
        self.assertEqual(pattern.shape, (10, 10))
        self.assertEqual(pattern.nnz, 52)

    def test_bdf_event_and_regular_report_grid(self):
        config = SolverConfig(
            radius_cm=0.1,
            internal_dr_cm=0.05,
            output_dr_cm=0.05,
            output_interval_s=10,
            initial_temperature_c=50.0,
            initial_moisture=0.16,
            mass_transfer_m_s=1e-6,
            relative_tolerance=1e-8,
            temperature_absolute_tolerance=1e-9,
            moisture_absolute_tolerance=1e-11,
            max_time_step_s=1.0,
            initial_time_limit_s=200.0,
            fallback_time_limit_s=400.0,
        )
        result = solve_problem3_bdf(self.environment, config)
        self.assertTrue(np.all(np.mod(result.time_s, 10.0) == 0.0))
        self.assertLess(float(result.moisture[-1].max()), 0.15)
        self.assertLessEqual(float(result.event_internal_moisture.max()), 0.1500000001)
        self.assertEqual(result.report_end_time_s, int(result.time_s[-1]))

    def test_picard_failure_is_not_silent(self):
        geometry = build_radial_geometry(0.1, 0.05)
        config = BESolverConfig(
            radius_cm=0.1,
            internal_dr_cm=0.05,
            maximum_picard_iterations=1,
            temperature_picard_tolerance=1e-30,
            moisture_picard_tolerance=1e-30,
        )
        with self.assertRaises(RuntimeError):
            coupled_backward_euler_step(
                np.full(geometry.node_count, 28.0),
                np.full(geometry.node_count, 2.55),
                1.0,
                1.0,
                geometry,
                self.environment,
                PostBoundary(50.0, 0.05),
                config,
            )


if __name__ == "__main__":
    unittest.main()
