import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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


def _get_email_credentials() -> tuple[str, str]:
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")

    if _is_missing_or_placeholder(email_address):
        raise EmailConfigurationError(
            "EMAIL_ADDRESS is not configured. Set EMAIL_ADDRESS in backend/.env."
        )
    if _is_missing_or_placeholder(email_password):
        raise EmailConfigurationError(
            "EMAIL_PASSWORD is not configured. Set EMAIL_PASSWORD in backend/.env. "
            "For Gmail, use an app password, not your regular account password."
        )

    return email_address, email_password


def send_email(to_email: str, subject: str, body: str):
    email_address, email_password = _get_email_credentials()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_address
    message["To"] = to_email
    message.set_content(body)

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

Please click the link below to schedule your interview:

http://localhost:4200/schedule/{interview_token}

Best regards,
AI Recruitment Team

"""
    send_email(candidate_email, subject, body)
    send_email(candidate_email, subject, body)


def send_confirmation_email(candidate_email: str, candidate_name: str, scheduled_at: datetime, job_title: str = "", token: str = ""):
    email_address, email_password = _get_email_credentials()

    interview_link = f"http://localhost:4200/interview/{token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Interview Confirmed"
    msg["From"] = email_address
    msg["To"] = candidate_email

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        
        <div style="background: linear-gradient(135deg, #2c3e50, #3498db); 
                    padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0;">Interview Confirmed! 🎉</h1>
        </div>

        <div style="background: white; padding: 30px; border-radius: 0 0 12px 12px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            
            <h2 style="color: #2c3e50;">Hello {candidate_name}!</h2>
            
            <p style="color: #7f8c8d;">
                Your interview for the <strong>{job_title}</strong> position 
                has been confirmed.
            </p>

            <div style="background: #f8f9fa; padding: 20px; 
                        border-radius: 8px; margin: 20px 0;">
                <p style="margin: 5px 0; color: #2c3e50;">
                    📅 <strong>Date:</strong> 
                    {scheduled_at.strftime("%B %d, %Y")}
                </p>
                <p style="margin: 5px 0; color: #2c3e50;">
                    ⏰ <strong>Time:</strong> 
                    {scheduled_at.strftime("%I:%M %p")}
                </p>
                <p style="margin: 5px 0; color: #2c3e50;">
                    🤖 <strong>Interviewer:</strong> AI Interview Agent
                </p>
            </div>

            <p style="color: #7f8c8d;">
                When it's time for your interview, click the button below to join:
            </p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{interview_link}" 
                   style="background: linear-gradient(135deg, #27ae60, #2ecc71);
                          color: white; padding: 15px 40px; 
                          text-decoration: none; border-radius: 25px;
                          font-size: 18px; font-weight: bold;">
                    Join Interview
                </a>
            </div>

            <p style="color: #e74c3c; font-size: 13px;">
                ⚠️ Please make sure your camera and microphone 
                are working before joining.
            </p>

            <p style="color: #7f8c8d;">Good luck! 🍀</p>
            <p style="color: #7f8c8d;">The Recruitment Team</p>
        </div>

    </body>
    </html>
    """

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_address, email_password)
            server.sendmail(email_address, candidate_email, msg.as_string())
            print(f"✅ Confirmation email sent to {candidate_email}")
            return True
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
