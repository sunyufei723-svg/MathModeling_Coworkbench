import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solver import (  # noqa: E402
    EnvironmentSeries,
    SolverConfig,
    build_coupled_jacobian_sparsity,
    build_radial_grid_cm,
    density,
    harmonic_mean,
    heat_capacity,
    moisture_diffusivity,
    radial_geometry,
    sample_to_output_grid,
    solve_problem2,
    thermal_conductivity,
)


class Problem2FvmBdfTests(unittest.TestCase):
    def test_appendix3_empirical_formulas(self):
        c = np.array([2.55])
        t_c = np.array([28.0])
        expected_d = 2.4e-3 * np.exp(-0.45 / 2.55) * np.exp(-3850.0 / (28.0 + 273.15))

        self.assertAlmostEqual(float(density(c)[0]), 650.0 + 128.0 * 2.55)
        self.assertAlmostEqual(float(heat_capacity(c)[0]), 1450.0 + 2736.0 * 2.55 / 3.55)
        self.assertAlmostEqual(float(thermal_conductivity(c)[0]), 0.21 + 0.38 * 2.55 / 3.55)
        self.assertAlmostEqual(float(moisture_diffusivity(c, t_c)[0]), expected_d)

    def test_harmonic_mean(self):
        left = np.array([2.0, 4.0])
        right = np.array([4.0, 0.0])
        result = harmonic_mean(left, right)

        self.assertTrue(np.allclose(result, [8.0 / 3.0, 0.0]))

    def test_control_volumes_cover_the_cross_section(self):
        radius_m = 0.02
        _, volumes, interface_areas = radial_geometry(radius_m, 0.001)

        self.assertAlmostEqual(float(volumes.sum()), float(np.pi * radius_m**2))
        self.assertEqual(len(volumes), 21)
        self.assertEqual(len(interface_areas), 20)
        self.assertGreater(volumes[0], 0.0)
        self.assertGreater(volumes[-1], 0.0)

    def test_coupled_jacobian_has_four_tridiagonal_blocks(self):
        node_count = 21
        pattern = build_coupled_jacobian_sparsity(node_count)

        self.assertEqual(pattern.shape, (42, 42))
        self.assertNotEqual(pattern[10, 10], 0.0)
        self.assertNotEqual(pattern[10, 31], 0.0)
        self.assertNotEqual(pattern[31, 10], 0.0)
        self.assertEqual(pattern[0, 5], 0.0)

    def test_internal_and_output_grids_are_separate(self):
        internal = build_radial_grid_cm(2.0, 0.025)
        output = build_radial_grid_cm(2.0, 0.1)
        values = np.vstack([internal, 2.0 * internal])

        sampled = sample_to_output_grid(internal, output, values)

        self.assertEqual(len(internal), 81)
        self.assertEqual(len(output), 21)
        self.assertTrue(np.allclose(sampled[0], output))
        self.assertTrue(np.allclose(sampled[1], 2.0 * output))

    def test_short_coupled_bdf_run_is_finite_and_physical(self):
        environment = EnvironmentSeries(
            time_s=np.array([0.0, 120.0]),
            temperature_c=np.array([28.0, 40.0]),
            moisture=np.array([0.01963, 0.021]),
        )
        config = SolverConfig(
            internal_dr_cm=0.1,
            output_dr_cm=0.1,
            duration_s=120,
            output_dt_s=1.0,
            max_time_step_s=5.0,
        )

        result = solve_problem2(environment, config)

        self.assertEqual(result.temperature_c.shape, (121, 21))
        self.assertEqual(result.moisture.shape, (121, 21))
        self.assertTrue(np.isfinite(result.temperature_c).all())
        self.assertTrue(np.isfinite(result.moisture).all())
        self.assertGreater(result.temperature_c[-1, -1], result.temperature_c[-1, 0])
        self.assertLess(result.moisture[-1, -1], result.moisture[-1, 0])
        self.assertGreaterEqual(result.moisture.min(), 0.0)
        self.assertEqual(result.diagnostics.state_size, 42)


if __name__ == "__main__":
    unittest.main()
