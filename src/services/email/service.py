import os

import resend
from dotenv import load_dotenv

load_dotenv()
FROM_EMAIL = os.getenv("FROM_EMAIL")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
resend.api_key = RESEND_API_KEY


def send_email(to, subject, html):
    resend.Emails.send({"from": FROM_EMAIL, "to": to, "subject": subject, "html": html})


def send_verification_mail(username, email, verification_code):

    to = email
    subject = "Verify your CineCircle account"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: #0b0b0f;
            font-family: "SF Pro Text", "SF Pro Display", Arial, sans-serif;
            color: #ffffff;
        }}
    
        .email-wrapper {{
            width: 100%;
            padding: 40px 15px;
            box-sizing: border-box;
        }}
    
        .email-card {{
            width: 100%;
            max-width: 560px;
            margin: 0 auto;
            background-color: #15151c;
            border: 1px solid #292936;
            border-radius: 18px;
            overflow: hidden;
        }}
    
        .header {{
            padding: 28px 30px;
            background: linear-gradient(135deg, #191923, #101017);
            border-bottom: 1px solid #292936;
            text-align: center;
        }}
    
        .logo {{
            font-family: "SF Pro Display", "SF Pro Text", Arial, sans-serif;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.8px;
            color: #ffffff;
        }}
    
        .logo span {{
            color: #e50914;
        }}
    
        .content {{
            padding: 40px 35px;
        }}
    
        .content h1 {{
            margin: 0 0 15px;
            font-family: "SF Pro Display", "SF Pro Text", Arial, sans-serif;
            font-size: 28px;
            line-height: 1.25;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: #ffffff;
        }}
    
        .greeting {{
            margin: 0 0 28px;
            font-size: 16px;
            line-height: 1.5;
            color: #d2d2d8;
        }}
    
        .message {{
            margin: 0 0 12px;
            font-size: 15px;
            line-height: 1.6;
            color: #aaaab5;
        }}
    
        .code-box {{
            margin: 28px 0;
            padding: 24px 20px;
            background-color: #0d0d12;
            border: 1px solid #343440;
            border-radius: 14px;
            text-align: center;
        }}
    
        .code-label {{
            margin-bottom: 10px;
            font-size: 12px;
            line-height: 1.4;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #888894;
        }}
    
        .verification-code {{
            font-family: "SF Pro Display", "SF Pro Text", Arial, sans-serif;
            font-size: 38px;
            line-height: 1.2;
            font-weight: 700;
            letter-spacing: 7px;
            color: #e50914;
        }}
    
        .expiry {{
            margin-top: 12px;
            font-size: 13px;
            line-height: 1.4;
            color: #888894;
        }}
    
        .security {{
            margin-top: 30px;
            padding: 16px;
            background-color: #1c1c25;
            border-radius: 10px;
            font-size: 13px;
            line-height: 1.5;
            color: #9999a4;
        }}
    
        .security strong {{
            color: #d8d8df;
        }}
    
        .footer {{
            padding: 22px 30px;
            background-color: #101015;
            border-top: 1px solid #292936;
            text-align: center;
        }}
    
        .footer p {{
            margin: 5px 0;
            font-size: 12px;
            line-height: 1.4;
            color: #6f6f7a;
        }}
    
        @media only screen and (max-width: 600px) {{
            .email-wrapper {{
                padding: 20px 10px;
            }}
    
            .content {{
                padding: 30px 22px;
            }}
    
            .content h1 {{
                font-size: 24px;
            }}
    
            .verification-code {{
                font-size: 32px;
                letter-spacing: 6px;
            }}
        }}
    </style>
    </head>
    
    <body>
    
    <div class="email-wrapper">
    
        <div class="email-card">
    
            <div class="header">
                <div class="logo">
                    Cine<span>Circle</span>
                </div>
            </div>
    
            <div class="content">
    
                <h1>Verify your account</h1>
    
                <p class="greeting">
                    Hello <strong>{username.title()}</strong>,
                </p>
    
                <p class="message">
                    Welcome to CineCircle! Use the verification code below
                    to verify your email address and complete your account setup.
                </p>
    
                <div class="code-box">
    
                    <div class="code-label">
                        Your verification code
                    </div>
    
                    <div class="verification-code">
                        {verification_code}
                    </div>
    
                    <div class="expiry">
                        This code expires in 10 minutes.
                    </div>
    
                </div>
    
                <p class="message">
                    Enter this code in the CineCircle app to continue.
                </p>
    
                <div class="security">
                    <strong>Didn't request this?</strong><br>
                    If you didn't try to create or verify a CineCircle
                    account, you can safely ignore this email.
                </div>
    
            </div>
    
            <div class="footer">
                <p>© 2026 CineCircle</p>
                <p>Enjoy movies. Discover stories. Connect with your circle.</p>
            </div>
    
        </div>
    
    </div>
    
    </body>
    </html>
    """
    send_email(to, subject, html)


def send_password_reset_otp(username, email, verification_code):

    to = email
    subject = "Password reset OTP"

    html = f"""
    <h2>Password reset OTP</h2>
    <p>Hello {username.title()},</p>
    <p>Use this OTP to reset your password :</p>
    <h1>{verification_code}</h1>
    <p>This code expires in 10 minutes.</p>
    <p>If you didn't request this,ignore this email</p>

    """
    send_email(to, subject, html)
