from __future__ import annotations

from dataclasses import dataclass

try:
    from .environment import PostBoundary
except ImportError:
    from environment import PostBoundary  # type: ignore


@dataclass(frozen=True)
class BoundaryScenario:
    name: str
    post_boundary: PostBoundary
    mass_transfer_factor: float = 1.0


def engineering_boundary_scenarios(default: PostBoundary) -> list[BoundaryScenario]:
    return [
        BoundaryScenario(
            f"T{temperature_delta:+g}_C{moisture_factor:.1f}",
            PostBoundary(
                default.temperature_c + temperature_delta,
                default.moisture * moisture_factor,
            ),
        )
        for temperature_delta in (-2.0, 0.0, 2.0)
        for moisture_factor in (0.9, 1.0, 1.1)
    ]


def mass_transfer_scenarios(default: PostBoundary) -> list[BoundaryScenario]:
    return [BoundaryScenario(f"hm_{factor:.1f}x", default, factor) for factor in (0.9, 1.0, 1.1)]
