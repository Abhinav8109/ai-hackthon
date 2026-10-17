import pytest
from backend.services.analytics import (
    calculate_qoq_variance,
    calculate_financial_summary,
    calculate_penalty_exposure,
    generate_linear_forecast,
    run_what_if_scenario
)
from backend.models.schemas import ScenarioInput

def test_qoq_variance_higher_is_better_breach():
    res = calculate_qoq_variance(
        metric_name="API Availability",
        category="SLA",
        reporting_period="2026-Q3",
        actual=98.8,
        target=99.5,
        unit="%",
        direction="higher_is_better",
        previous_value=99.6
    )
    assert res.breached is True
    assert res.variance_vs_target == round(98.8 - 99.5, 4)
    assert res.trend == "deteriorating"
    assert res.materiality_flag is True

def test_qoq_variance_lower_is_better_improving():
    res = calculate_qoq_variance(
        metric_name="P1 Incident Count",
        category="Quality",
        reporting_period="2026-Q3",
        actual=2.0,
        target=4.0,
        unit="count",
        direction="lower_is_better",
        previous_value=5.0
    )
    assert res.breached is False
    assert res.trend == "improving"
    assert res.pct_change == -60.0

def test_qoq_variance_zero_denominator_handled():
    # If prior value was 0, pct_change should not crash and be None
    res = calculate_qoq_variance(
        metric_name="Penalty Events",
        category="SLA",
        reporting_period="2026-Q3",
        actual=3.0,
        target=0.0,
        unit="count",
        direction="lower_is_better",
        previous_value=0.0
    )
    assert res.pct_change is None
    assert res.breached is True
    assert "pct undefined due to zero baseline" in res.formula_explanation

def test_financial_summary_calculations():
    fin = calculate_financial_summary(
        reporting_period="2026-Q3",
        approved_budget=1000000.0,
        planned_spend=800000.0,
        actual_spend=850000.0,
        forecast_spend=900000.0,
        revenue=1200000.0,
        cost=850000.0,
        penalty_exposure=25000.0
    )
    assert fin.budget_variance == 50000.0
    assert fin.budget_utilization_pct == 85.0
    assert fin.gross_profit == 350000.0
    assert fin.gross_margin_pct == round((350000.0 / 1200000.0) * 100, 2)
    assert fin.total_penalty_exposure == 25000.0

def test_penalty_exposure_calculation_and_cap():
    # Breach: Target 99.5%, Actual 98.5% -> 1.0% breach -> 10 steps of 0.1%
    # Step rate: $5,000 -> Raw = $50,000. Cap = $30,000.
    pen = calculate_penalty_exposure(
        rule_id="RULE-SLA-01",
        sla_name="Uptime SLA",
        target_threshold=99.5,
        actual_measured=98.5,
        penalty_rate_per_unit=5000.0,
        unit_step=0.1,
        cap_amount=30000.0,
        grace_period_threshold=99.0
    )
    assert pen.calculated_exposure == 50000.0
    assert pen.effective_exposure == 30000.0
    assert pen.validation_status == "capped"

def test_penalty_grace_period():
    # Grace period: 99.0% threshold. Actual is 99.2% (target 99.5%)
    pen = calculate_penalty_exposure(
        rule_id="RULE-SLA-02",
        sla_name="Uptime SLA",
        target_threshold=99.5,
        actual_measured=99.2,
        penalty_rate_per_unit=5000.0,
        unit_step=0.1,
        cap_amount=30000.0,
        grace_period_threshold=99.0
    )
    assert pen.grace_period_applied is True
    assert pen.effective_exposure == 0.0

def test_linear_forecast():
    # History: 10, 20, 30 -> next should be 40
    res = generate_linear_forecast([10.0, 20.0, 30.0], forecast_steps=2)
    assert res["forecast_values"] == [40.0, 50.0]
    assert res["method"] == "ordinary_least_squares_linear"

def test_what_if_scenario():
    baseline = {
        "sla_achievement_pct": 98.0,
        "actual_spend": 1000000.0,
        "penalty_exposure": 40000.0,
        "gross_margin_pct": 20.0
    }
    inputs = ScenarioInput(
        scenario_name="Aggressive Recovery",
        sla_recovery_delta_pct=1.5,
        cost_reduction_delta=50000.0,
        penalty_relief_pct=50.0
    )
    result = run_what_if_scenario(baseline, inputs)
    assert result.projected["sla_achievement_pct"] == 99.5
    assert result.projected["actual_spend"] == 950000.0
    assert result.projected["penalty_exposure"] == 20000.0
    assert len(result.tradeoffs) > 0
