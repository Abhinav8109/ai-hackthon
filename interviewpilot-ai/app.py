"""
TalentPilot AI — Production-Grade AI Recruitment Platform
Full End-to-End Workflow:
1. Admin Portal:
   - Sourced & shortlisted candidate profiles organized by Role
   - Match score analysis & claim summaries
   - "Approve for First-Round Interview" triggers automatic plan generation, token creation & email invitation
   - Zero "Launch Interview" options in admin views
   - Completed Interview Review with evidence scorecards & radar charts
   - Human-in-the-loop decisions: "Approve for Second Round" (auto-triggers email) & "Place on Hold"
   - Email Activity audit log with retry mechanism
2. Candidate Interview Portal:
   - Token-validated separate candidate interface (via URL ?token=... or direct token entry)
   - Welcome & instructions screen with explicit "Start Interview" trigger
   - 8-10 question resume-anchored adaptive interview with follow-up probing
   - Turn-by-turn persistence in SQLite
   - Completion submission screen
"""

import streamlit as st
import os
import json
from datetime import datetime, timezone

from database import (
    init_db,
    seed_database_if_empty,
    get_all_jobs,
    get_job_by_id,
    get_candidates_list,
    get_candidate_details,
    get_scorecard_by_candidate_id,
    get_qa_turns_by_session_id,
    get_all_email_logs,
    get_audit_events
)
from pipeline_manager import (
    get_pipeline_overview_metrics,
    approve_for_first_round,
    validate_candidate_interview_token,
    start_candidate_interview,
    record_turn_answer,
    complete_candidate_interview,
    approve_for_second_round,
    place_candidate_on_hold,
    retry_candidate_invitation_email
)
from email_service import get_base_url, retry_failed_notification
from agent import InterviewPilotAgent
from tools import get_activity_logs, clear_activity_logs
from report_generator import create_competency_radar_chart, create_competency_bar_chart, generate_markdown_report
from resume_parser import parse_resume
from demo_data import SAMPLE_RESPONSES


# Ensure database tables exist and are seeded
seed_database_if_empty()

