"""
Pipeline Manager Module for TalentPilot AI.
Implements the exact end-to-end recruitment business workflow:
- Step 1: Admin reviews shortlisted candidates (Search, filter, inspect claims)
- Step 2: First-round approval automatically triggers 8-10 question plan & invitation generation
- Step 3: Candidate invitation email dispatched (Subject: First-Round Interview Invitation — [Job Title])
- Step 4: Token validation for candidate interview portal
- Step 5: Candidate AI interview execution, adaptive follow-ups, and transcript persistence
- Step 6: Interview completion, consistency detection & scorecard generation
- Step 7: Admin reviews completed interviews without any Launch Interview button
- Step 8: Admin approves candidate for second round (Subject: Congratulations — Selected for the Second Round)
"""

from typing import List, Dict, Any, Optional
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from database import (
    get_db_connection,
    get_all_jobs,
    get_job_by_id,
    get_candidates_list,
    get_candidate_details,
    get_session_by_token,
    get_scorecard_by_candidate_id,
    get_qa_turns_by_session_id,
    log_audit_event,
    insert_or_replace_candidate,
    seed_database_if_empty
)
from email_service import (
    get_base_url,
    generate_first_round_invitation_email,
    generate_second_round_selection_email,
    generate_rejection_email,
    send_email_notification,
    retry_failed_notification
)
from resume_parser import parse_resume, StructuredResume
from agent import InterviewPilotAgent


def get_pipeline_overview_metrics() -> Dict[str, int]:
    """Computes real-time recruitment pipeline metrics from SQLite database."""
    seed_database_if_empty()
    with get_db_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM candidates;").fetchone()[0]
        shortlisted = conn.execute("SELECT COUNT(*) FROM candidates WHERE workflow_status = 'SHORTLISTED';").fetchone()[0]
        invitations_sent = conn.execute("SELECT COUNT(*) FROM candidates WHERE workflow_status IN ('INVITED', 'IN_PROGRESS', 'COMPLETED', 'SECOND_ROUND_APPROVED', 'ON_HOLD');").fetchone()[0]
        in_progress = conn.execute("SELECT COUNT(*) FROM candidates WHERE workflow_status = 'IN_PROGRESS';").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM candidates WHERE workflow_status IN ('COMPLETED', 'SECOND_ROUND_APPROVED', 'ON_HOLD', 'HUMAN_REVIEW_REQUIRED');").fetchone()[0]
        pending_review = conn.execute("SELECT COUNT(*) FROM candidates WHERE workflow_status IN ('COMPLETED', 'HUMAN_REVIEW_REQUIRED');").fetchone()[0]
        second_round = conn.execute("SELECT COUNT(*) FROM candidates WHERE workflow_status = 'SECOND_ROUND_APPROVED';").fetchone()[0]
        on_hold = conn.execute("SELECT COUNT(*) FROM candidates WHERE workflow_status = 'ON_HOLD';").fetchone()[0]

        return {
            "total_candidates": total,
            "shortlisted": shortlisted,
            "invitations_sent": invitations_sent,
            "in_progress": in_progress,
            "completed": completed,
            "pending_review": pending_review,
            "second_round_approved": second_round,
            "on_hold": on_hold
        }


