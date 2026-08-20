"""
test_fix_verification.py

HARD verification gate for the P6 fixes: the fixed controller (sim_lc.py) must
satisfy ϕ1-ϕ4 in EVERY scenario, with no CRASH. Fixes live in controller logic
only (F1 latch re-arm, F2 AEB trigger, F3 Euclidean-distance brake).
"""

import pytest

from sim_lc import simulate_scenario
from requirements import RequirementsConfig, evaluate_requirements_for_dataframe
from sim_config import DEFAULT_SIM_CONFIG as CFG

SCENARIOS = ["normal", "smooth", "cut-in", "retry"]
PHIS = ["ϕ1", "ϕ2", "ϕ3", "ϕ4"]


@pytest.fixture(scope="module")
def verdicts():
    out = {}
    for s in SCENARIOS:
        df = simulate_scenario(s)
        v, _ = evaluate_requirements_for_dataframe(df, RequirementsConfig())
        out[s] = v
    return out


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_phi1_to_phi4_all_satisfied(verdicts, scenario):
    v = verdicts[scenario]
    for phi in PHIS:
        assert v[phi] is True, f"{scenario} {phi} not satisfied by fixed controller"


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_no_crash(scenario):
    steps = int(CFG.T / CFG.dt)
    df = simulate_scenario(scenario)
    assert len(df) == steps, f"{scenario} truncated at {len(df)}/{steps} steps (CRASH?)"
