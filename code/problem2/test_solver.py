import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solver import (
    EnvironmentSeries,
    SolverConfig,
    build_radial_grid_cm,
    heat_capacity,
    density,
    moisture_diffusivity,
    thermal_conductivity,
    solve_problem2,
)


class Problem2SolverTests(unittest.TestCase):
    def test_empirical_formulas_use_division_by_c_and_kelvin_temperature(self):
        c = np.array([2.55])
        t_c = np.array([28.0])
        t_k = t_c + 273.15

        self.assertAlmostEqual(float(density(c)[0]), 650 + 128 * 2.55)
        self.assertAlmostEqual(float(heat_capacity(c)[0]), 1450 + 2736 * 2.55 / 3.55)
        self.assertAlmostEqual(float(thermal_conductivity(c)[0]), 0.21 + 0.38 * 2.55 / 3.55)
        expected_d = 2.4e-3 * np.exp(-0.45 / 2.55) * np.exp(-3850 / float(t_k[0]))
        self.assertAlmostEqual(float(moisture_diffusivity(c, t_c)[0]), expected_d)

    def test_grid_matches_required_spacing(self):
        grid = build_radial_grid_cm(radius_cm=2.0, dr_cm=0.1)
        self.assertEqual(len(grid), 21)
        self.assertTrue(np.allclose(grid[[0, 5, 10, 15, 20]], [0, 0.5, 1, 1.5, 2]))

    def test_solver_runs_three_hours_and_surface_responds_more_than_center(self):
        env = EnvironmentSeries(
            time_s=np.array([0.0, 10800.0]),
            temperature_c=np.array([28.0, 50.0]),
            moisture=np.array([0.01963, 0.05000]),
        )
        result = solve_problem2(env, SolverConfig(duration_s=600, dt_s=1.0, dr_cm=0.1))

        self.assertEqual(result.temperature_c.shape, (601, 21))
        self.assertEqual(result.moisture.shape, (601, 21))
        self.assertTrue(np.isfinite(result.temperature_c).all())
        self.assertTrue(np.isfinite(result.moisture).all())
        self.assertGreater(result.temperature_c[-1, -1], result.temperature_c[-1, 0])
        self.assertLess(result.moisture[-1, -1], result.moisture[-1, 0])
        self.assertGreaterEqual(result.moisture.min(), 0.0)


if __name__ == "__main__":
    unittest.main()