def approve_for_first_round(candidate_id: str, reviewer: str = "Admin") -> Dict[str, Any]:
    """
    Step 2: Admin approves candidate for first-round interview.
    Automatically:
    1. Validates candidate status and email
    2. Generates candidate-specific 8-10 question interview plan
    3. Creates secure interview session and cryptographic token
    4. Persists interview record and invitation state
    5. Generates candidate interview URL
    6. Automatically sends invitation email
    7. Updates status to INVITED (or INVITATION_FAILED if dispatch fails)
    """
    cand = get_candidate_details(candidate_id)
    if not cand:
        return {"status": "error", "message": f"Candidate {candidate_id} not found."}

    # Validation: must be SHORTLISTED, FIRST_ROUND_APPROVED, or INVITATION_FAILED
    allowed_statuses = ("SHORTLISTED", "FIRST_ROUND_APPROVED", "INVITATION_FAILED")
    if cand["workflow_status"] not in allowed_statuses and not cand.get("session_id"):
        return {
            "status": "error",
            "message": f"Cannot approve candidate in status '{cand['workflow_status']}'. Must be Shortlisted."
        }

    # Validate email: must be valid format and strictly @gmail.com
    email = cand["email"].strip().lower()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return {"status": "error", "message": f"Invalid candidate email address: {email}"}
    if not email.endswith("@gmail.com"):
        return {"status": "error", "message": f"Candidate email '{cand['email']}' is not a @gmail.com address. Only valid @gmail.com addresses are permitted for interview invitations."}

    job = get_job_by_id(cand["job_id"])
    if not job:
        return {"status": "error", "message": f"Associated job {cand['job_id']} not found."}

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_at = (now + timedelta(days=7)).isoformat()

    # 1. Update candidate state to FIRST_ROUND_APPROVED
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE candidates SET workflow_status = 'FIRST_ROUND_APPROVED', updated_at = ? WHERE id = ?;",
            (now_iso, candidate_id)
        )
        conn.commit()

    log_audit_event("candidate", candidate_id, "FIRST_ROUND_APPROVED", reviewer, f"Approved by {reviewer}")

    # 2. Generate 8-10 Question Interview Plan (Planner Agent)
    parsed_resume = parse_resume(cand["resume_text"])
    agent = InterviewPilotAgent()
    questions = agent.plan_interview(parsed_resume, job["description"])
    questions_dicts = [q.model_dump() for q in questions]

    plan_id = f"PLAN-{secrets.token_hex(6).upper()}"
    with get_db_connection() as conn:
        # Check if plan exists
        conn.execute("DELETE FROM interview_plans WHERE candidate_id = ?;", (candidate_id,))
        conn.execute(
            "INSERT INTO interview_plans (id, candidate_id, job_id, questions, created_at) VALUES (?, ?, ?, ?, ?);",
            (plan_id, candidate_id, job["id"], json.dumps(questions_dicts), now_iso)
        )
        conn.commit()

    # 3. Create Secure Interview Session & Unique Cryptographic Token
    token = secrets.token_urlsafe(32)
    session_id = f"SESS-{secrets.token_hex(8).upper()}"

    with get_db_connection() as conn:
        # Check if active session exists and clean up dependent records to avoid FK constraint violation
        old_sessions = conn.execute("SELECT id FROM interview_sessions WHERE candidate_id = ?;", (candidate_id,)).fetchall()
        for s in old_sessions:
            s_id = s[0]
            conn.execute("DELETE FROM evaluation_scorecards WHERE session_id = ?;", (s_id,))
            conn.execute("DELETE FROM interview_qa WHERE session_id = ?;", (s_id,))
        conn.execute("DELETE FROM interview_sessions WHERE candidate_id = ?;", (candidate_id,))
        conn.execute("""
        INSERT INTO interview_sessions (
            id, candidate_id, job_id, token, token_expires_at, status,
            current_question_index, created_at
        ) VALUES (?, ?, ?, ?, ?, 'INVITED', 0, ?);
        """, (session_id, candidate_id, job["id"], token, expires_at, now_iso))
        conn.commit()

    # 4. Generate Candidate Interview URL
    base_url = get_base_url()
    interview_url = f"{base_url}/?token={token}"

    # 5. Automatically Send Invitation Email
    email_data = generate_first_round_invitation_email(
        candidate_name=cand["name"],
        job_title=job["title"],
        interview_url=interview_url,
        expiration_days=7
    )

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE candidates SET workflow_status = 'INVITATION_PENDING', updated_at = ? WHERE id = ?;",
            (now_iso, candidate_id)
        )
        conn.commit()

    dispatch_res = send_email_notification(
        candidate_id=candidate_id,
        recipient_email=email,
        recipient_name=cand["name"],
        notification_type="FIRST_ROUND_INVITATION",
        subject=email_data["subject"],
        body_text=email_data["body_text"],
        body_html=email_data["body_html"]
    )

    # 6. Update Candidate Workflow Status based on actual dispatch result
    final_status = "INVITED" if dispatch_res["delivery_status"] in ("DELIVERED_SMTP", "ACCEPTED_DEV_MOCK") else "INVITATION_FAILED"
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE candidates SET workflow_status = ?, updated_at = ? WHERE id = ?;",
            (final_status, datetime.now(timezone.utc).isoformat(), candidate_id)
        )
        conn.commit()

    return {
        "status": "success",
        "candidate_id": candidate_id,
        "session_id": session_id,
        "token": token,
        "interview_url": interview_url,
        "workflow_status": final_status,
        "email_dispatch": dispatch_res
    }


