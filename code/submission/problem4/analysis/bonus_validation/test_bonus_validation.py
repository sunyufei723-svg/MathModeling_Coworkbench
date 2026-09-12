import unittest

import run_bonus_validation as bv


class LayeredUQTests(unittest.TestCase):
    def test_q4_layered_uq_names_model_form_as_dominant(self):
        layered = bv.layered_uq_statement()
        q4 = layered["problem4"]

        self.assertEqual(q4["dominant_layer"], "shrinkage_density_closure")
        self.assertGreater(q4["shrinkage_density_closure"]["upper_shift_h"], q4["boundary_surrogate"]["half_width_h"])
        self.assertAlmostEqual(q4["main_answer_h"], 50.824506989, places=6)
        self.assertAlmostEqual(q4["shrinkage_density_closure"]["upper_bound_h"], 60.7312, places=4)

    def test_robin_bessel_reports_boundary_convergence_range(self):
        rows = bv.robin_bessel_convergence()

        self.assertGreaterEqual(rows[-1].rate, 1.45)
        self.assertLess(rows[-1].l2_error, rows[0].l2_error / 10.0)

    def test_robin_mms_includes_outer_half_control_volume(self):
        rows = bv.robin_mms_convergence()

        self.assertGreaterEqual(rows[-1].rate, 1.45)
        self.assertLess(rows[-1].l2_error, rows[0].l2_error / 10.0)

    def test_lhs_surrogate_validation_is_not_marked_pde_validated_without_points(self):
        validation = bv.lhs_surrogate_validation()

        self.assertEqual(validation["status"], "needs_pde_points")
        self.assertEqual(validation["pde_point_count"], 0)
        self.assertIn("not yet a high-fidelity PDE validation", validation["interpretation"])

    def test_implicit_euler_time_check_reports_first_order_decay(self):
        rows = bv.implicit_euler_time_convergence()

        self.assertGreaterEqual(rows[-1].rate, 0.95)
        self.assertLess(rows[-1].l2_error, rows[0].l2_error / 3.0)


if __name__ == "__main__":
    unittest.main()
