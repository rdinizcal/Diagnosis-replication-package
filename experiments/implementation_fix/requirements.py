#!/usr/bin/env python3
"""
requirements.py

Canonical implementation of requirements ϕ1–ϕ5 over a single
simulation trace DataFrame. This is the **single source of truth**
for the Python-side semantics.

Columns expected in df:
    - TTC, brake, ego_acc
    - ego_x, ego_y, target_x, target_y
    - distance

Gaps (x_gap, y_gap) are treated as **absolute** differences when needed:
    y_gap_abs = |ego_y - target_y|
    x_gap_abs = |ego_x - target_x|
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import pandas as pd


@dataclass
class RequirementsConfig:
    # ϕ1: low TTC → brake within window
    ttc_low: float = 2.5
    phi1_window: int = 6  # steps [t, ..., t+5]

    # ϕ2: hard brake only when TTC is low
    ttc_hard_brake: float = 1.5
    brake_hard: float = -3.0  # m/s²

    # ϕ3: lateral divergence after close intrusion
    phi3_y_zone_low: float = 0.5
    phi3_y_zone_high: float = 3.5
    phi3_x_zone_max: float = 2.0
    phi3_y_zone_max: float = 1.5
    phi3_divergence: float = 1.0
    phi3_lookahead: int = 10  # steps [t+1, ..., t+10]

    # ϕ4: brake when distance too small
    phi4_dist: float = 7.0

    # ϕ5 implicitly uses TTC with a 3-step window; no extra parameters for now.


def evaluate_requirements_for_dataframe(
    df: pd.DataFrame,
    cfg: RequirementsConfig | None = None,
    *,
    track_phi3_violation: bool = False,
) -> Tuple[Dict[str, bool], Optional[int]]:
    """
    Evaluate ϕ1–ϕ5 on a single scenario trace DataFrame.

    Returns:
        (verdicts, phi3_violation_t)
        verdicts: {"ϕ1": bool, ..., "ϕ5": bool}
        phi3_violation_t: first index t where ϕ3 is violated (or None)
    """
    if cfg is None:
        cfg = RequirementsConfig()

    n = len(df)
    phi1 = phi2 = phi3 = phi4 = phi5 = True
    phi3_violation_t: Optional[int] = None

    # We will guard lookahead uses by bounds on t.
    for t in range(n):
        ttc = float(df.loc[t, "TTC"])
        brake_now = bool(df.loc[t, "brake"])
        ego_acc = float(df.loc[t, "ego_acc"])
        ego_x = float(df.loc[t, "ego_x"])
        ego_y = float(df.loc[t, "ego_y"])
        target_y = float(df.loc[t, "target_y"])
        target_x = float(df.loc[t, "target_x"])
        dist = float(df.loc[t, "distance"])

        # ϕ1: low TTC → some brake in next phi1_window steps
        # Only apply if we have enough future samples.
        last_phi1_idx = t + cfg.phi1_window - 1
        if last_phi1_idx < n:
            if ttc < cfg.ttc_low:
                window_brake = df.loc[t:last_phi1_idx, "brake"]
                if not bool(window_brake.any()):
                    phi1 = False

        # ϕ2: hard brake only allowed when TTC is already small
        if ego_acc < cfg.brake_hard and ttc >= cfg.ttc_hard_brake:
            phi2 = False

        # ϕ3: close lateral/longitudinal intrusion → eventually diverge laterally
        # Needs phi3_lookahead steps ahead: we use t+1..t+phi3_lookahead.
        last_phi3_idx = t + cfg.phi3_lookahead
        if last_phi3_idx < n:
            x_gap_abs = abs(ego_x - target_x)
            y_gap_abs = abs(ego_y - target_y)

            in_zone = (
                cfg.phi3_y_zone_low < target_y < cfg.phi3_y_zone_high
                and x_gap_abs < cfg.phi3_x_zone_max
                and y_gap_abs < cfg.phi3_y_zone_max
            )

            if in_zone:
                future_ego_y = df.loc[t + 1 : last_phi3_idx, "ego_y"]
                future_target_y = df.loc[t + 1 : last_phi3_idx, "target_y"]
                future_diff = (future_ego_y - future_target_y).abs()
                # Existential: there exists k in [1..phi3_lookahead] with |ego_y - target_y| > divergence
                if not bool(future_diff.gt(cfg.phi3_divergence).any()):
                    phi3 = False
                    if track_phi3_violation and phi3_violation_t is None:
                        phi3_violation_t = t

        # ϕ4: if distance < threshold, must be braking at that instant
        if dist < cfg.phi4_dist and not brake_now:
            phi4 = False

        # ϕ5: if TTC strictly decreasing over 3 samples, must brake at t+2
        if t + 2 < n:
            ttc0 = ttc
            ttc1 = float(df.loc[t + 1, "TTC"])
            ttc2 = float(df.loc[t + 2, "TTC"])
            if ttc0 > ttc1 > ttc2:
                if not bool(df.loc[t + 2, "brake"]):
                    phi5 = False

    verdicts: Dict[str, bool] = {
        "ϕ1": phi1,
        "ϕ2": phi2,
        "ϕ3": phi3,
        "ϕ4": phi4,
        "ϕ5": phi5,
    }
    return verdicts, phi3_violation_t


def evaluate_requirements_for_grouped(
    grouped: Dict[str, pd.DataFrame],
    cfg: RequirementsConfig | None = None,
    *,
    track_phi3_violation: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, Optional[int]]]:
    """
    Convenience wrapper: evaluate ϕ1–ϕ5 for each scenario in a grouped dict.

    grouped: mapping scenario -> df
    Returns:
        (results_df, phi3_indices)
        results_df has columns: scenario, ϕ1, ..., ϕ5
        phi3_indices maps scenario -> first ϕ3 violation index (or None)
    """
    if cfg is None:
        cfg = RequirementsConfig()

    rows = []
    phi3_indices: Dict[str, Optional[int]] = {}

    for scenario, df in grouped.items():
        verdicts, idx = evaluate_requirements_for_dataframe(
            df, cfg, track_phi3_violation=track_phi3_violation
        )
        row = {"scenario": scenario}
        row.update(verdicts)
        rows.append(row)
        phi3_indices[scenario] = idx

    results_df = pd.DataFrame(rows)
    return results_df, phi3_indices