def validate_candidate_interview_token(token: str) -> Dict[str, Any]:
    """
    Step 4: Validates interview token when candidate opens URL.
    Verifies:
    - Token exists
    - Session has not expired
    - Interview has not already been completed
    - Loads job and candidate details securely
    """
    if not token or not token.strip():
        return {"valid": False, "reason": "No invitation token provided."}

    session = get_session_by_token(token.strip())
    if not session:
        return {"valid": False, "reason": "Invalid or unrecognized interview link."}

    # Check expiration
    try:
        expires = datetime.fromisoformat(session["token_expires_at"])
        if datetime.now(timezone.utc) > expires:
            return {"valid": False, "reason": "This interview invitation link has expired. Please contact recruitment."}
    except Exception:
        pass

    # Check if already completed
    if session["status"] == "COMPLETED" or session["candidate_status"] in ("COMPLETED", "SECOND_ROUND_APPROVED"):
        return {
            "valid": False,
            "reason": "This interview has already been submitted and completed. Further submissions are locked.",
            "completed": True,
            "candidate_name": session["candidate_name"],
            "job_title": session["job_title"]
        }

    return {
        "valid": True,
        "session": session
    }


def start_candidate_interview(token: str) -> Dict[str, Any]:
    """Candidate clicks 'Start Interview' button on welcome screen."""
    val = validate_candidate_interview_token(token)
    if not val["valid"]:
        return val

    session = val["session"]
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE interview_sessions SET status = 'IN_PROGRESS', started_at = COALESCE(started_at, ?) WHERE id = ?;",
            (now_iso, session["id"])
        )
        conn.execute(
            "UPDATE candidates SET workflow_status = 'IN_PROGRESS', updated_at = ? WHERE id = ?;",
            (now_iso, session["candidate_id"])
        )
        conn.commit()

    log_audit_event("interview_session", session["id"], "INTERVIEW_STARTED", session["candidate_name"], "Candidate initiated live screening.")
    return {"status": "success", "session": session}


def record_turn_answer(
    session_id: str,
    question_id: int,
    competency: str,
    difficulty: str,
    question_text: str,
    targeted_claim: str,
    candidate_answer: str,
    followup_question: Optional[str],
    followup_answer: Optional[str],
    score: int,
    completeness: float,
    evidence_quote: str,
    rubric_match: str,
    strengths: str,
    gaps: Optional[str]
) -> None:
    """Saves candidate answer turn to database and updates progress."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute("""
        INSERT INTO interview_qa (
            session_id, question_id, competency, difficulty, question_text, targeted_claim,
            candidate_answer, followup_question, followup_answer, score, completeness,
            evidence_quote, rubric_match, strengths, gaps, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            session_id, question_id, competency, difficulty, question_text, targeted_claim,
            candidate_answer, followup_question, followup_answer, score, completeness,
            evidence_quote, rubric_match, strengths, gaps, now_iso
        ))

        conn.execute(
            "UPDATE interview_sessions SET current_question_index = ? WHERE id = ?;",
            (question_id, session_id)
        )
        conn.commit()


