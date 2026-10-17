from typing import List, Dict, Any, Optional
import math
from backend.models.schemas import (
    KPIVarianceResult,
    SLAIntelligenceItem,
    PenaltyCalculationDetail,
    FinancialIntelligenceSummary,
    ScenarioInput,
    ScenarioComparisonResult,
    CanonicalKPIRecord
)

def calculate_qoq_variance(
    metric_name: str,
    category: str,
    reporting_period: str,
    actual: float,
    target: float,
    unit: str,
    direction: str = "higher_is_better",
    previous_value: Optional[float] = None,
    source_lineage: str = "Imported record"
) -> KPIVarianceResult:
    """
    Deterministic calculation for Quarter-over-Quarter changes and target compliance.
    Handles zero denominator, metric directionality, and materiality thresholds.
    """
    absolute_change = None
    pct_change = None
    trend = "stable"

    if previous_value is not None:
        absolute_change = round(actual - previous_value, 4)
        if abs(previous_value) > 1e-9:
            pct_change = round(((actual - previous_value) / abs(previous_value)) * 100.0, 2)
        else:
            pct_change = None # Explicitly represented when denominator is zero

        # Determine trend based on improvement direction
        if direction == "higher_is_better":
            if actual > previous_value + 1e-6:
                trend = "improving"
            elif actual < previous_value - 1e-6:
                trend = "deteriorating"
            else:
                trend = "stable"
        else: # lower_is_better
            if actual < previous_value - 1e-6:
                trend = "improving"
            elif actual > previous_value + 1e-6:
                trend = "deteriorating"
            else:
                trend = "stable"

    # Evaluate target compliance
    if direction == "higher_is_better":
        variance_vs_target = round(actual - target, 4)
        breached = actual < target
    else: # lower_is_better
        variance_vs_target = round(target - actual, 4) # positive means better than target
        breached = actual > target

    # Materiality threshold: breach or QoQ swing > 5%
    materiality_flag = breached or (pct_change is not None and abs(pct_change) >= 5.0)

    formula_exp = f"Actual ({actual} {unit}) vs Target ({target} {unit})"
    if previous_value is not None:
        formula_exp += f" | Prior: {previous_value} {unit} (Δ {absolute_change} {unit}"
        if pct_change is not None:
            formula_exp += f", {pct_change}%)"
        else:
            formula_exp += ", pct undefined due to zero baseline)"

    return KPIVarianceResult(
        metric_name=metric_name,
        category=category,
        reporting_period=reporting_period,
        actual=actual,
        target=target,
        previous_period_value=previous_value,
        absolute_change=absolute_change,
        pct_change=pct_change,
        variance_vs_target=variance_vs_target,
        unit=unit,
        direction_of_improvement=direction,
        breached=breached,
        materiality_flag=materiality_flag,
        trend=trend,
        formula_explanation=formula_exp,
        source_lineage=source_lineage
    )

def calculate_financial_summary(
    reporting_period: str,
    approved_budget: float,
    planned_spend: float,
    actual_spend: float,
    forecast_spend: float,
    revenue: Optional[float] = None,
    cost: Optional[float] = None,
    penalty_exposure: float = 0.0,
    currency: str = "USD"
) -> FinancialIntelligenceSummary:
    """
    Deterministic financial calculations: Budget variance, utilization, gross profit, and gross margin.
    """
    budget_variance = round(actual_spend - planned_spend, 2)
    budget_utilization_pct = round((actual_spend / approved_budget * 100.0), 2) if approved_budget > 0 else 0.0

    gross_profit = None
    gross_margin_pct = None
    if revenue is not None and cost is not None:
        gross_profit = round(revenue - cost, 2)
        if revenue > 0:
            gross_margin_pct = round((gross_profit / revenue) * 100.0, 2)

    formulas = {
        "budget_variance": "actual_spend - planned_spend",
        "budget_utilization": "(actual_spend / approved_budget) * 100",
        "gross_profit": "revenue - cost",
        "gross_margin_pct": "(gross_profit / revenue) * 100"
    }

    return FinancialIntelligenceSummary(
        reporting_period=reporting_period,
        approved_budget=approved_budget,
        planned_spend=planned_spend,
        actual_spend=actual_spend,
        forecast_spend=forecast_spend,
        budget_variance=budget_variance,
        budget_utilization_pct=budget_utilization_pct,
        revenue=revenue,
        cost=cost,
        gross_profit=gross_profit,
        gross_margin_pct=gross_margin_pct,
        margin_variance_pct=None,
        total_penalty_exposure=penalty_exposure,
        currency=currency,
        formulas=formulas
    )

