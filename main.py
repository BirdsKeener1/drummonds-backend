from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
import logging
import os
from typing import Optional

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Email configuration - Consider using environment variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "drummondsbusinesssolutions@gmail.com"
SENDER_PASSWORD = "fbxp eqfk xrqy zxfv"  # This should be your Gmail App Password

# In-memory data store
user_data_store = []

class UserRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = ""
    company: Optional[str] = ""
    service: Optional[str] = ""
    message: str

app = FastAPI(title="Drummonds Business Solutions API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def send_email_sync(to_email: str, subject: str, body: str, sender_name: str = "Drummonds Business Solutions") -> dict:
    """
    Synchronous email sending function with detailed error reporting
    """
    result = {"success": False, "error": None, "details": ""}

    try:
        logger.info(f"Attempting to send email to: {to_email}")
        logger.info(f"Subject: {subject}")

        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name} <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add body
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        logger.info(f"Connecting to SMTP server: {SMTP_SERVER}:{SMTP_PORT}")

        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)

        # Enable debug output
        server.set_debuglevel(1)

        # Start TLS encryption
        logger.info("Starting TLS encryption...")
        server.starttls()

        # Login to Gmail
        logger.info(f"Logging in with email: {SENDER_EMAIL}")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        logger.info("Login successful!")

        # Send email
        logger.info("Sending email...")
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, [to_email], text)

        # Close connection
        server.quit()

        result["success"] = True
        result["details"] = f"Email sent successfully to {to_email}"
        logger.info(f"✅ Email sent successfully to {to_email}")

    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"Authentication failed. Check your email and app password. Error: {str(e)}"
        result["error"] = "SMTP Authentication Error"
        result["details"] = error_msg
        logger.error(f"❌ {error_msg}")

    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"Recipient email refused: {to_email}. Error: {str(e)}"
        result["error"] = "Recipient Refused"
        result["details"] = error_msg
        logger.error(f"❌ {error_msg}")

    except smtplib.SMTPServerDisconnected as e:
        error_msg = f"SMTP server disconnected. Error: {str(e)}"
        result["error"] = "Server Disconnected"
        result["details"] = error_msg
        logger.error(f"❌ {error_msg}")

    except smtplib.SMTPConnectError as e:
        error_msg = f"Cannot connect to SMTP server. Error: {str(e)}"
        result["error"] = "Connection Error"
        result["details"] = error_msg
        logger.error(f"❌ {error_msg}")

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        result["error"] = "Unknown Error"
        result["details"] = error_msg
        logger.error(f"❌ {error_msg}")

    return result

@app.post("/submit")
async def submit_user_data(user: UserRequest, background_tasks: BackgroundTasks):
    """Submit user data and send confirmation emails in the background for fast response"""
    try:
        logger.info(f"Processing submission from {user.name} ({user.email})")

        # Save to in-memory store
        user_data_store.append({
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "company": user.company,
            "service": user.service,
            "message": user.message
        })
        logger.info(f"✅ User data saved in memory for {user.email}")

        # Prepare emails
        user_subject = "Thank you for contacting Drummonds Business Solutions!"
        user_body = f"""Hi {user.name},

Thank you for reaching out to Drummonds Business Solutions! 

We have received your message and will get back to you within 24 hours during business days.

Here's what you submitted:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phone: {user.phone if user.phone else 'Not provided'}
Company: {user.company if user.company else 'Not provided'}
Service of Interest: {user.service if user.service else 'General Inquiry'}
Your Message: {user.message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Best regards,
The Drummonds Business Solutions Team
Email: {SENDER_EMAIL}
"""

        owner_subject = f"🔔 New Contact Form Submission - {user.name}"
        owner_body = f"""New contact form submission received:

👤 Customer Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {user.name}
Email: {user.email}
Phone: {user.phone if user.phone else 'Not provided'}
Company: {user.company if user.company else 'Not provided'}
Service: {user.service if user.service else 'Not specified'}

💬 Message:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{user.message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please respond to: {user.email}
"""

        # Send emails in the background for fast response
        def send_emails_bg():
            logger.info("Sending thank you email to user (background)...")
            user_email_result = send_email_sync(user.email, user_subject, user_body)
            logger.info("Sending notification email to owner (background)...")
            owner_email_result = send_email_sync(SENDER_EMAIL, owner_subject, owner_body)
            if not user_email_result["success"]:
                logger.error(f"User email failed: {user_email_result['details']}")
            if not owner_email_result["success"]:
                logger.error(f"Owner email failed: {owner_email_result['details']}")

        background_tasks.add_task(send_emails_bg)

        # Respond immediately for fast UX
        return {
            "status": "success",
            "message": "Submission received! We'll get back to you within 24 hours."
        }

    except Exception as e:
        logger.error(f"❌ Error processing submission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
