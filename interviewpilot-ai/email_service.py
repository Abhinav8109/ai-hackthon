"""
Email Service Module for TalentPilot AI.
Provides production-grade email notifications with real SMTP delivery,
verifiable delivery statuses, failure capture, and audit persistence.

Supported configurations:
- Real SMTP (e.g. Gmail SMTP via App Password, SendGrid, Mailgun, Amazon SES)
- Development Mock mode (safe offline testing, accurately labeled as ACCEPTED_DEV_MOCK)
- Delivery tracking: QUEUED, ACCEPTED_DEV_MOCK, DELIVERED_SMTP, FAILED
"""

from typing import Dict, Any, Optional
import os
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from database import get_db_connection, log_audit_event


def get_base_url() -> str:
    """Configurable Base URL for interview links (defaults to current Streamlit port)."""
    return os.getenv("APP_BASE_URL", "http://localhost:8501").rstrip("/")


def generate_first_round_invitation_email(
    candidate_name: str,
    job_title: str,
    interview_url: str,
    expiration_days: int = 7,
    support_email: str = "recruitment@nexusai-talent.com"
) -> Dict[str, str]:
    """Generates subject, plain text, and HTML body for Step 3 First-Round Invitation."""
    subject = f"First-Round Interview Invitation — {job_title}"

    body_text = f"""Dear {candidate_name},

Congratulations! Your profile has been shortlisted for the first-round interview for the {job_title} position.

Please use the secure link below to access your AI-powered interview:

Start Your Interview: {interview_url}

Important Instructions:
• This link is uniquely assigned to you and will expire in {expiration_days} days.
• Please ensure that you have a stable internet connection and approximately 20–25 minutes of uninterrupted time.
• You will be asked technical, architectural, problem-solving, and behavioral questions tailored to your experience.

If you require any assistance or special accommodations, please contact our talent team at {support_email}.

We look forward to learning more about your skills and experience.

Best regards,
Recruitment Team
"""

    body_html = f"""<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
    .header {{ border-bottom: 2px solid #00f0ff; padding-bottom: 16px; margin-bottom: 24px; text-align: center; }}
    .logo {{ font-size: 22px; font-weight: 800; color: #00f0ff; letter-spacing: 1px; }}
    h2 {{ color: #ffffff; font-size: 19px; margin-top: 0; }}
    p {{ color: #cbd5e1; font-size: 14.5px; line-height: 1.6; margin: 14px 0; }}
    .button-container {{ text-align: center; margin: 28px 0; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #00f0ff 0%, #6366f1 100%); color: #080d1a !important; font-weight: 700; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-size: 15px; box-shadow: 0 4px 15px rgba(0,240,255,0.3); }}
    .meta-box {{ background: #1e293b; border-left: 3px solid #00f0ff; border-radius: 6px; padding: 14px 18px; margin: 20px 0; font-size: 13.5px; color: #94a3b8; }}
    .footer {{ border-top: 1px solid #1f2937; margin-top: 30px; padding-top: 18px; font-size: 12px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">TALENTPILOT AI</div>
      <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-top: 4px;">Autonomous Technical Screening Platform</div>
    </div>
    <h2>Dear {candidate_name},</h2>
    <p>Congratulations! Your profile has been shortlisted for the first-round interview for the <strong>{job_title}</strong> position.</p>
    <p>Please use the secure link below to access your AI-powered interview:</p>

    <div class="button-container">
      <a href="{interview_url}" class="btn">Start Your Interview</a>
    </div>

    <div class="meta-box">
      <strong>Session Validity:</strong> This link is active for <strong>{expiration_days} days</strong>.<br>
      <strong>Preparation:</strong> Please ensure a stable internet connection and 20–25 minutes of quiet time.
    </div>

    <p>We look forward to learning more about your skills and experience.</p>
    <p>Best regards,<br><strong>Recruitment Team</strong></p>

    <div class="footer">
      Support Inquiries: {support_email}<br>
      © TalentPilot AI Recruitment Platform. All rights reserved.
    </div>
  </div>
</body>
</html>"""

    return {"subject": subject, "body_text": body_text, "body_html": body_html}


