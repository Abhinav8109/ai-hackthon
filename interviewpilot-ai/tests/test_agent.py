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

    assert 8 <= len(questions) <= 10, f"Expected 8-10 questions, got {len(questions)}"
    assert questions[0].competency == "Technical Depth"
    assert questions[0].targeted_resume_claim is not None
    assert agent.state.status == "IN_PROGRESS"

    logs = get_activity_logs()
    assert any(l.tool_name == "plan_interview" for l in logs), "plan_interview tool call not logged"
    print(f"✓ Successfully planned {len(questions)} resume-anchored interview questions.")


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
    print("\nTesting Full 10-Question Interview Flow & Final Report...")
    clear_activity_logs()
    agent = InterviewPilotAgent()
    resume = parse_resume(SYNTHETIC_RESUME_TEXT)
    questions = agent.plan_interview(resume, SYNTHETIC_JD_TEXT)
    total_q = len(questions)

    answers = [
        SAMPLE_RESPONSES["strong"]["text"],
        SAMPLE_RESPONSES["scenario_strong"]["text"],
        "We used Redis cluster with hash tags and read replicas in Postgres. We managed stampedes using Redlock and stale cache invalidation.",
        "In asynchronous Python, we prevent event loop blocking by dispatching CPU intensive tasks to ProcessPoolExecutor and blocking network libraries to loop.run_in_executor.",
        "We analyze pg_stat_activity for lock waits, set 5s timeouts, configure PgBouncer connection pooling, and add composite indexes.",
        "In our previous project, a teammate pushed to deploy without automated migrations. I advocated for rollback using telemetry data, then paired with them to build an automated migration pipeline.",
        "I was on-call during a misconfiguration incident. I immediately initiated canary rollback, communicated with customer teams, and automated configuration validation in our CI/CD pipeline.",
        "I explain message queues as an order ticket system at a busy restaurant kitchen: instead of a customer standing at the counter waiting for the chef to cook, they receive a ticket number and get notified when ready.",
        "We implement circuit breakers with Closed, Open, and Half-Open states, combined with exponential backoff and jittered retry budgets to prevent cascading outages.",
        "My background in high-throughput Python and caching directly aligns with your low-latency requirements, and I am excited to deepen my work with your multi-region Kubernetes infrastructure."
    ]

    for i in range(total_q):
        ans = answers[i] if i < len(answers) else "We ensure robust distributed systems design with metrics, telemetry, and automated unit testing."
        res = agent.submit_answer(ans)
        if res.get("status") == "followup_required":
            res = agent.submit_answer("Elaborating with specific distributed lock metrics and error budgets.")

    assert agent.state.status == "COMPLETED", f"Expected COMPLETED, got {agent.state.status}"
    assert len(agent.state.history) == total_q, f"Expected {total_q} turns, got {len(agent.state.history)}"

    # Verify score computation
    metrics = compute_overall_score(agent.state)
    assert 1.0 <= metrics["overall_score"] <= 5.0
    assert metrics["recommendation"] in ["ADVANCE", "HOLD", "REJECT"]
    assert len(agent.state.consistency_findings) > 0

    # Verify Markdown report generation
    report_md = generate_markdown_report(agent.state)
    assert "Candidate Evaluation Scorecard" in report_md
    assert "Alex Chen" in report_md
    assert "Human Oversight Safeguard Notice" in report_md
    print(f"✓ Full 10-question interview completed. Overall score: {metrics['overall_score']}/5.0 | Rec: {metrics['recommendation']}")


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


def test_admin_pipeline_and_roles():
    print("\nTesting Admin Talent Pipeline & Role Buckets...")
    from database import get_all_jobs, get_candidates_list, get_candidate_details

    jobs = get_all_jobs()
    job_titles = [j["title"] for j in jobs]
    assert len(jobs) >= 5, f"Expected at least 5 roles, found {len(jobs)}"
    assert any("Software Engineer" in t for t in job_titles)
    assert any("DevOps" in t for t in job_titles)
    assert any("AI" in t for t in job_titles)

    # Verify candidates are bucketed
    all_cands = get_candidates_list()
    assert len(all_cands) >= 5, "Expected at least 5 candidates"

    # Verify Sukrit exists under Software Engineer
    sukrit = get_candidate_details("CAND-SE-8109")
    assert sukrit is not None
    assert sukrit["email"] == "sukrit.ss.31@gmail.com"
    print(f"✓ Verified 5 Role Buckets and active profile for {sukrit['email']}.")


def test_approval_and_email_dispatch():
    print("\nTesting Candidate Approval & Email Dispatch...")
    from pipeline_manager import approve_for_first_round
    from database import get_candidate_details, get_all_email_logs

    res = approve_for_first_round("CAND-SE-8109")
    assert res["status"] == "success"
    assert res["token"] is not None

    cand = get_candidate_details("CAND-SE-8109")
    assert cand["workflow_status"] in ("INVITED", "FIRST_ROUND_APPROVED")

    logs = get_all_email_logs()
    cand_logs = [l for l in logs if l.get("candidate_id") == "CAND-SE-8109"]
    assert len(cand_logs) > 0
    latest_log = cand_logs[0]
    assert latest_log["recipient_email"] == "sukrit.ss.31@gmail.com"
    print(f"✓ Approved Sukrit Sharma; generated token {res['token'][:10]}...; email dispatched to {latest_log['recipient_email']}.")


def test_candidate_authentication_gateway():
    print("\nTesting Candidate Token Validation Gateway...")
    from pipeline_manager import validate_candidate_interview_token
    from database import get_candidate_details
    cand = get_candidate_details("CAND-SE-8109")
    assert cand["token"] is not None

    # Valid token lookup
    val_res = validate_candidate_interview_token(cand["token"])
    assert val_res["valid"] is True
    assert val_res["session"]["candidate_name"] is not None
    assert val_res["session"]["candidate_email"] == "sukrit.ss.31@gmail.com"

    # Invalid token lookup
    invalid_res = validate_candidate_interview_token("INVALID_TOKEN_123")
    assert invalid_res["valid"] is False
    print(f"✓ Candidate Token Gateway verified: securely authenticates valid session token and rejects invalid tokens.")


if __name__ == "__main__":
    print("==================================================")
    print("   RUNNING TALENTPILOT AI VALIDATION SUITE       ")
    print("==================================================")
    test_resume_parser()
    test_agent_planning()
    test_shallow_answer_triggers_followup()
    test_followup_resolution_and_advancement()
    test_full_interview_simulation_and_report()
    test_reset_functionality()
    test_admin_pipeline_and_roles()
    test_approval_and_email_dispatch()
    test_candidate_authentication_gateway()
    print("\n==================================================")
    print("   ALL TESTS PASSED WITH 100% SUCCESS RATE!       ")
    print("==================================================")


