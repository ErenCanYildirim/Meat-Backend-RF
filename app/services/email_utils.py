import base64
import os

from dotenv import load_dotenv
from python_http_client.exceptions import HTTPError
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

load_dotenv()

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
ROOT_EMAIL = os.environ.get("ROOT_ADMIN_EMAIL")


def send_mail_with_attachment(pdf_filename, pdf_path):
    mail_title = pdf_filename.capitalize()

    message = Mail(
        from_email=ROOT_EMAIL,
        to_emails=ROOT_EMAIL,
        subject=mail_title,
        html_content="<strong>Bestellung im Anhang. Automatisch gesendet von Grünlandfleischbestellung!</strong>",
    )

    with open(pdf_path, "rb") as pdf_file:
        encoded_pdf = base64.b64encode(pdf_file.read()).decode()

    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName(pdf_filename),
        FileType("application/pdf"),
        Disposition("attachment"),
    )

    message.add_attachment(attachment)

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent! Status code: {response.status_code}")
        return response.status_code
    except HTTPError as e:
        print(f"SendGrid Error: {e.status_code} - {e.body}")
        return None
