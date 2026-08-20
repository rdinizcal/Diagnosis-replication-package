import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from requirements import (
    RequirementsConfig,
    evaluate_requirements_for_grouped,
    evaluate_requirements_for_dataframe,
)
from sim_config import DEFAULT_SIM_CONFIG as SIM_CFG
from sim_config import fault_config_for_scenario

dt = SIM_CFG.dt
T = SIM_CFG.T
steps = int(T / dt)

ego_start_y = SIM_CFG.ego_start_y
target_start_lane_y = SIM_CFG.target_start_lane_y
target_end_lane_y = SIM_CFG.target_end_lane_y

# scenarios = ["normal", "smooth", "cut-in", "retry"]
scenarios = ["retry"]
SCENARIO_ORDER = ["normal", "smooth", "cut-in", "retry"]
line_styles = {
    "normal": "solid",
    "smooth": "dashed",
    "cut-in": "dashdot",
    "retry": "dotted"
}

plot_configs = [
    ("distance", None, "Distance Between Vehicles", "Time (s)", "Distance (m)"),
    ("TTC", None, "Time to Collision (TTC)", "Time (s)", "Time to Collision (s)"),
    ("ego_acc", None, "Ego Acceleration", "Time (s)", "Ego acceleration (m/s$^2$)"),
    ("target_y", None, "Target Vehicle Y Position", "Time (s)", "Y pos vehicle (m)"),
    ("y_gap", None, "Lateral Gap (Y)", "Time (s)", "Y gap (m)"),
    ("x_gap", None, "Longitudinal Gap (X)", "Time (s)", "X gap (m)"),
]


xy_plot_config = [
    ("ego_y", "target_y", "Y vs X Trajectories", "X (m)", "Y (m)")
]