def complete_candidate_interview(
    session_id: str,
    candidate_id: str,
    agent_state: Any
) -> Dict[str, Any]:
    """
    Step 6: Interview completion.
    Persists transcript, consistency findings, evaluator scorecard,
    and updates candidate state to COMPLETED (or HUMAN_REVIEW_REQUIRED).
    """
    from report_generator import compute_overall_score, generate_candidate_feedback_letter

    now_iso = datetime.now(timezone.utc).isoformat()
    metrics = compute_overall_score(agent_state)

    scorecard_id = f"SC-{secrets.token_hex(6).upper()}"
    consistency_json = json.dumps([f.model_dump() for f in agent_state.consistency_findings])
    feedback_note = generate_candidate_feedback_letter(agent_state, metrics["overall_score"])

    # Determine candidate workflow status
    if metrics["human_review_flag"] == 1:
        new_cand_status = "HUMAN_REVIEW_REQUIRED"
    else:
        new_cand_status = "COMPLETED"

    with get_db_connection() as conn:
        # Save evaluation scorecard
        conn.execute("DELETE FROM evaluation_scorecards WHERE session_id = ?;", (session_id,))
        conn.execute("""
        INSERT INTO evaluation_scorecards (
            id, session_id, candidate_id, overall_score, technical_score,
            problem_solving_score, communication_score, job_fit_score,
            recommendation, human_review_flag, strengths, gaps, candidate_feedback,
            consistency_findings, transcript_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            scorecard_id, session_id, candidate_id,
            metrics["overall_score"], metrics["technical_score"],
            metrics["problem_solving_score"], metrics["communication_score"],
            metrics["job_fit_score"], metrics["recommendation"],
            metrics["human_review_flag"],
            json.dumps([t.evaluation.strengths for t in agent_state.history if t.evaluation]),
            json.dumps([t.evaluation.gaps for t in agent_state.history if t.evaluation and t.evaluation.gaps]),
            feedback_note, consistency_json, metrics["rec_desc"], now_iso
        ))

        # Update session
        conn.execute(
            "UPDATE interview_sessions SET status = 'COMPLETED', completed_at = ? WHERE id = ?;",
            (now_iso, session_id)
        )

        # Update candidate
        conn.execute(
            "UPDATE candidates SET workflow_status = ?, updated_at = ? WHERE id = ?;",
            (new_cand_status, now_iso, candidate_id)
        )
        conn.commit()

    log_audit_event("interview_session", session_id, "INTERVIEW_COMPLETED", "Candidate", f"Score: {metrics['overall_score']} | Rec: {metrics['recommendation']}")
    return {
        "status": "success",
        "scorecard_id": scorecard_id,
        "metrics": metrics,
        "workflow_status": new_cand_status
    }


def approve_for_second_round(candidate_id: str, reviewer: str = "Admin", notes: str = "") -> Dict[str, Any]:
    """
    Step 8: Admin approves candidate for the second round.
    1. Validates candidate and interview completion
    2. Updates status to SECOND_ROUND_APPROVED
    3. Automatically sends second-round selection email (Subject: Congratulations — Selected for the Second Round)
    4. Prevents duplicate notifications
    """
    cand = get_candidate_details(candidate_id)
    if not cand:
        return {"status": "error", "message": f"Candidate {candidate_id} not found."}

    # Verify interview is completed
    if cand["workflow_status"] not in ("COMPLETED", "HUMAN_REVIEW_REQUIRED", "ON_HOLD", "SECOND_ROUND_APPROVED"):
        return {"status": "error", "message": "Candidate must complete first-round interview before second-round approval."}

    if cand["workflow_status"] == "SECOND_ROUND_APPROVED":
        return {"status": "info", "message": "Candidate has already been approved for the second round."}

    now_iso = datetime.now(timezone.utc).isoformat()

    # Update candidate status
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE candidates SET workflow_status = 'SECOND_ROUND_APPROVED', updated_at = ? WHERE id = ?;",
            (now_iso, candidate_id)
        )
        conn.commit()

    # Dispatch Second-Round Email
    email_data = generate_second_round_selection_email(
        candidate_name=cand["name"],
        job_title=cand["job_title"]
    )

    dispatch_res = send_email_notification(
        candidate_id=candidate_id,
        recipient_email=cand["email"],
        recipient_name=cand["name"],
        notification_type="SECOND_ROUND_SELECTION",
        subject=email_data["subject"],
        body_text=email_data["body_text"],
        body_html=email_data["body_html"]
    )

    log_audit_event(
        "candidate", candidate_id, "SECOND_ROUND_APPROVED", reviewer,
        f"Approved for second round by {reviewer}. Notes: {notes}"
    )

    return {
        "status": "success",
        "candidate_id": candidate_id,
        "workflow_status": "SECOND_ROUND_APPROVED",
        "email_dispatch": dispatch_res
    }


def place_candidate_on_hold(candidate_id: str, reviewer: str = "Admin", notes: str = "") -> Dict[str, Any]:
    """Step 7: Admin places candidate on hold. Blocked if candidate cleared and approved for Round 2."""
    cand = get_candidate_details(candidate_id)
    if not cand:
        return {"status": "error", "message": f"Candidate {candidate_id} not found."}

    if cand["workflow_status"] == "SECOND_ROUND_APPROVED":
        return {
            "status": "error",
            "message": "Candidate has already cleared Round 1 and been approved for the Second Round. Cannot place on hold."
        }

    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE candidates SET workflow_status = 'ON_HOLD', updated_at = ? WHERE id = ?;",
            (now_iso, candidate_id)
        )
        conn.commit()

    log_audit_event("candidate", candidate_id, "PLACED_ON_HOLD", reviewer, f"Candidate placed on hold. Notes: {notes}")
    return {"status": "success", "candidate_id": candidate_id, "workflow_status": "ON_HOLD"}


def mark_candidate_under_review(candidate_id: str, reviewer: str = "Admin", notes: str = "") -> Dict[str, Any]:
    """Admin marks candidate for further human review."""
    cand = get_candidate_details(candidate_id)
    if not cand:
        return {"status": "error", "message": f"Candidate {candidate_id} not found."}

    if cand["workflow_status"] == "SECOND_ROUND_APPROVED":
        return {"status": "error", "message": "Candidate has already cleared Round 1 and been approved for the Second Round."}

    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE candidates SET workflow_status = 'HUMAN_REVIEW_REQUIRED', updated_at = ? WHERE id = ?;",
            (now_iso, candidate_id)
        )
        conn.commit()

    log_audit_event("candidate", candidate_id, "MARKED_UNDER_REVIEW", reviewer, f"Candidate marked for further human review. Notes: {notes}")
    return {"status": "success", "candidate_id": candidate_id, "workflow_status": "HUMAN_REVIEW_REQUIRED"}


def reject_candidate(candidate_id: str, reviewer: str = "Admin", notes: str = "") -> Dict[str, Any]:
    """Admin rejects candidate and dispatches formal courteous update email to candidate's Gmail."""
    cand = get_candidate_details(candidate_id)
    if not cand:
        return {"status": "error", "message": f"Candidate {candidate_id} not found."}

    if cand["workflow_status"] == "SECOND_ROUND_APPROVED":
        return {"status": "error", "message": "Candidate has already cleared Round 1 and been approved for the Second Round. Cannot reject."}

    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE candidates SET workflow_status = 'REJECTED', updated_at = ? WHERE id = ?;",
            (now_iso, candidate_id)
        )
        conn.commit()

    # Dispatch rejection email to candidate's Gmail
    email_data = generate_rejection_email(
        candidate_name=cand["name"],
        job_title=cand["job_title"]
    )

    dispatch_res = send_email_notification(
        candidate_id=candidate_id,
        recipient_email=cand["email"],
        recipient_name=cand["name"],
        notification_type="APPLICATION_REJECTION",
        subject=email_data["subject"],
        body_text=email_data["body_text"],
        body_html=email_data["body_html"]
    )

    log_audit_event("candidate", candidate_id, "REJECTED", reviewer, f"Candidate rejected by {reviewer}. Notes: {notes}")
    return {"status": "success", "candidate_id": candidate_id, "workflow_status": "REJECTED", "email_dispatch": dispatch_res}



