"""
Report Generator Module for InterviewPilot AI.
Produces comprehensive scorecards, Plotly radar/bar visualizations,
consistency matrices, candidate-facing feedback notes, and recruiter follow-up guides.
Guarantees human-in-the-loop oversight and evidence-backed evaluations.
"""

from typing import Dict, Any, List
import plotly.graph_objects as go
from agent import InterviewState, TARGET_COMPETENCIES


def compute_overall_score(state: InterviewState) -> Dict[str, Any]:
    """
    Computes weighted aggregate score and recruiter recommendation.
    Weights:
    - Technical Depth: 30%
    - Problem Solving & Scenarios: 25%
    - System Design & Scalability: 20%
    - Behavioral & Ownership: 15%
    - Communication & Clarity: 10%
    """
    weights = {
        "Technical Depth": 0.30,
        "Problem Solving & Scenarios": 0.25,
        "System Design & Scalability": 0.20,
        "Behavioral & Ownership": 0.15,
        "Communication & Clarity": 0.10
    }

    comp_scores: Dict[str, float] = {}
    for t in state.history:
        comp_scores[t.competency] = float(t.final_score)

    weighted_sum = 0.0
    total_weight = 0.0

    for comp, weight in weights.items():
        score = comp_scores.get(comp, 3.0)
        weighted_sum += score * weight
        total_weight += weight

    overall = round(weighted_sum / total_weight if total_weight > 0 else 3.0, 2)

    # Check for consistency flags
    clarification_flags = sum(1 for f in state.consistency_findings if f.status == "Needs Clarification")

    # Recruiter recommendation logic
    if clarification_flags >= 2 or any(score <= 1.5 for score in comp_scores.values()):
        recommendation = "NEEDS HUMAN REVIEW"
        rec_color = "#FFB020"  # Amber/Yellow
        rec_desc = "Significant variance between resume claims and interview depth, or low core competency score. Recruiter should conduct manual review."
    elif overall >= 3.8 and all(score >= 3.0 for score in comp_scores.values()):
        recommendation = "ADVANCE TO TECHNICAL ROUND"
        rec_color = "#00F0FF"  # Cyan/Green
        rec_desc = "Strong demonstration of technical depth, structured problem solving, and production architecture awareness."
    elif overall >= 3.0:
        recommendation = "HOLD / BORDERLINE"
        rec_color = "#A855F7"  # Purple
        rec_desc = "Solid foundational capabilities with moderate technical depth. Recommend targeted follow-up probing in Round 2."
    else:
        recommendation = "NEEDS HUMAN REVIEW (BELOW BENCHMARK)"
        rec_color = "#EF4444"  # Red
        rec_desc = "Scores fall below standard benchmark for senior profile. Requires human recruiter review before final decision."

    return {
        "overall_score": overall,
        "competency_scores": comp_scores,
        "recommendation": recommendation,
        "rec_color": rec_color,
        "rec_desc": rec_desc,
        "clarification_flags": clarification_flags
    }


def create_competency_radar_chart(comp_scores: Dict[str, float]) -> go.Figure:
    """
    Generates a dark-themed Plotly Radar Chart comparing Candidate vs Target Benchmark.
    """
    categories = list(comp_scores.keys())
    candidate_values = list(comp_scores.values())
    target_values = [4.0] * len(categories)

    # Close the polygon loop
    categories_closed = categories + [categories[0]]
    candidate_closed = candidate_values + [candidate_values[0]]
    target_closed = target_values + [target_values[0]]

    fig = go.Figure()

    # Target Benchmark Trace
    fig.add_trace(go.Scatterpolar(
        r=target_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(124, 77, 255, 0.15)',
        line=dict(color='#7C4DFF', width=2, dash='dash'),
        name='Target Benchmark (4.0/5)'
    ))

    # Candidate Performance Trace
    fig.add_trace(go.Scatterpolar(
        r=candidate_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(0, 240, 255, 0.25)',
        line=dict(color='#00F0FF', width=3),
        name='Candidate Score'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickvals=[1, 2, 3, 4, 5],
                tickfont=dict(color='#94A3B8', size=10),
                gridcolor='rgba(255, 255, 255, 0.1)',
                linecolor='rgba(255, 255, 255, 0.1)'
            ),
            angularaxis=dict(
                tickfont=dict(color='#F1F5F9', size=11, family='sans-serif'),
                gridcolor='rgba(255, 255, 255, 0.1)',
                linecolor='rgba(255, 255, 255, 0.1)'
            ),
            bgcolor='rgba(15, 23, 42, 0.6)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(
            font=dict(color='#F1F5F9', size=11),
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=40, r=40, t=30, b=40),
        height=360
    )
    return fig