def simulate_scenario(scenario):
    fault = fault_config_for_scenario(scenario)

    ego_pos = np.array([0.0, ego_start_y])
    ego_velocity = SIM_CFG.ego_velocity
    target_initial_x = SIM_CFG.target_initial_x
    target_velocity = SIM_CFG.target_velocity

    if scenario == "normal":
        lane_change_start = 2.0
        lane_change_end = 3.0
    elif scenario == "smooth":
        lane_change_start = 2.0
        lane_change_end = 5.0
    elif scenario == "cut-in":
        lane_change_start = 1.0
        lane_change_end = 2.0
    elif scenario == "retry":
        lane_change_start = 2.0
        lane_change_end = 3.0
        retry_start = 4.5
        retry_end = 5.5

    trace = []
    ego_x = 0.0
    ego_y = ego_pos[1]
    target_x = target_initial_x
    # Initialise target_y so the first crash check is well-defined
    target_y = target_start_lane_y

    # F1 (evasion latch) state: a "maneuver completed" flag intended to stop
    # oscillatory nudging. Once ego has nudged and decayed back to its lane it
    # is set and — the bug — never re-armed on a new intrusion event, so the
    # evasive nudge cannot fire again on the target's second attempt.
    has_nudged = False
    evasion_completed = False

    for step in range(steps):
        t = step * dt

        if abs(ego_x - target_x) <= 0.5 and abs(ego_y - target_y) <= 0.5:
            print("[%s]- CRASH!!" % (scenario))
            break

        # Target lateral position
        if scenario != "retry":
            if lane_change_start <= t <= lane_change_end:
                progress = (t - lane_change_start) / (lane_change_end - lane_change_start)
                target_y = target_start_lane_y + progress * (target_end_lane_y - target_start_lane_y)
            elif t < lane_change_start:
                target_y = target_start_lane_y
            else:
                target_y = target_end_lane_y
        else:
            if lane_change_start <= t <= lane_change_end:
                progress = (t - lane_change_start) / (lane_change_end - lane_change_start)
                target_y = target_start_lane_y + progress * (3.0 - target_start_lane_y)
            elif retry_start <= t <= retry_end:
                progress = (t - retry_start) / (retry_end - retry_start)
                target_y = target_start_lane_y + progress * (target_end_lane_y - target_start_lane_y)
            elif t < lane_change_start:
                target_y = target_start_lane_y
            elif t > retry_end:
                target_y = target_end_lane_y
            else:
                target_y = target_start_lane_y

        # Compute distance and TTC
        dx = target_x - ego_x
        dy = target_y - ego_y
        distance = np.sqrt(dx**2 + dy**2)
        # rel_speed = abs(ego_velocity - target_velocity) if dx > 0 else 0.01
        # TTC = distance / rel_speed if rel_speed > 0 else np.inf

        dx = target_x - ego_x
        dv = target_velocity - ego_velocity  # relative velocity: target w.r.t. ego

        # Case 1: ego is behind and approaching
        if dx > 0 and dv < 0:
            TTC = dx / -dv

        # Case 2: ego is ahead and being approached
        elif dx < 0 and dv > 0:
            TTC = -dx / dv

        # Case 3: Not approaching → No collision
        else:
            TTC = np.inf

        # Adaptive Behavior
        if TTC < 2.0:
            desired_velocity = min(ego_velocity, target_velocity)
            ego_acc = -1.0 if ego_velocity > desired_velocity else 0.0
        else:
            ego_acc = 0.0

        if abs(ego_y - target_y) <= 2: # same lane
            if ego_x < target_x: # ego behind target
                if target_x - ego_x <= 2.0: ego_acc = -1
                elif 2.0 < target_x - ego_x <= 3.0: ego_acc = -0.5  
                elif target_x - ego_x > 3.0: ego_acc = 0.0
                else: ego_acc = 0.0
            else:
                 # Adaptive Behavior
                if TTC < 2.0:
                    desired_velocity = min(ego_velocity, target_velocity)
                    ego_acc = -1.0 if ego_velocity > desired_velocity else 0.0
                else:
                    ego_acc = 0.0

        # F2 (AEB miscalibration): over-aggressive emergency brake with both
        # constants wrong w.r.t. ϕ2 — the trigger fires at TTC < 2.0 (should be
        # < 1.5 s) and the magnitude is -3.5 m/s² (should be limited to >= -3.0).
        # Placed after the ACC/same-lane rules so it overrides the milder ones,
        # mirroring where the old injection window sat.
        if fault.aeb_miscalibration and TTC < 2.0:
            ego_acc = -3.5

        # Ego reacts laterally to nearbY pos
        y_gap = abs(ego_y - target_y)
        x_gap = abs(ego_x - target_x)

        # F1 (evasion latch): once the maneuver is flagged complete the nudge is
        # suppressed and never re-armed, so the second-attempt intrusion gets no
        # evasive response.
        nudge_allowed = not (fault.evasion_latch and evasion_completed)

        if 0.25 < target_y < 3.5 and y_gap < 2.5 and x_gap < 3.5 and nudge_allowed:
            # nudge away laterally for safety
            ego_y = ego_start_y + 1.5
            has_nudged = True
        else:
            ego_y = ego_y-0.125 if ego_y > ego_start_y else ego_start_y

        # Arm the latch once ego has nudged and then decayed back to its lane.
        if has_nudged and ego_y == ego_start_y:
            evasion_completed = True


        ego_velocity = max(ego_velocity + ego_acc * dt, 0.0)
        ego_x += ego_velocity * dt
        target_x += target_velocity * dt
        brake = ego_acc < 0

        trace.append({
            "time": t,
            "ego_x": ego_x,
            "ego_y": ego_y,
            "target_x": target_x,
            "target_y": target_y,         
            "distance": distance,
            "TTC": TTC,
            "ego_acc": ego_acc,
            "brake": brake,
            "scenario": scenario
        ,
        "y_gap": abs(ego_y - target_y),
        "x_gap": abs(ego_x - target_x)
    })

    df = pd.DataFrame(trace)

    df["y_gap"] = (df["ego_y"] - df["target_y"]).abs()
    df["x_gap"] = (df["ego_x"] - df["target_x"]).abs()

    return df