def retry_candidate_invitation_email(candidate_id: str) -> Dict[str, Any]:
    """Retries sending the invitation email for a candidate."""
    cand = get_candidate_details(candidate_id)
    if not cand or not cand.get("token"):
        return {"status": "error", "message": "No active interview session token found for candidate."}

    interview_url = f"{get_base_url()}/?token={cand['token']}"
    email_data = generate_first_round_invitation_email(
        candidate_name=cand["name"],
        job_title=cand["job_title"],
        interview_url=interview_url,
        expiration_days=7
    )

    dispatch_res = send_email_notification(
        candidate_id=candidate_id,
        recipient_email=cand["email"],
        recipient_name=cand["name"],
        notification_type="FIRST_ROUND_INVITATION",
        subject=email_data["subject"],
        body_text=email_data["body_text"],
        body_html=email_data["body_html"],
        force_retry=True
    )

    # Update candidate status
    new_status = "INVITED" if dispatch_res["delivery_status"] in ("DELIVERED_SMTP", "ACCEPTED_DEV_MOCK") else "INVITATION_FAILED"
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE candidates SET workflow_status = ?, updated_at = ? WHERE id = ?;",
            (new_status, datetime.now(timezone.utc).isoformat(), candidate_id)
        )
        conn.commit()

    return dispatch_res