def create_competency_bar_chart(comp_scores: Dict[str, float]) -> go.Figure:
    """
    Generates a horizontal bar chart displaying competency scores.
    """
    categories = list(comp_scores.keys())
    scores = list(comp_scores.values())

    colors = ['#00F0FF' if s >= 4.0 else ('#A855F7' if s >= 3.0 else '#EF4444') for s in scores]

    fig = go.Figure(go.Bar(
        x=scores,
        y=categories,
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='rgba(255,255,255,0.2)', width=1)
        ),
        text=[f"{s}/5" for s in scores],
        textposition='auto',
        textfont=dict(color='#FFFFFF', size=12)
    ))

    fig.add_vline(x=3.5, line_width=1.5, line_dash="dash", line_color="#E2E8F0")

    fig.update_layout(
        xaxis=dict(
            range=[0, 5.2],
            tickvals=[1, 2, 3, 4, 5],
            gridcolor='rgba(255,255,255,0.08)',
            tickfont=dict(color='#94A3B8')
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(color='#F8FAFC', size=11)
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=20, t=10, b=20),
        height=280
    )
    return fig


def generate_candidate_feedback_letter(state: InterviewState, overall_score: float) -> str:
    """
    Constructs a polite, constructive, candidate-facing feedback message.
    """
    name = state.candidate_name
    strengths: List[str] = []
    growth_areas: List[str] = []

    for t in state.history:
        if t.final_score >= 4:
            strengths.append(f"{t.competency} ({t.evaluation.strengths})")
        elif t.final_score <= 2 and t.evaluation.gaps:
            growth_areas.append(f"{t.competency}: Focus on elaborating production failure modes and trade-offs.")

    strengths_str = "\n".join([f"• {s}" for s in strengths[:3]]) if strengths else "• Demonstrated clear motivation and general architectural awareness."
    growth_str = "\n".join([f"• {g}" for g in growth_areas[:2]]) if growth_areas else "• Continue detailing quantifiable metrics and system edge cases."

    letter = f"""Dear {name},

Thank you for participating in the first-round technical screening interview for the {state.job_title} position.

Our team appreciated learning more about your technical background and experience. Here is a summary of the key strengths and constructive feedback identified during your interview:

Key Strengths:
{strengths_str}

Areas for Continued Growth:
{growth_str}

Next Steps:
Our talent acquisition team conducts a thorough human review of all technical screening results. A recruiter will be in touch with you shortly regarding the next steps in our hiring process.

We wish you continued success in your engineering endeavors!

Warm regards,
NexusAI Talent Acquisition Team
"""
    return letter


def generate_markdown_report(state: InterviewState) -> str:
    """
    Generates a full, publication-ready Markdown audit scorecard.
    """
    metrics = compute_overall_score(state)
    name = state.candidate_name
    title = state.job_title
    overall = metrics["overall_score"]
    rec = metrics["recommendation"]
    rec_desc = metrics["rec_desc"]

    md = f"""# 📋 InterviewPilot AI — Candidate Evaluation Scorecard
**Candidate:** {name} | **Target Role:** {title}  
**Date:** {state.history[0].evaluation.competency if state.history else "N/A"} Session | **Evaluation Engine:** InterviewPilot Agentic Orchestrator v1.0  

---

## 🏆 Executive Summary & Recruiter Recommendation
- **Overall Score:** `{overall} / 5.0`
- **Recommendation:** **`{rec}`**
- **Assessment Rationale:** {rec_desc}

> ⚠️ **Human Oversight Safeguard Notice:**  
> This evaluation is an AI-assisted recommendation to support recruiter decision-making. In compliance with ethical AI hiring standards, **no candidate is ever automatically rejected** by this software. All borderline and low-confidence scores require human recruiter review.

---

## 📊 Competency Breakdown & Verbatim Evidence

| Competency | Score | Verbatim Evidence Quote | Rubric Finding |
| :--- | :---: | :--- | :--- |
"""

    for t in state.history:
        quote = t.evaluation.evidence_quote.replace("\n", " ").strip()
        md += f"| **{t.competency}** | `{t.final_score}/5` | {quote} | {t.evaluation.rubric_match} |\n"

    md += """
---

## 🔍 Resume Consistency & Claim Verification

| Claim ID | Resume Statement | Status | Interview Evidence & Analysis |
| :--- | :--- | :---: | :--- |
"""

    for f in state.consistency_findings:
        status_icon = "✅ Supported" if f.status == "Supported" else ("⚠️ Needs Clarification" if f.status == "Needs Clarification" else "ℹ️ Partially Supported")
        md += f"| `{f.claim_id}` | {f.claim_text} | **{status_icon}** | {f.analysis} |\n"

    md += f"""
---

## 🎯 Recruiter Round-2 Probing Recommendations
Based on the candidate's screening responses, we recommend human interviewers probe the following areas in Round 2:
"""

    for t in state.history:
        if t.final_score <= 3 and t.evaluation.gaps:
            md += f"- **{t.competency}:** Probe deeper into: *{t.evaluation.gaps}*\n"

    md += f"""
---

## ✉️ Candidate-Facing Feedback Draft
```text
{generate_candidate_feedback_letter(state, overall)}
```

---
*Report generated by InterviewPilot AI — Agentic First-Round Screening Assistant.*
"""
    return md
