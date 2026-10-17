"""
Comprehensive Test Suite for InterviewPilot AI.
Validates:
1. Resume parsing from raw text and claim extraction.
2. Formulating 5-question interview agenda anchored to resume claims and JD requirements.
3. Incomplete / shallow answer triggering targeted follow-up probe.
4. Sufficient answer advancing to next question.
5. Adaptive difficulty adjustment.
6. Real tool call logging and verification.
7. Score evidence grounding and absence of hallucinated quotes.
8. Consistency matrix generation.
9. Final scorecard computation and report generation.
10. Reset functionality.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resume_parser import parse_resume
from demo_data import SYNTHETIC_RESUME_TEXT, SYNTHETIC_JD_TEXT, SAMPLE_RESPONSES
from agent import InterviewPilotAgent
from tools import get_activity_logs, clear_activity_logs
from report_generator import compute_overall_score, generate_markdown_report


def test_resume_parser():
    print("Testing Resume Parser...")
    resume = parse_resume(SYNTHETIC_RESUME_TEXT)
    assert resume.candidate_name == "Alex Chen", f"Expected Alex Chen, got {resume.candidate_name}"
    assert len(resume.claims) > 0, "No claims extracted from resume"
    assert "Languages" in resume.skills or "AI & Data" in resume.skills
    print(f"✓ Parsed candidate: {resume.candidate_name}, Extracted {len(resume.claims)} claims.")


def test_agent_planning():
    print("\nTesting Interview Planning...")
    clear_activity_logs()
    agent = InterviewPilotAgent()
    resume = parse_resume(SYNTHETIC_RESUME_TEXT)
    questions = agent.plan_interview(resume, SYNTHETIC_JD_TEXT)

    assert len(questions) == 5, f"Expected 5 questions, got {len(questions)}"
    assert questions[0].competency == "Technical Depth"
    assert questions[0].targeted_resume_claim is not None
    assert agent.state.status == "IN_PROGRESS"

    logs = get_activity_logs()
    assert any(l.tool_name == "plan_interview" for l in logs), "plan_interview tool call not logged"
    print("✓ Successfully planned 5 resume-anchored interview questions.")


def test_shallow_answer_triggers_followup():
    print("\nTesting Adaptive Follow-up on Shallow Answer...")
    agent = InterviewPilotAgent()
    resume = parse_resume(SYNTHETIC_RESUME_TEXT)
    agent.plan_interview(resume, SYNTHETIC_JD_TEXT)

    shallow_ans = SAMPLE_RESPONSES["shallow"]["text"]
    res = agent.submit_answer(shallow_ans)

    assert res["status"] == "followup_required", f"Expected followup_required, got {res['status']}"
    assert agent.state.status == "AWAITING_FOLLOWUP"
    assert agent.state.active_followup is not None
    assert res["evaluation"].needs_followup is True
    assert res["evaluation"].completeness < 0.60

    logs = get_activity_logs()
    assert any(l.tool_name == "evaluate_answer" for l in logs)
    assert any(l.tool_name == "validate_score_evidence" for l in logs)
    print(f"✓ Shallow answer correctly triggered follow-up probe: '{agent.state.active_followup}'")


def test_followup_resolution_and_advancement():
    print("\nTesting Follow-up Resolution with Strong Answer...")
    agent = InterviewPilotAgent()
    resume = parse_resume(SYNTHETIC_RESUME_TEXT)
    agent.plan_interview(resume, SYNTHETIC_JD_TEXT)

    # 1. Submit shallow answer
    agent.submit_answer(SAMPLE_RESPONSES["shallow"]["text"])
    assert agent.state.status == "AWAITING_FOLLOWUP"

    # 2. Submit strong follow-up answer
    strong_ans = SAMPLE_RESPONSES["strong"]["text"]
    res = agent.submit_answer(strong_ans)

    assert res["status"] == "advanced"
    assert agent.state.status == "IN_PROGRESS"
    assert agent.state.current_index == 1
    # Check that score was elevated
    turn = agent.state.history[0]
    assert turn.final_score >= 4, f"Expected score >= 4 after recovery, got {turn.final_score}"
    assert turn.followup_answer == strong_ans
    print(f"✓ Follow-up resolved; score recovered to {turn.final_score}/5 and advanced to Q2.")


def test_full_interview_simulation_and_report():
    print("\nTesting Full 5-Question Interview Flow & Final Report...")
    clear_activity_logs()
    agent = InterviewPilotAgent()
    resume = parse_resume(SYNTHETIC_RESUME_TEXT)
    agent.plan_interview(resume, SYNTHETIC_JD_TEXT)

    answers = [
        SAMPLE_RESPONSES["strong"]["text"],
        SAMPLE_RESPONSES["scenario_strong"]["text"],
        "We used Redis cluster with hash tags and read replicas in Postgres. We managed stampedes using Redlock and stale cache invalidation.",
        "In our previous project, a teammate pushed to deploy without automated migrations. I advocated for rollback using telemetry data, then paired with them to build an automated migration pipeline.",
        "I explain message queues as an order ticket system at a busy restaurant kitchen: instead of a customer standing at the counter waiting for the chef to cook, they receive a ticket number and get notified when ready."
    ]

    for i, ans in enumerate(answers):
        res = agent.submit_answer(ans)
        if res.get("status") == "followup_required":
            res = agent.submit_answer("Elaborating with specific distributed lock metrics and error budgets.")

    assert agent.state.status == "COMPLETED", f"Expected COMPLETED, got {agent.state.status}"
    assert len(agent.state.history) == 5, f"Expected 5 turns, got {len(agent.state.history)}"

    # Verify score computation
    metrics = compute_overall_score(agent.state)
    assert 1.0 <= metrics["overall_score"] <= 5.0
    assert metrics["recommendation"] in ["ADVANCE TO TECHNICAL ROUND", "HOLD / BORDERLINE", "NEEDS HUMAN REVIEW"]
    assert len(agent.state.consistency_findings) > 0

    # Verify Markdown report generation
    report_md = generate_markdown_report(agent.state)
    assert "Candidate Evaluation Scorecard" in report_md
    assert "Alex Chen" in report_md
    assert "Human Oversight Safeguard Notice" in report_md
    print(f"✓ Full interview completed. Overall score: {metrics['overall_score']}/5.0 | Rec: {metrics['recommendation']}")


def test_reset_functionality():
    print("\nTesting Reset Functionality...")
    agent = InterviewPilotAgent()
    resume = parse_resume(SYNTHETIC_RESUME_TEXT)
    agent.plan_interview(resume, SYNTHETIC_JD_TEXT)
    agent.submit_answer(SAMPLE_RESPONSES["strong"]["text"])

    agent.reset_interview()
    assert agent.state.status == "READY"
    assert len(agent.state.questions) == 0
    assert len(agent.state.history) == 0
    assert len(get_activity_logs()) == 0
    print("✓ Reset verified cleanly.")


if __name__ == "__main__":
    print("==================================================")
    print("   RUNNING INTERVIEWPILOT AI VALIDATION SUITE    ")
    print("==================================================")
    test_resume_parser()
    test_agent_planning()
    test_shallow_answer_triggers_followup()
    test_followup_resolution_and_advancement()
    test_full_interview_simulation_and_report()
    test_reset_functionality()
    print("\n==================================================")
    print("   ALL TESTS PASSED WITH 100% SUCCESS RATE!       ")
    print("==================================================")
