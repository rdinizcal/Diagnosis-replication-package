"""
test_verdict_matrix.py

HARD verification gate for the FaultConfig refactor (P2):
the Fig.-4 verdict matrix must be reproduced exactly by the FAULTY controller
(sim_lc_faulty.py), with all seeded faults living in the controller (no post-hoc
trace injection). After the P6 fixes land in sim_lc.py, the Fig.-4 matrix is a
property of the archived faulty version, so this test targets sim_lc_faulty.

Expected violations (everything else satisfied):
    normal : ϕ4
    smooth : ϕ4
    cut-in : ϕ2, ϕ4
    retry  : ϕ3, ϕ4
"""

import pandas as pd
import pytest

from sim_lc_faulty import simulate_scenario
from requirements import RequirementsConfig, evaluate_requirements_for_dataframe

SCENARIOS = ["normal", "smooth", "cut-in", "retry"]

# Expected verdicts: True == satisfied, False == violated.
EXPECTED = {
    "normal": {"ϕ1": True, "ϕ2": True, "ϕ3": True, "ϕ4": False},
    "smooth": {"ϕ1": True, "ϕ2": True, "ϕ3": True, "ϕ4": False},
    "cut-in": {"ϕ1": True, "ϕ2": False, "ϕ3": True, "ϕ4": False},
    "retry": {"ϕ1": True, "ϕ2": True, "ϕ3": False, "ϕ4": False},
}


@pytest.fixture(scope="module")
def verdicts():
    out = {}
    for s in SCENARIOS:
        df = simulate_scenario(s)
        v, _ = evaluate_requirements_for_dataframe(df, RequirementsConfig())
        out[s] = v
    return out


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_verdict_matrix(verdicts, scenario):
    v = verdicts[scenario]
    for phi, expected in EXPECTED[scenario].items():
        assert v[phi] == expected, (
            f"{scenario} {phi}: expected {'satisfied' if expected else 'violated'}, "
            f"got {'satisfied' if v[phi] else 'violated'}"
        )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_no_crash(scenario):
    # A CRASH breaks the loop early, truncating the trace below the horizon.
    from sim_config import DEFAULT_SIM_CONFIG as CFG
    steps = int(CFG.T / CFG.dt)
    df = simulate_scenario(scenario)
    assert len(df) == steps, f"{scenario} truncated at {len(df)}/{steps} steps (CRASH?)"
