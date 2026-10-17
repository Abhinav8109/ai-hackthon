"""
InterviewPilot AI — Agentic Interview Assistant
Streamlit Application Entrypoint.
A modern, presentation-ready dark navy SaaS interface for automated,
adaptive first-round technical screening interviews.
"""

import streamlit as st
import os
import json

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


# Page Configuration
st.set_page_config(
    page_title="InterviewPilot AI — Agentic Screening Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Dark Navy SaaS Styling
CUSTOM_CSS = """
<style>
    /* Dark Navy Background & Global Palette */
    .stApp {
        background-color: #080D1A;
        color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0D1527;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(8px);
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
        font-weight: 600;
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

    /* Activity Log Item */
    .activity-item {
        background: rgba(15, 23, 42, 0.6);
        border-left: 3px solid #00F0FF;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
        font-size: 0.85rem;
    }

    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    /* Stat Box */
    .metric-card {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 14px;
        text-align: center;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #00F0FF;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #94A3B8;
        text-transform: uppercase;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# Initialize Session State
if "agent" not in st.session_state:
    st.session_state.agent = InterviewPilotAgent()

if "parsed_resume" not in st.session_state:
    st.session_state.parsed_resume = None

if "job_description" not in st.session_state:
    st.session_state.job_description = ""

if "answer_input" not in st.session_state:
    st.session_state.answer_input = ""

if "followup_input" not in st.session_state:
    st.session_state.followup_input = ""


agent: InterviewPilotAgent = st.session_state.agent


# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("### 🤖 InterviewPilot AI")
    st.caption("Agentic First-Round Screening Assistant")
    st.markdown("---")

    # Mode Selector
    app_mode = st.radio(
        "Navigation / Workflow",
        ["1. Setup & Planner", "2. Interactive Interview", "3. Final Scorecard & Audit"],
        index=0 if agent.state.status == "READY" else (1 if agent.state.status in ["IN_PROGRESS", "AWAITING_FOLLOWUP"] else 2)
    )

    st.markdown("---")
    st.markdown("#### ⚙️ Configuration")
    demo_btn = st.button("⚡ Load 1-Click Synthetic Demo", use_container_width=True, type="primary")

    if demo_btn:
        st.session_state.parsed_resume = parse_resume(SYNTHETIC_RESUME_TEXT)
        st.session_state.job_description = SYNTHETIC_JD_TEXT
        agent.reset_interview()
        agent.plan_interview(st.session_state.parsed_resume, st.session_state.job_description)
        st.success("Loaded Alex Chen (Senior AI Engineer) Demo!")
        st.rerun()

    # Reset Button
    if st.button("🔄 Reset Interview", use_container_width=True):
        agent.reset_interview()
        st.session_state.parsed_resume = None
        st.session_state.job_description = ""
        st.session_state.answer_input = ""
        st.session_state.followup_input = ""
        st.rerun()

    st.markdown("---")
    st.markdown("#### 📊 Session Overview")
    if agent.state.questions:
        st.markdown(f"**Candidate:** `{agent.state.candidate_name}`")
        st.markdown(f"**Progress:** `{agent.state.current_index}/{len(agent.state.questions)} Questions`")
        st.markdown(f"**Difficulty Level:** `{agent.state.current_difficulty.upper()}`")
        st.markdown(f"**Agent Status:** `{agent.state.status}`")
    else:
        st.info("No active interview session. Load the 1-click demo or upload a resume to begin.")

    st.markdown("---")
    st.caption("🔒 100% Offline Rule-Based Agentic Engine. No paid API key required.")


# ============================================================================
# PAGE 1: SETUP & INTERVIEW PLANNER
# ============================================================================
if app_mode == "1. Setup & Planner":
    st.markdown("## 🎯 Candidate & Job Description Setup")
    st.markdown("Upload a candidate resume (PDF or text) and target Job Description. The **Planner Agent** will analyze claims and synthesize an adaptive 5-question interview agenda.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 📄 Candidate Resume")
        resume_upload = st.file_uploader("Upload Candidate Resume (PDF)", type=["pdf"])

        resume_text_input = st.text_area(
            "Or Paste Resume Plain Text",
            value=st.session_state.parsed_resume.raw_text if st.session_state.parsed_resume else "",
            height=260,
            placeholder="Paste raw resume text here..."
        )

        if resume_upload is not None:
            try:
                extracted_pdf_text = extract_text_from_pdf(resume_upload.read())
                st.session_state.parsed_resume = parse_resume(extracted_pdf_text)
                st.success(f"Successfully parsed PDF: {resume_upload.name}")
            except Exception as e:
                st.error(f"Error parsing PDF: {e}")

        elif resume_text_input and (not st.session_state.parsed_resume or st.session_state.parsed_resume.raw_text != resume_text_input):
            st.session_state.parsed_resume = parse_resume(resume_text_input)

    with col2:
        st.markdown("#### 📋 Target Job Description (JD)")
        jd_input = st.text_area(
            "Job Description & Role Requirements",
            value=st.session_state.job_description,
            height=320,
            placeholder="Paste job description requirements, responsibilities, and qualifications..."
        )
        st.session_state.job_description = jd_input

    # Plan Generation Action
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state.parsed_resume and st.session_state.job_description:
        # Display Candidate Metadata Preview
        r = st.session_state.parsed_resume
        st.markdown(f"""
        <div class="glass-card">
            <h4>👤 Extracted Profile: <span style="color:#00F0FF;">{r.candidate_name}</span> ({r.title})</h4>
            <p><strong>Years Experience:</strong> ~{r.years_experience} Years | <strong>Email:</strong> {r.email or 'N/A'}</p>
            <p><strong>Skills Identified:</strong> {' • '.join([k for skills in r.skills.values() for k in skills][:10])}...</p>
            <p><strong>Quantifiable Claims Extracted:</strong> {len(r.claims)} verifiable achievement statements.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 Synthesize Agentic Interview Plan", type="primary", use_container_width=True):
            agent.plan_interview(st.session_state.parsed_resume, st.session_state.job_description)
            st.success("✨ Interview plan formulated! Navigating to interactive interview room...")
            st.rerun()

    # If questions already planned, preview them
    if agent.state.questions:
        st.markdown("### 📋 Formulated Interview Agenda")
        for q in agent.state.questions:
            st.markdown(f"""
            <div class="glass-card">
                <span class="badge-pill badge-cyan">{q.competency}</span>
                <span class="badge-pill badge-purple" style="margin-left: 8px;">Difficulty: {q.difficulty.upper()}</span>
                <p style="margin-top: 10px; font-size: 1.05rem;"><strong>Q{q.id}:</strong> {q.text}</p>
                <p style="font-size: 0.85rem; color: #94A3B8;"><strong>Targeted Resume Claim:</strong> <em>"{q.targeted_resume_claim}"</em></p>
            </div>
            """, unsafe_allow_html=True)


# ============================================================================
# PAGE 2: INTERACTIVE INTERVIEW ROOM
# ============================================================================
elif app_mode == "2. Interactive Interview":
    if not agent.state.questions:
        st.warning("⚠️ No active interview plan. Please set up a candidate resume and JD in 'Setup & Planner' or load the 1-click demo.")
        st.stop()

    curr_q = agent.get_current_question()

    # Main Interview Columns: Left = Chat / Q&A, Right = Live Agent Activity Timeline
    chat_col, timeline_col = st.columns([1.6, 1.0])

    with chat_col:
        st.markdown("### 🎙️ Live Interview Workspace")

        # Top Progress Metrics
        progress_val = min(1.0, agent.state.current_index / len(agent.state.questions))
        st.progress(progress_val)
        st.caption(f"Question {min(agent.state.current_index + 1, len(agent.state.questions))} of {len(agent.state.questions)} • Current Competency: **{curr_q.competency if curr_q else 'Completed'}**")

        if agent.state.status == "COMPLETED":
            st.success("🎉 All interview questions completed! Review the comprehensive scorecard in the 'Final Scorecard & Audit' tab.")
            if st.button("📊 View Final Scorecard & Report", type="primary"):
                # Switch tab
                st.session_state.app_mode = "3. Final Scorecard & Audit"
                st.rerun()

        elif curr_q:
            # Active Question Card
            st.markdown(f"""
            <div class="question-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="badge-pill badge-cyan">{curr_q.competency}</span>
                    <span class="badge-pill badge-purple">Adaptive Level: {agent.state.current_difficulty.upper()}</span>
                </div>
                <h3 style="margin-top: 14px; color: #FFFFFF;">Question #{curr_q.id}</h3>
                <p style="font-size: 1.15rem; line-height: 1.6; color: #F1F5F9;">{curr_q.text}</p>
                <div style="background: rgba(0,0,0,0.25); padding: 10px 14px; border-radius: 8px; border-left: 2px solid #00F0FF; margin-top: 12px;">
                    <small style="color: #94A3B8;">Targeting Resume Claim: <em>"{curr_q.targeted_resume_claim}"</em></small>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Follow-up Alert if Active
            if agent.state.status == "AWAITING_FOLLOWUP":
                st.markdown(f"""
                <div class="followup-card">
                    <span class="badge-pill badge-amber">⚡ Adaptive Agent Follow-up Probe</span>
                    <h4 style="margin-top: 10px; color: #FCD34D;">Agent Detected Shallow Answer</h4>
                    <p style="font-size: 1.05rem; color: #F1F5F9;">{agent.state.active_followup}</p>
                    <small style="color: #CBD5E1;">Please provide specific technical depth, metrics, or trade-offs to address this probe.</small>
                </div>
                """, unsafe_allow_html=True)

                followup_ans = st.text_area(
                    "Candidate Follow-up Response",
                    value=st.session_state.followup_input,
                    height=130,
                    key="followup_box",
                    placeholder="Provide additional architectural details, specific libraries, or trade-offs..."
                )

                col_f1, col_f2 = st.columns([1, 1])
                with col_f1:
                    if st.button("⚡ Quick-Fill Strong Follow-up Answer", use_container_width=True):
                        st.session_state.followup_input = SAMPLE_RESPONSES["strong"]["text"]
                        st.rerun()
                with col_f2:
                    if st.button("🚀 Submit Follow-up Answer", type="primary", use_container_width=True):
                        if followup_ans.strip():
                            res = agent.submit_answer(followup_ans)
                            st.session_state.followup_input = ""
                            st.rerun()
                        else:
                            st.warning("Please enter a response before submitting.")

            else:
                # Standard Question Response Input
                candidate_ans = st.text_area(
                    "Candidate Answer",
                    value=st.session_state.answer_input,
                    height=150,
                    key="answer_box",
                    placeholder="Type or paste the candidate's spoken/written answer here..."
                )

                # Quick-test buttons for hackathon judges & presentations
                st.markdown("**⚡ Live Demo Quick-Fill Controls:**")
                btn_c1, btn_c2 = st.columns([1, 1])

                with btn_c1:
                    if st.button("⚠️ Test Shallow Answer (Triggers Follow-up)", use_container_width=True):
                        st.session_state.answer_input = SAMPLE_RESPONSES["shallow"]["text"]
                        st.rerun()

                with btn_c2:
                    if st.button("✅ Test Strong Answer (Advances with Score 5)", use_container_width=True):
                        st.session_state.answer_input = SAMPLE_RESPONSES["strong"]["text"]
                        st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📤 Submit Candidate Answer", type="primary", use_container_width=True):
                    if candidate_ans.strip():
                        res = agent.submit_answer(candidate_ans)
                        st.session_state.answer_input = ""
                        st.rerun()
                    else:
                        st.warning("Please enter a response before submitting.")

    # Timeline Column: Real Agentic Tool Executions
    with timeline_col:
        st.markdown("### 🧠 Live Agent Activity Panel")
        st.caption("Verifiable Python tool calls & execution logs:")

        logs = get_activity_logs()
        if not logs:
            st.info("No tool calls recorded yet. Submit an answer to view real-time agent tool invocations.")
        else:
            # Display logs in reverse chronological order
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


# ============================================================================
# PAGE 3: FINAL SCORECARD & AUDIT
# ============================================================================
elif app_mode == "3. Final Scorecard & Audit":
    st.markdown("## 📊 Comprehensive Interview Scorecard & Recruiter Audit")

    if not agent.state.history:
        st.warning("⚠️ No interview turns recorded yet. Complete at least one question in the 'Interactive Interview' tab.")
        st.stop()

    metrics = compute_overall_score(agent.state)

    # Top KPI Banner
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{metrics['overall_score']} / 5.0</div>
            <div class="metric-label">Weighted Overall Score</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val" style="color: {metrics['rec_color']}; font-size: 1.1rem; padding-top: 6px;">{metrics['recommendation']}</div>
            <div class="metric-label">Recruiter Recommendation</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{len(agent.state.history)}</div>
            <div class="metric-label">Questions Evaluated</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val" style="color: {'#00F0FF' if metrics['clarification_flags'] == 0 else '#FFB020'};">{metrics['clarification_flags']}</div>
            <div class="metric-label">Resume Clarification Flags</div>
        </div>
        """, unsafe_allow_html=True)

    # Human Oversight Alert Banner
    st.markdown("""
    <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 12px 18px; margin: 16px 0;">
        <strong style="color: #FCD34D;">⚠️ Human Oversight Safeguard:</strong>
        <span style="color: #CBD5E1; font-size: 0.9rem;"> All agentic evaluations are decision-support recommendations for human recruiters. No candidate is ever automatically rejected.</span>
    </div>
    """, unsafe_allow_html=True)

    # Charts Row
    chart_c1, chart_c2 = st.columns([1, 1])
    with chart_c1:
        st.markdown("#### 🕸️ Competency Radar Analysis (vs Target 4.0)")
        radar_fig = create_competency_radar_chart(metrics["competency_scores"])
        st.plotly_chart(radar_fig, use_container_width=True)

    with chart_c2:
        st.markdown("#### 📊 Competency Performance Breakdown")
        bar_fig = create_competency_bar_chart(metrics["competency_scores"])
        st.plotly_chart(bar_fig, use_container_width=True)

    st.markdown("---")

    # Detailed Q&A and Evidence Breakdown
    st.markdown("### 🔍 Question-by-Question Rubric & Verbatim Evidence")
    for t in agent.state.history:
        with st.expander(f"Question #{t.question_id}: {t.competency} — Score: {t.final_score}/5", expanded=True):
            col_t1, col_t2 = st.columns([1.2, 1])
            with col_t1:
                st.markdown(f"**Question:** {t.question}")
                st.markdown(f"**Candidate Answer:** *\"{t.answer}\"*")
                if t.followup_question:
                    st.markdown(f"**⚡ Follow-up Probe:** *{t.followup_question}*")
                    st.markdown(f"**Follow-up Answer:** *\"{t.followup_answer}\"*")
            with col_t2:
                st.markdown(f"**Rubric Assessment:** `{t.evaluation.rubric_match}`")
                st.markdown(f"**Verbatim Supporting Evidence:** <span style='color:#00F0FF;'>{t.evaluation.evidence_quote}</span>", unsafe_allow_html=True)
                st.markdown(f"**Strengths:** {t.evaluation.strengths}")
                if t.evaluation.gaps:
                    st.markdown(f"**Gaps / Probing Needed:** <span style='color:#FFB020;'>{t.evaluation.gaps}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # Resume Claim Consistency Table
    st.markdown("### 📑 Resume Claim Verification & Consistency Matrix")
    if agent.state.consistency_findings:
        claim_data = []
        for f in agent.state.consistency_findings:
            claim_data.append({
                "Claim ID": f.claim_id,
                "Resume Statement": f.claim_text,
                "Verification Status": f.status,
                "Analysis & Interview Findings": f.analysis
            })
        st.dataframe(claim_data, use_container_width=True)
    else:
        st.info("Consistency findings compiled at interview completion.")

    # Candidate Feedback Letter Preview
    st.markdown("---")
    st.markdown("### ✉️ Candidate-Facing Feedback Draft")
    feedback_text = generate_candidate_feedback_letter(agent.state, metrics["overall_score"])
    st.text_area("Polite, Constructive Candidate Letter", value=feedback_text, height=200)

    # Download Options
    st.markdown("---")
    st.markdown("### 📥 Export Scorecard & Reports")
    d_c1, d_c2 = st.columns(2)

    with d_c1:
        md_report = generate_markdown_report(agent.state)
        st.download_button(
            label="📄 Download Full Markdown Scorecard (.md)",
            data=md_report,
            file_name=f"InterviewPilot_Scorecard_{agent.state.candidate_name.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )

    with d_c2:
        st.download_button(
            label="✉️ Download Candidate Feedback Note (.txt)",
            data=feedback_text,
            file_name=f"Candidate_Feedback_{agent.state.candidate_name.replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )
