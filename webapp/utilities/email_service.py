import os
import smtplib
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader
from utilities.environment_variables import load_environment
load_environment("./../data/.env.webapp")
EMAIL_TEMPLATES_PATH=os.getenv("EMAIL_TEMPLATES_PATH")
if EMAIL_TEMPLATES_PATH is None: EMAIL_TEMPLATES_PATH = "./e-templates"

TEMPLATE_DIR = "webapp/e-template"

env = Environment(loader=FileSystemLoader(EMAIL_TEMPLATES_PATH))


def render_template(template_name: str, data: dict) -> str:
    template = env.get_template(template_name)
    return template.render(**data)


def send_email(
    to: list,
    subject: str,
    template_name: str,
    template_data: dict,
    cc: list = None,
    bcc: list = None,
):
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(to)

    if cc:
        msg["Cc"] = ", ".join(cc)

    msg["Subject"] = subject

    html_body = render_template(template_name, template_data)
    msg.add_alternative(html_body, subtype="html")

    recipients = to + (cc or []) + (bcc or [])

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg, to_addrs=recipients)

        print("[EMAIL] Sent successfully")

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
