"""
InterviewPilot AI — Complete Talent Acquisition & Agentic Screening System
Features:
1. Admin Portal:
   - Sourced & shortlisted candidate profiles organized by Role Buckets (Software Engineer, DevOps, AI/ML, etc.)
   - Match score analysis & claim summaries
   - Admin Approval workflow with automated Gmail dispatching to candidate email (e.g. sukrit.ss.31@gmail.com)
   - Live Email Dispatch Terminal with full rendered HTML previews & credentials
   - Completed Interview Audit & Scorecards review
   - Sourcing Agent for uploading and auto-classifying new resumes
2. Candidate Interview Gateway:
   - Protected login requiring Candidate Access ID and Passcode (received via Gmail invitation)
   - 1-click Quick-Fill for instant demonstration
   - Personalized first-round screening interview with resume-aware questions
   - Real-time adaptive follow-ups, observable tool execution, Plotly visualizations, and scorecard export.
"""

import streamlit as st
import os
import json
from datetime import datetime

from resume_parser import parse_resume, extract_text_from_pdf, StructuredResume
from tools import get_activity_logs, clear_activity_logs
from agent import InterviewPilotAgent, TARGET_COMPETENCIES
from report_generator import (
    compute_overall_score,
    create_competency_radar_chart,
    create_competency_bar_chart,
    generate_candidate_feedback_letter,
    generate_markdown_report
)
from demo_data import SYNTHETIC_RESUME_TEXT, SYNTHETIC_JD_TEXT, SAMPLE_RESPONSES
from pipeline_manager import (
    get_all_roles,
    get_role_definition,
    get_candidates,
    get_candidate_by_id,
    approve_candidate,
    authenticate_candidate,
    record_interview_completion,
    shortlist_uploaded_resume,
    CandidateProfile
)
from notification_service import get_dispatch_logs, send_interview_invitation


