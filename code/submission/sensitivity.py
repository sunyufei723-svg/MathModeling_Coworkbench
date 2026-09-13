"""问题四全局敏感性与刚性求解器交叉验证（单文件 · 无参数运行）。

在题设直接给定的物质坐标问题四主模型上，复现论文附录 B / 图6 的全部敏感性与
不确定度量化结论，六阶段串联：
  1. 9 参数 Morris 筛选（N401 高保真 PDE，mu_star 排序取前 5）；
  2. 对筛选出的 5 参数建 Legendre PCE（160 LHS + 32 角点训练、40 独立验证，N801）；
  3. 从正交 PCE 系数解析算 Sobol 一阶/总效应，Saltelli 代理抽样交叉复核 + 残差 bootstrap 区间；
  4. N3201 高保真抽查（默认/代理最快/最慢/3 个最大验证误差点）；
  5. Radau IIA 复核默认/快/慢三情景的事件时间与代表时刻全水分剖面（N1601）；
  6. 汇总验收 + 终端打印关键结论。

数据源与产物（全部相对本脚本目录 code/submission/）：
- 输入：附件/附件1.xlsx（环境边界）、附件/附件2.xlsx（半径轨迹）；
- 求解核心：同目录 problem4.py（EnvironmentSeries/PostBoundary/PhysicalParameters/
  RadiusSeries/SolverConfig/solve_problem4_bdf，与问题四主答案同口径，数值逻辑零改动）；
- 产物：global_sensitivity/{parameter_ranges,morris_results,pce_validation,sobol_indices,
  high_fidelity_checks,radau_comparison,pipeline_summary}.json（喂 figures.py 的 fig5 与论文附录 B）；
- 缓存：global_sensitivity/_work/evaluation_cache.json（每个 PDE 样本落盘，可中断续跑）。

参数范围是独立均匀的工程扰动假设，不是观测数据识别的概率分布；Sobol 是筛选后 5 参数的
条件分析，其余 4 参数固定于基准值；干物质质量闭合替代模型属离散模型形式层，不入连续 Sobol 空间。
结论不替换问题四主答案 50.8245 h。

计算量：全流程约 444 次唯一 PDE 求解（N401/801/1601/3201 混合），首跑约数分钟（多进程，
默认用满 CPU 核）；缓存命中后再次运行秒级完成。

用法：python sensitivity.py   （无任何命令行参数；缺附件时友好提示后退出）
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import scipy
from numpy.polynomial.legendre import legval

BASE = Path(__file__).resolve().parent           # 本脚本与 problem4.py 同目录（code/submission）
ATTACH_DIR = BASE / "附件"
ATTACHMENT1 = ATTACH_DIR / "附件1.xlsx"           # 环境边界输入
ATTACHMENT2 = ATTACH_DIR / "附件2.xlsx"           # 半径轨迹输入
OUT = BASE / "global_sensitivity"                 # JSON 产物目录
WORK = OUT / "_work"                              # 求解缓存目录（可续跑，gitignore）

sys.path.insert(0, str(BASE))
from problem4 import (  # noqa: E402  复用问题四已验证的求解核心（同口径、数值逻辑零改动）
    EnvironmentSeries,
    PhysicalParameters,
    PostBoundary,
    RadiusSeries,
    SolverConfig,
    solve_problem4_bdf,
)

# 问题四主答案（默认参数 N3201 连续事件时间），作为高保真抽查的基准锚点
BASELINE_EVENT_TIME_S = 182968.2251620822


# ======================================================================================
# 参数空间（parameters.py）
# ======================================================================================
@dataclass(frozen=True)
class ParameterSpec:
    name: str
    label: str
    lower: float
    upper: float
    unit: str
    interpretation: str

    def __post_init__(self) -> None:
        if not np.isfinite([self.lower, self.upper]).all() or self.upper <= self.lower:
            raise ValueError(f"invalid range for {self.name}")

    def from_unit(self, value: float) -> float:
        if not np.isfinite(value) or value < -1.0e-12 or value > 1.0 + 1.0e-12:
            raise ValueError(f"normalized {self.name} must lie in [0, 1]")
        clipped = min(max(float(value), 0.0), 1.0)
        return self.lower + clipped * (self.upper - self.lower)


PARAMETER_SPECS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        "ambient_temperature_delta_c",
        r"$\Delta T_\infty$",
        -2.0,
        2.0,
        "deg C",
        "4 h 后环境温度相对附件末值的工程偏移",
    ),
    ParameterSpec(
        "ambient_moisture_factor",
        r"$f_{C_\infty}$",
        0.9,
        1.1,
        "1",
        "4 h 后环境水分边界倍率",
    ),
    ParameterSpec(
        "heat_transfer_factor",
        r"$f_h$",
        0.9,
        1.1,
        "1",
        "表面对流换热系数倍率",
    ),
    ParameterSpec(
        "mass_transfer_factor",
        r"$f_{h_m}$",
        0.9,
        1.1,
        "1",
        "表面对流传质系数倍率",
    ),
    ParameterSpec(
        "diffusivity_prefactor_factor",
        r"$f_{D_0}$",
        0.9,
        1.1,
        "1",
        "附录4水分扩散前因子倍率",
    ),
    ParameterSpec(
        "activation_temperature_factor",
        r"$f_\beta$",
        0.95,
        1.05,
        "1",
        "活化温度参数 beta=3850 K 的倍率",
    ),
    ParameterSpec(
        "shrinkage_amplitude_factor",
        r"$f_R$",
        0.95,
        1.05,
        "1",
        "保持初始半径不变的收缩幅度倍率",
    ),
    ParameterSpec(
        "density_intercept_factor",
        r"$f_{\rho_0}$",
        0.95,
        1.05,
        "1",
        "密度关系截距760的倍率",
    ),
    ParameterSpec(
        "density_slope_factor",
        r"$f_{\rho_1}$",
        0.9,
        1.1,
        "1",
        "密度关系水分系数90的倍率",
    ),
)


def parameter_names() -> tuple[str, ...]:
    return tuple(item.name for item in PARAMETER_SPECS)


def default_unit_point() -> np.ndarray:
    return np.full(len(PARAMETER_SPECS), 0.5, dtype=float)


def point_from_unit(unit_point: np.ndarray | list[float]) -> dict[str, float]:
    values = np.asarray(unit_point, dtype=float)
    if values.shape != (len(PARAMETER_SPECS),):
        raise ValueError(f"unit point must have shape ({len(PARAMETER_SPECS)},)")
    return {spec.name: spec.from_unit(value) for spec, value in zip(PARAMETER_SPECS, values, strict=True)}


def parameter_metadata() -> list[dict[str, object]]:
    return [asdict(item) for item in PARAMETER_SPECS]


# ======================================================================================
# 求解缓存（cache.py）
# ======================================================================================
class JsonEvaluationCache:
    """小型、可中断续跑的JSON缓存；每个完成样本立即原子落盘。"""

    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("evaluation cache must contain a JSON object")
            self.data: dict[str, dict[str, Any]] = loaded
        else:
            self.data = {}

    def get(self, key: str) -> dict[str, Any] | None:
        return self.data.get(key)

    def put(self, key: str, value: dict[str, Any]) -> None:
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        temporary.replace(self.path)


# ======================================================================================
# PDE 求值器（evaluator.py）—— 调用 problem4.py 的求解核心
# ======================================================================================
def load_inputs(attachment1: Path, attachment2: Path) -> tuple[EnvironmentSeries, RadiusSeries]:
    environment_frame = pd.read_excel(attachment1)
    radius_frame = pd.read_excel(attachment2)
    return (
        EnvironmentSeries(
            environment_frame.iloc[:, 0].to_numpy(dtype=float),
            environment_frame.iloc[:, 1].to_numpy(dtype=float),
            environment_frame.iloc[:, 2].to_numpy(dtype=float),
        ),
        RadiusSeries(
            radius_frame.iloc[:, 0].to_numpy(dtype=float),
            radius_frame.iloc[:, 1].to_numpy(dtype=float),
            "linear",
        ),
    )


def input_fingerprint(attachment1: Path, attachment2: Path) -> str:
    digest = hashlib.sha256()
    for path in (attachment1, attachment2):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def evaluation_key(
    unit_point: np.ndarray,
    node_count: int,
    integration_method: str,
    fingerprint: str,
    include_profiles: bool = False,
) -> str:
    payload = {
        "unit_point": [round(float(value), 12) for value in unit_point],
        "node_count": int(node_count),
        "integration_method": integration_method,
        "input_fingerprint": fingerprint,
        "rtol": 1.0e-8,
        "temperature_atol": 1.0e-8,
        "moisture_atol": 1.0e-10,
        "max_step_s": 30.0,
        "initial_time_limit_s": 72.0 * 3600.0,
        "fallback_time_limit_s": 168.0 * 3600.0,
    }
    if include_profiles:
        payload["include_profiles"] = True
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _run_payload(payload: dict[str, object]) -> dict[str, object]:
    attachment1 = Path(str(payload["attachment1"]))
    attachment2 = Path(str(payload["attachment2"]))
    unit_point = np.asarray(payload["unit_point"], dtype=float)
    node_count = int(payload["node_count"])
    integration_method = str(payload["integration_method"])
    include_profiles = bool(payload.get("include_profiles", False))
    point = point_from_unit(unit_point)
    environment, radius = load_inputs(attachment1, attachment2)
    defaults = SolverConfig()
    physical = PhysicalParameters(
        density_intercept=760.0 * point["density_intercept_factor"],
        density_moisture_coefficient=90.0 * point["density_slope_factor"],
        diffusivity_prefactor=4.2e-4 * point["diffusivity_prefactor_factor"],
        diffusivity_moisture_parameter=0.30,
        activation_temperature_k=3850.0 * point["activation_temperature_factor"],
        shrinkage_amplitude_factor=point["shrinkage_amplitude_factor"],
    )
    config = replace(
        defaults,
        node_count=node_count,
        sample_interval_s=21600,
        report_interval_s=60,
        heat_transfer_w_m2_k=defaults.heat_transfer_w_m2_k * point["heat_transfer_factor"],
        mass_transfer_m_s=defaults.mass_transfer_m_s * point["mass_transfer_factor"],
        physical_parameters=physical,
        integration_method=integration_method,
        relative_tolerance=1.0e-8,
        temperature_absolute_tolerance=1.0e-8,
        moisture_absolute_tolerance=1.0e-10,
        max_time_step_s=30.0,
        initial_time_limit_s=72.0 * 3600.0,
        fallback_time_limit_s=168.0 * 3600.0,
    )
    post_boundary = PostBoundary(
        environment.terminal_temperature_c + point["ambient_temperature_delta_c"],
        environment.terminal_moisture * point["ambient_moisture_factor"],
    )
    started = time.perf_counter()
    result = solve_problem4_bdf(environment, radius, config, post_boundary)
    runtime_s = time.perf_counter() - started
    quality = bool(
        result.diagnostics.maximum_normalized_balance_residual < 1.0e-6
        and result.diagnostics.minimum_raw_moisture >= -1.0e-8
        and result.diagnostics.radial_monotonicity_all_outputs
        and int(np.argmax(result.event_moisture_internal)) == 0
        and result.report_max_moisture < config.completion_threshold
    )
    if not quality:
        raise RuntimeError("sensitivity run failed numerical quality checks")
    record = {
        "unit_point": [float(value) for value in unit_point],
        "parameters": point,
        "node_count": node_count,
        "integration_method": integration_method,
        "continuous_event_time_s": float(result.drying_event_time_s),
        "continuous_event_time_h": float(result.drying_event_time_s / 3600.0),
        "report_event_time_s": int(result.report_end_time_s),
        "report_event_time_h": float(result.report_end_time_s / 3600.0),
        "event_center_moisture": float(result.event_moisture_internal[0]),
        "event_surface_moisture": float(result.event_moisture_internal[-1]),
        "event_radius_cm": float(result.event_radius_cm),
        "event_argmax_index": int(np.argmax(result.event_moisture_internal)),
        "minimum_raw_moisture": float(result.diagnostics.minimum_raw_moisture),
        "maximum_normalized_balance_residual": float(
            result.diagnostics.maximum_normalized_balance_residual
        ),
        "radial_monotonicity": bool(result.diagnostics.radial_monotonicity_all_outputs),
        "function_evaluations": int(result.diagnostics.function_evaluations),
        "jacobian_evaluations": int(result.diagnostics.jacobian_evaluations),
        "lu_decompositions": int(result.diagnostics.lu_decompositions),
        "runtime_s": float(runtime_s),
        "quality_checks_passed": quality,
    }
    if include_profiles:
        record["sample_time_s"] = [float(value) for value in result.time_s]
        record["sample_moisture"] = [
            [None if not np.isfinite(value) else float(value) for value in row]
            for row in result.moisture
        ]
    return record


class ModelEvaluator:
    def __init__(
        self,
        attachment1: Path,
        attachment2: Path,
        cache_path: Path,
        workers: int = 1,
    ) -> None:
        self.attachment1 = Path(attachment1).resolve()
        self.attachment2 = Path(attachment2).resolve()
        self.cache = JsonEvaluationCache(Path(cache_path))
        self.workers = max(1, int(workers))
        self.fingerprint = input_fingerprint(self.attachment1, self.attachment2)

    def evaluate_many(
        self,
        unit_points: Iterable[np.ndarray | list[float]],
        node_count: int,
        integration_method: str = "BDF",
        include_profiles: bool = False,
    ) -> list[dict[str, object]]:
        points = [np.asarray(item, dtype=float) for item in unit_points]
        if any(point.shape != (len(PARAMETER_SPECS),) for point in points):
            raise ValueError("all unit points must contain every declared parameter")
        keys = [
            evaluation_key(point, node_count, integration_method, self.fingerprint, include_profiles)
            for point in points
        ]
        records: list[dict[str, object] | None] = [self.cache.get(key) for key in keys]
        pending: dict[str, tuple[int, np.ndarray]] = {}
        for index, (key, point, record) in enumerate(zip(keys, points, records, strict=True)):
            if record is None and key not in pending:
                pending[key] = (index, point)

        if pending:
            payloads = [
                {
                    "attachment1": str(self.attachment1),
                    "attachment2": str(self.attachment2),
                    "unit_point": point.tolist(),
                    "node_count": node_count,
                    "integration_method": integration_method,
                    "include_profiles": include_profiles,
                }
                for _, point in pending.values()
            ]
            if self.workers == 1:
                for number, payload in enumerate(payloads, start=1):
                    record = _run_payload(payload)
                    point = np.asarray(record["unit_point"], dtype=float)
                    key = evaluation_key(
                        point,
                        node_count,
                        integration_method,
                        self.fingerprint,
                        include_profiles,
                    )
                    self.cache.put(key, record)
                    print(
                        f"completed {number}/{len(payloads)} new {integration_method} evaluations",
                        flush=True,
                    )
            else:
                executor = ProcessPoolExecutor(max_workers=self.workers)
                payload_iterator = iter(payloads)
                active = {}
                try:
                    for _ in range(min(self.workers, len(payloads))):
                        payload = next(payload_iterator)
                        active[executor.submit(_run_payload, payload)] = payload
                    completed = 0
                    while active:
                        done, _ = wait(active, return_when=FIRST_COMPLETED)
                        for future in done:
                            active.pop(future)
                            record = future.result()
                            point = np.asarray(record["unit_point"], dtype=float)
                            key = evaluation_key(
                                point,
                                node_count,
                                integration_method,
                                self.fingerprint,
                                include_profiles,
                            )
                            self.cache.put(key, record)
                            completed += 1
                            print(
                                f"completed {completed}/{len(payloads)} new {integration_method} evaluations",
                                flush=True,
                            )
                            try:
                                payload = next(payload_iterator)
                            except StopIteration:
                                continue
                            active[executor.submit(_run_payload, payload)] = payload
                except BaseException:
                    for future in active:
                        future.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
                else:
                    executor.shutdown(wait=True)

        output = []
        for key in keys:
            record = self.cache.get(key)
            if record is None:
                raise RuntimeError("evaluation cache unexpectedly missed a completed point")
            output.append(record)
        return output


# ======================================================================================
# Morris 筛选（morris.py）
# ======================================================================================
@dataclass(frozen=True)
class MorrisDesign:
    points: np.ndarray
    trajectories: list[dict[str, object]]
    levels: int
    delta: float


def generate_morris_design(
    dimension: int,
    trajectories_per_seed: int = 10,
    levels: int = 6,
    seeds: tuple[int, ...] = (20260912, 20260913),
) -> MorrisDesign:
    if dimension < 1 or trajectories_per_seed < 1:
        raise ValueError("dimension and trajectories_per_seed must be positive")
    if levels < 4 or levels % 2:
        raise ValueError("Morris levels must be an even integer >= 4")
    delta = levels / (2.0 * (levels - 1.0))
    grid = np.linspace(0.0, 1.0, levels)
    points: list[np.ndarray] = []
    metadata: list[dict[str, object]] = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        for local_index in range(trajectories_per_seed):
            directions = rng.choice(np.array([-1.0, 1.0]), size=dimension)
            base = np.empty(dimension, dtype=float)
            for index, direction in enumerate(directions):
                candidates = grid[grid <= 1.0 - delta + 1.0e-12]
                low = float(rng.choice(candidates))
                base[index] = low if direction > 0.0 else low + delta
            order = rng.permutation(dimension)
            trajectory_indices = [len(points)]
            points.append(base.copy())
            current = base.copy()
            steps = []
            for parameter_index in order:
                following = current.copy()
                signed_delta = directions[parameter_index] * delta
                following[parameter_index] += signed_delta
                if following[parameter_index] < -1.0e-12 or following[parameter_index] > 1.0 + 1.0e-12:
                    raise RuntimeError("generated Morris point outside [0, 1]")
                points.append(following)
                next_index = len(points) - 1
                steps.append(
                    {
                        "parameter_index": int(parameter_index),
                        "from_point_index": int(trajectory_indices[-1]),
                        "to_point_index": int(next_index),
                        "signed_delta": float(signed_delta),
                    }
                )
                trajectory_indices.append(next_index)
                current = following
            metadata.append(
                {
                    "seed": int(seed),
                    "trajectory_within_seed": int(local_index),
                    "point_indices": trajectory_indices,
                    "steps": steps,
                }
            )
    return MorrisDesign(np.vstack(points), metadata, levels, float(delta))


def analyse_morris(
    design: MorrisDesign,
    outputs: np.ndarray,
    parameter_names: tuple[str, ...],
) -> dict[str, object]:
    outputs = np.asarray(outputs, dtype=float)
    if outputs.shape != (len(design.points),):
        raise ValueError("Morris output length does not match design")
    effects: dict[str, list[float]] = {name: [] for name in parameter_names}
    seed_effects: dict[int, dict[str, list[float]]] = {}
    for trajectory in design.trajectories:
        seed = int(trajectory["seed"])
        seed_effects.setdefault(seed, {name: [] for name in parameter_names})
        for step in trajectory["steps"]:
            parameter_index = int(step["parameter_index"])
            effect = (
                outputs[int(step["to_point_index"])] - outputs[int(step["from_point_index"])]
            ) / float(step["signed_delta"])
            name = parameter_names[parameter_index]
            effects[name].append(float(effect))
            seed_effects[seed][name].append(float(effect))

    rows = []
    for name in parameter_names:
        values = np.asarray(effects[name], dtype=float)
        rows.append(
            {
                "parameter": name,
                "mu_h": float(np.mean(values)),
                "mu_star_h": float(np.mean(np.abs(values))),
                "sigma_h": float(np.std(values, ddof=1)),
                "elementary_effect_count": int(values.size),
                "effects_h": values.tolist(),
                "seed_mu_star_h": {
                    str(seed): float(np.mean(np.abs(per_parameter[name])))
                    for seed, per_parameter in seed_effects.items()
                },
            }
        )
    rows.sort(key=lambda item: float(item["mu_star_h"]), reverse=True)
    maximum = float(rows[0]["mu_star_h"])
    selected = [str(row["parameter"]) for row in rows[: min(5, len(rows))]]
    return {
        "levels": design.levels,
        "delta": design.delta,
        "trajectory_count": len(design.trajectories),
        "model_evaluation_count": len(design.points),
        "rows": rows,
        "selected_parameters": selected,
        "selection_rule": (
            "retain the top 5 by mu_star; the 10% of maximum threshold is reported as a diagnostic, "
            "not used to discard shrinkage or mass-transfer effects before PCE"
        ),
        "ten_percent_of_maximum_mu_star_h": 0.1 * maximum,
        "interpretation": "screening elementary effects, not variance contributions",
    }



# ======================================================================================
# PCE 代理与独立验证（pce.py）
# ======================================================================================
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


# ======================================================================================
# Sobol 方差分解（sobol.py）
# ======================================================================================
def analytical_sobol(model: PCEModel) -> dict[str, object]:
    variance = float(np.sum(model.coefficients[1:] ** 2))
    if variance <= 0.0:
        raise ValueError("PCE variance must be positive")
    rows = []
    for index, name in enumerate(model.parameter_names):
        active = model.multi_indices > 0
        first_mask = active[:, index] & (np.sum(active, axis=1) == 1)
        total_mask = active[:, index]
        rows.append(
            {
                "parameter": name,
                "first_order": float(np.sum(model.coefficients[first_mask] ** 2) / variance),
                "total_order": float(np.sum(model.coefficients[total_mask] ** 2) / variance),
            }
        )
    interactions = []
    active = model.multi_indices > 0
    for left in range(len(model.parameter_names)):
        for right in range(left + 1, len(model.parameter_names)):
            mask = active[:, left] & active[:, right] & (np.sum(active, axis=1) == 2)
            value = float(np.sum(model.coefficients[mask] ** 2) / variance)
            interactions.append(
                {
                    "parameter_left": model.parameter_names[left],
                    "parameter_right": model.parameter_names[right],
                    "second_order": value,
                }
            )
    interactions.sort(key=lambda item: float(item["second_order"]), reverse=True)
    rows.sort(key=lambda item: float(item["total_order"]), reverse=True)
    return {
        "pce_variance_h2": variance,
        "rows": rows,
        "sum_first_order": float(sum(float(row["first_order"]) for row in rows)),
        "interactions": interactions,
    }


def saltelli_crosscheck(model: PCEModel, sample_count: int = 100000, seed: int = 20260914) -> dict[str, object]:
    dimension = len(model.parameter_names)
    a = latin_hypercube(sample_count, dimension, seed)
    b = latin_hypercube(sample_count, dimension, seed + 1)
    fa = model.predict(a)
    fb = model.predict(b)
    variance = float(np.var(np.concatenate([fa, fb]), ddof=1))
    rows = []
    for index, name in enumerate(model.parameter_names):
        ab = a.copy()
        ab[:, index] = b[:, index]
        fab = model.predict(ab)
        first = float(np.mean(fb * (fab - fa)) / variance)
        total = float(0.5 * np.mean((fa - fab) ** 2) / variance)
        rows.append({"parameter": name, "first_order": first, "total_order": total})
    return {"sample_count": sample_count, "rows": rows}


def bootstrap_sobol(
    train_points: np.ndarray,
    train_outputs: np.ndarray,
    parameter_names: tuple[str, ...],
    degree: int,
    repetitions: int = 500,
    seed: int = 20260915,
) -> dict[str, dict[str, list[float]]]:
    rng = np.random.default_rng(seed)
    multi_indices = total_degree_indices(len(parameter_names), degree)
    matrix = design_matrix(np.asarray(train_points, dtype=float), multi_indices)
    pseudo_inverse = np.linalg.pinv(matrix)
    base_model = PCEModel(
        parameter_names,
        degree,
        multi_indices,
        pseudo_inverse @ np.asarray(train_outputs, dtype=float),
    )
    fitted = base_model.predict(train_points)
    residuals = np.asarray(train_outputs, dtype=float) - fitted
    residuals = residuals - np.mean(residuals)
    first: dict[str, list[float]] = {name: [] for name in parameter_names}
    total: dict[str, list[float]] = {name: [] for name in parameter_names}
    for _ in range(repetitions):
        bootstrap_outputs = fitted + rng.choice(residuals, size=len(residuals), replace=True)
        model = PCEModel(
            parameter_names,
            degree,
            multi_indices,
            pseudo_inverse @ bootstrap_outputs,
        )
        result = analytical_sobol(model)
        for row in result["rows"]:
            name = str(row["parameter"])
            first[name].append(float(row["first_order"]))
            total[name].append(float(row["total_order"]))
    return {
        name: {
            "first_order_95_interval": [
                float(np.quantile(first[name], 0.025)),
                float(np.quantile(first[name], 0.975)),
            ],
            "total_order_95_interval": [
                float(np.quantile(total[name], 0.025)),
                float(np.quantile(total[name], 0.975)),
            ],
        }
        for name in parameter_names
    }


def merge_sobol_checks(
    analytical: dict[str, object],
    saltelli: dict[str, object],
) -> dict[str, object]:
    saltelli_by_name = {str(row["parameter"]): row for row in saltelli["rows"]}
    comparisons = []
    for row in analytical["rows"]:
        name = str(row["parameter"])
        numerical = saltelli_by_name[name]
        comparisons.append(
            {
                "parameter": name,
                "first_order_absolute_difference": abs(
                    float(row["first_order"]) - float(numerical["first_order"])
                ),
                "total_order_absolute_difference": abs(
                    float(row["total_order"]) - float(numerical["total_order"])
                ),
            }
        )
    maximum = max(
        max(item["first_order_absolute_difference"], item["total_order_absolute_difference"])
        for item in comparisons
    )
    return {
        "comparisons": comparisons,
        "maximum_absolute_difference": float(maximum),
        "passed": bool(maximum < 0.02),
    }


# ======================================================================================
# Radau IIA 刚性求解器交叉验证（radau_crosscheck.py）
# ======================================================================================
def _common_profile_difference(
    left: dict[str, object],
    right: dict[str, object],
) -> float:
    left_times = np.asarray(left["sample_time_s"], dtype=float)
    right_times = np.asarray(right["sample_time_s"], dtype=float)
    common = np.intersect1d(left_times, right_times)
    if common.size == 0:
        raise ValueError("integrator records have no common profile times")
    left_profile = np.asarray(
        [[np.nan if value is None else float(value) for value in row] for row in left["sample_moisture"]],
        dtype=float,
    )
    right_profile = np.asarray(
        [[np.nan if value is None else float(value) for value in row] for row in right["sample_moisture"]],
        dtype=float,
    )
    differences = []
    for time_s in common:
        left_index = int(np.where(np.isclose(left_times, time_s))[0][0])
        right_index = int(np.where(np.isclose(right_times, time_s))[0][0])
        finite = np.isfinite(left_profile[left_index]) & np.isfinite(right_profile[right_index])
        if np.any(finite):
            differences.append(
                float(
                    np.max(
                        np.abs(
                            left_profile[left_index, finite]
                            - right_profile[right_index, finite]
                        )
                    )
                )
            )
    if not differences:
        raise ValueError("integrator records have no common finite profile values")
    return max(differences)


def compare_integrators(
    scenario_names: list[str],
    bdf_records: list[dict[str, object]],
    radau_records: list[dict[str, object]],
) -> dict[str, object]:
    if not (len(scenario_names) == len(bdf_records) == len(radau_records)):
        raise ValueError("Radau comparison inputs differ in length")
    rows = []
    for name, bdf, radau in zip(scenario_names, bdf_records, radau_records, strict=True):
        difference = abs(
            float(bdf["continuous_event_time_s"]) - float(radau["continuous_event_time_s"])
        )
        rows.append(
            {
                "scenario": name,
                "bdf_event_time_h": float(bdf["continuous_event_time_h"]),
                "radau_event_time_h": float(radau["continuous_event_time_h"]),
                "absolute_difference_s": float(difference),
                "event_surface_moisture_difference": abs(
                    float(bdf["event_surface_moisture"])
                    - float(radau["event_surface_moisture"])
                ),
                "representative_profile_maximum_moisture_difference": _common_profile_difference(
                    bdf,
                    radau,
                ),
                "event_argmax_same": int(bdf["event_argmax_index"])
                == int(radau["event_argmax_index"]),
                "bdf_runtime_s": float(bdf["runtime_s"]),
                "radau_runtime_s": float(radau["runtime_s"]),
            }
        )
    return {
        "node_count": int(bdf_records[0]["node_count"]),
        "rows": rows,
        "acceptance": {
            "event_time_difference_limit_s": 30.0,
            "surface_moisture_difference_limit": 1.0e-4,
            "representative_profile_maximum_moisture_difference_limit": 1.0e-4,
        },
        "passed": bool(
            all(
                float(row["absolute_difference_s"]) < 30.0
                and float(row["event_surface_moisture_difference"]) < 1.0e-4
                and float(row["representative_profile_maximum_moisture_difference"]) < 1.0e-4
                and bool(row["event_argmax_same"])
                for row in rows
            )
        ),
    }


# ======================================================================================
# 流水线编排与产物落盘（run_pipeline.py 改编：去 argparse、删 md 报告、改终端打印）
# ======================================================================================
def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def embed_selected(points: np.ndarray, selected_indices: list[int]) -> np.ndarray:
    full = np.tile(default_unit_point(), (len(points), 1))
    full[:, selected_indices] = points
    return full


def event_outputs(records: list[dict[str, object]]) -> np.ndarray:
    return np.asarray([float(record["continuous_event_time_h"]) for record in records], dtype=float)


def unique_rows(points: list[np.ndarray]) -> list[np.ndarray]:
    unique: dict[tuple[float, ...], np.ndarray] = {}
    for point in points:
        key = tuple(round(float(value), 12) for value in point)
        unique[key] = np.asarray(point, dtype=float)
    return list(unique.values())


def recorded_solver_cost(record_groups: list[list[dict[str, object]]]) -> dict[str, float | int]:
    """Summarise the unique PDE solves represented by the final data products.

    This is intentionally distinct from the wall time of a resumed, cache-backed
    pipeline run.  A physical sample is identified by its grid, integrator and
    full nine-parameter unit point.
    """
    unique: dict[tuple[object, ...], dict[str, object]] = {}
    for records in record_groups:
        for record in records:
            key = (
                int(record["node_count"]),
                str(record["integration_method"]),
                *tuple(round(float(value), 12) for value in record["unit_point"]),
            )
            unique[key] = record
    return {
        "unique_pde_evaluation_count_in_final_dataset": len(unique),
        "sum_recorded_solver_runtime_s": float(
            sum(float(record["runtime_s"]) for record in unique.values())
        ),
    }


def print_summary(
    morris: dict[str, object],
    pce: dict[str, object],
    sobol: dict[str, object],
    high_fidelity: dict[str, object],
    radau: dict[str, object],
    summary: dict[str, object],
) -> None:
    """把关键结论按节打印到终端（替代原 md 长篇报告，供队员直接抄进论文）。"""
    line = "=" * 78
    metrics = pce["metrics"]
    distribution = pce["conditional_distribution_summary"]
    analytical = sobol["analytical"]
    crosscheck = sobol["crosscheck"]

    print("\n" + line)
    print("问题四 全局敏感性 / PCE-Sobol / Radau 交叉验证 —— 关键结论")
    print(line)

    print("\n[1] Morris 筛选（mu_star 衡量筛选影响强度，非方差贡献率）")
    print(f"    轨迹数={morris['trajectory_count']}  N401 模型评估次数={morris['model_evaluation_count']}"
          f"  质量检查全通过={morris['all_quality_checks_passed']}")
    for index, row in enumerate(morris["rows"], start=1):
        print(f"    #{index:<2d} {str(row['parameter']):<34s} mu*={float(row['mu_star_h']):.6f} h"
              f"  sigma={float(row['sigma_h']):.6f} h")
    print("    进入 PCE/Sobol 的参数：" + ", ".join(str(name) for name in morris["selected_parameters"]))

    print("\n[2] PCE 代理与独立验证")
    print(f"    选定阶数={pce['selected_degree']}  训练样本={pce['training_sample_count']}"
          f"（LHS {pce['latin_hypercube_training_sample_count']} + 角点 {pce['corner_enrichment_sample_count']}）"
          f"  独立验证样本={pce['validation_sample_count']}")
    print(f"    Q2={metrics['q_squared_independent']:.9f}  RMSE={metrics['rmse_h']:.6f} h"
          f"  最大绝对误差={metrics['maximum_absolute_error_h']:.6f} h"
          f"  NRMSE={metrics['normalized_rmse_by_range']:.6f}  验收={'通过' if pce['passed'] else '未通过'}")
    print(f"    条件分布（5 参数独立均匀、其余 4 固定基准）：均值={distribution['mean_h']:.4f} h"
          f"  标准差={distribution['standard_deviation_h']:.4f} h")
    print(f"      P5={distribution['p05_h']:.4f} h  中位数={distribution['median_h']:.4f} h"
          f"  P95={distribution['p95_h']:.4f} h（工程扰动条件分布，非统计置信区间）")

    print("\n[3] Sobol 方差分解（正交 PCE 系数解析 + Saltelli 代理交叉 + 残差 bootstrap 区间）")
    for row in analytical["rows"]:
        first_interval = ", ".join(f"{float(value):.6f}" for value in row["first_order_95_interval"])
        total_interval = ", ".join(f"{float(value):.6f}" for value in row["total_order_95_interval"])
        print(f"    {str(row['parameter']):<34s} S_i={float(row['first_order']):.5f}"
              f"  S_Ti={float(row['total_order']):.5f}")
        print(f"        一阶95%[{first_interval}]  总效应95%[{total_interval}]")
    print(f"    一阶指数和={analytical['sum_first_order']:.6f}"
          f"  解析 vs Saltelli 最大差={crosscheck['maximum_absolute_difference']:.6f}"
          f"  验收={'通过' if crosscheck['passed'] else '未通过'}")
    print("    最大二阶交互项：")
    for row in analytical["interactions"][:3]:
        print(f"      {str(row['parameter_left'])} × {str(row['parameter_right'])}"
              f"  = {float(row['second_order']):.6f}")

    print("\n[4] N3201 高保真抽查")
    for row in high_fidelity["rows"]:
        print(f"    {str(row['scenario']):<24s} PCE={float(row['pce_prediction_h']):.6f} h"
              f"  PDE={float(row['pde_event_time_h']):.6f} h"
              f"  绝对误差={float(row['absolute_error_h']):.6f} h")
    print(f"    默认参数相对基准 {high_fidelity['baseline_reference_event_time_s']:.6f} s 的差"
          f"={high_fidelity['baseline_absolute_difference_s']:.6f} s  验收={'通过' if high_fidelity['passed'] else '未通过'}")

    print("\n[5] Radau IIA 交叉验证（默认/快/慢三情景，不参与批量 UQ）")
    for row in radau["rows"]:
        print(f"    {str(row['scenario']):<24s} BDF={float(row['bdf_event_time_h']):.6f} h"
              f"  Radau={float(row['radau_event_time_h']):.6f} h"
              f"  差={float(row['absolute_difference_s']):.4f} s"
              f"  剖面最大水分差={float(row['representative_profile_maximum_moisture_difference']):.3e}")
    print(f"    联合验收（事件时间差<30 s 且剖面水分差<1e-4）：{'通过' if radau['passed'] else '未通过'}")

    print("\n[6] 汇总")
    print(f"    全部验收通过={summary['all_acceptance_checks_passed']}")
    print(f"    最终数据集唯一 PDE 求解次数={summary['unique_pde_evaluation_count_in_final_dataset']}"
          f"  累计求解器 CPU 时间={summary['sum_recorded_solver_runtime_s']:.3f} s")
    print(f"    本次续跑墙钟时间={summary['final_resume_wall_time_s']:.2f} s（缓存命中后接近 0）")
    print(f"    问题四主答案不变={summary['main_answer_unchanged_h']:.10f} h")
    print(line + "\n")


def main() -> None:
    workers = os.cpu_count() or 1
    morris_trajectories_per_seed = 10
    pce_training = 160
    pce_validation = 40
    for required in (ATTACHMENT1, ATTACHMENT2):
        if not required.exists():
            raise SystemExit(
                f"缺少输入附件：{required}\n"
                f"请把 附件1.xlsx / 附件2.xlsx 放到目录 {ATTACH_DIR} 后重试（本脚本不接受命令行参数）。"
            )
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    evaluator = ModelEvaluator(
        ATTACHMENT1,
        ATTACHMENT2,
        WORK / "evaluation_cache.json",
        workers=workers,
    )
    started_all = time.perf_counter()

    parameter_payload = {
        "target": "problem4 continuous drying event time t_star",
        "distributions": "independent uniform engineering perturbations",
        "not_statistical_confidence_interval": True,
        "model_form_exclusion": "dry-mass-closure alternative remains a separate discrete layer",
        "parameters": parameter_metadata(),
        "attachments": {
            "attachment1_sha256": file_sha256(ATTACHMENT1),
            "attachment2_sha256": file_sha256(ATTACHMENT2),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }
    write_json(OUT / "parameter_ranges.json", parameter_payload)

    print("STAGE Morris", flush=True)
    design = generate_morris_design(
        len(PARAMETER_SPECS),
        trajectories_per_seed=morris_trajectories_per_seed,
    )
    morris_records = evaluator.evaluate_many(design.points, node_count=401, integration_method="BDF")
    morris = analyse_morris(design, event_outputs(morris_records), parameter_names())
    morris["design_unit_points"] = design.points.tolist()
    morris["event_time_h"] = event_outputs(morris_records).tolist()
    morris["all_quality_checks_passed"] = all(bool(row["quality_checks_passed"]) for row in morris_records)
    write_json(OUT / "morris_results.json", morris)

    selected_names = tuple(str(name) for name in morris["selected_parameters"])
    name_to_index = {name: index for index, name in enumerate(parameter_names())}
    selected_indices = [name_to_index[name] for name in selected_names]

    print("STAGE PCE training and independent validation", flush=True)
    lhs_train_reduced = latin_hypercube(pce_training, len(selected_indices), seed=20260916)
    corner_reduced = np.asarray(
        list(product((0.0, 1.0), repeat=len(selected_indices))),
        dtype=float,
    )
    train_reduced = np.vstack([lhs_train_reduced, corner_reduced])
    validation_reduced = latin_hypercube(pce_validation, len(selected_indices), seed=20260917)
    train_full = embed_selected(train_reduced, selected_indices)
    validation_full = embed_selected(validation_reduced, selected_indices)
    train_records = evaluator.evaluate_many(train_full, node_count=801, integration_method="BDF")
    validation_records = evaluator.evaluate_many(validation_full, node_count=801, integration_method="BDF")
    train_outputs = event_outputs(train_records)
    validation_outputs = event_outputs(validation_records)

    degree_results = []
    selected_model = None
    selected_metrics = None
    for degree in (2, 3, 4):
        model = fit_pce(train_reduced, train_outputs, selected_names, degree)
        metrics = validation_metrics(validation_outputs, model.predict(validation_reduced))
        passed = validation_passed(metrics)
        degree_results.append({"degree": degree, "metrics": metrics, "passed": passed})
        if selected_model is None and passed:
            selected_model = model
            selected_metrics = metrics
    if selected_model is None or selected_metrics is None:
        failure = {
            "selected_parameters": list(selected_names),
            "degree_results": degree_results,
            "passed": False,
            "message": "No degree-2 through degree-4 PCE passed independent validation",
        }
        write_json(OUT / "pce_validation.json", failure)
        raise RuntimeError(failure["message"])
    pce_predictions = selected_model.predict(validation_reduced)
    pce_payload = {
        "selected_parameters": list(selected_names),
        "selected_degree": selected_model.degree,
        "training_sample_count": len(train_outputs),
        "latin_hypercube_training_sample_count": len(lhs_train_reduced),
        "corner_enrichment_sample_count": len(corner_reduced),
        "validation_sample_count": len(validation_outputs),
        "degree_results": degree_results,
        "metrics": selected_metrics,
        "passed": True,
        "model": selected_model.as_dict(),
        "design_matrix_condition_number": float(
            np.linalg.cond(design_matrix(train_reduced, selected_model.multi_indices))
        ),
        "training": {
            "reduced_unit_points": train_reduced.tolist(),
            "event_time_h": train_outputs.tolist(),
        },
        "validation": {
            "reduced_unit_points": validation_reduced.tolist(),
            "event_time_h": validation_outputs.tolist(),
            "prediction_h": pce_predictions.tolist(),
            "error_h": (pce_predictions - validation_outputs).tolist(),
        },
    }
    print("STAGE Sobol", flush=True)
    analytical = analytical_sobol(selected_model)
    bootstrap = bootstrap_sobol(
        train_reduced,
        train_outputs,
        selected_names,
        selected_model.degree,
        repetitions=500,
    )
    for row in analytical["rows"]:
        row.update(bootstrap[str(row["parameter"])])
    saltelli = saltelli_crosscheck(selected_model, sample_count=100000)
    crosscheck = merge_sobol_checks(analytical, saltelli)
    sobol_payload = {
        "method": "orthonormal Legendre PCE coefficients with Saltelli surrogate cross-check",
        "distribution_assumption": "independent uniform engineering ranges",
        "conditioning": "five Morris-selected parameters vary; four excluded parameters remain at baseline",
        "not_direct_full_pde_saltelli": True,
        "bootstrap_interval_interpretation": "residual-bootstrap PCE coefficient uncertainty only; not a physical or statistical parameter confidence interval",
        "analytical": analytical,
        "saltelli_surrogate_crosscheck": saltelli,
        "crosscheck": crosscheck,
    }
    write_json(OUT / "sobol_indices.json", sobol_payload)

    print("STAGE N3201 high-fidelity checks", flush=True)
    candidate_reduced = latin_hypercube(100000, len(selected_indices), seed=20260918)
    candidate_predictions = selected_model.predict(candidate_reduced)
    pce_payload["conditional_distribution_summary"] = {
        "sample_count": len(candidate_predictions),
        "conditioning": "selected five parameters vary independently and uniformly; excluded parameters fixed at baseline",
        "mean_h": float(np.mean(candidate_predictions)),
        "standard_deviation_h": float(np.std(candidate_predictions, ddof=1)),
        "p05_h": float(np.quantile(candidate_predictions, 0.05)),
        "median_h": float(np.quantile(candidate_predictions, 0.50)),
        "p95_h": float(np.quantile(candidate_predictions, 0.95)),
        "minimum_sample_h": float(np.min(candidate_predictions)),
        "maximum_sample_h": float(np.max(candidate_predictions)),
    }
    write_json(OUT / "pce_validation.json", pce_payload)
    minimum_reduced = candidate_reduced[int(np.argmin(candidate_predictions))]
    maximum_reduced = candidate_reduced[int(np.argmax(candidate_predictions))]
    validation_errors = np.abs(pce_predictions - validation_outputs)
    worst_validation = np.argsort(validation_errors)[-3:]
    high_points = unique_rows(
        [
            default_unit_point(),
            embed_selected(minimum_reduced[None, :], selected_indices)[0],
            embed_selected(maximum_reduced[None, :], selected_indices)[0],
            *[validation_full[index] for index in worst_validation],
        ]
    )
    high_records = evaluator.evaluate_many(high_points, node_count=3201, integration_method="BDF")
    high_reduced = np.asarray(high_points)[:, selected_indices]
    high_predictions = selected_model.predict(high_reduced)
    high_rows = []
    for index, (point, prediction, record) in enumerate(
        zip(high_points, high_predictions, high_records, strict=True)
    ):
        if np.allclose(point, default_unit_point()):
            scenario = "default"
        elif np.allclose(point[selected_indices], minimum_reduced):
            scenario = "surrogate_fast_sample"
        elif np.allclose(point[selected_indices], maximum_reduced):
            scenario = "surrogate_slow_sample"
        else:
            scenario = f"worst_validation_{index}"
        actual = float(record["continuous_event_time_h"])
        high_rows.append(
            {
                "scenario": scenario,
                "unit_point": point.tolist(),
                "pce_prediction_h": float(prediction),
                "pde_event_time_h": actual,
                "absolute_error_h": abs(float(prediction) - actual),
                "quality_checks_passed": bool(record["quality_checks_passed"]),
            }
        )
    default_record = next(row for point, row in zip(high_points, high_records, strict=True) if np.allclose(point, default_unit_point()))
    baseline_difference = abs(float(default_record["continuous_event_time_s"]) - BASELINE_EVENT_TIME_S)
    high_fidelity = {
        "node_count": 3201,
        "rows": high_rows,
        "baseline_reference_event_time_s": BASELINE_EVENT_TIME_S,
        "baseline_parameterized_event_time_s": float(default_record["continuous_event_time_s"]),
        "baseline_absolute_difference_s": float(baseline_difference),
        "passed": bool(
            baseline_difference < 1.0
            and max(float(row["absolute_error_h"]) for row in high_rows) <= 0.1
            and all(bool(row["quality_checks_passed"]) for row in high_rows)
        ),
    }
    write_json(OUT / "high_fidelity_checks.json", high_fidelity)

    print("STAGE Radau", flush=True)
    default_point = default_unit_point()
    fast_point = embed_selected(minimum_reduced[None, :], selected_indices)[0]
    slow_point = embed_selected(maximum_reduced[None, :], selected_indices)[0]
    radau_points = [default_point, fast_point, slow_point]
    scenario_names = ["default", "surrogate_fast_sample", "surrogate_slow_sample"]
    bdf_records = evaluator.evaluate_many(
        radau_points,
        node_count=1601,
        integration_method="BDF",
        include_profiles=True,
    )
    radau_records = evaluator.evaluate_many(
        radau_points,
        node_count=1601,
        integration_method="Radau",
        include_profiles=True,
    )
    radau_payload = compare_integrators(scenario_names, bdf_records, radau_records)
    write_json(OUT / "radau_comparison.json", radau_payload)

    solver_cost = recorded_solver_cost(
        [
            morris_records,
            train_records,
            validation_records,
            high_records,
            bdf_records,
            radau_records,
        ]
    )
    summary = {
        "morris_passed": bool(morris["all_quality_checks_passed"]),
        "pce_passed": bool(pce_payload["passed"]),
        "sobol_crosscheck_passed": bool(crosscheck["passed"]),
        "high_fidelity_passed": bool(high_fidelity["passed"]),
        "radau_passed": bool(radau_payload["passed"]),
        "all_acceptance_checks_passed": bool(
            morris["all_quality_checks_passed"]
            and pce_payload["passed"]
            and crosscheck["passed"]
            and high_fidelity["passed"]
            and radau_payload["passed"]
        ),
        "final_resume_wall_time_s": float(time.perf_counter() - started_all),
        **solver_cost,
        "main_answer_unchanged_h": BASELINE_EVENT_TIME_S / 3600.0,
    }
    write_json(OUT / "pipeline_summary.json", summary)
    print_summary(morris, pce_payload, sobol_payload, high_fidelity, radau_payload, summary)


if __name__ == "__main__":
    main()
