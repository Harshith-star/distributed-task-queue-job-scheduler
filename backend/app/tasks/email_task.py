"""Email task — sends an email via SMTP."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.workers.celery_app import celery_app
from app.tasks.base_task import BaseTaskQ


@celery_app.task(bind=True, base=BaseTaskQ, name="app.tasks.email_task.send_email")
def send_email_task(self, execution_id: int, task_id: int, config: dict) -> str:
    return self.run(execution_id, task_id, config)


class SendEmailTask(BaseTaskQ):
    name = "app.tasks.email_task.send_email"

    def run_task(self, config: dict) -> str:
        from app.core.config import get_settings
        settings = get_settings()
        msg = MIMEMultipart("alternative")
        msg["Subject"] = config.get("subject", "TaskQ Notification")
        msg["From"]    = settings.EMAIL_FROM
        msg["To"]      = config.get("to_email", "")
        body = config.get("body", "")
        msg.attach(MIMEText(body, "plain"))

        if config.get("html_body"):
            msg.attach(MIMEText(config["html_body"], "html"))

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            if settings.SMTP_USERNAME:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return f"Email sent to {config.get('to_email')}"
