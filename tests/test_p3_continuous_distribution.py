"""v4.16 P3 — continuous-distribution visualization tests.

Verifies the KDE-shaped helper that turns the discrete-branch
ConsoleResult into a smoothed density curve over the user's time
horizon.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from console import (  # noqa: E402
    ConsoleHypothesis,
    ConsoleResult,
    _branch_characteristic_time,
    build_continuous_distribution,
)


def _hyp(
    label: str = "x",
    branch_type: str = "realistic",
    probability: float = 0.3,
) -> ConsoleHypothesis:
    return ConsoleHypothesis(
        label=label,
        narrative="",
        probability=probability,
        key_uncertainty_driver="",
        depends_on_decision=None,
        branch_type=branch_type,
    )


def _result(hyps: list[ConsoleHypothesis]) -> ConsoleResult:
    return ConsoleResult(
        scenario="x",
        decision_options=[],
        hypotheses=hyps,
        joint_offdiag=[],
        recommended_evidence=[],
        used_omytea_substrate=False,
    )


# ----- _branch_characteristic_time -----


def test_wishful_branch_centers_early() -> None:
    mu = _branch_characteristic_time(_hyp(branch_type="wishful"), 10.0)
    assert mu == pytest.approx(2.0)


def test_realistic_branch_centers_mid() -> None:
    mu = _branch_characteristic_time(_hyp(branch_type="realistic"), 10.0)
    assert mu == pytest.approx(5.0)


def test_worst_branch_centers_late() -> None:
    mu = _branch_characteristic_time(_hyp(branch_type="worst"), 10.0)
    assert mu == pytest.approx(7.0)


def test_unknown_branch_type_falls_back_to_realistic() -> None:
    mu = _branch_characteristic_time(_hyp(branch_type="weird"), 10.0)
    assert mu == pytest.approx(5.0)


# ----- build_continuous_distribution — basics -----


def test_no_hypotheses_returns_none() -> None:
    out = build_continuous_distribution(_result([]), time_horizon_months=6)
    assert out is None


def test_returns_expected_keys() -> None:
    out = build_continuous_distribution(
        _result([_hyp(probability=1.0)]),
        time_horizon_months=6, n_points=10,
    )
    assert out is not None
    expected = {
        "x_months", "density", "per_branch_density",
        "characteristic_times", "sigma_months",
        "horizon_months", "n_points",
    }
    assert expected.issubset(set(out.keys()))


def test_x_length_matches_n_points() -> None:
    out = build_continuous_distribution(
        _result([_hyp()]), time_horizon_months=6, n_points=25,
    )
    assert out is not None
    assert len(out["x_months"]) == 25
    assert len(out["density"]) == 25


def test_x_axis_spans_zero_to_horizon() -> None:
    out = build_continuous_distribution(
        _result([_hyp()]), time_horizon_months=12, n_points=13,
    )
    assert out is not None
    assert out["x_months"][0] == pytest.approx(0.0)
    assert out["x_months"][-1] == pytest.approx(12.0)


def test_per_branch_density_has_one_series_per_hypothesis() -> None:
    out = build_continuous_distribution(
        _result([_hyp("a"), _hyp("b"), _hyp("c")]),
        time_horizon_months=6, n_points=20,
    )
    assert out is not None
    assert set(out["per_branch_density"].keys()) == {"a", "b", "c"}
    for series in out["per_branch_density"].values():
        assert len(series) == 20


def test_density_is_sum_of_per_branch() -> None:
    out = build_continuous_distribution(
        _result([_hyp("a", probability=0.4),
                 _hyp("b", probability=0.6)]),
        time_horizon_months=6, n_points=15,
    )
    assert out is not None
    for i, total in enumerate(out["density"]):
        per_sum = sum(
            out["per_branch_density"][lbl][i]
            for lbl in out["per_branch_density"]
        )
        assert total == pytest.approx(per_sum)


def test_density_nonnegative_everywhere() -> None:
    out = build_continuous_distribution(
        _result([_hyp(branch_type="wishful", probability=0.1),
                 _hyp(branch_type="worst", probability=0.1)]),
        time_horizon_months=6, n_points=30,
    )
    assert out is not None
    assert all(d >= 0 for d in out["density"])


# ----- Characteristic-time alignment in output -----


def test_wishful_kernel_peaks_near_0_2_horizon() -> None:
    """A wishful branch's contribution should peak around 0.2 ×
    horizon, where its Gaussian kernel is centered."""
    horizon = 10.0
    out = build_continuous_distribution(
        _result([_hyp("w", branch_type="wishful", probability=1.0)]),
        time_horizon_months=horizon, n_points=101,
    )
    assert out is not None
    series = out["per_branch_density"]["w"]
    peak_idx = max(range(len(series)), key=lambda i: series[i])
    peak_t = out["x_months"][peak_idx]
    assert abs(peak_t - 0.2 * horizon) < 0.5  # within half a month


def test_worst_kernel_peaks_near_0_7_horizon() -> None:
    horizon = 10.0
    out = build_continuous_distribution(
        _result([_hyp("w", branch_type="worst", probability=1.0)]),
        time_horizon_months=horizon, n_points=101,
    )
    assert out is not None
    series = out["per_branch_density"]["w"]
    peak_idx = max(range(len(series)), key=lambda i: series[i])
    peak_t = out["x_months"][peak_idx]
    assert abs(peak_t - 0.7 * horizon) < 0.5


def test_characteristic_times_in_output_match_helper() -> None:
    """Output's characteristic_times dict should agree with the
    underlying _branch_characteristic_time helper."""
    out = build_continuous_distribution(
        _result([
            _hyp("w", branch_type="wishful"),
            _hyp("r", branch_type="realistic"),
            _hyp("x", branch_type="worst"),
        ]),
        time_horizon_months=12, n_points=20,
    )
    assert out is not None
    assert out["characteristic_times"]["w"] == pytest.approx(2.4)
    assert out["characteristic_times"]["r"] == pytest.approx(6.0)
    assert out["characteristic_times"]["x"] == pytest.approx(8.4)


# ----- Sigma scales with horizon -----


def test_sigma_scales_with_horizon() -> None:
    """sigma = sigma_fraction × horizon, floor of 0.05 to avoid zero."""
    out_short = build_continuous_distribution(
        _result([_hyp()]), time_horizon_months=6,
        n_points=10, sigma_fraction=0.15,
    )
    out_long = build_continuous_distribution(
        _result([_hyp()]), time_horizon_months=24,
        n_points=10, sigma_fraction=0.15,
    )
    assert out_short is not None and out_long is not None
    assert out_short["sigma_months"] == pytest.approx(0.9)
    assert out_long["sigma_months"] == pytest.approx(3.6)


def test_sigma_floored_at_minimum() -> None:
    """Even with horizon × fraction below 0.05, sigma stays ≥ 0.05."""
    out = build_continuous_distribution(
        _result([_hyp()]), time_horizon_months=0.1,
        n_points=5, sigma_fraction=0.001,
    )
    assert out is not None
    assert out["sigma_months"] >= 0.05


# ----- Probability-weighted contribution -----


def test_higher_probability_branch_dominates_density() -> None:
    """A 0.9-probability branch's Gaussian peak should be ~9× the
    height of a 0.1-probability branch's peak."""
    out = build_continuous_distribution(
        _result([
            _hyp("big", branch_type="realistic", probability=0.9),
            _hyp("small", branch_type="realistic", probability=0.1),
        ]),
        time_horizon_months=6, n_points=51,
    )
    assert out is not None
    big_peak = max(out["per_branch_density"]["big"])
    small_peak = max(out["per_branch_density"]["small"])
    assert big_peak / small_peak == pytest.approx(9.0, rel=0.01)


