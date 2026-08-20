from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    dt: float = 0.1
    T: float = 10.0

    ego_start_y: float = 4.0
    target_start_lane_y: float = 0.0
    target_end_lane_y: float = 4.0

    ego_velocity: float = 25.0
    target_initial_x: float = 7.0
    target_velocity: float = 23.5


DEFAULT_SIM_CONFIG = SimulationConfig()


@dataclass(frozen=True)
class FaultConfig:
    """Seeded controller faults, toggled per scenario.

    All faults live in the controller code (see sim_lc.simulate_scenario);
    there is no post-hoc trace rewriting. A third fault (F3) — the absence of
    a Euclidean-distance braking rule, which violates ϕ4 — is inherent to the
    controller and has no switch.
    """
    evasion_latch: bool = False       # F1: stale-state bug (retry, ϕ3)
    aeb_miscalibration: bool = False  # F2: parameter fault (cut-in, ϕ2)


def fault_config_for_scenario(scenario: str) -> "FaultConfig":
    """Scenario -> fault mapping: retry -> F1, cut-in -> F2, all others off."""
    if scenario == "retry":
        return FaultConfig(evasion_latch=True)
    if scenario == "cut-in":
        return FaultConfig(aeb_miscalibration=True)
    return FaultConfig()