def calculate_penalty_exposure(
    rule_id: str,
    sla_name: str,
    target_threshold: float,
    actual_measured: float,
    penalty_rate_per_unit: float,
    unit_step: float = 0.1,
    cap_amount: float = 50000.0,
    grace_period_threshold: Optional[float] = None,
    rule_source: str = "Master Services Agreement (MSA) Schedule 4.2",
    currency: str = "USD"
) -> PenaltyCalculationDetail:
    """
    Transparent, verifiable contract penalty engine.
    Applies thresholds, steps, grace periods, and caps deterministically.
    """
    # Breach if actual is below target
    breach_amount = target_threshold - actual_measured
    if breach_amount <= 0:
        return PenaltyCalculationDetail(
            rule_id=rule_id,
            sla_name=sla_name,
            target_threshold=target_threshold,
            actual_measured=actual_measured,
            breach_interval=f"per {unit_step}% below target",
            penalty_basis="incremental_step",
            penalty_rate=penalty_rate_per_unit,
            calculated_exposure=0.0,
            grace_period_applied=False,
            cap_amount=cap_amount,
            effective_exposure=0.0,
            currency=currency,
            rule_source=rule_source,
            assumptions="No target breach detected.",
            validation_status="verified_contract"
        )

    # Check grace period
    grace_applied = False
    if grace_period_threshold is not None and actual_measured >= grace_period_threshold:
        grace_applied = True
        return PenaltyCalculationDetail(
            rule_id=rule_id,
            sla_name=sla_name,
            target_threshold=target_threshold,
            actual_measured=actual_measured,
            breach_interval=f"per {unit_step}% below target",
            penalty_basis="incremental_step",
            penalty_rate=penalty_rate_per_unit,
            calculated_exposure=0.0,
            grace_period_applied=True,
            cap_amount=cap_amount,
            effective_exposure=0.0,
            currency=currency,
            rule_source=rule_source,
            assumptions=f"Within contract grace band ({grace_period_threshold}% - {target_threshold}%).",
            validation_status="verified_contract"
        )

    # Calculate steps
    steps = math.ceil(breach_amount / unit_step) if unit_step > 0 else 1
    raw_penalty = round(steps * penalty_rate_per_unit, 2)
    effective_penalty = min(raw_penalty, cap_amount)

    status = "capped" if raw_penalty > cap_amount else "verified_contract"
    assumptions = (
        f"Breach of {round(breach_amount, 2)}% evaluated at {steps} steps of {unit_step}%. "
        f"Cap is ${cap_amount:,.2f}."
    )

    return PenaltyCalculationDetail(
        rule_id=rule_id,
        sla_name=sla_name,
        target_threshold=target_threshold,
        actual_measured=actual_measured,
        breach_interval=f"per {unit_step}% below target",
        penalty_basis="incremental_step",
        penalty_rate=penalty_rate_per_unit,
        calculated_exposure=raw_penalty,
        grace_period_applied=grace_applied,
        cap_amount=cap_amount,
        effective_exposure=effective_penalty,
        currency=currency,
        rule_source=rule_source,
        assumptions=assumptions,
        validation_status=status
    )

