"""
Notification Service for InterviewPilot AI.
Dispatches official interview invitations with secure credentials to candidate email (Gmail).
Supports live SMTP sending if credentials exist in .env, with a 100% reliable
in-app Email Dispatch Terminal / Simulator that logs and previews outgoing emails.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


# In-memory dispatch audit log
DISPATCH_LOGS: List[Dict[str, Any]] = []


def send_interview_invitation(
    candidate_name: str,
    candidate_email: str,
    role_name: str,
    access_id: str,
    access_code: str,
    interview_url: str = "http://localhost:8501"
) -> Dict[str, Any]:
    """
    Sends an official first-round screening invitation email with credentials to the candidate.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"🎯 Selected for First-Round Screening Interview: {role_name} — TalentPilot AI"

    # HTML Email Body
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 20px; }}
        .email-container {{ max-width: 600px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        .header {{ text-align: center; border-bottom: 2px solid #00f0ff; padding-bottom: 20px; margin-bottom: 25px; }}
        .logo {{ font-size: 24px; font-weight: 800; color: #00f0ff; letter-spacing: 1px; }}
        .subtitle {{ font-size: 13px; color: #94a3b8; text-transform: uppercase; margin-top: 5px; }}
        h2 {{ color: #ffffff; font-size: 20px; margin-top: 0; }}
        p {{ color: #cbd5e1; font-size: 15px; line-height: 1.6; }}
        .credentials-box {{ background: #1e293b; border-left: 4px solid #00f0ff; border-radius: 8px; padding: 20px; margin: 25px 0; }}
        .cred-item {{ margin: 10px 0; font-size: 16px; }}
        .cred-label {{ color: #94a3b8; font-size: 13px; text-transform: uppercase; display: block; }}
        .cred-value {{ color: #00f0ff; font-family: monospace; font-size: 18px; font-weight: bold; background: #0f172a; padding: 4px 10px; border-radius: 4px; display: inline-block; margin-top: 4px; }}
        .button {{ display: inline-block; background: linear-gradient(135deg, #00f0ff 0%, #7c4dff 100%); color: #070a13 !important; font-weight: bold; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-size: 16px; margin: 15px 0; text-align: center; }}
        .footer {{ border-top: 1px solid #1f2937; margin-top: 30px; padding-top: 20px; font-size: 12px; color: #64748b; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="email-container">
        <div class="header">
          <div class="logo">🤖 TALENTPILOT AI</div>
          <div class="subtitle">Autonomous Technical Screening System</div>
        </div>
        <h2>Dear {candidate_name},</h2>
        <p>Congratulations! After an initial review of your qualifications and technical accomplishments, our talent acquisition team has <strong>shortlisted your profile</strong> for the <strong>{role_name}</strong> position.</p>
        <p>You are invited to complete your <strong>First-Round Technical Screening Interview</strong> with our autonomous AI interviewer.</p>

        <div class="credentials-box">
          <div style="font-weight: bold; color: #ffffff; margin-bottom: 15px; font-size: 16px;">🔐 Your Secure Interview Credentials:</div>
          <div class="cred-item">
            <span class="cred-label">Candidate Access ID</span>
            <span class="cred-value">{access_id}</span>
          </div>
          <div class="cred-item">
            <span class="cred-label">Interview Access Passcode</span>
            <span class="cred-value">{access_code}</span>
          </div>
        </div>

        <p>Please click the secure link below and enter your credentials to initiate your interview room:</p>
        <div style="text-align: center;">
          <a href="{interview_url}" class="button">🚀 Launch Technical Screening Room</a>
        </div>

        <p style="font-size: 13px; color: #94a3b8; margin-top: 20px;">
          <strong>Interview Format:</strong> 5 adaptive technical, problem-solving, and architectural questions tailored to your experience. Average duration: 15–20 minutes.
        </p>

        <div class="footer">
          NexusAI Talent Acquisition Team • Automated Notification Service<br>
          Sent to: {candidate_email} • All evaluations are subject to human recruiter review.
        </div>
      </div>
    </body>
    </html>
    """

    # Plain text alternative
    text_content = f"""
    TALENTPILOT AI — INTERVIEW INVITATION

    Dear {candidate_name},

    Congratulations! Your profile has been shortlisted for the {role_name} position.
    You are invited to complete your First-Round Screening Interview.

    YOUR SECURE CREDENTIALS:
    - Candidate Access ID: {access_id}
    - Interview Passcode: {access_code}
    - Interview Portal URL: {interview_url}

    Please navigate to the portal, enter your credentials, and begin your interview.

    NexusAI Talent Acquisition Team
    """

    smtp_success = False
    smtp_message = "Simulated Dispatch (Logged in Terminal)"

    # Attempt real SMTP if configured
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    if smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"TalentPilot AI <{smtp_user}>"
            msg["To"] = candidate_email

            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, candidate_email, msg.as_string())
            smtp_success = True
            smtp_message = f"Delivered via live SMTP ({smtp_host}) to {candidate_email}"
        except Exception as e:
            smtp_message = f"SMTP Attempt failed ({e}); recorded to Live Dispatch Log."

    # Record dispatch audit log
    log_entry = {
        "timestamp": timestamp,
        "recipient_name": candidate_name,
        "recipient_email": candidate_email,
        "role": role_name,
        "access_id": access_id,
        "access_code": access_code,
        "subject": subject,
        "interview_url": interview_url,
        "html_content": html_content,
        "text_content": text_content,
        "status": "SENT",
        "smtp_status": smtp_message
    }
    DISPATCH_LOGS.append(log_entry)
    return log_entry


def get_dispatch_logs() -> List[Dict[str, Any]]:
    """Returns all sent notification email logs."""
    return DISPATCH_LOGS
