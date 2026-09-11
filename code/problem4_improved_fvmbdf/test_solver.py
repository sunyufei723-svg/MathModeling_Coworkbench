import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solver import (
    EnvironmentSeries,
    RadiusSeries,
    SolverConfig,
    build_output_seconds,
    build_xi_grid,
    density,
    drying_complete,
    heat_capacity,
    moisture_diffusivity,
    solve_problem4,
    thermal_conductivity,
    _coupled_step,
    _face_harmonic_average,
    _implicit_radial_variable_step,
)
import run_problem4


class Problem4SolverTests(unittest.TestCase):
    def test_runner_writes_inside_improved_folder(self):
        self.assertEqual(run_problem4.MODULE_NAME, "problem4_improved_fvmbdf")
        self.assertEqual(run_problem4.PROJECT_ROOT.name, "MathModeling_Coworkbench_push_tmp2")
        self.assertEqual(
            run_problem4.OUTPUT_DIR,
            run_problem4.PROJECT_ROOT / "results" / "problem4_improved_fvmbdf",
        )

    def test_radius_series_interpolates_and_clamps_to_last(self):
        radius = RadiusSeries(
            time_s=np.array([0.0, 1800.0, 3600.0]),
            radius_cm=np.array([2.0, 1.873, 1.794]),
        )
        self.assertAlmostEqual(radius.radius_cm_at(0.0), 2.0)
        self.assertAlmostEqual(radius.radius_cm_at(900.0), 2.0 + 0.5 * (1.873 - 2.0), places=6)
        # 超出附件2 范围（>末点）按末值保持
        self.assertAlmostEqual(radius.radius_cm_at(259200.0), 1.794)

    def test_environment_holds_last_boundary_after_range(self):
        env = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([28.0, 50.0]),
            moisture=np.array([0.02, 0.05]),
        )
        self.assertEqual(env.temperature_at(120.0), 50.0)
        self.assertEqual(env.moisture_at(120.0), 0.05)

    def test_diffusivity_uses_appendix4_formula(self):
        c = np.array([2.55])
        t_c = np.array([50.0])
        expected = 4.2e-4 * np.exp(-0.30 / 2.55) * np.exp(-3850.0 / (50.0 + 273.15))
        self.assertAlmostEqual(float(moisture_diffusivity(c, t_c)[0]), expected)

    def test_appendix4_property_coefficients(self):
        self.assertAlmostEqual(float(density(np.array([0.0]))[0]), 760.0)
        self.assertAlmostEqual(float(density(np.array([1.0]))[0]), 850.0)
        self.assertAlmostEqual(float(heat_capacity(np.array([0.0]))[0]), 1850.0)
        self.assertAlmostEqual(float(thermal_conductivity(np.array([0.0]))[0]), 0.12)

    def test_default_grid_matches_production_resolution(self):
        self.assertEqual(SolverConfig().xi_points, 201)

    def test_harmonic_face_average_limits_jump_flux(self):
        face = _face_harmonic_average(np.array([1.0, 100.0]))
        self.assertAlmostEqual(float(face[0]), 2.0 / (1.0 / 1.0 + 1.0 / 100.0))
        self.assertLess(float(face[0]), 0.5 * (1.0 + 100.0))

    def test_drying_complete_requires_every_point_below_threshold(self):
        self.assertFalse(drying_complete(np.array([0.10, 0.16, 0.08]), threshold=0.15))
        self.assertTrue(drying_complete(np.array([0.10, 0.149, 0.08]), threshold=0.15))

    def test_output_seconds_are_sixty_multiples_and_include_end(self):
        seconds = build_output_seconds(end_time_s=3700, interval_s=60)
        self.assertEqual(seconds[0], 60)
        self.assertEqual(seconds[1], 120)
        self.assertEqual(seconds[-2], 3660)
        self.assertEqual(seconds[-1], 3700)

    def test_zero_diffusivity_step_preserves_material_profile(self):
        """front-fixing 物质型自检：D=0（无扩散）+ hm=0（无交换）时，
        即便半径收缩，物质点 C 也应守恒（无虚假平流）⇒ 离散算子退化为恒等。"""
        n = 11
        dxi = 1.0 / (n - 1)
        profile = np.linspace(2.55, 1.0, n)
        out = _implicit_radial_variable_step(
            profile,
            np.zeros(n),        # conductivity = D/R² = 0
            np.ones(n),
            10.0,
            dxi,
            0.0,                # boundary_transfer = hm/R = 0
            0.05,
        )
        np.testing.assert_allclose(out, profile, atol=1e-12)

    def test_variable_step_can_use_harmonic_faces(self):
        n = 5
        dxi = 1.0 / (n - 1)
        profile = np.linspace(2.55, 0.2, n)
        conductivity = np.array([100.0, 100.0, 1.0, 1.0, 1.0])

        arithmetic = _implicit_radial_variable_step(
            profile,
            conductivity,
            np.ones(n),
            10.0,
            dxi,
            0.0,
            0.05,
            face_average="arithmetic",
        )
        harmonic = _implicit_radial_variable_step(
            profile,
            conductivity,
            np.ones(n),
            10.0,
            dxi,
            0.0,
            0.05,
            face_average="harmonic",
        )

        self.assertGreater(np.linalg.norm(arithmetic - harmonic), 1e-6)

    def test_contraction_accelerates_drying(self):
        """收缩经 1/R² 加快扩散、经 hm/R 加强表面对流 ⇒ 半径越小干燥越快。"""
        n = 21
        dxi = 1.0 / (n - 1)
        env = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([70.0, 70.0]),
            moisture=np.array([0.05, 0.05]),
        )
        config = SolverConfig(xi_points=n, dt_s=10.0)
        c0 = np.full(n, 2.55)
        t0 = np.full(n, 28.0)

        _, c_big, _, _ = _coupled_step(t0, c0, env, 2.0, 10.0, config, dxi)
        _, c_small, _, _ = _coupled_step(t0, c0, env, 1.0, 10.0, config, dxi)

        self.assertLess(float(c_small[-1]), float(c_big[-1]))

    def test_solver_stops_when_full_profile_below_threshold(self):
        env = EnvironmentSeries(
            time_s=np.array([0.0, 60.0]),
            temperature_c=np.array([50.0, 50.0]),
            moisture=np.array([0.05, 0.05]),
        )
        radius = RadiusSeries(time_s=np.array([0.0, 600.0]), radius_cm=np.array([2.0, 1.9]))
        config = SolverConfig(
            xi_points=11,
            duration_limit_s=600,
            dt_s=10.0,
            initial_temperature_c=50.0,
            initial_moisture=0.149,
            completion_threshold=0.15,
            mass_transfer_m_s=1e-4,
        )

        result = solve_problem4(env, radius, config)

        self.assertLessEqual(float(result.moisture[-1].max()), 0.15)
        self.assertGreater(result.drying_end_time_s, 0)
        self.assertTrue(result.coupling_converged.all())
        self.assertEqual(len(result.radius_cm), len(result.time_s))


if __name__ == "__main__":
    unittest.main()