import os
from pathlib import Path

def _save_single_time_plot(all_traces, sim_scenarios, var, ylabel, outpath, xlim=(0, 10)):
    fig, ax = plt.subplots(1, 1, figsize=(5.2, 2.2))  # ~one-column friendly
    for scenario in [s for s in SCENARIO_ORDER if s in sim_scenarios]:
        df = all_traces[all_traces["scenario"] == scenario]
        style = line_styles[scenario]
        ax.plot(df["time"], df[var], linestyle=style, linewidth=1, label=scenario)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel(ylabel)
    # ax.set_xlim(*xlim)
    ax.set_xlim(0, 6)
    ax.grid(True, which="both", axis="both")

    if var == "TTC":
        ax.set_ylim(1, 7)

    # Legend inside to avoid tiny external legends in one-column figures
    ax.legend(loc="best", frameon=False, ncol=2)

    fig.tight_layout()
    fig.savefig(outpath, format="pdf", bbox_inches="tight")
    plt.close(fig)

def _save_xy_plot(all_traces, sim_scenarios, outpath, xlim=(0, 200)):
    fig, ax = plt.subplots(1, 1, figsize=(5.2, 2.6))
    for scenario in [s for s in SCENARIO_ORDER if s in sim_scenarios]:

        df = all_traces[all_traces["scenario"] == scenario]
        style = line_styles[scenario]
        ax.plot(df["ego_x"], df["ego_y"], linestyle=style, linewidth=1, label=f"{scenario} ego")
        ax.plot(df["target_x"], df["target_y"], linestyle=style, linewidth=1, label=f"{scenario} target")

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_xlim(*xlim)
    ax.grid(True, which="both", axis="both")
    ax.legend(loc="best", frameon=False, ncol=2)

    fig.tight_layout()
    fig.savefig(outpath, format="pdf", bbox_inches="tight")
    plt.close(fig)

def run_sim_and_plot(selected_scenarios=None, out_dir="figures", save_pdf=True, show=False):
    if selected_scenarios is None:
        sim_scenarios = scenarios
    else:
        sim_scenarios = selected_scenarios

    all_traces = pd.concat([simulate_scenario(s) for s in sim_scenarios])

    grouped = {name: df.reset_index(drop=True) for name, df in all_traces.groupby("scenario")}
    cfg = RequirementsConfig()
    results_df, phi3_indices = evaluate_requirements_for_grouped(
        grouped, cfg, track_phi3_violation=True
    )
    print(results_df)

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.titlesize": 10,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "grid.linestyle": "--",
        "grid.alpha": 0.6,
        # makes text editable/searchable in the PDF
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    out_dir = Path(out_dir)
    if save_pdf:
        out_dir.mkdir(parents=True, exist_ok=True)

        _save_single_time_plot(all_traces, sim_scenarios, "distance", "Distance (m)", out_dir / "trace_distance.pdf")
        _save_single_time_plot(all_traces, sim_scenarios, "TTC", "TTC (s)", out_dir / "trace_ttc.pdf")
        _save_single_time_plot(all_traces, sim_scenarios, "ego_acc", "Ego acceleration (m/s$^2$)", out_dir / "trace_ego_acc.pdf")
        _save_single_time_plot(all_traces, sim_scenarios, "target_y", "Y pos (m)", out_dir / "trace_target_y.pdf")
        _save_single_time_plot(all_traces, sim_scenarios, "y_gap", "Y gap (m)", out_dir / "trace_y_gap.pdf")
        _save_single_time_plot(all_traces, sim_scenarios, "x_gap", "X gap (m)", out_dir / "trace_x_gap.pdf")

    if show:
        plt.show()