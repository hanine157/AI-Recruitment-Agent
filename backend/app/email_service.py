import os
import smtplib
from datetime import datetime
from email.message import EmailMessage


class EmailConfigurationError(ValueError):
    """Raised when required email settings are missing."""


class EmailDeliveryError(RuntimeError):
    """Raised when SMTP accepts configuration but sending fails."""


PLACEHOLDER_VALUES = {
    "your-email@gmail.com",
    "your-gmail-app-password",
    "your_app_password_here",
}


def _is_missing_or_placeholder(value: str | None) -> bool:
    return not value or value.strip() in PLACEHOLDER_VALUES


def send_email(to_email: str, subject: str, body: str):
    # Read credentials at runtime (not import time) to ensure .env is loaded
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")
    
    # Validate credentials
    if _is_missing_or_placeholder(email_address):
        raise EmailConfigurationError(
            "EMAIL_ADDRESS is not configured. Set EMAIL_ADDRESS in backend/.env."
        )
    if _is_missing_or_placeholder(email_password):
        raise EmailConfigurationError(
            "EMAIL_PASSWORD is not configured. Set EMAIL_PASSWORD in backend/.env. "
            "For Gmail, use an app password, not your regular account password."
        )

    # Create the email
    message = EmailMessage()

    message["Subject"] = subject
    message["From"] = email_address
    message["To"] = to_email

    message.set_content(body)

    # Connect to Gmail SMTP server
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(email_address, email_password)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as e:
        raise EmailConfigurationError(
            "SMTP authentication failed. Check EMAIL_ADDRESS and EMAIL_PASSWORD."
        ) from e
    except smtplib.SMTPException as e:
        raise EmailDeliveryError(f"SMTP error occurred: {e}") from e
    except OSError as e:
        raise EmailDeliveryError(
            "Could not connect to the email server. Check your network, firewall, "
            "or antivirus settings for outbound SMTP on port 465."
        ) from e


def send_interview_email(candidate_email: str, candidate_name: str, job_title: str, interview_token: str):
    """Send interview invitation email to candidate"""
    subject = "Interview Invitation"
    body = f"""
Hello {candidate_name},

Congratulations!

You have been selected for an interview for the position of:

{job_title}

Please click the link below to access your interview:

http://localhost:4200/interview/{interview_token}

Best regards,
AI Recruitment Team

"""
    send_email(candidate_email, subject, body)


def send_confirmation_email(candidate_email: str, candidate_name: str, scheduled_at):
    """Send a confirmation email once the interview is scheduled."""
    subject = "Interview Scheduled"
    body = f"""
Hello {candidate_name},

Your interview has been scheduled for {scheduled_at}.

Best regards,
AI Recruitment Team
"""
    send_email(candidate_email, subject, body)


def send_recruiter_notification(recruiter_email: str, candidate_name: str, scheduled_at: datetime):
    if not recruiter_email:
        return False

    subject = f"Interview Scheduled — {candidate_name}"
    body = f"""
Interview scheduled for candidate: {candidate_name}
Date and time: {scheduled_at}

No action is required — the AI agent will conduct the interview automatically.
"""

    try:
        send_email(recruiter_email, subject, body)
        print(f"✅ Recruiter notification sent to {recruiter_email}")
        return True
    except Exception as e:
        print(f"❌ Recruiter notification error: {e}")
        return False