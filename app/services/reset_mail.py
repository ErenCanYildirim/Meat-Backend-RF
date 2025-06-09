import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "kasse@buhara-burger.de")
FROM_NAME = os.getenv("FROM_NAME", "BuHaRa Burger")
FRONTEND_URL = os.getenv("FRONTEND_URL")


reset_template = f"""
<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 40px;
                    border-radius: 10px;
                    color: white;
                    text-align: center;
                }}
                .content {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    color: #333;
                    margin: 20px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    font-size: 14px;
                    color: #666;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Passwort zurücksetzen</h1>
                <div class="content">
                    <h2>Guten Tag,</h2>
                    <p>Sie haben eine Anfrage zum Zurücksetzen Ihres Passwortes geschickt. Klicken Sie auf den Link um Ihr Passwort zurückzusetzen:</p>

                    <a href="{reset_link}" class="button">Passwort zurücksetzen</a>

                    <p>Oder kopieren Sie diesen Link in Ihren Browser:</p>
                    <p style="word-break: break-all; background: #f5f5f5; padding: 10px; border-radius: 5px;">
                        {reset_link}
                    </p>

                    <div class="footer">
                        <p><strong>Important:</strong>Dieser Link wird nach 1h verfallen.</p>
                        <p>Wenn Sie keine Passwortrückgabe angefordert haben, ignorieren Sie diese Mail. Ihr Passwort wird gleichbleiben!</p>
                    </div>
                </div>
            </div>
        </body>
"""

plain_reset_text = f"""
Anfrage zur Passwortzurücksetzung

Guten Tag,
Sie haben eine Anfrage zur Passwortrücksetzung geschickt! Klicken Sie auf den Link unten um Ihr Passwort zurückzusetzen:

{reset_link}

Der Link wird in einer Stunde verfallen!
Wenn Sie keine Passwortrückgabe angefordert haben, ignorieren Sie diese Mail. Ihr Passwort wird gleichbleiben!

Beste Grüße,
{FROM_NAME}
"""


def send_reset_email(email: str, token: str):
    try:
        if not SENDGRID_API_KEY:
            print("SendGrid API key not configured")
            return False

        reset_link = f"{FRONTEND_URL}/reset-password?token={token}"

        message = Mail(
            from_email=(FROM_EMAIL, FROM_NAME),
            to_emails=email,
            subject="Password reset request",
            html_content=reset_template,
            plain_text=plain_reset_text,
        )

        sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in [200, 201, 202]:
            print(f"Password reset email sent successfully to {email}")
            return True
        else:
            print(f"Failed to send email. Status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"Failed to send email via SendGrid: {e}")
        return False
