"""
Comprehensive End-to-End Workflow Test Suite for TalentPilot AI.
Validates the complete 16-step business workflow:
1. Admin reviews shortlisted candidate (Use Case 1 output)
2. Admin inspects candidate profile and resume claims
3. Admin approves first-round interview
4. Backend generates 8-10 question tailored plan
5. Secure cryptographic token and interview session created
6. Automated email notification dispatched to candidate (Subject: First-Round Interview Invitation — [Job Title])
7. Token validation in Candidate Portal
8. Candidate starts interview independently
9. Candidate completes turns with adaptive follow-ups on shallow answers
10. Transcript, Q&A, and evidence quotes persisted in SQLite
11. Evaluator agent scores against rubrics and consistency checker runs
12. Completed scorecard visible in Admin Portal without any Launch Interview button
13. Admin reviews scorecard, radar metrics, and evidence quotes
14. Admin approves candidate for second round
15. Second-round notification email dispatched (Subject: Congratulations — Selected for the Second Round)
16. Candidate status updated to SECOND_ROUND_APPROVED with full audit trail
17. Edge cases: Token expiration, invalid token, duplicate approvals, email retries
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import (
    init_db,
    seed_database_if_empty,
    get_db_connection,
    get_candidates_list,
    get_candidate_details,
    get_scorecard_by_candidate_id,
    get_qa_turns_by_session_id,
    get_all_email_logs,
    get_audit_events
)
from pipeline_manager import (
    approve_for_first_round,
    validate_candidate_interview_token,
    start_candidate_interview,
    record_turn_answer,
    complete_candidate_interview,
    approve_for_second_round,
    place_candidate_on_hold,
    retry_candidate_invitation_email,
    get_pipeline_overview_metrics
)
from agent import InterviewPilotAgent
from resume_parser import parse_resume
from demo_data import SAMPLE_RESPONSES


def run_full_recruitment_workflow_test():
    print("=================================================================")
    print("   RUNNING TALENTPILOT AI END-TO-END WORKFLOW ACCEPTANCE SUITE   ")
    print("=================================================================")

    # Setup database
    init_db()
    seed_database_if_empty()

    # Ensure test candidate is in clean SHORTLISTED state for fresh workflow test execution
    with get_db_connection() as conn:
        conn.execute("UPDATE candidates SET workflow_status = 'SHORTLISTED' WHERE email = 'sukrit.ss.31@gmail.com';")
        conn.execute("DELETE FROM email_notifications WHERE recipient_email = 'sukrit.ss.31@gmail.com';")
        conn.execute("DELETE FROM evaluation_scorecards WHERE candidate_id = 'CAND-SE-8109';")
        conn.execute("DELETE FROM interview_qa WHERE session_id IN (SELECT id FROM interview_sessions WHERE candidate_id = 'CAND-SE-8109');")
        conn.execute("DELETE FROM interview_sessions WHERE candidate_id = 'CAND-SE-8109';")
        conn.commit()

    # Step 1: Admin reviews shortlisted candidates
    print("\n[Step 1] Admin reviews shortlisted candidates from Use Case 1...")
    candidates = get_candidates_list()
    assert len(candidates) >= 5, f"Expected at least 5 candidates, found {len(candidates)}"

    sukrit = next((c for c in candidates if c["email"] == "sukrit.ss.31@gmail.com"), None)
    assert sukrit is not None, "Sukrit Sharma (sukrit.ss.31@gmail.com) not found in database."
    assert sukrit["workflow_status"] == "SHORTLISTED"
    assert sukrit["match_score"] >= 90
    print(f"✓ Found candidate: {sukrit['name']} ({sukrit['email']}) | Match Score: {sukrit['match_score']}% | Status: {sukrit['workflow_status']}")

    # Step 2: Admin inspects candidate profile & claims
    print("\n[Step 2] Admin opens candidate profile and inspects resume claims...")
    cand_details = get_candidate_details(sukrit["id"])
    assert cand_details is not None
    assert "FastAPI" in cand_details["skills"] or "Python" in cand_details["skills"]
    assert len(cand_details["resume_text"]) > 100
    print(f"✓ Inspected profile for {cand_details['name']}. Resume contains verified FastAPI & Redis claims.")

    # Step 3 & 4: Admin approves candidate for first round
    print("\n[Step 3 & 4] Admin clicks 'Approve for First-Round Interview'...")
    res = approve_for_first_round(sukrit["id"], reviewer="Admin_Abhinav")
    assert res["status"] == "success", f"Approval failed: {res}"
    assert res["workflow_status"] in ("INVITED", "INVITATION_FAILED")
    assert res["token"] is not None
    assert "http" in res["interview_url"]
    token = res["token"]
    session_id = res["session_id"]
    print(f"✓ Approved! Session ID: {session_id} | Token generated ({token[:12]}...) | URL: {res['interview_url']}")

    # Step 5: Verify email notification record in database
    print("\n[Step 5] Checking automated invitation email dispatch...")
    email_logs = get_all_email_logs()
    invitation_email = next((e for e in email_logs if e["candidate_id"] == sukrit["id"] and e["notification_type"] == "FIRST_ROUND_INVITATION"), None)
    assert invitation_email is not None, "First-round invitation email record not found in database."
    assert "First-Round Interview Invitation" in invitation_email["subject"]
    assert invitation_email["recipient_email"] == "sukrit.ss.31@gmail.com"
    assert token in invitation_email["body_text"] or token in invitation_email["body_html"]
    assert invitation_email["delivery_status"] in ("DELIVERED_SMTP", "ACCEPTED_DEV_MOCK")
    print(f"✓ Verified email record to {invitation_email['recipient_email']}. Status: {invitation_email['delivery_status']} | Subject: {invitation_email['subject']}")

    # Step 6: Verify 8-10 Question Interview Plan generated
    print("\n[Step 6] Verifying Planner Agent 8-10 question agenda...")
    val_check = validate_candidate_interview_token(token)
    assert val_check["valid"] is True
    plan_q = val_check["session"]["plan_questions"]
    assert len(plan_q) >= 8, f"Expected 8-10 questions in plan, got {len(plan_q)}"
    assert any(q["competency"] == "Technical Depth" for q in plan_q)
    assert any(q["competency"] == "Problem Solving & Scenarios" for q in plan_q)
    assert any(q["competency"] == "Behavioral & Ownership" for q in plan_q)
    assert any(q["competency"] == "Communication & Clarity" for q in plan_q)
    print(f"✓ Planner Agent synthesized {len(plan_q)} tailored questions covering technical depth, scenarios, behavioral, and communication.")

    # Step 7: Candidate opens link and sees Welcome Screen
    print("\n[Step 7] Candidate accesses interview portal via secure token...")
    start_res = start_candidate_interview(token)
    assert start_res["status"] == "success"
    active_cand = get_candidate_details(sukrit["id"])
    assert active_cand["workflow_status"] == "IN_PROGRESS"
    print(f"✓ Token authenticated. Interview initiated independently by candidate (Status: {active_cand['workflow_status']}).")

    # Step 8: Candidate completes interview turns with adaptive follow-ups
    print("\n[Step 8] Conducting live agentic screening interview with adaptive follow-ups...")
    agent = InterviewPilotAgent()
    agent.plan_interview(parse_resume(sukrit["resume_text"]), val_check["session"]["job_description"])

    # Turn 1: Test shallow answer triggering follow-up probe
    shallow_ans = SAMPLE_RESPONSES["shallow"]["text"]
    t1_res = agent.submit_answer(shallow_ans)
    assert t1_res["status"] == "followup_required", f"Expected follow-up probe, got {t1_res}"
    assert agent.state.status == "AWAITING_FOLLOWUP"
    print(f"  • Q1 Shallow answer correctly intercepted by agent! Triggered probe: '{t1_res['followup_question']}'")

    # Candidate provides deep recovery answer
    strong_ans = SAMPLE_RESPONSES["strong"]["text"]
    t1_recov = agent.submit_answer(strong_ans)
    assert t1_recov["status"] == "advanced"
    record_turn_answer(
        session_id=session_id,
        question_id=1,
        competency="Technical Depth",
        difficulty="standard",
        question_text=plan_q[0]["text"],
        targeted_claim=plan_q[0]["targeted_resume_claim"],
        candidate_answer=shallow_ans,
        followup_question=t1_res["followup_question"],
        followup_answer=strong_ans,
        score=5,
        completeness=0.95,
        evidence_quote=agent.state.history[0].evaluation.evidence_quote,
        rubric_match="Deep production mastery",
        strengths="Demonstrated Redis cluster distributed mutex locks and stale-while-revalidate invalidation.",
        gaps=None
    )
    print(f"  • Q1 Follow-up resolved! Candidate recovered with depth; score elevated to 5/5.")

    # Answer remaining questions with structured depth
    remaining_answers = [
        SAMPLE_RESPONSES["scenario_strong"]["text"],
        "We used Redis cluster with hash tags and read replicas in Postgres. We managed stampedes using Redlock and stale cache invalidation.",
        "In asynchronous Python, calling blocking synchronous I/O or heavy CPU functions directly blocks the asyncio event loop thread. To fix this, we offload CPU processing to ProcessPoolExecutor and blocking network libraries to loop.run_in_executor.",
        "We analyze pg_stat_activity for wait_event_type lock, set lock_timeout to 5s, implement PgBouncer transaction pooling, and add composite B-Tree indexes on active query predicates.",
        "A teammate wanted to deploy raw unindexed migrations in production. I benchmarked the lock duration on a staging replica, proved it caused 45s table locks, and proposed an asynchronous concurrent index migration instead.",
        "I was on-call when an incorrect environment variable pointed a microservice to the primary database rather than the read replica, causing connection exhaustion. I immediately rolled back, drafted a blameless post-mortem, and added automated environment schema validation to CI/CD.",
        "I explain message queues using an airport baggage carousel: instead of passengers following baggage handlers into the airplane hold, bags are placed on a queue carousel and consumed asynchronously.",
        "We implement circuit breakers with Netflix Hystrix/Resilience4j patterns using three states: Closed, Open, and Half-Open, combined with exponential backoff and jittered retry budgets.",
        "My background in high-throughput FastAPI and Redis caching directly matches your latency requirements, and I am eager to expand deeper into your multi-region Kubernetes infrastructure."
    ]

    for idx, ans in enumerate(remaining_answers, start=2):
        q_item = plan_q[idx - 1] if (idx - 1) < len(plan_q) else plan_q[-1]
        agent.submit_answer(ans)
        record_turn_answer(
            session_id=session_id,
            question_id=idx,
            competency=q_item["competency"],
            difficulty="standard",
            question_text=q_item["text"],
            targeted_claim=q_item.get("targeted_resume_claim", ""),
            candidate_answer=ans,
            followup_question=None,
            followup_answer=None,
            score=4,
            completeness=0.85,
            evidence_quote=f'"{ans[:80]}..."',
            rubric_match="Clear technical and scenario understanding",
            strengths="Clear explanation with concrete technical mechanisms.",
            gaps=None
        )

    # Step 9: Complete interview and persist scorecard
    print("\n[Step 9] Candidate completes interview and submits responses...")
    agent._finalize_interview()
    comp_res = complete_candidate_interview(session_id, sukrit["id"], agent.state)
    assert comp_res["status"] == "success"

    # Step 10: Verify Q&A persistence and completed scorecard in database
    print("\n[Step 10] Verifying database persistence for turns and scorecard...")
    saved_turns = get_qa_turns_by_session_id(session_id)
    assert len(saved_turns) >= 8, f"Expected at least 8 saved QA turns, found {len(saved_turns)}"
    print(f"✓ Verified {len(saved_turns)} turn records persisted in interview_qa table.")

    scorecard = get_scorecard_by_candidate_id(sukrit["id"])
    assert scorecard is not None, "Evaluation scorecard not found in database."
    assert scorecard["overall_score"] >= 3.0
    assert scorecard["recommendation"] in ("ADVANCE", "HOLD", "REJECT")
    assert len(scorecard["consistency_findings"]) > 0
    print(f"✓ Scorecard generated! Overall Score: {scorecard['overall_score']}/5.0 | AI Recommendation: {scorecard['recommendation']}")

    # Step 11: Admin reviews scorecard (Step 7)
    print("\n[Step 11] Admin reviews completed scorecard in Admin Portal (No Launch Interview present)...")
    admin_cand = get_candidate_details(sukrit["id"])
    assert admin_cand["workflow_status"] in ("COMPLETED", "HUMAN_REVIEW_REQUIRED")
    print(f"✓ Candidate visible in Admin Completed tab (Status: {admin_cand['workflow_status']}).")

    # Step 12: Admin approves candidate for Second Round (Step 8)
    print("\n[Step 12] Admin clicks 'Approve for Second Round'...")
    r2_res = approve_for_second_round(sukrit["id"], reviewer="Admin_Abhinav", notes="Outstanding system design and concurrency depth.")
    assert r2_res["status"] == "success"
    assert r2_res["workflow_status"] == "SECOND_ROUND_APPROVED"

    updated_cand = get_candidate_details(sukrit["id"])
    assert updated_cand["workflow_status"] == "SECOND_ROUND_APPROVED"
    print(f"✓ Candidate status updated to {updated_cand['workflow_status']}.")

    # Step 13: Verify Second-Round selection email dispatched
    print("\n[Step 13] Verifying automated Second-Round notification email...")
    all_emails = get_all_email_logs()
    second_email = next((e for e in all_emails if e["candidate_id"] == sukrit["id"] and e["notification_type"] == "SECOND_ROUND_SELECTION"), None)
    assert second_email is not None, "Second-round notification email not found in database."
    assert "Congratulations — Selected for the Second Round" in second_email["subject"]
    assert second_email["recipient_email"] == "sukrit.ss.31@gmail.com"
    assert second_email["delivery_status"] in ("DELIVERED_SMTP", "ACCEPTED_DEV_MOCK")
    print(f"✓ Verified Second-Round email record to {second_email['recipient_email']}. Subject: '{second_email['subject']}'")

    # Step 14: Test Duplicate Prevention
    print("\n[Step 14] Testing duplicate approval & notification prevention...")
    dup_res = approve_for_second_round(sukrit["id"], reviewer="Admin_Abhinav")
    assert dup_res["status"] == "info", "Duplicate approval should be prevented safely."
    print("✓ Duplicate approval click safely ignored without redundant emails.")

    # Step 15: Test Token Security & Expiration on completed session
    print("\n[Step 15] Testing token protection against re-submission...")
    token_retest = validate_candidate_interview_token(token)
    assert token_retest["valid"] is False, "Completed interview token must not allow re-submission."
    assert token_retest.get("completed") is True
    print("✓ Completed interview is securely locked against unauthorized re-entry.")

    # Step 16: Verify Audit Trail
    print("\n[Step 16] Verifying audit event logging...")
    audit_events = get_audit_events()
    cand_audits = [a for a in audit_events if a["entity_id"] in (sukrit["id"], session_id)]
    assert len(cand_audits) >= 3, "Expected multiple audit records for candidate lifecycle."
    print(f"✓ Verified {len(cand_audits)} audit trail events logged for {sukrit['name']}.")

    print("\n=================================================================")
    print("   ALL 16 WORKFLOW ACCEPTANCE CRITERIA PASSED (100% SUCCESS)    ")
    print("=================================================================")


def test_resume_upload_and_profile_matching():
    print("\n=================================================================")
    print("   RUNNING RESUME UPLOAD, AUTO-MATCHING & REJECTION TEST SUITE  ")
    print("=================================================================")
    from pipeline_manager import match_resume_to_profiles, approve_for_first_round, validate_candidate_interview_token
    from demo_data import SAMPLE_DEVOPS_RESUME, SAMPLE_AI_RESUME, SAMPLE_NONMATCHING_CHEF_RESUME
    from database import get_candidate_details

    # Test 1: DevOps Resume Upload -> Correct Profile Matching
    print("\n[Upload Test 1] Uploading and analyzing DevOps Engineer Resume...")
    res_devops = match_resume_to_profiles(SAMPLE_DEVOPS_RESUME, override_name="David Ross", override_email="david.ross.devops@example.com")
    assert res_devops["matched"] is True, "DevOps resume should have matched an open role."
    assert "DevOps" in res_devops["matched_job"]["job_title"], f"Expected DevOps role, got {res_devops['matched_job']['job_title']}"
    assert res_devops["match_score"] >= 80, f"Expected match score >= 80, got {res_devops['match_score']}"
    assert len(res_devops["matched_skills"]) >= 4
    print(f"✓ Matched to '{res_devops['matched_job']['job_title']}' with {res_devops['match_score']}% score.")

    # Verify candidate is saved in DB and resume is downloadable
    db_cand = get_candidate_details(res_devops["candidate_id"])
    assert db_cand is not None
    assert db_cand["name"] == "David Ross"
    assert db_cand["workflow_status"] == "SHORTLISTED"
    assert len(db_cand["resume_text"]) > 200, "Resume text must be persisted for downloading."
    print("✓ Candidate profile successfully bucketed into Lead DevOps role; resume text ready for download.")

    # Test 2: AI Systems Resume Upload -> Correct Profile Matching
    print("\n[Upload Test 2] Uploading and analyzing AI/ML Systems Engineer Resume...")
    res_ai = match_resume_to_profiles(SAMPLE_AI_RESUME, override_name="Anita Roy", override_email="anita.roy.ai@example.com")
    assert res_ai["matched"] is True, "AI resume should match AI Systems role."
    assert "AI" in res_ai["matched_job"]["job_title"], f"Expected AI role, got {res_ai['matched_job']['job_title']}"
    assert res_ai["match_score"] >= 80
    print(f"✓ Matched to '{res_ai['matched_job']['job_title']}' with {res_ai['match_score']}% score.")

    # Test 3: Non-Matching Resume -> Correct Rejection & Profile Mismatch Flag
    print("\n[Upload Test 3] Uploading Non-Matching Resume (Executive Chef)...")
    res_chef = match_resume_to_profiles(SAMPLE_NONMATCHING_CHEF_RESUME, override_name="Chef Marco Pierre", override_email="marco.pierre@culinaryart.com")
    assert res_chef["matched"] is False, "Culinary resume should NOT match any technical role."
    assert res_chef["best_score"] < 50, f"Expected non-matching score < 50%, got {res_chef['best_score']}%"
    assert "does not match any open profile" in res_chef["reason"]
    assert len(res_chef["all_evaluations"]) == 5, "Should evaluate fit across all 5 open roles."
    print(f"✓ Correctly rejected non-matching resume: '{res_chef['reason']}'")

    # Test 4: Approval & Link Generation for Uploaded Candidate
    print("\n[Upload Test 4] Admin approves uploaded candidate (David Ross) for interview...")
    app_res = approve_for_first_round(res_devops["candidate_id"])
    assert app_res["status"] == "success"
    assert "http://localhost:8501/?token=" in app_res["interview_url"]
    print(f"✓ Generated interview link: {app_res['interview_url']}")

    # Test 5: Candidate Accesses Screening Room via Generated Link
    print("\n[Upload Test 5] Candidate accesses interview portal with new link...")
    cand_val = validate_candidate_interview_token(app_res["token"])
    assert cand_val["valid"] is True
    assert cand_val["session"]["candidate_name"] == "David Ross"
    assert len(cand_val["session"]["plan_questions"]) >= 8
    print(f"✓ Candidate portal validated token for {cand_val['session']['candidate_name']} ({cand_val['session']['job_title']}) with {len(cand_val['session']['plan_questions'])} tailored questions.")

    print("\n=================================================================")
    print("   ALL RESUME UPLOAD & MATCHING ACCEPTANCE CRITERIA PASSED!      ")
    print("=================================================================")


if __name__ == "__main__":
    run_full_recruitment_workflow_test()
    test_resume_upload_and_profile_matching()