# ----- Edge cases -----


def test_n_points_below_2_returns_degenerate() -> None:
    """A single sample point is degenerate; UI should skip rendering."""
    out = build_continuous_distribution(
        _result([_hyp()]), time_horizon_months=6, n_points=1,
    )
    assert out is not None
    assert out["n_points"] == 1
    assert len(out["x_months"]) == 1


def test_zero_horizon_returns_degenerate() -> None:
    out = build_continuous_distribution(
        _result([_hyp()]), time_horizon_months=0, n_points=10,
    )
    assert out is not None
    assert out["n_points"] == 1


def test_negative_horizon_returns_degenerate() -> None:
    out = build_continuous_distribution(
        _result([_hyp()]), time_horizon_months=-3, n_points=10,
    )
    assert out is not None
    assert out["n_points"] == 1


def test_gaussian_normalization_constants() -> None:
    """Sanity check: a single branch with probability 1 + small σ
    should integrate (trapezoidal-rule) to roughly 1."""
    out = build_continuous_distribution(
        _result([_hyp(branch_type="realistic", probability=1.0)]),
        time_horizon_months=10, n_points=1001,
        sigma_fraction=0.1,
    )
    assert out is not None
    # Trapezoidal integration of the total density over the horizon.
    x = out["x_months"]
    d = out["density"]
    integral = sum(
        0.5 * (d[i] + d[i + 1]) * (x[i + 1] - x[i])
        for i in range(len(x) - 1)
    )
    # The mean is at 0.5 × horizon (middle), so most mass is inside
    # the horizon. With σ=1.0 and μ=5.0 over [0,10], integral should
    # be close to 1.0 (a small tail leaks out the edges).
    assert 0.9 < integral < 1.01
