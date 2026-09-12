"""L5 干物质闭合分支单元测试。

运行：python code/problem4_mass_closure/test_closure.py

设计：解析 / 契约 / 更新式测试不解 PDE（毫秒级）；唯一的功能测试
`test_closure_increases_t_star_and_closes_mass` 跑一次小网格（N=201, 2 次迭代），
且在缺少 gitignored 附件时自动跳过（保证队友无附件也能跑其余测试）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
_HERE = ROOT / "code" / "submission" / "problem4" / "analysis" / "problem4_mass_closure"
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from closure import (  # noqa: E402
    ClosureConfig,
    ClosureState,
    _closure_update,
    _contract_check,
    density,
    load_inputs,
    run_closure,
)

ATT1 = ROOT / "附件" / "附件1.xlsx"
ATT2 = ROOT / "附件" / "附件2.xlsx"


def _make_state(r_cm: np.ndarray, comp: np.ndarray, t_h: np.ndarray) -> ClosureState:
    kappa = (r_cm / 2.0) ** 2 * comp
    return ClosureState(
        label="synthetic", t_star_h=float(t_h[-1]), radius=None, t_h=t_h, r_cm=r_cm,
        kappa=kappa, comp_series=comp, kappa_min=float(kappa.min()),
        t_kappa_min_h=float(t_h[int(np.argmin(kappa))]), kappa_event=float(kappa[-1]),
        kappa_rel_range=0.0, kappa_rel_range_official=0.0,
        R_event_cm=float(r_cm[-1]), coverage_terminal_h=float(t_h[-1]),
    )


def test_contract_check_passes() -> None:
    """problem4_fvm_bdf 暴露的 API 与本模块依赖一致（否则显式报错）。"""
    _contract_check()


def test_rho_s0_and_supremum() -> None:
    """ρ_s(C)=ρ/(1+C)=90+670/(1+C)：C0=2.55→278.7324，C=0→760（上确界），单调递减。"""
    c0 = ClosureConfig().solver_config().initial_moisture
    rho_s0 = float(density(c0) / (1.0 + c0))
    assert abs(rho_s0 - 278.7324) < 1.0e-3, rho_s0
    # model.py 的 density(0)=760.00000009（~1e-10 相对数值伪影），数学上确界仍为 760；
    # 用 1e-5 容差确认「绝干极限 ≈ 760」即可，不追求逐位相等。
    assert abs(float(density(0.0) / 1.0) - 760.0) < 1.0e-5
    for a, b in [(0.0, 0.5), (0.5, 1.5), (1.5, 2.55)]:
        assert density(a) / (1.0 + a) > density(b) / (1.0 + b)


def test_solver_config_maps_main_caliber() -> None:
    """闭合分支默认口径与主模型 B2 一致（仅节点数可变）。"""
    cfg = ClosureConfig(node_count=3201).solver_config()
    assert cfg.node_count == 3201
    assert cfg.model_form == "material"
    assert cfg.relative_tolerance == 1.0e-8
    assert cfg.temperature_absolute_tolerance == 1.0e-8
    assert cfg.moisture_absolute_tolerance == 1.0e-10
    assert cfg.max_time_step_s == 30.0
    assert cfg.sample_interval_s == 60


def test_closure_update_identity() -> None:
    """R0/sqrt(S) 与 r/sqrt(κ) 数值恒等（κ=G·S, G=(r/R0)^2）；t=0 补 R0；时间严格增。"""
    r0 = 2.0
    t_h = np.array([1.0, 2.0, 3.0])          # 不含 t=0（与 _solve_state 契约一致，_closure_update 自行 prepend 0）
    r_cm = np.array([1.6, 1.3, 1.25])
    comp = np.array([1.3, 1.7, 1.9])
    state = _make_state(r_cm, comp, t_h)
    series = _closure_update(state, r0)
    expected = r0 / np.sqrt(comp)
    assert abs(series.radius_cm[0] - r0) < 1.0e-12
    assert series.time_s[0] == 0.0
    assert np.all(np.diff(series.time_s) > 0.0)
    assert np.allclose(series.radius_cm[1:], expected, rtol=0.0, atol=1.0e-9)
    assert np.allclose(series.radius_cm[1:], r_cm / np.sqrt(state.kappa), rtol=0.0, atol=1.0e-9)


def test_closure_update_rejects_nonfinite() -> None:
    """S 含 0（→R 非有限）时应报错，而非产出坏序列。"""
    state = _make_state(np.array([1.6, 1.3]), np.array([1.0, 0.0]), np.array([1.0, 2.0]))
    try:
        _closure_update(state, 2.0)
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError for non-finite closure radius")


def test_closure_increases_t_star_and_closes_mass() -> None:
    """功能测试（需附件，缺失则跳过）：闭合推迟 t* 且降低 κ 变幅。"""
    if not (ATT1.exists() and ATT2.exists()):
        print("SKIP test_closure_increases_t_star_and_closes_mass（附件缺失，gitignored）")
        return
    env, given = load_inputs(ATT1, ATT2)
    res = run_closure(env, given, ClosureConfig(node_count=201, max_iterations=2), verbose=False)
    assert res.n_iterations >= 1
    assert res.closure.t_star_h > res.given.t_star_h, (res.closure.t_star_h, res.given.t_star_h)
    assert res.closure.kappa_rel_range < res.given.kappa_rel_range
    assert abs(res.r0_cm - 2.0) < 1.0e-9


def main() -> int:
    tests = [
        test_contract_check_passes,
        test_rho_s0_and_supremum,
        test_solver_config_maps_main_caliber,
        test_closure_update_identity,
        test_closure_update_rejects_nonfinite,
        test_closure_increases_t_star_and_closes_mass,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