def generate_linear_forecast(
    historical_points: List[float],
    forecast_steps: int = 1
) -> Dict[str, Any]:
    """
    Deterministic linear trend forecast using least squares.
    Explicitly outputs method, slope, and confidence notice.
    """
    n = len(historical_points)
    if n < 2:
        return {
            "method": "insufficient_data",
            "forecast_values": historical_points[-1:] if historical_points else [0.0],
            "confidence_note": "Insufficient historical points for regression (minimum 2 required)."
        }

    x = list(range(n))
    y = historical_points
    x_mean = sum(x) / n
    y_mean = sum(y) / n

    denom = sum((xi - x_mean) ** 2 for xi in x)
    if abs(denom) < 1e-9:
        slope = 0.0
    else:
        slope = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n)) / denom
    
    intercept = y_mean - slope * x_mean

    projected = []
    for step in range(1, forecast_steps + 1):
        target_x = (n - 1) + step
        val = round(intercept + slope * target_x, 2)
        projected.append(val)

    return {
        "method": "ordinary_least_squares_linear",
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "history_count": n,
        "forecast_values": projected,
        "confidence_note": f"Based on linear extrapolation of {n} quarters. Assumes constant operational trajectory."
    }

def run_what_if_scenario(
    baseline: Dict[str, float],
    inputs: ScenarioInput
) -> ScenarioComparisonResult:
    """
    Evaluates scenario impacts on baseline SLA, Budget, and Margin.
    """
    baseline_sla = baseline.get("sla_achievement_pct", 98.2)
    baseline_spend = baseline.get("actual_spend", 1250000.0)
    baseline_penalty = baseline.get("penalty_exposure", 32500.0)
    baseline_margin = baseline.get("gross_margin_pct", 24.5)

    proj_sla = min(100.0, max(0.0, baseline_sla + inputs.sla_recovery_delta_pct))
    proj_spend = max(0.0, baseline_spend - inputs.cost_reduction_delta)
    proj_penalty = max(0.0, baseline_penalty * (1.0 - (inputs.penalty_relief_pct / 100.0)))
    
    # Margin calculation delta approximation
    margin_improvement = (inputs.cost_reduction_delta / baseline_spend * 10.0) if baseline_spend > 0 else 0.0
    proj_margin = round(baseline_margin + margin_improvement, 2)

    projected = {
        "sla_achievement_pct": round(proj_sla, 2),
        "actual_spend": round(proj_spend, 2),
        "penalty_exposure": round(proj_penalty, 2),
        "gross_margin_pct": round(proj_margin, 2)
    }

    delta = {
        "sla_achievement_delta": round(proj_sla - baseline_sla, 2),
        "spend_delta": round(proj_spend - baseline_spend, 2),
        "penalty_delta": round(proj_penalty - baseline_penalty, 2),
        "margin_delta": round(proj_margin - baseline_margin, 2)
    }

    # Feasibility scoring
    feasibility = 95.0
    if inputs.cost_reduction_delta > (baseline_spend * 0.15):
        feasibility -= 25.0
    if inputs.sla_recovery_delta_pct > 3.0:
        feasibility -= 20.0
    if inputs.milestone_acceleration_days > 30:
        feasibility -= 15.0

    tradeoffs = []
    if inputs.cost_reduction_delta > 0:
        tradeoffs.append("Cost reduction may increase risk on delivery milestones.")
    if inputs.sla_recovery_delta_pct > 1.5:
        tradeoffs.append("Targeting >1.5% SLA recovery requires on-call senior engineering allocation.")
    if inputs.milestone_acceleration_days > 14:
        tradeoffs.append("Schedule compression requires customer approval for deferred low-priority requirements.")

    impact_summary = (
        f"Scenario '{inputs.scenario_name}' projects SLA to reach {proj_sla}% "
        f"with ${inputs.cost_reduction_delta:,.0f} cost reduction and penalty relief of "
        f"${abs(delta['penalty_delta']):,.0f}."
    )

    return ScenarioComparisonResult(
        scenario_name=inputs.scenario_name,
        baseline=baseline,
        projected=projected,
        delta=delta,
        feasibility_score=max(20.0, min(100.0, feasibility)),
        impact_summary=impact_summary,
        tradeoffs=tradeoffs
    )
