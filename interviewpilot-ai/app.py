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
import time
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
    mark_candidate_under_review,
    reject_candidate,
    retry_candidate_invitation_email,
    match_resume_to_profiles
)
from email_service import (
    get_base_url,
    retry_failed_notification,
    get_smtp_credentials,
    save_smtp_credentials,
    test_smtp_connection
)
from agent import InterviewPilotAgent
from tools import get_activity_logs, clear_activity_logs
from report_generator import create_competency_radar_chart, create_competency_bar_chart, generate_markdown_report
from resume_parser import parse_resume, extract_text_from_pdf
from demo_data import (
    SAMPLE_RESPONSES,
    SAMPLE_DEVOPS_RESUME,
    SAMPLE_AI_RESUME,
    SAMPLE_NONMATCHING_CHEF_RESUME
)


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
        st.caption("Authorized to review candidates, approve first-round invitations, review scorecards, and make hiring decisions.")
        st.info("🔒 Note: Manual 'Launch Interview' actions have been removed. Candidates conduct interviews independently via secure invitation links.")

        st.markdown("---")
        st.markdown("#### 📧 Real Gmail SMTP Dispatch")
        st.caption("Configure your Gmail address & Google App Password to dispatch live emails for invitations, second rounds, and rejections.")

        creds = get_smtp_credentials()
        is_live = bool(creds["user"] and creds["password"])
        if is_live:
            st.markdown(f'<span class="status-pill pill-emerald">🟢 Live Gmail Active: {creds["user"]}</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-pill pill-amber">🟡 Fallback: ACCEPTED_DEV_MOCK</span>', unsafe_allow_html=True)

        with st.expander("⚙️ Configure Live Gmail Dispatch", expanded=not is_live):
            gmail_user_input = st.text_input(
                "Gmail Address",
                value=creds["user"] or "",
                placeholder="your.account@gmail.com",
                key="admin_gmail_user"
            )
            gmail_pass_input = st.text_input(
                "16-Character App Password",
                value=creds["password"] or "",
                type="password",
                placeholder="abcd efgh ijkl mnop",
                help="Requires 2-Step Verification enabled in Google Account > Security > App passwords. Enter the 16-character code.",
                key="admin_gmail_pass"
            )

            if st.button("💾 Save Gmail Credentials", key="btn_save_gmail", use_container_width=True):
                if not gmail_user_input.strip():
                    st.warning("Please provide a Gmail address.")
                elif not gmail_user_input.strip().lower().endswith("@gmail.com"):
                    st.error("Email must be a valid @gmail.com address.")
                elif not gmail_pass_input.strip():
                    st.warning("Please enter your 16-character Google App Password.")
                else:
                    save_smtp_credentials(gmail_user_input, gmail_pass_input)
                    st.session_state.toast_msg = "Gmail SMTP credentials saved successfully!"
                    st.rerun()

            st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 8px 0;'>", unsafe_allow_html=True)
            test_recipient = st.text_input(
                "Recipient for Live Test",
                value=gmail_user_input or "sukrit.ss.31@gmail.com",
                placeholder="recipient@gmail.com",
                key="admin_test_recipient"
            )
            if st.button("📨 Send Live Test Email", key="btn_test_gmail", use_container_width=True):
                if not test_recipient.strip():
                    st.warning("Please enter a test recipient email.")
                elif not test_recipient.strip().lower().endswith("@gmail.com"):
                    st.error("Recipient must be a valid @gmail.com address.")
                else:
                    with st.spinner("Connecting to smtp.gmail.com:587 (TLS)..."):
                        test_res = test_smtp_connection(test_recipient.strip())
                        if test_res["success"]:
                            st.success(f"✓ {test_res['message']}")
                        else:
                            st.error(f"SMTP Connection Failed: {test_res['error']}")
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

            # Quick-Load Helper for Demonstration & Testing
            st.markdown("**⚡ Quick Test: Select an Approved Candidate**")
            invited_cands = [c for c in get_candidates_list() if c.get("token") and c["workflow_status"] in ("INVITED", "IN_PROGRESS", "FIRST_ROUND_APPROVED")]
            if invited_cands:
                cand_options = {f"{c['name']} — {c['job_title']} ({c['token'][:8]}...)": c["token"] for c in invited_cands}
                selected_cand_label = st.selectbox("Approved Candidates Ready to Interview:", list(cand_options.keys()))
                if st.button("🚀 Enter Screening Room as Selected Candidate", type="primary", use_container_width=True):
                    st.session_state.candidate_token = cand_options[selected_cand_label]
                    st.query_params["token"] = cand_options[selected_cand_label]
                    st.rerun()
            else:
                st.caption("No active interview sessions yet. Approve a candidate in the Admin Portal to generate an invitation link.")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔓 Validate Token & Enter", use_container_width=True):
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

    # Active Question Display (Candidate-Facing Focused Layout)
    _, cand_col, _ = st.columns([0.08, 0.84, 0.08])

    with cand_col:
        progress_val = min(1.0, agent.state.current_index / max(1, total_q))
        st.progress(progress_val)
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
            <span style="font-size:0.9rem; color:#94A3B8;">Question <strong>{agent.state.current_index + 1} of {total_q}</strong> • Domain: <strong style="color:#38BDF8;">{curr_q.competency if curr_q else 'In Progress'}</strong></span>
            <span class="status-pill pill-purple">Level: {agent.state.current_difficulty.upper()}</span>
        </div>
        """, unsafe_allow_html=True)

        # 60-Second Real-Time Countdown Timer Widget
        q_timer_key = f"q_timer_start_{agent.state.current_index}_{agent.state.status}"
        if q_timer_key not in st.session_state:
            st.session_state[q_timer_key] = time.time()

        timer_html = f"""
        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 12px 18px; margin: 0 0 16px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 1.1rem;">⏱️</span>
                    <span style="font-size: 0.82rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em;">Response Window</span>
                </div>
                <div id="countdown-val" style="font-size: 1.35rem; font-weight: 800; font-family: monospace; color: #10B981;">01:00</div>
            </div>
            <div style="width: 100%; height: 7px; background: rgba(255, 255, 255, 0.08); border-radius: 4px; overflow: hidden;">
                <div id="countdown-bar" style="width: 100%; height: 100%; background: #10B981; transition: width 1s linear, background-color 1s ease;"></div>
            </div>
            <div id="timer-status" style="margin-top: 6px; font-size: 0.76rem; color: #64748B; text-align: right;">Standard recommended response: 60 seconds per question</div>
        </div>
        <!-- timer_idx_{agent.state.current_index}_{agent.state.status} -->
        <script>
            let remaining = 60;
            const valEl = document.getElementById('countdown-val');
            const barEl = document.getElementById('countdown-bar');
            const statEl = document.getElementById('timer-status');
            const timer = setInterval(() => {{
                remaining--;
                if (remaining <= 0) {{
                    clearInterval(timer);
                    valEl.innerText = "00:00";
                    valEl.style.color = "#EF4444";
                    barEl.style.width = "0%";
                    statEl.innerText = "⏱️ Time limit reached! Please finalize and submit your response.";
                    statEl.style.color = "#F87171";
                    return;
                }}
                let m = Math.floor(remaining / 60);
                let s = remaining % 60;
                valEl.innerText = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
                barEl.style.width = ((remaining / 60) * 100) + "%";
                if (remaining > 20) {{
                    valEl.style.color = "#10B981";
                    barEl.style.background = "#10B981";
                }} else if (remaining > 10) {{
                    valEl.style.color = "#F59E0B";
                    barEl.style.background = "#F59E0B";
                    statEl.innerText = "⚠️ 20 seconds remaining — wrap up your core points.";
                    statEl.style.color = "#FBBF24";
                }} else {{
                    valEl.style.color = "#EF4444";
                    barEl.style.background = "#EF4444";
                    statEl.innerText = "🚨 Under 10 seconds! Submit your answer now.";
                    statEl.style.color = "#F87171";
                }}
            }}, 1000);
        </script>
        """
        st.components.v1.html(timer_html, height=88)

        if curr_q:
            st.markdown(f"""
            <div class="question-panel" style="margin-bottom: 18px;">
                <span class="status-pill pill-blue">{curr_q.competency}</span>
                <h3 style="margin-top: 14px; color: #FFFFFF;">Question #{curr_q.id}</h3>
                <p style="font-size: 1.15rem; line-height: 1.6; color: #F1F5F9;">{curr_q.text}</p>
            </div>
            """, unsafe_allow_html=True)

            # Adaptive follow-up probe mode
            if agent.state.status == "AWAITING_FOLLOWUP":
                st.markdown(f"""
                <div class="followup-panel" style="margin-bottom: 18px;">
                    <span class="status-pill pill-amber">⚡ Interviewer Follow-up Question</span>
                    <h4 style="margin-top: 10px; color: #FBBF24;">Please Elaborate</h4>
                    <p style="font-size: 1.05rem; color: #F1F5F9; line-height: 1.5;">{agent.state.active_followup}</p>
                    <small style="color: #CBD5E1;">Please provide additional technical specifics, architectural trade-offs, edge cases, or production metrics.</small>
                </div>
                """, unsafe_allow_html=True)

                followup_ans = st.text_area(
                    "Your Follow-up Answer",
                    height=130,
                    placeholder="Elaborate with specific libraries, architecture decisions, or error recovery...",
                    key=f"cand_fu_input_{agent.state.current_index}"
                )

                if st.button("📤 Submit Follow-up", type="primary", use_container_width=True, key=f"submit_fu_{curr_q.id}"):
                    if followup_ans.strip():
                        start_t = st.session_state.get(q_timer_key, time.time())
                        raw_sec = int(time.time() - start_t)
                        rt_sec = raw_sec if (5 <= raw_sec <= 60) else (38 if raw_sec < 5 else 60)
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
                            gaps=agent.state.history[-1].evaluation.gaps,
                            response_time_seconds=rt_sec
                        )
                        st.rerun()
                    else:
                        st.warning("Please provide a response before submitting.")

                with st.expander("⚡ Demonstration Shortcuts (For Evaluators)", expanded=False):
                    st.caption("One-click shortcut to test agentic recovery on follow-up probes:")
                    if st.button("⚡ Quick-Fill Strong Follow-up Answer (Advances with Score 5)", use_container_width=True, key=f"qf_fu_{curr_q.id}"):
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
                            gaps=agent.state.history[-1].evaluation.gaps,
                            response_time_seconds=40
                        )
                        st.rerun()

            else:
                candidate_ans = st.text_area(
                    "Your Answer",
                    height=140,
                    placeholder="Type or paste your technical answer here...",
                    key=f"cand_ans_input_{agent.state.current_index}"
                )

                if st.button("📤 Submit Answer", type="primary", use_container_width=True, key=f"submit_ans_{curr_q.id}"):
                    if candidate_ans.strip():
                        start_t = st.session_state.get(q_timer_key, time.time())
                        raw_sec = int(time.time() - start_t)
                        rt_sec = raw_sec if (5 <= raw_sec <= 60) else (42 if raw_sec < 5 else 60)
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
                                gaps=agent.state.history[-1].evaluation.gaps,
                                response_time_seconds=rt_sec
                            )
                        st.rerun()
                    else:
                        st.warning("Please enter your answer before submitting.")

                with st.expander("⚡ Demonstration Shortcuts (For Evaluators)", expanded=False):
                    st.caption("One-click shortcuts to test agentic evaluation, adaptive follow-ups, and scoring:")
                    b_c1, b_c2 = st.columns(2)
                    with b_c1:
                        if st.button("⚠️ Test Shallow Answer (Triggers Follow-up)", use_container_width=True, key=f"demo_shallow_{curr_q.id}"):
                            candidate_ans = SAMPLE_RESPONSES["shallow"]["text"]
                            agent.submit_answer(candidate_ans)
                            st.rerun()
                    with b_c2:
                        if st.button("✅ Test Strong Answer (Advances with Score 5)", use_container_width=True, key=f"demo_strong_{curr_q.id}"):
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
                                gaps=agent.state.history[-1].evaluation.gaps,
                                response_time_seconds=45
                            )
                            st.rerun()


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
    tab_upload, tab_candidates, tab_pipeline, tab_scorecards, tab_email_activity = st.tabs([
        "📤 Ingest & Auto-Match Resume",
        "👥 Candidate Management (Shortlist Review)",
        "📊 Interview Pipeline Kanban",
        "📑 Completed Interview Scorecards & Audit",
        "📨 Email Delivery & Activity Log"
    ])

    # ------------------------------------------------------------------------
    # TAB 1: RESUME INGESTION & AUTO-MATCHING (USE CASE 1 - RESUME MATCHING)
    # ------------------------------------------------------------------------
    with tab_upload:
        st.markdown("### 📤 AI Resume Ingestion & Role Matching Engine")
        st.markdown(
            "Upload a candidate's resume (PDF file or plain text). The AI Agent evaluates technical skills, "
            "experience, and achievements against all **5 active enterprise roles**, automatically assigns the candidate "
            "to the highest-matching profile bucket if qualified, or flags if the resume does not match any open role."
        )

        st.markdown("""
        <div class="saas-card">
            <h4 style="color:#38BDF8; margin-top:0;">⚡ Live Demonstration Quick-Fill Shortcuts</h4>
            <p style="color:#94A3B8; font-size:0.88rem; margin-bottom: 8px;">
                Click a profile below to immediately populate a synthetic test resume:
            </p>
        </div>
        """, unsafe_allow_html=True)

        qf_c1, qf_c2, qf_c3 = st.columns(3)
        with qf_c1:
            if st.button("⚡ Load DevOps Lead Sample (Matches DevOps)", use_container_width=True):
                st.session_state.upload_text_val = SAMPLE_DEVOPS_RESUME
                st.session_state.upload_name_val = "David Ross"
                st.session_state.upload_email_val = "david.ross.devops@gmail.com"
                st.session_state.upload_match_result = None
                st.rerun()
        with qf_c2:
            if st.button("⚡ Load AI Engineer Sample (Matches AI Systems)", use_container_width=True):
                st.session_state.upload_text_val = SAMPLE_AI_RESUME
                st.session_state.upload_name_val = "Anita Roy"
                st.session_state.upload_email_val = "anita.roy.ai@gmail.com"
                st.session_state.upload_match_result = None
                st.rerun()
        with qf_c3:
            if st.button("⚡ Load Non-Matching Sample (Chef Marco)", use_container_width=True):
                st.session_state.upload_text_val = SAMPLE_NONMATCHING_CHEF_RESUME
                st.session_state.upload_name_val = "Chef Marco Pierre"
                st.session_state.upload_email_val = "marco.pierre.chef@gmail.com"
                st.session_state.upload_match_result = None
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        up_col1, up_col2 = st.columns([1.2, 1.0])
        with up_col1:
            uploaded_pdf = st.file_uploader("Upload Resume File (PDF)", type=["pdf"], key="admin_pdf_uploader")
            pdf_extracted_text = ""
            if uploaded_pdf is not None:
                try:
                    pdf_extracted_text = extract_text_from_pdf(uploaded_pdf)
                    st.success(f"✓ Successfully extracted text from PDF ({len(pdf_extracted_text)} characters).")
                except Exception as e:
                    st.error(f"Error reading PDF: {e}")

            initial_text = pdf_extracted_text if pdf_extracted_text else st.session_state.get("upload_text_val", "")
            resume_text_input = st.text_area(
                "Or Review / Paste Candidate Resume Text",
                value=initial_text,
                height=220,
                placeholder="Paste candidate resume text with work history, projects, and skills..."
            )

        with up_col2:
            st.markdown("""
            <div class="saas-card" style="height:100%;">
                <h4 style="color:#FFFFFF; margin-top:0;">📋 Candidate Identity (Strictly @gmail.com)</h4>
                <p style="color:#94A3B8; font-size:0.85rem;">
                    Candidate emails must strictly be <strong>@gmail.com</strong> for real Gmail delivery. If omitted, the agent extracts and formats from resume.
                </p>
            </div>
            """, unsafe_allow_html=True)
            cand_name_ov = st.text_input("Candidate Name", value=st.session_state.get("upload_name_val", ""), placeholder="e.g. David Ross")
            cand_email_ov = st.text_input("Candidate Email (Must be @gmail.com)", value=st.session_state.get("upload_email_val", ""), placeholder="e.g. david.ross@gmail.com")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🤖 Analyze & Auto-Match Resume to Open Roles", type="primary", use_container_width=True):
            if not resume_text_input.strip():
                st.warning("Please upload a PDF or enter resume text to analyze.")
            elif cand_email_ov.strip() and not cand_email_ov.strip().lower().endswith("@gmail.com"):
                st.error("❌ Candidate email must end with @gmail.com (e.g. candidate@gmail.com). Non-Gmail domains are not permitted.")
            else:
                with st.spinner("AI Agent analyzing skills, taxonomy keywords, and job alignment across all 5 open roles..."):
                    match_res = match_resume_to_profiles(
                        raw_text=resume_text_input,
                        override_name=cand_name_ov,
                        override_email=cand_email_ov,
                        min_threshold=50,
                        save_if_matched=True
                    )
                    st.session_state.upload_match_result = match_res
                    st.rerun()

        # Display Evaluation & Matching Results
        if st.session_state.get("upload_match_result"):
            res = st.session_state.upload_match_result

            if res["matched"]:
                st.markdown(f"""
                <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid #10B981; border-radius: 12px; padding: 22px; margin-top: 20px;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <span class="status-pill pill-emerald">🎉 MATCHED & SHORTLISTED</span>
                            <h2 style="margin: 8px 0 4px 0; color:#FFFFFF;">{res['candidate_name']}</h2>
                            <p style="margin:0; color:#38BDF8; font-weight:600; font-size:1.1rem;">
                                Assigned Role Bucket: {res['matched_job']['job_title']} ({res['matched_job']['department']})
                            </p>
                            <p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.9rem;">
                                📧 {res['candidate_email']} • 💼 {res['experience_years']} Years Experience • ID: <code>{res['candidate_id']}</code>
                            </p>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:2.4rem; font-weight:800; color:#10B981;">{res['match_score']}%</div>
                            <div style="font-size:0.75rem; color:#94A3B8; text-transform:uppercase;">Profile Match Score</div>
                        </div>
                    </div>
                    <div style="margin: 14px 0;">
                        <strong style="color:#CBD5E1;">Matched Core Skills:</strong><br>
                        {''.join([f'<span class="skill-tag" style="background:#065F46; color:#A7F3D0; border:1px solid #10B981;">✓ {s}</span>' for s in res['matched_skills']])}
                    </div>
                    <p style="color:#CBD5E1; font-size:0.9rem; margin-bottom:0;">
                        <strong>AI Shortlist Rationale:</strong> {res['summary']}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                act_col1, act_col2 = st.columns([1.5, 1.0])

                with act_col1:
                    # Check candidate status in database
                    curr_cand = get_candidate_details(res["candidate_id"])
                    if curr_cand and curr_cand["workflow_status"] in ("SHORTLISTED", "INVITATION_FAILED"):
                        st.markdown("**Next Step: Authorize Candidate for First-Round Interview**")
                        if st.button(f"✅ Approve {res['candidate_name']} for First-Round Interview", key="app_up_btn", type="primary", use_container_width=True):
                            with st.spinner(f"Synthesizing 8-10 question agenda and dispatching invitation to {res['candidate_email']}..."):
                                app_res = approve_for_first_round(res["candidate_id"])
                                if app_res["status"] == "success":
                                    st.session_state.toast_msg = f"Approved {res['candidate_name']}! Invitation dispatched."
                                    st.session_state.upload_approval_details = app_res
                                    st.rerun()
                                else:
                                    st.error(app_res["message"])

                    elif curr_cand and curr_cand["workflow_status"] in ("INVITED", "FIRST_ROUND_APPROVED"):
                        base_url = get_base_url()
                        cand_url = f"{base_url}/?token={curr_cand['token']}"
                        st.success(f"✉️ Invitation Email Dispatched to {curr_cand['email']}! Status: {curr_cand.get('session_status', 'ACTIVE')}")

                        st.markdown(f"""
                        <div style="background: rgba(56, 189, 248, 0.12); border: 1px solid #38BDF8; border-radius: 8px; padding: 12px; margin: 10px 0;">
                            <strong style="color:#38BDF8;">🔗 Direct Candidate Interview Link:</strong><br>
                            <a href="{cand_url}" target="_blank" style="color:#60A5FA; font-size:0.95rem; word-break:break-all;">{cand_url}</a>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button("🚀 Open Candidate Portal to Take Interview Now", key="go_cand_now", type="primary", use_container_width=True):
                            st.session_state.active_portal = "Candidate Portal"
                            st.session_state.candidate_token = curr_cand["token"]
                            st.query_params["token"] = curr_cand["token"]
                            st.session_state.candidate_agent = None
                            st.session_state.interview_started = False
                            st.rerun()

                with act_col2:
                    st.download_button(
                        label="📥 Download Candidate Resume (.txt)",
                        data=res["resume_text"],
                        file_name=f"{res['candidate_name'].replace(' ', '_')}_Resume.txt",
                        mime="text/plain",
                        key="dl_up_resume",
                        use_container_width=True
                    )

            else:
                # Non-matching profile result
                st.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid #EF4444; border-radius: 12px; padding: 22px; margin-top: 20px;">
                    <span class="status-pill pill-red">⚠️ NOT MATCHING ANY PROFILE</span>
                    <h2 style="margin: 8px 0 4px 0; color:#FFFFFF;">{res['candidate_name']}</h2>
                    <p style="margin:0; color:#F87171; font-weight:600; font-size:1.05rem;">
                        {res['reason']}
                    </p>
                    <p style="margin:6px 0 0 0; color:#94A3B8; font-size:0.88rem;">
                        This candidate profile does not meet minimum technical qualifications (50% threshold) and has NOT been shortlisted.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br><strong>📊 Alignment Across All 5 Open Roles:</strong>", unsafe_allow_html=True)
                breakdown_data = []
                for ev in res["all_evaluations"]:
                    breakdown_data.append({
                        "Job Title": ev["job_title"],
                        "Department": ev["department"],
                        "Match Score": f"{ev['match_score']}%",
                        "Matched Skills": ", ".join(ev["matched_skills"]) if ev["matched_skills"] else "None",
                        "Qualification Status": "🔴 Below 50% Threshold"
                    })
                st.table(breakdown_data)

    # ------------------------------------------------------------------------
    # TAB 2: CANDIDATE MANAGEMENT (STEP 1: REVIEW SHORTLISTED CANDIDATES)
    # ------------------------------------------------------------------------
    with tab_candidates:
        st.markdown("### Step 1: Candidate Management Command Center")
        st.markdown("Review candidate resumes, inspect AI match scores, download resumes, and execute **Approve for First-Round Interview** to automatically dispatch secure interview invitations.")

        all_cands_pool = get_candidates_list()

        # Categorize candidates into distinct lifecycle buckets
        c_shortlisted = [c for c in all_cands_pool if c["workflow_status"] in ("SHORTLISTED", "INVITATION_FAILED")]
        c_active = [c for c in all_cands_pool if c["workflow_status"] in ("INVITED", "FIRST_ROUND_APPROVED", "IN_PROGRESS")]
        c_cleared = [c for c in all_cands_pool if c["workflow_status"] == "SECOND_ROUND_APPROVED"]
        c_review_hold = [c for c in all_cands_pool if c["workflow_status"] in ("HUMAN_REVIEW_REQUIRED", "ON_HOLD")]
        c_rejected = [c for c in all_cands_pool if c["workflow_status"] == "REJECTED"]

        def render_candidate_row_card(c, card_key_prefix="dir"):
            st_class = "pill-blue"
            if c["workflow_status"] == "SHORTLISTED":
                st_class = "pill-blue"
            elif c["workflow_status"] in ("INVITED", "FIRST_ROUND_APPROVED"):
                st_class = "pill-purple"
            elif c["workflow_status"] == "IN_PROGRESS":
                st_class = "pill-amber"
            elif c["workflow_status"] in ("COMPLETED", "SECOND_ROUND_APPROVED"):
                st_class = "pill-emerald"
            elif c["workflow_status"] in ("HUMAN_REVIEW_REQUIRED", "ON_HOLD"):
                st_class = "pill-amber"
            elif c["workflow_status"] in ("REJECTED", "INVITATION_FAILED"):
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

                btn_col1, btn_col2, btn_col3 = st.columns([1.5, 0.9, 0.9])

                with btn_col1:
                    # Action: Approve for First-Round Interview
                    if c["workflow_status"] in ("SHORTLISTED", "INVITATION_FAILED"):
                        if st.button(f"✅ Approve for First-Round Interview ({c['name']})", key=f"{card_key_prefix}_app_btn_{c['id']}", type="primary"):
                            with st.spinner(f"Generating tailored question plan, creating session, and dispatching invitation to {c['email']}..."):
                                res = approve_for_first_round(c["id"])
                                if res["status"] == "success":
                                    st.session_state.toast_msg = f"Approved {c['name']}! Invitation dispatched to {c['email']}."
                                    st.rerun()
                                else:
                                    st.error(res["message"])

                    elif c["workflow_status"] in ("INVITED", "FIRST_ROUND_APPROVED"):
                        base_url = get_base_url()
                        cand_url = f"{base_url}/?token={c['token']}"
                        st.markdown(f"""
                        <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid #38BDF8; border-radius: 6px; padding: 6px 10px; margin-bottom: 8px;">
                            <span style="color:#38BDF8; font-weight:bold; font-size:0.82rem;">🔗 Interview Link:</span>
                            <a href="{cand_url}" target="_blank" style="color:#60A5FA; font-size:0.82rem; word-break:break-all;">{cand_url}</a>
                        </div>
                        """, unsafe_allow_html=True)

                        col_act_a, col_act_b = st.columns(2)
                        with col_act_a:
                            if st.button(f"🚀 Open Candidate Portal", key=f"{card_key_prefix}_test_cand_{c['id']}", type="primary", use_container_width=True):
                                st.session_state.active_portal = "Candidate Portal"
                                st.session_state.candidate_token = c["token"]
                                st.query_params["token"] = c["token"]
                                st.session_state.candidate_agent = None
                                st.session_state.interview_started = False
                                st.rerun()
                        with col_act_b:
                            if st.button(f"🔄 Resend Email", key=f"{card_key_prefix}_resend_{c['id']}", use_container_width=True):
                                with st.spinner("Retrying email dispatch..."):
                                    retry_res = retry_candidate_invitation_email(c["id"])
                                    st.session_state.toast_msg = f"Email re-dispatched to {c['email']} ({retry_res['delivery_status']})"
                                    st.rerun()

                    elif c["workflow_status"] == "IN_PROGRESS":
                        base_url = get_base_url()
                        cand_url = f"{base_url}/?token={c['token']}"
                        st.markdown(f"""
                        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid #F59E0B; border-radius: 6px; padding: 6px 10px; margin-bottom: 8px;">
                            <span style="color:#FBBF24; font-weight:bold; font-size:0.82rem;">⚡ Screening In Progress:</span>
                            <a href="{cand_url}" target="_blank" style="color:#FCD34D; font-size:0.82rem; word-break:break-all;">{cand_url}</a>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"🚀 Open Screening Portal", key=f"{card_key_prefix}_prog_cand_{c['id']}", type="primary", use_container_width=True):
                            st.session_state.active_portal = "Candidate Portal"
                            st.session_state.candidate_token = c["token"]
                            st.query_params["token"] = c["token"]
                            st.rerun()

                    elif c["workflow_status"] in ("COMPLETED", "HUMAN_REVIEW_REQUIRED"):
                        st.success(f"🎯 Interview Completed! Rating: {c.get('overall_score', 'N/A')}/5.0 — Review scorecard in Tab 4.")

                    elif c["workflow_status"] == "SECOND_ROUND_APPROVED":
                        st.markdown('<span class="status-pill pill-emerald">🎉 Approved for Second Round</span>', unsafe_allow_html=True)

                    elif c["workflow_status"] == "ON_HOLD":
                        st.markdown('<span class="status-pill pill-amber">⏸️ Placed on Hold</span>', unsafe_allow_html=True)

                    elif c["workflow_status"] == "REJECTED":
                        st.markdown('<span class="status-pill pill-red">❌ Application Rejected</span>', unsafe_allow_html=True)

                with btn_col2:
                    st.download_button(
                        label="📥 Download Resume",
                        data=c["resume_text"],
                        file_name=f"{c['name'].replace(' ', '_')}_Resume.txt",
                        mime="text/plain",
                        key=f"{card_key_prefix}_dl_card_{c['id']}",
                        use_container_width=True
                    )

                with btn_col3:
                    with st.popover("📄 Inspect Claims"):
                        st.markdown(f"#### {c['name']} — Resume Details")
                        st.markdown(f"**Target Role:** {c['job_title']}")
                        st.text_area("Verifiable Resume Text", value=c["resume_text"], height=220, key=f"{card_key_prefix}_pop_text_{c['id']}")
                        st.download_button(
                            label="📥 Download Resume (.txt)",
                            data=c["resume_text"],
                            file_name=f"{c['name'].replace(' ', '_')}_Resume.txt",
                            mime="text/plain",
                            key=f"{card_key_prefix}_dl_pop_{c['id']}",
                            use_container_width=True
                        )

                st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

        # Segmented Sub-Tabs for Clean Stage Organization
        sub_pend, sub_act, sub_clear, sub_hold, sub_rej, sub_all = st.tabs([
            f"📌 Awaiting Approval ({len(c_shortlisted)})",
            f"🚀 Active Screening ({len(c_active)})",
            f"🏆 Round 2 Cleared ({len(c_cleared)})",
            f"⏸️ On Hold & Review ({len(c_review_hold)})",
            f"❌ Rejected ({len(c_rejected)})",
            f"🌐 All Candidates Directory ({len(all_cands_pool)})"
        ])

        with sub_pend:
            st.markdown("#### 📌 Candidates Shortlisted from Use Case 1 Awaiting First-Round Approval")
            st.caption("Review candidate resume alignment and click **Approve for First-Round Interview** to generate a candidate-specific interview plan and dispatch an invitation email.")
            if not c_shortlisted:
                st.info("No candidates currently awaiting approval. Ingest new candidate resumes in Tab 1 to match open roles.")
            else:
                for c in c_shortlisted:
                    render_candidate_row_card(c, card_key_prefix="pend")

        with sub_act:
            st.markdown("#### 🚀 Candidates in Active Screening (Invitations Dispatched)")
            st.caption("Candidates who have been approved and invited. You can launch their candidate portal for testing or re-dispatch invitation emails.")
            if not c_active:
                st.info("No candidates currently in active screening.")
            else:
                for c in c_active:
                    render_candidate_row_card(c, card_key_prefix="act")

        with sub_clear:
            st.markdown("#### 🏆 Candidates Who Cleared Round 1 & Were Approved for Round 2")
            st.caption("Candidates whose technical interview evaluations qualified them for final-round team matching. Selection notifications have been dispatched.")
            if not c_cleared:
                st.info("No candidates have cleared Round 1 yet. Complete active interviews and review scorecards in Tab 4.")
            else:
                for c in c_cleared:
                    render_candidate_row_card(c, card_key_prefix="clr")

        with sub_hold:
            st.markdown("#### ⏸️ Candidates On Hold or Under Human Review")
            st.caption("Candidates flagged by the AI for borderline scores or placed on hold by a recruiter.")
            if not c_review_hold:
                st.info("No candidates currently on hold or under review.")
            else:
                for c in c_review_hold:
                    render_candidate_row_card(c, card_key_prefix="hld")

        with sub_rej:
            st.markdown("#### ❌ Rejected Candidates")
            st.caption("Candidates disqualified after review or technical screening. Courteous rejection notifications were dispatched.")
            if not c_rejected:
                st.info("No candidates rejected.")
            else:
                for c in c_rejected:
                    render_candidate_row_card(c, card_key_prefix="rej")

        with sub_all:
            st.markdown("#### 🌐 Comprehensive Candidate Directory")
            f_c1, f_c2, f_c3 = st.columns([1.5, 1.2, 1.2])
            with f_c1:
                search_query = st.text_input("🔍 Search by Candidate Name or Email", value=st.session_state.admin_search, key="dir_search_input")
                st.session_state.admin_search = search_query
            with f_c2:
                all_jobs = get_all_jobs()
                job_choices = ["ALL"] + [j["id"] for j in all_jobs]
                job_labels = {j["id"]: f"{j['title']} ({j['department']})" for j in all_jobs}
                job_labels["ALL"] = "All Positions"
                sel_job = st.selectbox("Filter by Role:", job_choices, format_func=lambda x: job_labels.get(x, x), key="dir_job_select")
                st.session_state.admin_filter_job = sel_job
            with f_c3:
                status_choices = ["ALL", "SHORTLISTED", "FIRST_ROUND_APPROVED", "INVITED", "IN_PROGRESS", "COMPLETED", "HUMAN_REVIEW_REQUIRED", "SECOND_ROUND_APPROVED", "ON_HOLD", "REJECTED", "INVITATION_FAILED"]
                sel_status = st.selectbox("Filter by Status:", status_choices, key="dir_status_select")
                st.session_state.admin_filter_status = sel_status

            candidates = get_candidates_list(
                status_filter=st.session_state.admin_filter_status,
                job_filter=st.session_state.admin_filter_job,
                search=st.session_state.admin_search
            )

            st.caption(f"Showing **{len(candidates)}** candidate(s)")
            for c in candidates:
                render_candidate_row_card(c, card_key_prefix="all")

    # ------------------------------------------------------------------------
    # TAB 3: INTERVIEW PIPELINE KANBAN
    # ------------------------------------------------------------------------
    with tab_pipeline:
        st.markdown("### 📊 Recruitment Workflow Pipeline")
        p_c1, p_c2, p_c3, p_c4, p_c5, p_c6 = st.columns(6)

        stages = [
            ("1. Shortlisted", ["SHORTLISTED"], p_c1),
            ("2. Invited", ["INVITED", "FIRST_ROUND_APPROVED"], p_c2),
            ("3. In Progress", ["IN_PROGRESS"], p_c3),
            ("4. Completed", ["COMPLETED", "HUMAN_REVIEW_REQUIRED"], p_c4),
            ("5. Round 2 Approved", ["SECOND_ROUND_APPROVED"], p_c5),
            ("6. Hold / Rejected", ["ON_HOLD", "REJECTED"], p_c6)
        ]

        all_candidates = get_candidates_list()

        for title, status_list, col in stages:
            with col:
                st.markdown(f"#### {title}")
                stage_cands = [c for c in all_candidates if c["workflow_status"] in status_list]
                st.caption(f"{len(stage_cands)} candidate(s)")

                for sc in stage_cands:
                    border_color = "#10B981" if sc["workflow_status"] == "SECOND_ROUND_APPROVED" else ("#EF4444" if sc["workflow_status"] == "REJECTED" else "#1F2937")
                    st.markdown(f"""
                    <div style="background: #111827; border: 1px solid {border_color}; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                        <strong style="color: #FFFFFF;">{sc['name']}</strong><br>
                        <small style="color: #94A3B8;">{sc['job_title']}</small><br>
                        <span style="color:#38BDF8; font-size:0.75rem; font-weight:bold;">Match: {sc['match_score']}%</span>
                        <div style="font-size:0.72rem; color:#94A3B8; margin-top:4px;">Status: <code>{sc['workflow_status']}</code></div>
                    </div>
                    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # TAB 4: COMPLETED INTERVIEW SCORECARDS & AUDIT (STEP 7 & STEP 8)
    # ------------------------------------------------------------------------
    with tab_scorecards:
        st.markdown("### Step 7 & 8: Review Completed Interviews & Authorize Second Round")
        st.markdown("Inspect objective, evidence-grounded AI evaluations. Recruiter decisions include **Approve for Second Round**, **Put Under Review**, **On Hold**, and **Reject**.")

        with st.expander("🧠 Verifiable Python Tool Execution Inspector (For Evaluators)", expanded=False):
            st.caption("Inspect live Python function invocations: `evaluate_answer()`, `search_resume_claims()`, `validate_score_evidence()`, and `check_competency_coverage()`.")
            logs = get_activity_logs()
            if not logs:
                st.info("Tool executions appear here in real-time as candidate answers are evaluated.")
            else:
                for log in reversed(logs[-10:]):
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

        # Find all candidates with completed scorecards
        completed_cands = [c for c in get_candidates_list() if c.get("overall_score") is not None or c["workflow_status"] in ("COMPLETED", "HUMAN_REVIEW_REQUIRED", "SECOND_ROUND_APPROVED", "ON_HOLD", "REJECTED")]

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
                        rt_sec = t.get("response_time_seconds") or 42
                        with st.expander(f"Q#{t['question_id']}: {t['competency']} (Score: {t['score']}/5 | ⏱️ {rt_sec}s)", expanded=False):
                            st.markdown(f"**Question:** {t['question_text']}")
                            st.markdown(f"⏱️ **Candidate Response Time:** `{rt_sec} seconds` / 60s limit (Recorded by Real-Time Countdown)")
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

                    # Step 8 Actions: Recruiter Decision & Advancement
                    st.markdown("#### ⚖️ Human Recruiter Decision & Advancement")
                    cand_status = cand["workflow_status"]

                    if cand_status == "SECOND_ROUND_APPROVED":
                        st.markdown(f"""
                        <div style="background: rgba(16, 185, 129, 0.12); border: 2px solid #10B981; border-radius: 10px; padding: 18px; margin: 12px 0;">
                            <div style="display: flex; align-items: center; gap: 14px;">
                                <span style="font-size: 2.2rem;">🎉</span>
                                <div>
                                    <h3 style="color: #10B981; margin: 0 0 4px 0;">Cleared Round 1 — Approved for Second Round!</h3>
                                    <p style="color: #E2E8F0; margin: 0; font-size: 0.95rem;">
                                        Candidate has cleared first-round technical screening. Official Round 2 selection email has been dispatched to <strong>{cand['email']}</strong>.
                                    </p>
                                    <p style="color: #94A3B8; margin: 6px 0 0 0; font-size: 0.85rem;">
                                        🔒 <em>Candidate has cleared the first round; 'On Hold' and 'Reject' options are permanently disabled.</em>
                                    </p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    elif cand_status == "REJECTED":
                        st.markdown(f"""
                        <div style="background: rgba(239, 68, 68, 0.12); border: 2px solid #EF4444; border-radius: 10px; padding: 18px; margin: 12px 0;">
                            <div style="display: flex; align-items: center; gap: 14px;">
                                <span style="font-size: 2.2rem;">❌</span>
                                <div>
                                    <h3 style="color: #F87171; margin: 0 0 4px 0;">Application Rejected</h3>
                                    <p style="color: #E2E8F0; margin: 0; font-size: 0.95rem;">
                                        Candidate status is marked as Rejected. A formal, courteous update email was dispatched to <strong>{cand['email']}</strong>.
                                    </p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    else:
                        if cand_status == "HUMAN_REVIEW_REQUIRED":
                            st.info("⚠️ This candidate is currently marked as **Under Human Review** pending recruiter review.")
                        elif cand_status == "ON_HOLD":
                            st.warning("⏸️ This candidate is currently **On Hold** in the recruitment pipeline.")

                        st.markdown("<p style='color:#94A3B8; font-size:0.9rem;'>Select recruiter advancement action for this candidate:</p>", unsafe_allow_html=True)

                        c_act1, c_act2, c_act3, c_act4 = st.columns(4)

                        with c_act1:
                            if st.button(f"🎉 Approve Round 2", key=f"round2_{cand['id']}", type="primary", use_container_width=True):
                                with st.spinner("Authorizing Round 2 & dispatching selection email..."):
                                    r2_res = approve_for_second_round(cand["id"], reviewer="Admin")
                                    if r2_res.get("status") in ("success", "info"):
                                        st.session_state.toast_msg = f"Approved {cand['name']} for Second Round! Selection email dispatched to {cand['email']}."
                                        st.rerun()
                                    else:
                                        st.error(r2_res.get("message", "Error approving candidate."))

                        with c_act2:
                            if st.button(f"⚠️ Put Under Review", key=f"rev_{cand['id']}", use_container_width=True):
                                with st.spinner("Marking candidate under review..."):
                                    rev_res = mark_candidate_under_review(cand["id"], reviewer="Admin", notes="Recruiter requested additional human review.")
                                    if rev_res.get("status") == "success":
                                        st.session_state.toast_msg = f"{cand['name']} marked as Under Human Review."
                                        st.rerun()
                                    else:
                                        st.error(rev_res.get("message", "Error updating status."))

                        with c_act3:
                            if cand_status == "ON_HOLD":
                                st.button("⏸️ Already On Hold", key=f"held_{cand['id']}", disabled=True, use_container_width=True)
                            else:
                                if st.button(f"⏸️ Place on Hold", key=f"hold_{cand['id']}", use_container_width=True):
                                    with st.spinner("Placing candidate on hold..."):
                                        h_res = place_candidate_on_hold(cand["id"], reviewer="Admin", notes="Recruiter placed candidate on hold.")
                                        if h_res.get("status") == "success":
                                            st.session_state.toast_msg = f"Candidate {cand['name']} placed on hold."
                                            st.rerun()
                                        else:
                                            st.error(h_res.get("message", "Error placing candidate on hold."))

                        with c_act4:
                            if st.button(f"❌ Reject Candidate", key=f"rej_{cand['id']}", use_container_width=True):
                                with st.spinner("Rejecting candidate & dispatching courteous email..."):
                                    rej_res = reject_candidate(cand["id"], reviewer="Admin", notes="Rejected based on interview evaluation.")
                                    if rej_res.get("status") == "success":
                                        st.session_state.toast_msg = f"Candidate {cand['name']} rejected. Courteous notification dispatched to {cand['email']}."
                                        st.rerun()
                                    else:
                                        st.error(rej_res.get("message", "Error rejecting candidate."))

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
