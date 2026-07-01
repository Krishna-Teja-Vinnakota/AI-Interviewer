"""Email service for sending interview invitations and notifications."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)


async def send_interview_invitation_email(
    candidate_email: str,
    candidate_name: str,
    invitation_code: str,
    jd_title: str,
    expires_at: datetime
):
    """Send interview invitation email with invitation code."""
    try:
        # Email configuration
        sender_email = settings.SMTP_USER if hasattr(settings, 'SMTP_USER') else "noreply@aiinterview.com"
        sender_name = "AI Interview System"
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Interview Invitation - {jd_title}"
        message["From"] = f"{sender_name} <{sender_email}>"
        message["To"] = candidate_email
        
        # Create HTML content
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .content {{
            background: #ffffff;
            padding: 30px;
            border: 1px solid #e5e7eb;
            border-top: none;
        }}
        .invitation-code {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 32px;
            font-weight: bold;
            letter-spacing: 8px;
            padding: 20px;
            text-align: center;
            border-radius: 8px;
            margin: 30px 0;
        }}
        .info-box {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .info-item {{
            margin: 10px 0;
        }}
        .info-label {{
            font-weight: 600;
            color: #4b5563;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 14px 28px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }}
        .instructions {{
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 15px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #6b7280;
            font-size: 14px;
            border-top: 1px solid #e5e7eb;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🤖 AI Interview System</div>
        <h2 style="margin: 0;">Interview Invitation</h2>
    </div>
    
    <div class="content">
        <p>Dear {candidate_name},</p>
        
        <p>Congratulations! Your profile has been shortlisted for the <strong>{jd_title}</strong> position.</p>
        
        <p>We are pleased to invite you to participate in an AI-powered video interview. This innovative interview process will help us better understand your skills and experience.</p>
        
        <div class="invitation-code">
            {invitation_code}
        </div>
        
        <div class="info-box">
            <div class="info-item">
                <span class="info-label">📋 Position:</span> {jd_title}
            </div>
            <div class="info-item">
                <span class="info-label">⏰ Valid Until:</span> {expires_at.strftime("%B %d, %Y")}
            </div>
            <div class="info-item">
                <span class="info-label">🔑 Your Invitation Code:</span> <strong>{invitation_code}</strong>
            </div>
        </div>
        
        <div class="instructions">
            <h3 style="margin-top: 0;">📝 How to Start Your Interview:</h3>
            <ol>
                <li>Keep your invitation code ready: <strong>{invitation_code}</strong></li>
                <li>Visit the candidate portal (link will be shared after deployment)</li>
                <li>Enter your invitation code when prompted</li>
                <li>Allow camera and microphone permissions</li>
                <li>Click "Start Interview" when you're ready</li>
                <li>Answer the questions thoughtfully</li>
            </ol>
        </div>
        
        <div style="text-align: center; padding: 20px; background: #f9fafb; border-radius: 8px;">
            <p style="margin: 0; font-size: 1.1rem; color: #4b5563;">
                <strong>Portal link will be provided separately</strong>
            </p>
            <p style="margin: 10px 0 0 0; color: #6b7280;">
                Make sure you have your invitation code ready when accessing the portal
            </p>
        </div>
        
        <div style="margin-top: 30px; padding: 20px; background: #fef2f2; border-radius: 8px; border-left: 4px solid #ef4444;">
            <p style="margin: 0; color: #991b1b;"><strong>⚠️ Important Notes:</strong></p>
            <ul style="margin: 10px 0;">
                <li>Ensure you have a working webcam and microphone</li>
                <li>Find a quiet, well-lit space for the interview</li>
                <li>Use a stable internet connection</li>
                <li>Allow browser permissions for camera and microphone</li>
                <li>The invitation code expires on {expires_at.strftime("%B %d, %Y")}</li>
            </ul>
        </div>
        
        <p style="margin-top: 30px;">We look forward to learning more about you!</p>
        
        <p>Best regards,<br>
        <strong>The Hiring Team</strong></p>
    </div>
    
    <div class="footer">
        <p>This is an automated email from AI Interview System.</p>
        <p>If you have any questions, please contact the hiring team.</p>
        <p style="margin-top: 20px; color: #9ca3af; font-size: 12px;">
            © {datetime.now().year} AI Interview System. All rights reserved.
        </p>
    </div>
</body>
</html>
"""
        
        # Create plain text version
        text_content = f"""
AI Interview System - Interview Invitation

Dear {candidate_name},

Congratulations! Your profile has been shortlisted for the {jd_title} position.

Your Invitation Code: {invitation_code}

How to Start Your Interview:
1. Keep your invitation code ready: {invitation_code}
2. Visit the candidate portal (link will be provided separately)
3. Enter your invitation code when prompted
4. Allow camera and microphone permissions
5. Click "Start Interview" when you're ready

Position: {jd_title}
Valid Until: {expires_at.strftime("%B %d, %Y")}

Important Notes:
- Ensure you have a working webcam and microphone
- Find a quiet, well-lit space
- Use a stable internet connection
- Camera and microphone permissions are REQUIRED

Best regards,
The Hiring Team

---
This is an automated email from AI Interview System.
"""
        
        # Attach parts
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Send email using SMTP if configured
        if hasattr(settings, 'SMTP_HOST') and hasattr(settings, 'SMTP_USER'):
            try:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    if settings.SMTP_TLS:
                        server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(message)
                    logger.info(f"Email sent successfully to {candidate_email}")
                    return True
            except Exception as e:
                logger.error(f"SMTP error: {e}")
                raise
        else:
            # If SMTP not configured, log the email content
            logger.warning("SMTP not configured. Email content:")
            logger.info(f"To: {candidate_email}")
            logger.info(f"Subject: {message['Subject']}")
            logger.info(f"Invitation Code: {invitation_code}")
            logger.info("Email would have been sent if SMTP was configured")
            return True
            
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise


async def send_interview_reminder_email(
    candidate_email: str,
    candidate_name: str,
    invitation_code: str,
    expires_at: datetime
):
    """Send reminder email to candidate."""
    # TODO: Implement reminder email
    pass