def generate_second_round_selection_email(
    candidate_name: str,
    job_title: str
) -> Dict[str, str]:
    """Generates subject, plain text, and HTML body for Step 8 Second-Round Approval."""
    subject = f"Congratulations — Selected for the Second Round"

    body_text = f"""Dear {candidate_name},

Congratulations!

We are pleased to inform you that you have been selected to proceed to the second round of the interview process for the {job_title} position.

Thank you for your time and participation in the first-round interview.

Further details regarding the next round, including the schedule and instructions, will be shared with you soon.

We appreciate your interest in joining our team and look forward to the next stage of the process.

Best regards,
Recruitment Team
"""

    body_html = f"""<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
    .header {{ border-bottom: 2px solid #10b981; padding-bottom: 16px; margin-bottom: 24px; text-align: center; }}
    .logo {{ font-size: 22px; font-weight: 800; color: #10b981; letter-spacing: 1px; }}
    h2 {{ color: #ffffff; font-size: 19px; margin-top: 0; }}
    p {{ color: #cbd5e1; font-size: 14.5px; line-height: 1.6; margin: 14px 0; }}
    .success-box {{ background: rgba(16, 185, 129, 0.1); border-left: 3px solid #10b981; border-radius: 6px; padding: 16px 20px; margin: 20px 0; font-size: 14px; color: #e2e8f0; }}
    .footer {{ border-top: 1px solid #1f2937; margin-top: 30px; padding-top: 18px; font-size: 12px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">TALENTPILOT AI</div>
      <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-top: 4px;">Talent Acquisition Team</div>
    </div>
    <h2>Dear {candidate_name},</h2>
    <div class="success-box">
      <strong>Status Update:</strong> You have been selected to proceed to the second round of the interview process for the <strong>{job_title}</strong> position.
    </div>
    <p>Thank you for your time and participation in the first-round technical screening interview.</p>
    <p>Further details regarding the next round, including the schedule and instructions, will be shared with you soon.</p>
    <p>We appreciate your interest in joining our team and look forward to the next stage of the process.</p>
    <p>Best regards,<br><strong>Recruitment Team</strong></p>
    <div class="footer">
      NexusAI Talent Acquisition • Second-Round Interview Advancement
    </div>
  </div>
</body>
</html>"""

    return {"subject": subject, "body_text": body_text, "body_html": body_html}


def send_email_notification(
    candidate_id: str,
    recipient_email: str,
    recipient_name: str,
    notification_type: str,
    subject: str,
    body_text: str,
    body_html: str,
    force_retry: bool = False
) -> Dict[str, Any]:
    """
    Core notification dispatcher.
    Checks for duplicate sends unless force_retry is True.
    Attempts real SMTP if configured; otherwise logs verifiable ACCEPTED_DEV_MOCK status.
    Persists exact delivery audit record in database.
    """
    now = datetime.now(timezone.utc).isoformat()
    notif_id = f"NOTIF-{uuid.uuid4().hex[:10].upper()}"

    # 1. Duplicate Prevention
    with get_db_connection() as conn:
        if not force_retry:
            existing = conn.execute(
                "SELECT * FROM email_notifications WHERE candidate_id = ? AND notification_type = ? AND delivery_status IN ('DELIVERED_SMTP', 'ACCEPTED_DEV_MOCK');",
                (candidate_id, notification_type)
            ).fetchone()
            if existing:
                return {
                    "status": "duplicate_prevented",
                    "notification_id": existing["id"],
                    "delivery_status": existing["delivery_status"],
                    "message": "Notification already successfully sent to candidate."
                }

    # 2. Inspect SMTP Configuration
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER") or os.getenv("GMAIL_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "recruitment@nexusai-talent.com")

    delivery_status = "QUEUED"
    provider_ref = None
    error_details = None

    # Attempt real SMTP if credentials are present
    if smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"TalentPilot Recruitment <{smtp_from}>"
            msg["To"] = recipient_email
            msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

            msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10.0) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                res = server.sendmail(smtp_from, [recipient_email], msg.as_string())
                delivery_status = "DELIVERED_SMTP"
                provider_ref = f"SMTP 250 OK via {smtp_host}"
        except Exception as e:
            delivery_status = "FAILED"
            error_details = str(e)
    else:
        # Development / Offline Mock Provider
        delivery_status = "ACCEPTED_DEV_MOCK"
        provider_ref = "DevMockProvider: Credentials unconfigured in .env. Logged in database."

    # 3. Persist Notification in SQLite
    with get_db_connection() as conn:
        conn.execute("""
        INSERT INTO email_notifications (
            id, candidate_id, notification_type, recipient_email, recipient_name,
            subject, body_text, body_html, delivery_status, provider_reference,
            error_details, attempts, sent_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?);
        """, (
            notif_id, candidate_id, notification_type, recipient_email, recipient_name,
            subject, body_text, body_html, delivery_status, provider_ref,
            error_details, now if delivery_status in ("DELIVERED_SMTP", "ACCEPTED_DEV_MOCK") else None, now
        ))
        conn.commit()

    log_audit_event(
        entity_type="candidate",
        entity_id=candidate_id,
        action=f"EMAIL_{notification_type}_{delivery_status}",
        actor="System",
        details=f"Recipient: {recipient_email} | Status: {delivery_status} | Ref: {provider_ref or error_details}"
    )

    return {
        "status": "success" if delivery_status != "FAILED" else "failed",
        "notification_id": notif_id,
        "delivery_status": delivery_status,
        "provider_reference": provider_ref,
        "error_details": error_details,
        "recipient_email": recipient_email
    }


def retry_failed_notification(notification_id: str) -> Dict[str, Any]:
    """Retries a failed email notification."""
    with get_db_connection() as conn:
        notif = conn.execute("SELECT * FROM email_notifications WHERE id = ?;", (notification_id,)).fetchone()
        if not notif:
            return {"status": "error", "message": "Notification record not found."}

    return send_email_notification(
        candidate_id=notif["candidate_id"],
        recipient_email=notif["recipient_email"],
        recipient_name=notif["recipient_name"],
        notification_type=notif["notification_type"],
        subject=notif["subject"],
        body_text=notif["body_text"],
        body_html=notif["body_html"],
        force_retry=True
    )
