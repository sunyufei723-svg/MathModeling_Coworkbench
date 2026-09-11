import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from environment import EnvironmentSeries, PostBoundary
from fvm import (
    build_coupled_jacobian_sparsity,
    build_reference_geometry,
    harmonic_mean,
    interface_values,
    internal_flux_numerator,
)
from model import density, heat_capacity, moisture_diffusivity, thermal_conductivity
from radius import RadiusSeries
from solver_bdf import SolverConfig, build_coupled_rhs, drying_event_value, solve_problem4_bdf
from solver_be import BESolverConfig, coupled_backward_euler_step


class Problem4FvmBdfTests(unittest.TestCase):
    def setUp(self):
        self.environment = EnvironmentSeries(
            np.array([0.0, 10.0]),
            np.array([50.0, 50.0]),
            np.array([0.05, 0.05]),
        )
        self.radius = RadiusSeries(
            np.array([0.0, 10000.0]),
            np.array([2.0, 1.5]),
        )

    def test_appendix4_properties(self):
        c = np.array([2.55])
        t = np.array([50.0])
        self.assertAlmostEqual(float(density(c)[0]), 760.0 + 90.0 * 2.55)
        self.assertAlmostEqual(float(heat_capacity(c)[0]), 1850.0 + 2150.0 * 2.55 / 3.55)
        self.assertAlmostEqual(float(thermal_conductivity(c)[0]), 0.12 + 0.20 * 2.55 / 3.55)
        expected_d = 4.2e-4 * np.exp(-0.30 / 2.55) * np.exp(-3850.0 / 323.15)
        self.assertAlmostEqual(float(moisture_diffusivity(c, t)[0]), expected_d, places=18)

    def test_reference_geometry_is_exact_half_disk_weight(self):
        geometry = build_reference_geometry(81)
        self.assertAlmostEqual(float(np.sum(geometry.volumes_hat)), 0.5, places=14)
        self.assertEqual(float(geometry.xi[0]), 0.0)
        self.assertEqual(float(geometry.xi[-1]), 1.0)

    def test_harmonic_mean_and_flux_cancellation(self):
        self.assertTrue(np.allclose(harmonic_mean(np.array([1.0, 0.0]), np.array([3.0, 0.0])), [1.5, 0.0]))
        geometry = build_reference_geometry(21)
        values = np.linspace(2.0, 0.1, geometry.node_count)
        numerator = internal_flux_numerator(values, np.ones(geometry.node_count - 1), geometry)
        self.assertAlmostEqual(float(np.sum(numerator)), 0.0, places=15)
        self.assertTrue(np.allclose(interface_values(np.array([1.0, 3.0]), "arithmetic"), [2.0]))

    def test_material_coordinate_constant_field_survives_radius_change(self):
        geometry = build_reference_geometry(21)
        config = replace(
            SolverConfig(node_count=21),
            heat_transfer_w_m2_k=0.0,
            mass_transfer_m_s=0.0,
        )
        state = np.concatenate([np.full(21, 28.0), np.full(21, 2.55)])
        rhs = build_coupled_rhs(
            geometry,
            self.environment,
            PostBoundary(50.0, 0.05),
            self.radius,
            config,
        )
        np.testing.assert_allclose(rhs(5.0, state), 0.0, atol=1e-15)

    def test_closed_surface_weighted_moisture_rate_is_zero(self):
        geometry = build_reference_geometry(21)
        config = replace(SolverConfig(node_count=21), mass_transfer_m_s=0.0)
        state = np.concatenate([np.linspace(28.0, 50.0, 21), np.linspace(2.55, 0.5, 21)])
        rhs = build_coupled_rhs(
            geometry,
            self.environment,
            PostBoundary(50.0, 0.05),
            self.radius,
            config,
        )
        moisture_rate = rhs(5.0, state)[21:]
        self.assertAlmostEqual(float(np.sum(moisture_rate * geometry.volumes_hat)), 0.0, places=15)

    def test_event_uses_whole_profile(self):
        state = np.array([40.0, 40.0, 40.0, 0.10, 0.16, 0.08])
        self.assertAlmostEqual(drying_event_value(state, 3, 0.15), 0.01)

    def test_jacobian_has_four_nearest_neighbour_blocks(self):
        pattern = build_coupled_jacobian_sparsity(5)
        self.assertEqual(pattern.shape, (10, 10))
        self.assertEqual(pattern.nnz, 52)

    def test_radius_linear_and_pchip_clamp(self):
        self.assertAlmostEqual(self.radius.radius_cm_at(5000.0), 1.75)
        self.assertAlmostEqual(self.radius.radius_cm_at(20000.0), 1.5)
        pchip = self.radius.with_interpolation("pchip")
        self.assertAlmostEqual(pchip.radius_cm_at(5000.0), 1.75)
        self.assertAlmostEqual(pchip.radius_rate_cm_s_at(20000.0), 0.0)

    def test_bdf_continuous_event_and_strict_report_time(self):
        environment = EnvironmentSeries(
            np.array([0.0, 1.0]),
            np.array([50.0, 50.0]),
            np.array([0.05, 0.05]),
        )
        radius = RadiusSeries(np.array([0.0, 5000.0]), np.array([0.1, 0.1]))
        config = SolverConfig(
            node_count=5,
            sample_interval_s=10,
            report_interval_s=10,
            fixed_distances_cm=(0.0,),
            initial_temperature_c=50.0,
            initial_moisture=0.16,
            mass_transfer_m_s=1e-6,
            max_time_step_s=2.0,
            initial_time_limit_s=2000.0,
            fallback_time_limit_s=4000.0,
        )
        result = solve_problem4_bdf(environment, radius, config)
        self.assertLess(result.report_max_moisture, 0.15)
        self.assertGreaterEqual(result.previous_report_max_moisture, 0.15 - 1e-10)
        self.assertGreater(result.report_end_time_s, result.drying_event_time_s)
        self.assertLessEqual(float(np.max(result.event_moisture_internal)), 0.1500000001)

    def test_picard_failure_is_not_silent(self):
        geometry = build_reference_geometry(5)
        config = BESolverConfig(
            node_count=5,
            maximum_picard_iterations=1,
            temperature_picard_tolerance=1e-30,
            moisture_picard_tolerance=1e-30,
        )
        with self.assertRaises(RuntimeError):
            coupled_backward_euler_step(
                np.full(5, 28.0),
                np.full(5, 2.55),
                1.0,
                1.0,
                geometry,
                self.environment,
                PostBoundary(50.0, 0.05),
                self.radius,
                config,
            )


if __name__ == "__main__":
    unittest.main()