# Page Configuration
st.set_page_config(
    page_title="TalentPilot AI — Agentic Screening & Hiring System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Dark Navy SaaS Styling
CUSTOM_CSS = """
<style>
    /* Dark Navy Background & Global Palette */
    .stApp {
        background-color: #070B14;
        color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0D1527;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Glassmorphic Cards */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(8px);
    }

    .candidate-card {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.85) 0%, rgba(20, 27, 45, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 16px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .candidate-card:hover {
        border-color: rgba(0, 240, 255, 0.4);
    }

    .question-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%);
        border: 1px solid rgba(0, 240, 255, 0.3);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 0 25px rgba(0, 240, 255, 0.08);
    }

    .followup-card {
        background: linear-gradient(135deg, rgba(46, 16, 101, 0.4) 0%, rgba(30, 27, 75, 0.6) 100%);
        border: 1px solid rgba(168, 85, 247, 0.4);
        border-radius: 14px;
        padding: 20px;
        margin-top: 15px;
        margin-bottom: 20px;
    }

    /* Badge Pills */
    .badge-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-cyan {
        background: rgba(0, 240, 255, 0.15);
        color: #00F0FF;
        border: 1px solid rgba(0, 240, 255, 0.3);
    }
    .badge-purple {
        background: rgba(168, 85, 247, 0.15);
        color: #C084FC;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    .badge-amber {
        background: rgba(245, 158, 11, 0.15);
        color: #FCD34D;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .badge-green {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    /* Activity Log Item */
    .activity-item {
        background: rgba(15, 23, 42, 0.6);
        border-left: 3px solid #00F0FF;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
        font-size: 0.85rem;
    }

    /* Stat Box */
    .metric-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .metric-val {
        font-size: 2rem;
        font-weight: 800;
        color: #00F0FF;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }

    /* Skill Chip */
    .skill-chip {
        display: inline-block;
        background: rgba(255, 255, 255, 0.06);
        color: #E2E8F0;
        font-size: 0.8rem;
        padding: 3px 10px;
        border-radius: 6px;
        margin: 2px 4px 2px 0;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Initialize Session State
if "portal_view" not in st.session_state:
    st.session_state.portal_view = "Admin Portal"

if "authenticated_candidate" not in st.session_state:
    st.session_state.authenticated_candidate = None

if "agent" not in st.session_state:
    st.session_state.agent = InterviewPilotAgent()

if "candidate_answer_input" not in st.session_state:
    st.session_state.candidate_answer_input = ""

if "candidate_followup_input" not in st.session_state:
    st.session_state.candidate_followup_input = ""

if "approval_message" not in st.session_state:
    st.session_state.approval_message = None


agent: InterviewPilotAgent = st.session_state.agent


# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================
with st.sidebar:
    st.markdown("### 🤖 TALENTPILOT AI")
    st.caption("Autonomous Technical Screening & Hiring Agent")
    st.markdown("---")

    # Portal Selector
    st.markdown("#### 🌐 Active Gateway")
    selected_view = st.radio(
        "Select Portal",
        ["🛡️ Admin & Recruiter Portal", "🎓 Candidate Interview Gateway"],
        index=0 if st.session_state.portal_view == "Admin Portal" else 1
    )

    if selected_view == "🛡️ Admin & Recruiter Portal" and st.session_state.portal_view != "Admin Portal":
        st.session_state.portal_view = "Admin Portal"
        st.rerun()
    elif selected_view == "🎓 Candidate Interview Gateway" and st.session_state.portal_view != "Candidate Portal":
        st.session_state.portal_view = "Candidate Portal"
        st.rerun()

    st.markdown("---")

    if st.session_state.portal_view == "Admin Portal":
        st.markdown("#### ⚡ 1-Click Presenter Shortcut")
        if st.button("🚀 Auto-Approve & Launch Sukrit", use_container_width=True, type="primary"):
            # Auto approve Sukrit
            res = approve_candidate("CAND-SE-8109")
            sukrit_profile = res["candidate"]
            st.session_state.authenticated_candidate = sukrit_profile

            # Initialize agent for Sukrit
            parsed_resume = parse_resume(sukrit_profile.resume_text)
            role_def = get_role_definition(sukrit_profile.role)
            agent.reset_interview()
            agent.plan_interview(parsed_resume, role_def["description"])

            st.session_state.portal_view = "Candidate Portal"
            st.success(f"Approved {sukrit_profile.name} & launched interview!")
            st.rerun()

    else:
        # Candidate Portal Sidebar info
        if st.session_state.authenticated_candidate:
            c = st.session_state.authenticated_candidate
            st.markdown(f"**Candidate:** `{c.name}`")
            st.markdown(f"**Target Role:** `{c.role}`")
            st.markdown(f"**Progress:** `{agent.state.current_index}/{len(agent.state.questions)} Questions`")
            st.markdown(f"**Status:** `{agent.state.status}`")

            if st.button("🚪 Logout Candidate", use_container_width=True):
                st.session_state.authenticated_candidate = None
                st.session_state.portal_view = "Admin Portal"
                st.rerun()

    st.markdown("---")
    st.caption("🔒 100% Offline Rule-Based Agentic Engine. No paid API key required.")


# ============================================================================
# VIEW 1: RECRUITER & ADMIN PORTAL
# ============================================================================
if st.session_state.portal_view == "Admin Portal":
    st.markdown("## 🛡️ Recruiter & Talent Acquisition Dashboard")
    st.markdown("AI-driven talent sourcing, multi-role shortlisting, candidate approvals, and automated Gmail interview dispatching.")

    all_cands = get_candidates()
    total_shortlisted = len(all_cands)
    total_approved = sum(1 for c in all_cands if "Approved" in c.status or "Completed" in c.status)
    total_completed = sum(1 for c in all_cands if c.status == "Interview Completed")

    # Top KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{len(get_all_roles())}</div>
            <div class="metric-label">Active Recruiting Roles</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{total_shortlisted}</div>
            <div class="metric-label">AI Shortlisted Profiles</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val" style="color:#A855F7;">{total_approved}</div>
            <div class="metric-label">Invitations Dispatched</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val" style="color:#10B981;">{total_completed}</div>
            <div class="metric-label">Completed Interviews</div>
        </div>
        """, unsafe_allow_html=True)

    # Show approval banner if recent
    if st.session_state.approval_message:
        msg = st.session_state.approval_message
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 10px; padding: 16px 20px; margin: 18px 0;">
            <h4 style="color:#34D399; margin: 0 0 6px 0;">🎉 {msg['headline']}</h4>
            <p style="margin: 0; color: #E2E8F0; font-size: 0.95rem;">
                Official invitation sent to: <strong>{msg['email']}</strong> | Access ID: <code>{msg['access_id']}</code> | Passcode: <code>{msg['access_code']}</code>
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Admin Tabs
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "🗂️ Candidate Role Buckets & Approvals",
        "📨 Live Email Dispatch Terminal",
        "📊 Completed Interview Audits",
        "➕ Sourcing AI & Resume Ingestion"
    ])

    # ------------------------------------------------------------------------
    # TAB 1: Role Buckets & Candidate Cards
    # ------------------------------------------------------------------------
    with admin_tab1:
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            role_options = ["All Roles"] + get_all_roles()
            selected_role = st.selectbox("Filter by Profile Role Bucket:", role_options, index=0)

        candidates_to_display = get_candidates(selected_role)
        st.caption(f"Showing {len(candidates_to_display)} candidate(s) under **{selected_role}**")

        for cand in candidates_to_display:
            skills_html = "".join([f'<span class="skill-chip">{s}</span>' for s in cand.skills])
            status_badge = "badge-green" if "Completed" in cand.status else ("badge-purple" if "Approved" in cand.status else "badge-cyan")

            with st.container():
                st.markdown(f"""
                <div class="candidate-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <span class="badge-pill {status_badge}">{cand.status}</span>
                            <span class="badge-pill badge-cyan" style="margin-left: 8px;">{cand.role}</span>
                            <h3 style="margin: 10px 0 4px 0; color: #FFFFFF; font-size: 1.4rem;">{cand.name}</h3>
                            <p style="margin: 0; color: #94A3B8; font-size: 0.9rem;">
                                📧 {cand.email} • 💼 {cand.experience_years} Years Experience • ID: <code>{cand.id}</code>
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #00F0FF;">{cand.match_score}%</div>
                            <div style="font-size: 0.75rem; color: #94A3B8; text-transform: uppercase;">Role Match Score</div>
                        </div>
                    </div>
                    <div style="margin: 14px 0 8px 0;">
                        <small style="color:#94A3B8; text-transform:uppercase; font-size:0.75rem; font-weight:bold;">Matched Competencies & Skills:</small><br>
                        {skills_html}
                    </div>
                    <p style="font-size: 0.95rem; color: #CBD5E1; line-height: 1.5; margin: 10px 0;">
                        <strong>Agentic Sourcing Summary:</strong> {cand.resume_summary}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                c_btn1, c_btn2, c_btn3 = st.columns([1.4, 1.2, 1.2])

                with c_btn1:
                    if cand.status == "Shortlisted":
                        if st.button(f"✅ Approve & Send Gmail to {cand.name.split()[0]}", key=f"app_{cand.id}", type="primary", use_container_width=True):
                            res = approve_candidate(cand.id)
                            st.session_state.approval_message = {
                                "headline": f"Candidate Approved: {cand.name}",
                                "email": cand.email,
                                "access_id": res["access_id"],
                                "access_code": res["access_code"]
                            }
                            st.rerun()
                    else:
                        st.info(f"🔑 Passcode: `{cand.access_code}` | Sent: `{cand.invitation_sent_at}`")

                with c_btn2:
                    if cand.status != "Shortlisted":
                        if st.button(f"🚀 Launch Interview ({cand.name.split()[0]})", key=f"launch_{cand.id}", use_container_width=True):
                            st.session_state.authenticated_candidate = cand
                            parsed = parse_resume(cand.resume_text)
                            role_def = get_role_definition(cand.role)
                            agent.reset_interview()
                            agent.plan_interview(parsed, role_def["description"])
                            st.session_state.portal_view = "Candidate Portal"
                            st.rerun()

                with c_btn3:
                    with st.popover("📄 View Resume Claims"):
                        st.markdown(f"### {cand.name} — Full Resume")
                        st.text_area("Resume Content", value=cand.resume_text, height=280)

                st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # TAB 2: Live Email Dispatch Terminal
    # ------------------------------------------------------------------------
    with admin_tab2:
        st.markdown("### 📨 Automated Email Dispatch Terminal")
        st.caption("Live audit trail of all invitation emails sent to shortlisted candidates (with generated credentials).")

        logs = get_dispatch_logs()
        if not logs:
            st.info("No invitation emails dispatched yet. Click 'Approve & Send Gmail' on any shortlisted candidate in Tab 1.")
        else:
            for log in reversed(logs):
                with st.expander(f"✉️ {log['subject']} ➔ {log['recipient_email']} ({log['timestamp']})", expanded=True):
                    col_m1, col_m2 = st.columns([1, 1])
                    with col_m1:
                        st.markdown(f"**Recipient:** `{log['recipient_name']} <{log['recipient_email']}>`")
                        st.markdown(f"**Target Role:** `{log['role']}`")
                        st.markdown(f"**Generated Access ID:** ` {log['access_id']} `")
                        st.markdown(f"**Generated Passcode:** ` {log['access_code']} `")
                        st.markdown(f"**Delivery Status:** `{log['smtp_status']}`")
                    with col_m2:
                        st.markdown("**Rendered Email Preview:**")
                        st.components.v1.html(log["html_content"], height=320, scrolling=True)

    # ------------------------------------------------------------------------
    # TAB 3: Completed Interview Audits
    # ------------------------------------------------------------------------
    with admin_tab3:
        st.markdown("### 📊 Completed Interview Scorecards & Recruiter Audit")
        completed_cands = [c for c in get_candidates() if c.status == "Interview Completed"]

        if not completed_cands:
            st.info("No candidates have completed their first-round interview yet. Launch an interview from Tab 1 to test the full lifecycle.")
        else:
            for c in completed_cands:
                card = c.interview_scorecard or {}
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display:flex; justify-content:space-between;">
                        <div>
                            <h3>{c.name} ({c.role})</h3>
                            <p>Email: {c.email} | Overall Score: <strong style="color:#00F0FF;">{card.get('overall_score', 'N/A')}/5.0</strong></p>
                        </div>
                        <div>
                            <span class="badge-pill badge-green">{card.get('recommendation', 'COMPLETED')}</span>
                        </div>
                    </div>
                    <p style="color:#94A3B8; font-size:0.9rem;">{card.get('rec_desc', '')}</p>
                </div>
                """, unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # TAB 4: Sourcing AI & Ingestion
    # ------------------------------------------------------------------------
    with admin_tab4:
        st.markdown("### ➕ Sourcing Agent: Ingest & Auto-Classify New Resume")
        st.markdown("Upload a PDF resume or paste raw text. The Sourcing AI will parse skills, calculate the role match score, and bucket the candidate automatically.")

        in_c1, in_c2 = st.columns(2)
        with in_c1:
            new_name = st.text_input("Candidate Full Name", placeholder="e.g. Maya Lin")
            new_email = st.text_input("Candidate Email (Gmail)", placeholder="e.g. maya.lin@gmail.com")
            target_role = st.selectbox("Target Profile Role", get_all_roles())

        with in_c2:
            new_pdf = st.file_uploader("Upload Candidate Resume (PDF)", type=["pdf"])
            new_text = st.text_area("Or Paste Resume Text", height=150, placeholder="Paste resume plain text here...")

        if st.button("🚀 Ingest & Shortlist Candidate via AI", type="primary"):
            raw_resume = ""
            if new_pdf:
                raw_resume = extract_text_from_pdf(new_pdf.read())
            elif new_text:
                raw_resume = new_text

            if raw_resume:
                new_cand = shortlist_uploaded_resume(new_name, new_email, target_role, raw_resume)
                st.success(f"Candidate {new_cand.name} successfully shortlisted under {new_cand.role} with a Match Score of {new_cand.match_score}%!")
                st.rerun()
            else:
                st.warning("Please upload a PDF or enter resume text.")


# ============================================================================
# VIEW 2: CANDIDATE INTERVIEW GATEWAY (ID & PASSCODE PROTECTED)
# ============================================================================
elif st.session_state.portal_view == "Candidate Portal":
    # ------------------------------------------------------------------------
    # STAGE A: Login Gateway
    # ------------------------------------------------------------------------
    if not st.session_state.authenticated_candidate:
        st.markdown("## 🔐 Candidate First-Round Screening Gateway")
        st.markdown("Please enter the unique **Access ID** and **Passcode** that were delivered to your Gmail inbox.")

        gate_col1, gate_col2 = st.columns([1.2, 1])

        with gate_col1:
            st.markdown("""
            <div class="glass-card">
                <h3 style="color:#00F0FF; margin-top:0;">Secure Candidate Login</h3>
                <p style="color:#94A3B8; font-size:0.9rem;">
                    Your credentials were automatically generated and sent upon recruiter approval.
                </p>
            </div>
            """, unsafe_allow_html=True)

            login_id = st.text_input("Candidate Access ID or Gmail Address", placeholder="e.g. CAND-SE-8109 or sukrit.ss.31@gmail.com")
            login_pass = st.text_input("Interview Access Passcode", type="password", placeholder="e.g. PILOT-XXXX")

            # Quick-Fill Helper for effortless presentations
            st.markdown("**⚡ Live Demo Quick-Credentials:**")
            if st.button("⚡ Quick-Fill Sukrit's Approved Credentials", use_container_width=True):
                # Ensure Sukrit is approved
                approve_res = approve_candidate("CAND-SE-8109")
                st.session_state.authenticated_candidate = approve_res["candidate"]

                # Initialize interview agent for Sukrit
                cand = st.session_state.authenticated_candidate
                parsed = parse_resume(cand.resume_text)
                role_def = get_role_definition(cand.role)
                agent.reset_interview()
                agent.plan_interview(parsed, role_def["description"])

                st.success(f"Authenticated as {cand.name}! Entering interview room...")
                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔓 Authenticate & Begin Interview", type="primary", use_container_width=True):
                matched_cand = authenticate_candidate(login_id, login_pass)
                if matched_cand:
                    st.session_state.authenticated_candidate = matched_cand
                    parsed = parse_resume(matched_cand.resume_text)
                    role_def = get_role_definition(matched_cand.role)
                    agent.reset_interview()
                    agent.plan_interview(parsed, role_def["description"])
                    st.success(f"Welcome, {matched_cand.name}! Launching your interview...")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please verify your Access ID and Passcode from your Gmail invitation.")

        with gate_col2:
            st.markdown("""
            <div class="glass-card">
                <h4>📋 What to Expect:</h4>
                <p style="color:#CBD5E1; font-size:0.9rem; line-height: 1.6;">
                    • <strong>Resume-Anchored Probing:</strong> The AI will ask about specific technical projects and metrics from your CV.<br>
                    • <strong>Adaptive Follow-ups:</strong> If a response lacks depth, the agent will prompt for technical specifics.<br>
                    • <strong>Zero Hallucination:</strong> Your scores are grounded in verbatim quotes from your answers.<br>
                    • <strong>Recruiter Review:</strong> All results are submitted for final human recruiter evaluation.
                </p>
            </div>
            """, unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # STAGE B: Active Interview Room
    # ------------------------------------------------------------------------
    else:
        cand: CandidateProfile = st.session_state.authenticated_candidate

        st.markdown(f"## 🎙️ Screening Room: <span style='color:#00F0FF;'>{cand.name}</span>", unsafe_allow_html=True)
        st.caption(f"Role: **{cand.role}** • Email: `{cand.email}` • Access ID: `{cand.id}`")

        curr_q = agent.get_current_question()

        # Two Columns: Left = Chat / Q&A, Right = Live Agent Activity
        q_col, act_col = st.columns([1.6, 1.0])

        with q_col:
            # Progress Bar
            progress_val = min(1.0, agent.state.current_index / max(1, len(agent.state.questions)))
            st.progress(progress_val)
            st.caption(f"Question {min(agent.state.current_index + 1, len(agent.state.questions))} of {len(agent.state.questions)} • Domain: **{curr_q.competency if curr_q else 'Session Concluded'}**")

            # 1. When all questions are done
            if agent.state.status == "COMPLETED":
                st.success("🎉 All interview questions completed! Your scorecard has been submitted for recruiter review.")

                score_data = compute_overall_score(agent.state)
                record_interview_completion(cand.id, score_data)

                st.markdown(f"""
                <div class="glass-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h3>Overall Screening Rating: <span style="color:#00F0FF;">{score_data['overall_score']} / 5.0</span></h3>
                            <p style="color:#94A3B8; margin:0;">Recommendation: <strong style="color:{score_data['rec_color']}">{score_data['recommendation']}</strong></p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Radar chart
                st.markdown("#### 🕸️ Competency Benchmark Radar")
                radar = create_competency_radar_chart(score_data["competency_scores"])
                st.plotly_chart(radar, use_container_width=True)

                # Candidate Feedback Letter
                st.markdown("#### ✉️ Candidate Feedback Letter Draft")
                feedback_letter = generate_candidate_feedback_letter(agent.state, score_data["overall_score"])
                st.text_area("Official Feedback", value=feedback_letter, height=200)

                down_c1, down_c2 = st.columns(2)
                with down_c1:
                    full_md = generate_markdown_report(agent.state)
                    st.download_button(
                        label="📄 Download Full Scorecard (.md)",
                        data=full_md,
                        file_name=f"Scorecard_{cand.name.replace(' ', '_')}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                with down_c2:
                    if st.button("⬅️ Return to Admin Portal", use_container_width=True):
                        st.session_state.portal_view = "Admin Portal"
                        st.rerun()

            # 2. When an active question is displayed
            elif curr_q:
                st.markdown(f"""
                <div class="question-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="badge-pill badge-cyan">{curr_q.competency}</span>
                        <span class="badge-pill badge-purple">Adaptive Level: {agent.state.current_difficulty.upper()}</span>
                    </div>
                    <h3 style="margin-top: 14px; color: #FFFFFF;">Question #{curr_q.id}</h3>
                    <p style="font-size: 1.15rem; line-height: 1.6; color: #F1F5F9;">{curr_q.text}</p>
                    <div style="background: rgba(0,0,0,0.25); padding: 10px 14px; border-radius: 8px; border-left: 2px solid #00F0FF; margin-top: 12px;">
                        <small style="color: #94A3B8;">Targeted Resume Claim: <em>"{curr_q.targeted_resume_claim}"</em></small>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Adaptive follow-up probe mode
                if agent.state.status == "AWAITING_FOLLOWUP":
                    st.markdown(f"""
                    <div class="followup-card">
                        <span class="badge-pill badge-amber">⚡ Adaptive Agent Follow-up Probe</span>
                        <h4 style="margin-top: 10px; color: #FCD34D;">Agent Detected Shallow Answer</h4>
                        <p style="font-size: 1.05rem; color: #F1F5F9;">{agent.state.active_followup}</p>
                        <small style="color: #CBD5E1;">Please provide specific technical depth, metrics, or trade-offs to address this probe.</small>
                    </div>
                    """, unsafe_allow_html=True)

                    f_ans = st.text_area(
                        "Candidate Follow-up Response",
                        value=st.session_state.candidate_followup_input,
                        height=130,
                        placeholder="Provide additional architectural details, specific libraries, or trade-offs..."
                    )

                    cf1, cf2 = st.columns(2)
                    with cf1:
                        if st.button("⚡ Quick-Fill Strong Follow-up Answer", use_container_width=True):
                            st.session_state.candidate_followup_input = SAMPLE_RESPONSES["strong"]["text"]
                            st.rerun()
                    with cf2:
                        if st.button("🚀 Submit Follow-up Answer", type="primary", use_container_width=True):
                            if f_ans.strip():
                                agent.submit_answer(f_ans)
                                st.session_state.candidate_followup_input = ""
                                st.rerun()

                else:
                    c_ans = st.text_area(
                        "Your Answer",
                        value=st.session_state.candidate_answer_input,
                        height=140,
                        placeholder="Type or paste your technical answer here..."
                    )

                    st.markdown("**⚡ Live Presentation Controls:**")
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("⚠️ Test Shallow Answer (Triggers Follow-up Probe)", use_container_width=True):
                            st.session_state.candidate_answer_input = SAMPLE_RESPONSES["shallow"]["text"]
                            st.rerun()
                    with b2:
                        if st.button("✅ Test Strong Answer (Advances with Score 5)", use_container_width=True):
                            st.session_state.candidate_answer_input = SAMPLE_RESPONSES["strong"]["text"]
                            st.rerun()

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("📤 Submit Answer to Agent", type="primary", use_container_width=True):
                        if c_ans.strip():
                            agent.submit_answer(c_ans)
                            st.session_state.candidate_answer_input = ""
                            st.rerun()

        # Right Column: Real-Time Tool Calls & Activity
        with act_col:
            st.markdown("### 🧠 Live Agent Activity Panel")
            st.caption("Real-time Python tool executions & agent decisions:")

            logs = get_activity_logs()
            if not logs:
                st.info("No tool calls recorded yet. Submit an answer to view real-time agent tool invocations.")
            else:
                for log in reversed(logs[-8:]):
                    st.markdown(f"""
                    <div class="activity-item">
                        <div style="display:flex; justify-content:space-between; color:#94A3B8; font-size:0.75rem;">
                            <span>⚙️ <strong>{log.tool_name}()</strong></span>
                            <span>{log.timestamp} ({log.execution_ms}ms)</span>
                        </div>
                        <div style="color: #00F0FF; font-weight:600; margin: 4px 0;">{log.result_summary}</div>
                        <div style="color: #CBD5E1; font-size: 0.8rem;"><em>Reasoning:</em> {log.agent_reasoning}</div>
                    </div>
                    """, unsafe_allow_html=True)