# Page Configuration
st.set_page_config(
    page_title="TalentPilot AI — Enterprise Screening Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-End Slate / Navy Enterprise SaaS Design System
CUSTOM_CSS = """
<style>
    /* Dark Slate / Navy Palette */
    .stApp {
        background-color: #0B0F19;
        color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar Navigation */
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Enterprise Cards */
    .saas-card {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    .candidate-row-card {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 14px;
        transition: border-color 0.2s ease;
    }
    .candidate-row-card:hover {
        border-color: #3B82F6;
    }

    .question-panel {
        background: linear-gradient(135deg, #111827 0%, #1E293B 100%);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 14px;
        padding: 26px;
        margin-bottom: 20px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }

    .followup-panel {
        background: rgba(88, 28, 135, 0.25);
        border: 1px solid #8B5CF6;
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
    }

    /* Status Pills */
    .status-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .pill-blue { background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }
    .pill-emerald { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .pill-amber { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .pill-red { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .pill-purple { background: rgba(168, 85, 247, 0.15); color: #C084FC; border: 1px solid rgba(168, 85, 247, 0.3); }

    /* KPI Metrics */
    .kpi-box {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .kpi-number {
        font-size: 1.8rem;
        font-weight: 800;
        color: #38BDF8;
        line-height: 1.2;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }

    /* Skill Tags */
    .skill-tag {
        display: inline-block;
        background: #1E293B;
        color: #E2E8F0;
        font-size: 0.78rem;
        padding: 2px 8px;
        border-radius: 4px;
        margin: 2px 4px 2px 0;
        border: 1px solid #334155;
    }

    /* Activity Log Entry */
    .log-entry {
        background: #111827;
        border-left: 3px solid #38BDF8;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
        font-size: 0.85rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Parse Query Parameters for Direct Candidate Interview Links (?token=...)
query_params = st.query_params
url_token = query_params.get("token")

# Initialize Session State
if "active_portal" not in st.session_state:
    st.session_state.active_portal = "Candidate Portal" if url_token else "Admin Portal"

if "candidate_token" not in st.session_state:
    st.session_state.candidate_token = url_token if url_token else ""

if "candidate_agent" not in st.session_state:
    st.session_state.candidate_agent = None

if "interview_started" not in st.session_state:
    st.session_state.interview_started = False

if "admin_search" not in st.session_state:
    st.session_state.admin_search = ""

if "admin_filter_job" not in st.session_state:
    st.session_state.admin_filter_job = "ALL"

if "admin_filter_status" not in st.session_state:
    st.session_state.admin_filter_status = "ALL"

if "toast_msg" not in st.session_state:
    st.session_state.toast_msg = None


# Display Toast notifications if queued
if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg)
    st.session_state.toast_msg = None


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("### 🎯 TALENTPILOT AI")
    st.caption("Production Recruitment & Screening System")
    st.markdown("---")

    # Portal Switcher
    portal_options = ["🛡️ Admin Portal", "🎓 Candidate Interview Portal"]
    current_idx = 0 if st.session_state.active_portal == "Admin Portal" else 1

    selected_portal = st.radio("Navigation View", portal_options, index=current_idx)

    target_portal = "Admin Portal" if "Admin" in selected_portal else "Candidate Portal"
    if target_portal != st.session_state.active_portal:
        st.session_state.active_portal = target_portal
        st.rerun()

    st.markdown("---")

    # Sidebar context information
    if st.session_state.active_portal == "Admin Portal":
        st.markdown("#### 👤 Admin Role: Recruitment Manager")
        st.caption("Authorized to review candidates, approve first-round invitations, review scorecards, and approve second rounds.")
        st.info("🔒 Note: Manual 'Launch Interview' actions have been removed. Candidates conduct interviews independently via secure invitation links.")
    else:
        st.markdown("#### 🎓 Candidate Screening Gateway")
        st.caption("Candidate-facing interface. Access is isolated and validated via unique cryptographic invitation tokens.")
        if st.session_state.candidate_token:
            st.markdown(f"**Token:** `{st.session_state.candidate_token[:12]}...`")

    st.markdown("---")
    st.caption("⚡ Powered by TalentPilot Agentic Interview Engine • SQLite Relational Store")


# ============================================================================
# VIEW 1: CANDIDATE INTERVIEW PORTAL (ISOLATED EXPERIENCE)
# ============================================================================
if st.session_state.active_portal == "Candidate Portal":

    # Step 4: Token Validation
    token_to_verify = st.session_state.candidate_token.strip()

    if not token_to_verify:
        st.markdown("## 🔐 Candidate Interview Gateway")
        st.markdown("Please enter the **Interview Invitation Token** from your official invitation email, or open the link directly from your email.")

        c_col1, c_col2 = st.columns([1.2, 1])
        with c_col1:
            st.markdown("""
            <div class="saas-card">
                <h4 style="color:#38BDF8; margin-top:0;">Access Your Screening Room</h4>
                <p style="color:#94A3B8; font-size:0.9rem;">
                    Your invitation link contains a secure cryptographic token. You can also paste it below:
                </p>
            </div>
            """, unsafe_allow_html=True)

            token_input = st.text_input("Interview Token", placeholder="e.g. jA9eK3_z9L...")

            # Quick-Load Helper for Demonstration
            st.markdown("**⚡ Live Demonstration Shortcut:**")
            invited_cands = [c for c in get_candidates_list() if c.get("token")]
            if invited_cands:
                sample_cand = invited_cands[0]
                if st.button(f"⚡ Load {sample_cand['name']}'s Active Token ({sample_cand['token'][:10]}...)", use_container_width=True):
                    st.session_state.candidate_token = sample_cand["token"]
                    st.rerun()
            else:
                st.caption("No active interview sessions yet. Approve a candidate in the Admin Portal to generate an invitation link.")

            if st.button("🔓 Validate Token & Enter", type="primary", use_container_width=True):
                if token_input.strip():
                    st.session_state.candidate_token = token_input.strip()
                    st.rerun()
                else:
                    st.warning("Please enter your invitation token.")

        with c_col2:
            st.markdown("""
            <div class="saas-card">
                <h4>📋 Interview Instructions</h4>
                <p style="color:#CBD5E1; font-size:0.88rem; line-height: 1.6;">
                    • <strong>8–10 Tailored Questions:</strong> The interview covers core technical depth, system troubleshooting, behavioral ownership, and communication.<br>
                    • <strong>Adaptive Follow-up:</strong> The interviewer asks follow-ups when an answer needs technical depth.<br>
                    • <strong>Estimated Time:</strong> 20–25 minutes.<br>
                    • <strong>Privacy:</strong> Your interview is isolated and submitted directly to hiring managers for human review.
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.stop()

    # Validate the token
    val_res = validate_candidate_interview_token(token_to_verify)

    if not val_res["valid"]:
        if val_res.get("completed"):
            st.success(f"🎉 Thank you, {val_res.get('candidate_name', 'Candidate')}! Your interview for the {val_res.get('job_title', 'selected')} position has already been completed and submitted.")
            st.info("Our recruitment team is reviewing your evaluation. Further details regarding the second round will be sent to your email.")
            if st.button("Enter New Token"):
                st.session_state.candidate_token = ""
                st.rerun()
            st.stop()
        else:
            st.error(f"⚠️ {val_res['reason']}")
            if st.button("Try Another Token"):
                st.session_state.candidate_token = ""
                st.rerun()
            st.stop()

    session_data = val_res["session"]
    candidate_id = session_data["candidate_id"]
    job_title = session_data["job_title"]
    cand_name = session_data["candidate_name"]

    # Initialize Interview Agent for this Candidate Session if not yet in state
    if st.session_state.candidate_agent is None or getattr(st.session_state.candidate_agent, "session_id", None) != session_data["id"]:
        agent = InterviewPilotAgent()
        agent.session_id = session_data["id"]

        # Load plan questions from database
        plan_questions = session_data["plan_questions"]
        if plan_questions:
            from agent import Question
            agent.state.questions = [Question(**q) for q in plan_questions]
            agent.state.candidate_name = cand_name
            agent.state.job_description = session_data["job_description"]
            agent.state.resume = parse_resume(session_data["resume_text"])
            agent.state.current_index = session_data.get("current_question_index", 0)
        else:
            # Fallback formulation if plan was missing
            parsed_resume = parse_resume(session_data["resume_text"])
            agent.plan_interview(parsed_resume, session_data["job_description"])

        # Check existing QA turns to restore state if interrupted
        existing_turns = get_qa_turns_by_session_id(session_data["id"])
        agent.state.current_index = len(existing_turns)
        agent.state.status = "IN_PROGRESS" if len(existing_turns) > 0 else "INVITED"

        st.session_state.candidate_agent = agent
        st.session_state.interview_started = (len(existing_turns) > 0 or session_data["status"] == "IN_PROGRESS")

    agent = st.session_state.candidate_agent

    # ------------------------------------------------------------------------
    # SCREEN 1: WELCOME SCREEN (Interviews only start when candidate clicks Start)
    # ------------------------------------------------------------------------
    if not st.session_state.interview_started:
        st.markdown(f"## 🎙️ Welcome, <span style='color:#38BDF8;'>{cand_name}</span>", unsafe_allow_html=True)
        st.markdown(f"#### First-Round Technical Screening for **{job_title}** ({session_data['job_department']})")

        w_col1, w_col2 = st.columns([1.5, 1])
        with w_col1:
            st.markdown("""
            <div class="saas-card">
                <h3 style="color:#FFFFFF; margin-top:0;">About This Screening Interview</h3>
                <p style="color:#CBD5E1; font-size:1rem; line-height: 1.6;">
                    You have been invited to complete an interactive, AI-facilitated technical screening.
                    The interviewer agent will ask you <strong>8 to 10 tailored questions</strong> based on your background and the role requirements.
                </p>
                <div style="background: rgba(59, 130, 246, 0.08); border-left: 3px solid #3B82F6; padding: 12px 16px; border-radius: 6px; margin: 16px 0;">
                    <p style="margin:0; font-size:0.92rem; color:#E2E8F0;">
                        ⏱️ <strong>Estimated Duration:</strong> 20–25 minutes<br>
                        🎯 <strong>Format:</strong> One question at a time. The interviewer may ask a follow-up probe if an answer lacks technical detail.<br>
                        🔒 <strong>Human Oversight:</strong> All scores are grounded in your verbatim responses and reviewed by human hiring managers.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🚀 Start Interview", type="primary", use_container_width=True):
                start_candidate_interview(token_to_verify)
                st.session_state.interview_started = True
                agent.state.status = "IN_PROGRESS"
                st.rerun()

        with w_col2:
            st.markdown("""
            <div class="saas-card">
                <h4>💡 Tips for Success</h4>
                <p style="color:#94A3B8; font-size:0.88rem; line-height:1.6;">
                    • Be specific about tools, architectures, and metrics.<br>
                    • Mention trade-offs and reasons behind your decisions.<br>
                    • Answer questions in your own words.<br>
                    • Your session progress is saved automatically.
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.stop()

    # ------------------------------------------------------------------------
    # SCREEN 2: ACTIVE INTERVIEW ROOM
    # ------------------------------------------------------------------------
    st.markdown(f"## 🎙️ Screening Session: <span style='color:#38BDF8;'>{cand_name}</span>", unsafe_allow_html=True)
    st.caption(f"Role: **{job_title}** • Session ID: `{session_data['id']}`")

    curr_q = agent.get_current_question()
    total_q = len(agent.state.questions)

    # When all questions are completed
    if agent.state.status == "COMPLETED" or agent.state.current_index >= total_q:
        # Run final completion tools if not already marked completed
        if session_data["status"] != "COMPLETED":
            with st.spinner("Compiling transcript and running consistency audits..."):
                agent._finalize_interview()
                complete_res = complete_candidate_interview(session_data["id"], candidate_id, agent.state)

        st.markdown("""
        <div class="saas-card" style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 3rem; margin-bottom: 10px;">🎉</div>
            <h2 style="color: #34D399; margin: 0 0 10px 0;">Interview Successfully Completed!</h2>
            <p style="color: #CBD5E1; font-size: 1.1rem; max-width: 650px; margin: 0 auto 20px auto; line-height: 1.6;">
                Thank you for completing your first-round technical screening interview for the <strong>""" + job_title + """</strong> position.
                Your responses, code architecture explanations, and transcript have been securely submitted to our talent acquisition team.
            </p>
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 14px 20px; display: inline-block; text-align: left; margin-bottom: 20px;">
                <strong style="color: #34D399;">What happens next?</strong><br>
                <span style="color: #E2E8F0; font-size: 0.92rem;">
                    1. A human hiring manager reviews your complete evaluation scorecard.<br>
                    2. If selected for the second round, you will automatically receive an official scheduling notification via email.<br>
                    3. No further action is required from you at this time.
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("⬅️ Exit Screening Portal", use_container_width=True):
            st.session_state.candidate_token = ""
            st.session_state.interview_started = False
            st.session_state.candidate_agent = None
            st.session_state.active_portal = "Admin Portal"
            st.rerun()

        st.stop()

    # Active Question Display
    q_col, act_col = st.columns([1.6, 1.0])

    with q_col:
        progress_val = min(1.0, agent.state.current_index / max(1, total_q))
        st.progress(progress_val)
        st.caption(f"Question **{agent.state.current_index + 1} of {total_q}** • Domain: **{curr_q.competency if curr_q else 'In Progress'}**")

        if curr_q:
            st.markdown(f"""
            <div class="question-panel">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="status-pill pill-blue">{curr_q.competency}</span>
                    <span class="status-pill pill-purple">Level: {agent.state.current_difficulty.upper()}</span>
                </div>
                <h3 style="margin-top: 14px; color: #FFFFFF;">Question #{curr_q.id}</h3>
                <p style="font-size: 1.15rem; line-height: 1.6; color: #F1F5F9;">{curr_q.text}</p>
                <div style="background: rgba(0,0,0,0.3); padding: 10px 14px; border-radius: 6px; border-left: 2px solid #38BDF8; margin-top: 12px;">
                    <small style="color: #94A3B8;">Targeting Resume Claim: <em>"{curr_q.targeted_resume_claim}"</em></small>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Adaptive follow-up probe mode
            if agent.state.status == "AWAITING_FOLLOWUP":
                st.markdown(f"""
                <div class="followup-panel">
                    <span class="status-pill pill-amber">⚡ Adaptive Follow-up Probe</span>
                    <h4 style="margin-top: 10px; color: #FBBF24;">Interviewer Follow-up Question</h4>
                    <p style="font-size: 1.05rem; color: #F1F5F9; line-height: 1.5;">{agent.state.active_followup}</p>
                    <small style="color: #CBD5E1;">Please provide additional technical specifics, trade-offs, or production metrics.</small>
                </div>
                """, unsafe_allow_html=True)

                followup_ans = st.text_area(
                    "Your Follow-up Answer",
                    height=130,
                    placeholder="Elaborate with specific libraries, architecture decisions, or error recovery..."
                )

                f_btn1, f_btn2 = st.columns(2)
                with f_btn1:
                    if st.button("⚡ Quick-Fill Strong Follow-up Answer", use_container_width=True):
                        followup_ans = SAMPLE_RESPONSES["strong"]["text"]
                        agent.submit_answer(followup_ans)
                        record_turn_answer(
                            session_id=session_data["id"],
                            question_id=curr_q.id,
                            competency=curr_q.competency,
                            difficulty=agent.state.current_difficulty,
                            question_text=curr_q.text,
                            targeted_claim=curr_q.targeted_resume_claim or "",
                            candidate_answer=agent.state.history[-1].answer,
                            followup_question=agent.state.active_followup,
                            followup_answer=followup_ans,
                            score=agent.state.history[-1].final_score,
                            completeness=agent.state.history[-1].evaluation.completeness,
                            evidence_quote=agent.state.history[-1].evaluation.evidence_quote,
                            rubric_match=agent.state.history[-1].evaluation.rubric_match,
                            strengths=agent.state.history[-1].evaluation.strengths,
                            gaps=agent.state.history[-1].evaluation.gaps
                        )
                        st.rerun()

                with f_btn2:
                    if st.button("📤 Submit Follow-up", type="primary", use_container_width=True):
                        if followup_ans.strip():
                            agent.submit_answer(followup_ans)
                            record_turn_answer(
                                session_id=session_data["id"],
                                question_id=curr_q.id,
                                competency=curr_q.competency,
                                difficulty=agent.state.current_difficulty,
                                question_text=curr_q.text,
                                targeted_claim=curr_q.targeted_resume_claim or "",
                                candidate_answer=agent.state.history[-1].answer,
                                followup_question=agent.state.active_followup,
                                followup_answer=followup_ans,
                                score=agent.state.history[-1].final_score,
                                completeness=agent.state.history[-1].evaluation.completeness,
                                evidence_quote=agent.state.history[-1].evaluation.evidence_quote,
                                rubric_match=agent.state.history[-1].evaluation.rubric_match,
                                strengths=agent.state.history[-1].evaluation.strengths,
                                gaps=agent.state.history[-1].evaluation.gaps
                            )
                            st.rerun()
                        else:
                            st.warning("Please provide a response before submitting.")

            else:
                candidate_ans = st.text_area(
                    "Your Answer",
                    height=140,
                    placeholder="Type or paste your technical answer here..."
                )

                st.markdown("**⚡ Live Evaluation Quick-Fill Controls:**")
                b_c1, b_c2 = st.columns(2)
                with b_c1:
                    if st.button("⚠️ Test Shallow Answer (Triggers Follow-up)", use_container_width=True):
                        candidate_ans = SAMPLE_RESPONSES["shallow"]["text"]
                        agent.submit_answer(candidate_ans)
                        st.rerun()
                with b_c2:
                    if st.button("✅ Test Strong Answer (Advances with Score 5)", use_container_width=True):
                        candidate_ans = SAMPLE_RESPONSES["strong"]["text"]
                        res = agent.submit_answer(candidate_ans)
                        record_turn_answer(
                            session_id=session_data["id"],
                            question_id=curr_q.id,
                            competency=curr_q.competency,
                            difficulty=agent.state.current_difficulty,
                            question_text=curr_q.text,
                            targeted_claim=curr_q.targeted_resume_claim or "",
                            candidate_answer=candidate_ans,
                            followup_question=None,
                            followup_answer=None,
                            score=agent.state.history[-1].final_score,
                            completeness=agent.state.history[-1].evaluation.completeness,
                            evidence_quote=agent.state.history[-1].evaluation.evidence_quote,
                            rubric_match=agent.state.history[-1].evaluation.rubric_match,
                            strengths=agent.state.history[-1].evaluation.strengths,
                            gaps=agent.state.history[-1].evaluation.gaps
                        )
                        st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📤 Submit Answer", type="primary", use_container_width=True):
                    if candidate_ans.strip():
                        res = agent.submit_answer(candidate_ans)
                        if res.get("status") != "followup_required":
                            record_turn_answer(
                                session_id=session_data["id"],
                                question_id=curr_q.id,
                                competency=curr_q.competency,
                                difficulty=agent.state.current_difficulty,
                                question_text=curr_q.text,
                                targeted_claim=curr_q.targeted_resume_claim or "",
                                candidate_answer=candidate_ans,
                                followup_question=None,
                                followup_answer=None,
                                score=agent.state.history[-1].final_score,
                                completeness=agent.state.history[-1].evaluation.completeness,
                                evidence_quote=agent.state.history[-1].evaluation.evidence_quote,
                                rubric_match=agent.state.history[-1].evaluation.rubric_match,
                                strengths=agent.state.history[-1].evaluation.strengths,
                                gaps=agent.state.history[-1].evaluation.gaps
                            )
                        st.rerun()
                    else:
                        st.warning("Please enter your answer before submitting.")

    # Timeline Column
    with act_col:
        st.markdown("### 🧠 Live Agent Activity Panel")
        st.caption("Verifiable Python tool executions:")

        logs = get_activity_logs()
        if not logs:
            st.info("Tool executions appear here in real-time as you submit answers.")
        else:
            for log in reversed(logs[-8:]):
                st.markdown(f"""
                <div class="log-entry">
                    <div style="display:flex; justify-content:space-between; color:#94A3B8; font-size:0.75rem;">
                        <span>⚙️ <strong>{log.tool_name}()</strong></span>
                        <span>{log.timestamp} ({log.execution_ms}ms)</span>
                    </div>
                    <div style="color: #38BDF8; font-weight:600; margin: 4px 0;">{log.result_summary}</div>
                    <div style="color: #CBD5E1; font-size: 0.8rem;"><em>Reasoning:</em> {log.agent_reasoning}</div>
                </div>
                """, unsafe_allow_html=True)


# ============================================================================
# VIEW 2: ADMIN PORTAL (DEDICATED RECRUITER & SOURCING INTERFACE)
# ============================================================================
elif st.session_state.active_portal == "Admin Portal":
    st.markdown("## 🛡️ Talent Acquisition & Screening Command Center")
    st.caption("Enterprise AI-Powered Screening: Candidate Management • Automated Invitations • Completed Scorecard Audits")

    # 1. Top Real-Time KPI Cards (From SQLite Backend)
    metrics = get_pipeline_overview_metrics()

    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    with k1:
        st.markdown(f'<div class="kpi-box"><div class="kpi-number">{metrics["total_candidates"]}</div><div class="kpi-label">Total Sourced</div></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="kpi-box"><div class="kpi-number" style="color:#60A5FA;">{metrics["shortlisted"]}</div><div class="kpi-label">Shortlisted</div></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="kpi-box"><div class="kpi-number" style="color:#C084FC;">{metrics["invitations_sent"]}</div><div class="kpi-label">Invitations Sent</div></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="kpi-box"><div class="kpi-number" style="color:#FBBF24;">{metrics["in_progress"]}</div><div class="kpi-label">In Progress</div></div>', unsafe_allow_html=True)
    with k5:
        st.markdown(f'<div class="kpi-box"><div class="kpi-number" style="color:#34D399;">{metrics["completed"]}</div><div class="kpi-label">Completed</div></div>', unsafe_allow_html=True)
    with k6:
        st.markdown(f'<div class="kpi-box"><div class="kpi-number" style="color:#F87171;">{metrics["pending_review"]}</div><div class="kpi-label">Pending Review</div></div>', unsafe_allow_html=True)
    with k7:
        st.markdown(f'<div class="kpi-box"><div class="kpi-number" style="color:#10B981;">{metrics["second_round_approved"]}</div><div class="kpi-label">Round 2 Approved</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Admin Navigation Tabs
    tab_candidates, tab_pipeline, tab_scorecards, tab_email_activity = st.tabs([
        "👥 Candidate Management (Shortlist Review)",
        "📊 Interview Pipeline Kanban",
        "📑 Completed Interview Scorecards & Audit",
        "📨 Email Delivery & Activity Log"
    ])

    # ------------------------------------------------------------------------
    # TAB 1: CANDIDATE MANAGEMENT (STEP 1: REVIEW SHORTLISTED CANDIDATES)
    # ------------------------------------------------------------------------
    with tab_candidates:
        st.markdown("### Step 1: Review Shortlisted Candidates")
        st.markdown("Review candidate resumes, inspect AI match scores, and execute **Approve for First-Round Interview** to automatically dispatch secure interview invitations.")

        # Filters and Search
        f_c1, f_c2, f_c3 = st.columns([1.5, 1.2, 1.2])
        with f_c1:
            search_query = st.text_input("🔍 Search by Candidate Name or Email", value=st.session_state.admin_search)
            st.session_state.admin_search = search_query
        with f_c2:
            all_jobs = get_all_jobs()
            job_choices = ["ALL"] + [j["id"] for j in all_jobs]
            job_labels = {j["id"]: f"{j['title']} ({j['department']})" for j in all_jobs}
            job_labels["ALL"] = "All Positions"
            sel_job = st.selectbox("Filter by Role:", job_choices, format_func=lambda x: job_labels.get(x, x))
            st.session_state.admin_filter_job = sel_job
        with f_c3:
            status_choices = ["ALL", "SHORTLISTED", "FIRST_ROUND_APPROVED", "INVITED", "IN_PROGRESS", "COMPLETED", "SECOND_ROUND_APPROVED", "ON_HOLD", "INVITATION_FAILED"]
            sel_status = st.selectbox("Filter by Status:", status_choices)
            st.session_state.admin_filter_status = sel_status

        candidates = get_candidates_list(
            status_filter=st.session_state.admin_filter_status,
            job_filter=st.session_state.admin_filter_job,
            search=st.session_state.admin_search
        )

        st.caption(f"Showing **{len(candidates)}** candidate(s)")

        for c in candidates:
            # Status Badge Styling
            st_class = "pill-blue"
            if c["workflow_status"] == "SHORTLISTED":
                st_class = "pill-blue"
            elif c["workflow_status"] in ("INVITED", "FIRST_ROUND_APPROVED"):
                st_class = "pill-purple"
            elif c["workflow_status"] == "IN_PROGRESS":
                st_class = "pill-amber"
            elif c["workflow_status"] in ("COMPLETED", "SECOND_ROUND_APPROVED"):
                st_class = "pill-emerald"
            elif c["workflow_status"] == "INVITATION_FAILED":
                st_class = "pill-red"

            skills_html = "".join([f'<span class="skill-tag">{s}</span>' for s in c["skills"][:6]])
            score_str = f"{c['overall_score']}/5.0" if c.get("overall_score") is not None else "Pending"
            token_str = "Generated" if c.get("token") else "Pending Approval"
            email_status_str = c.get("last_email_status") or "Not Sent"

            with st.container():
                st.markdown(f"""
                <div class="candidate-row-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <span class="status-pill {st_class}">{c["workflow_status"]}</span>
                            <span style="color:#94A3B8; font-size:0.85rem; margin-left: 10px;">ID: <code>{c["id"]}</code></span>
                            <h3 style="margin: 8px 0 4px 0; color: #FFFFFF; font-size: 1.35rem;">{c["name"]}</h3>
                            <p style="margin: 0; color: #38BDF8; font-size: 0.95rem; font-weight:600;">
                                {c["job_title"]} • {c["job_department"]}
                            </p>
                            <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 0.88rem;">
                                📧 {c["email"]} • 💼 {c["experience_years"]} Years Experience
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #38BDF8;">{c["match_score"]}%</div>
                            <div style="font-size: 0.72rem; color: #94A3B8; text-transform: uppercase;">Use Case 1 Match</div>
                        </div>
                    </div>
                    <div style="margin: 12px 0 8px 0;">
                        {skills_html}
                    </div>
                    <p style="color: #CBD5E1; font-size: 0.92rem; line-height: 1.5; margin: 8px 0;">
                        <strong>Profile Summary:</strong> {c["resume_summary"]}
                    </p>
                    <div style="display:flex; gap:15px; font-size:0.8rem; color:#94A3B8; margin-top:8px;">
                        <span>Email Status: <strong>{email_status_str}</strong></span>
                        <span>Interview Link: <strong>{token_str}</strong></span>
                        <span>Scorecard: <strong>{score_str}</strong></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                btn_col1, btn_col2 = st.columns([1.5, 1.0])

                with btn_col1:
                    # Action: Approve for First-Round Interview
                    if c["workflow_status"] in ("SHORTLISTED", "INVITATION_FAILED"):
                        if st.button(f"✅ Approve for First-Round Interview ({c['name']})", key=f"app_btn_{c['id']}", type="primary"):
                            with st.spinner(f"Generating 8-10 question plan, creating session, and dispatching invitation to {c['email']}..."):
                                res = approve_for_first_round(c["id"])
                                if res["status"] == "success":
                                    st.session_state.toast_msg = f"Approved {c['name']}! Invitation dispatched to {c['email']}."
                                    st.rerun()
                                else:
                                    st.error(res["message"])

                    elif c["workflow_status"] in ("INVITED", "FIRST_ROUND_APPROVED"):
                        st.info(f"✉️ Invitation sent ({c.get('last_email_status', 'SENT')}). Candidate link is active.")
                        if st.button(f"🔄 Resend Invitation Email ({c['name']})", key=f"resend_{c['id']}"):
                            with st.spinner("Retrying email dispatch..."):
                                retry_res = retry_candidate_invitation_email(c["id"])
                                st.session_state.toast_msg = f"Email re-dispatched to {c['email']} ({retry_res['delivery_status']})"
                                st.rerun()

                    elif c["workflow_status"] in ("COMPLETED", "HUMAN_REVIEW_REQUIRED"):
                        st.success(f"🎯 Interview Completed! Rating: {c.get('overall_score', 'N/A')}/5.0 — Review scorecard in Tab 3.")

                    elif c["workflow_status"] == "SECOND_ROUND_APPROVED":
                        st.markdown('<span class="status-pill pill-emerald">Approved for Second Round</span>', unsafe_allow_html=True)

                    elif c["workflow_status"] == "ON_HOLD":
                        st.markdown('<span class="status-pill pill-amber">Placed on Hold</span>', unsafe_allow_html=True)

                with btn_col2:
                    with st.popover("📄 Inspect Full Resume & Claims"):
                        st.markdown(f"#### {c['name']} — Resume Details")
                        st.markdown(f"**Target Role:** {c['job_title']}")
                        st.text_area("Verifiable Resume Text", value=c["resume_text"], height=250)

                st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # TAB 2: INTERVIEW PIPELINE KANBAN
    # ------------------------------------------------------------------------
    with tab_pipeline:
        st.markdown("### 📊 Recruitment Workflow Pipeline")
        p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns(5)

        stages = [
            ("1. Shortlisted", "SHORTLISTED", p_c1),
            ("2. Invited", "INVITED", p_c2),
            ("3. In Progress", "IN_PROGRESS", p_c3),
            ("4. Completed", "COMPLETED", p_c4),
            ("5. Round 2 Approved", "SECOND_ROUND_APPROVED", p_c5)
        ]

        all_candidates = get_candidates_list()

        for title, status_code, col in stages:
            with col:
                st.markdown(f"#### {title}")
                stage_cands = [c for c in all_candidates if c["workflow_status"] == status_code or (status_code == "COMPLETED" and c["workflow_status"] == "HUMAN_REVIEW_REQUIRED")]
                st.caption(f"{len(stage_cands)} candidate(s)")

                for sc in stage_cands:
                    st.markdown(f"""
                    <div style="background: #111827; border: 1px solid #1F2937; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                        <strong style="color: #FFFFFF;">{sc['name']}</strong><br>
                        <small style="color: #94A3B8;">{sc['job_title']}</small><br>
                        <span style="color:#38BDF8; font-size:0.75rem; font-weight:bold;">Match: {sc['match_score']}%</span>
                    </div>
                    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # TAB 3: COMPLETED INTERVIEW SCORECARDS & AUDIT (STEP 7 & STEP 8)
    # ------------------------------------------------------------------------
    with tab_scorecards:
        st.markdown("### Step 7 & 8: Review Completed Interviews & Authorize Second Round")
        st.markdown("Inspect objective, evidence-grounded AI evaluations. **No automated rejections:** Human recruiters make the definitive decision to **Approve for Second Round** or **Place on Hold**.")

        # Find all candidates with completed scorecards
        completed_cands = [c for c in get_candidates_list() if c.get("overall_score") is not None or c["workflow_status"] in ("COMPLETED", "HUMAN_REVIEW_REQUIRED", "SECOND_ROUND_APPROVED", "ON_HOLD")]

        if not completed_cands:
            st.info("No completed interviews yet. To test, open an active candidate link or use the Candidate Interview Portal.")
        else:
            for cand in completed_cands:
                card = get_scorecard_by_candidate_id(cand["id"])
                if not card:
                    continue

                rec_color = "#10B981" if card["recommendation"] == "ADVANCE" else ("#F59E0B" if card["recommendation"] == "HOLD" else "#EF4444")

                with st.expander(f"📑 {cand['name']} — {cand['job_title']} (Overall Score: {card['overall_score']}/5.0 | {card['recommendation']})", expanded=True):
                    # Top Score Card Banner
                    st.markdown(f"""
                    <div class="saas-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span class="status-pill pill-blue">{cand['workflow_status']}</span>
                                <h2 style="margin: 8px 0 4px 0; color:#FFFFFF;">{cand['name']}</h2>
                                <p style="margin:0; color:#94A3B8;">Role: <strong>{cand['job_title']}</strong> • Completed: {card['interview_completed_at'] or card['created_at']}</p>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 2.2rem; font-weight: 800; color: #38BDF8;">{card['overall_score']} <span style="font-size:1.2rem; color:#94A3B8;">/ 5.0</span></div>
                                <div style="font-weight: 700; color: {rec_color}; font-size: 1rem;">AI Recommendation: {card['recommendation']}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Human Review Flag Banner
                    if card["human_review_flag"] == 1:
                        st.markdown("""
                        <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 8px; padding: 12px 18px; margin-bottom: 16px;">
                            <strong style="color: #FBBF24;">⚠️ Human Review Required:</strong>
                            <span style="color: #E2E8F0; font-size: 0.92rem;">
                                The AI flagged low confidence or variance between resume claims and answer depth. Recruiter verification is required.
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                    # Domain Scores Row
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    with sc1:
                        st.markdown(f'<div class="kpi-box"><div class="kpi-number">{card["technical_score"]}</div><div class="kpi-label">Technical Depth</div></div>', unsafe_allow_html=True)
                    with sc2:
                        st.markdown(f'<div class="kpi-box"><div class="kpi-number">{card["problem_solving_score"]}</div><div class="kpi-label">Problem Solving</div></div>', unsafe_allow_html=True)
                    with sc3:
                        st.markdown(f'<div class="kpi-box"><div class="kpi-number">{card["communication_score"]}</div><div class="kpi-label">Communication</div></div>', unsafe_allow_html=True)
                    with sc4:
                        st.markdown(f'<div class="kpi-box"><div class="kpi-number">{card["job_fit_score"]}</div><div class="kpi-label">Job Fit & Alignment</div></div>', unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Radar Chart & Transcript
                    r_col1, r_col2 = st.columns([1, 1])
                    with r_col1:
                        st.markdown("#### 🕸️ Competency Benchmark Radar")
                        scores_dict = {
                            "Technical Depth": card["technical_score"],
                            "Problem Solving": card["problem_solving_score"],
                            "Communication": card["communication_score"],
                            "Job Fit": card["job_fit_score"]
                        }
                        radar_fig = create_competency_radar_chart(scores_dict)
                        st.plotly_chart(radar_fig, use_container_width=True)

                    with r_col2:
                        st.markdown("#### 📝 AI Executive Evaluation Summary")
                        st.markdown(f"**Assessment Rationale:** {card['transcript_summary']}")
                        st.markdown(f"**Identified Strengths:** {card['strengths']}")
                        st.markdown(f"**Identified Growth Areas:** {card['gaps']}")

                    # Question by Question Turn Viewer
                    st.markdown("#### 🔍 Verbatim Turn-by-Turn Evidence")
                    turns = get_qa_turns_by_session_id(card["session_id"])
                    for t in turns:
                        with st.expander(f"Q#{t['question_id']}: {t['competency']} (Score: {t['score']}/5)", expanded=False):
                            st.markdown(f"**Question:** {t['question_text']}")
                            st.markdown(f"**Candidate Answer:** *\"{t['candidate_answer']}\"*")
                            if t['followup_question']:
                                st.markdown(f"**⚡ Follow-up Probe:** *{t['followup_question']}*")
                                st.markdown(f"**Follow-up Response:** *\"{t['followup_answer']}\"*")
                            st.markdown(f"**Verbatim Evidence Quote:** <span style='color:#38BDF8;'>{t['evidence_quote']}</span>", unsafe_allow_html=True)
                            st.markdown(f"**Rubric Assessment:** `{t['rubric_match']}`")

                    # Consistency Matrix
                    st.markdown("#### 📑 Resume Claim Verification Findings")
                    findings = card["consistency_findings"]
                    if findings:
                        f_table = []
                        for f in findings:
                            status_str = "✅ Supported" if f["status"] == "Supported" else ("⚠️ Needs Clarification" if f["status"] == "Needs Clarification" else "ℹ️ Partially Supported")
                            f_table.append({
                                "Claim ID": f["claim_id"],
                                "Resume Claim Statement": f["claim_text"],
                                "Verification Status": status_str,
                                "Analysis & Interview Grounding": f["analysis"]
                            })
                        st.dataframe(f_table, use_container_width=True)

                    st.markdown("---")

                    # Step 8 Actions: Approve for Second Round or Place on Hold
                    st.markdown("#### ⚖️ Human Recruiter Decision & Advancement")
                    d_col1, d_col2 = st.columns(2)

                    with d_col1:
                        if cand["workflow_status"] != "SECOND_ROUND_APPROVED":
                            if st.button(f"🎉 Approve for Second Round ({cand['name']})", key=f"round2_{cand['id']}", type="primary", use_container_width=True):
                                with st.spinner("Authorizing second round and dispatching notification email..."):
                                    r2_res = approve_for_second_round(cand["id"], reviewer="Admin")
                                    st.session_state.toast_msg = f"Approved {cand['name']} for Second Round! Selection email dispatched to {cand['email']}."
                                    st.rerun()
                        else:
                            st.success("✅ Candidate Approved for Second Round. Notification email has been dispatched.")

                    with d_col2:
                        if cand["workflow_status"] != "ON_HOLD":
                            if st.button(f"⏸️ Place on Hold ({cand['name']})", key=f"hold_{cand['id']}", use_container_width=True):
                                place_candidate_on_hold(cand["id"], reviewer="Admin")
                                st.session_state.toast_msg = f"Candidate {cand['name']} placed on hold."
                                st.rerun()
                        else:
                            st.warning("Candidate is currently on hold.")

    # ------------------------------------------------------------------------
    # TAB 4: EMAIL DELIVERY & ACTIVITY LOG (STEP 3 & STEP 8 TRACKING)
    # ------------------------------------------------------------------------
    with tab_email_activity:
        st.markdown("### 📨 Email Notification Audit Trail")
        st.caption("Verifiable email delivery status, provider message references, and retry operations:")

        email_logs = get_all_email_logs()

        if not email_logs:
            st.info("No email notifications logged yet.")
        else:
            for el in email_logs:
                badge = "pill-emerald" if el["delivery_status"] in ("DELIVERED_SMTP", "ACCEPTED_DEV_MOCK") else "pill-red"
                with st.expander(f"✉️ {el['subject']} ➔ {el['recipient_email']} [{el['delivery_status']}]", expanded=False):
                    em1, em2 = st.columns([1.2, 1])
                    with em1:
                        st.markdown(f"**Recipient:** `{el['recipient_name']} <{el['recipient_email']}>`")
                        st.markdown(f"**Notification Type:** `{el['notification_type']}`")
                        st.markdown(f"**Delivery Status:** <span class='status-pill {badge}'>{el['delivery_status']}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Provider Reference:** `{el['provider_reference']}`")
                        if el.get("error_details"):
                            st.error(f"Error: {el['error_details']}")
                        st.markdown(f"**Sent At:** `{el['sent_at'] or el['created_at']}`")

                        if el["delivery_status"] == "FAILED":
                            if st.button(f"🔄 Retry Dispatch ({el['id']})", key=f"retry_{el['id']}"):
                                retry_failed_notification(el["id"])
                                st.session_state.toast_msg = "Retried email notification."
                                st.rerun()

                    with em2:
                        st.markdown("**Rendered Body:**")
                        st.components.v1.html(el["body_html"], height=260, scrolling=True)