# Domain keywords taxonomy for role matching
ROLE_DOMAIN_KEYWORDS = {
    "JOB-SE-01": [
        "python", "fastapi", "redis", "postgresql", "postgres", "microservice", "microservices",
        "asyncio", "rest", "api", "database", "latency", "throughput", "caching", "sql", "backend"
    ],
    "JOB-DE-02": [
        "kubernetes", "k8s", "aws", "terraform", "devops", "sre", "ci/cd", "prometheus", "helm",
        "docker", "infrastructure", "grafana", "observability", "deploy", "cluster", "cloud"
    ],
    "JOB-AI-03": [
        "pytorch", "langchain", "rag", "vector", "chromadb", "ai", "ml", "llm", "llms",
        "machine learning", "embeddings", "hallucination", "deep learning", "nlp", "inference"
    ],
    "JOB-FE-04": [
        "react", "typescript", "next.js", "redux", "tailwind", "tailwindcss", "web vitals",
        "frontend", "ui", "ux", "css", "html", "javascript", "dom", "responsive"
    ],
    "JOB-CD-05": [
        "kafka", "spark", "snowflake", "airflow", "data", "glue", "etl", "lakehouse",
        "warehouse", "streaming", "batch", "pipeline", "sql", "big data"
    ]
}


def match_resume_to_profiles(
    raw_text: str,
    override_name: Optional[str] = None,
    override_email: Optional[str] = None,
    min_threshold: int = 50,
    save_if_matched: bool = True
) -> Dict[str, Any]:
    """
    Ingests and matches a candidate resume against all 5 open enterprise roles.
    - If top match >= min_threshold (default 50%):
        Matches to that profile bucket, saves/shortlists candidate, and enables approval.
    - If top match < min_threshold:
        Marks as NOT matching any profile, surfaces role breakdown, and avoids saving.
    """
    seed_database_if_empty()
    if not raw_text or len(raw_text.strip()) < 20:
        return {
            "matched": False,
            "reason": "Resume text is empty or too short to analyze. Please provide a valid resume.",
            "all_evaluations": []
        }

    structured = parse_resume(raw_text)
    lower_text = raw_text.lower()

    # Collect all candidate skill keywords
    cand_skills = set()
    for cat_skills in structured.skills.values():
        for s in cat_skills:
            cand_skills.add(s.lower())

    jobs = get_all_jobs()
    evaluations = []

    for job in jobs:
        req_skills = json.loads(job["skills_required"]) if isinstance(job["skills_required"], str) else job["skills_required"]
        matched_skills = []
        for s in req_skills:
            pattern = r"\b" + re.escape(s.lower()) + r"\b"
            if s.lower() in cand_skills or re.search(pattern, lower_text):
                matched_skills.append(s)

        missing_skills = [s for s in req_skills if s not in matched_skills]
        skill_ratio = len(matched_skills) / max(len(req_skills), 1)

        # Domain terms analysis
        domain_terms = ROLE_DOMAIN_KEYWORDS.get(job["id"], [])
        matched_terms = [t for t in domain_terms if re.search(r"\b" + re.escape(t) + r"\b", lower_text)]
        term_ratio = min(1.0, len(matched_terms) / max(min(len(domain_terms), 6), 1))

        # Experience alignment bonus
        min_exp = job.get("min_experience", 3)
        exp_bonus = 0.10 if (structured.years_experience or 0) >= min_exp else 0.0

        if len(matched_skills) == 0 and len(matched_terms) == 0:
            match_score = 0
        else:
            calc_score = (skill_ratio * 65.0) + (term_ratio * 25.0) + (exp_bonus * 100.0)
            match_score = int(min(98, max(5, round(calc_score))))

        evaluations.append({
            "job_id": job["id"],
            "job_title": job["title"],
            "department": job["department"],
            "match_score": match_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "matched_terms_count": len(matched_terms)
        })

    # Sort jobs by match score descending
    evaluations.sort(key=lambda x: x["match_score"], reverse=True)
    top_job = evaluations[0]

    candidate_name = override_name.strip() if override_name and override_name.strip() else structured.candidate_name
    raw_email = override_email.strip() if override_email and override_email.strip() else (
        structured.email or f"{candidate_name.lower().replace(' ', '.')}@gmail.com"
    )

    # Strictly enforce @gmail.com email domain
    if override_email and not override_email.strip().lower().endswith("@gmail.com"):
        return {
            "matched": False,
            "candidate_name": candidate_name,
            "candidate_email": override_email,
            "reason": f"Candidate email '{override_email}' is not a valid @gmail.com address. Only valid @gmail.com email addresses are allowed.",
            "all_evaluations": []
        }

    candidate_email = raw_email if raw_email.lower().endswith("@gmail.com") else re.sub(r"@.*$", "@gmail.com", raw_email)

    if top_job["match_score"] >= min_threshold:
        # Generate summary
        if structured.claims:
            summary = "; ".join([c.text for c in structured.claims[:2]])
        else:
            summary = f"Candidate with {structured.years_experience} years experience matching {top_job['job_title']} with {len(top_job['matched_skills'])} verified core skills."

        cand_id = f"CAND-UP-{secrets.token_hex(3).upper()}"
        saved_id = cand_id

        if save_if_matched:
            save_res = insert_or_replace_candidate(
                candidate_id=cand_id,
                job_id=top_job["job_id"],
                name=candidate_name,
                email=candidate_email,
                department=top_job["department"],
                experience_years=structured.years_experience or 3,
                match_score=top_job["match_score"],
                skills=top_job["matched_skills"] if top_job["matched_skills"] else ["Python"],
                resume_summary=summary,
                resume_text=raw_text,
                shortlist_status="SHORTLISTED",
                workflow_status="SHORTLISTED"
            )
            saved_id = save_res["id"]

        return {
            "matched": True,
            "candidate_id": saved_id,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "matched_job": top_job,
            "match_score": top_job["match_score"],
            "matched_skills": top_job["matched_skills"],
            "missing_skills": top_job["missing_skills"],
            "experience_years": structured.years_experience or 3,
            "summary": summary,
            "resume_text": raw_text,
            "all_evaluations": evaluations
        }
    else:
        return {
            "matched": False,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "best_job": top_job,
            "best_score": top_job["match_score"],
            "reason": f"The uploaded resume does not match any open profile. Best alignment was '{top_job['job_title']}' with only {top_job['match_score']}% relevance, which is below the minimum qualification threshold of {min_threshold}%.",
            "all_evaluations": evaluations,
            "resume_text": raw_text
        }

