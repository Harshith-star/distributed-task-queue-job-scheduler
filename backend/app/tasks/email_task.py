"""Email Task — sends an email over SMTP."""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

from app.tasks.base_task import BaseTaskQ
from app.workers.celery_app import celery_app


class EmailTask(BaseTaskQ):
    name = "app.tasks.email_task.send_email"
    # NOTE: no `abstract = True` here — only the base class is abstract.

    def execute_task(self, config: dict) -> str:
        from app.core.config import get_settings
        settings = get_settings()

        raw = config.get("to_email")
        if not raw:
            raise ValueError("to_email is required")

        recipients = [e.strip() for e in
                      (raw if isinstance(raw, list) else str(raw).replace(";", ",").split(","))
                      if e.strip()]
        for addr in recipients:
            if "@" not in parseaddr(addr)[1]:
                raise ValueError(f"Invalid recipient address: {addr}")

        message = MIMEMultipart("alternative")
        message["Subject"] = config.get("subject", "TaskQ Notification")
        from_name = getattr(settings, "EMAIL_FROM_NAME", None) or "TaskQ"
        message["From"] = formataddr((from_name, settings.EMAIL_FROM))
        message["To"] = ", ".join(recipients)

        message.attach(MIMEText(config.get("body", "") or "(no content)", "plain", "utf-8"))
        if config.get("html_body"):
            message.attach(MIMEText(config["html_body"], "html", "utf-8"))

        port = int(settings.SMTP_PORT)
        context = ssl.create_default_context()

        if port == 465:                                    # implicit TLS
            server = smtplib.SMTP_SSL(settings.SMTP_SERVER, port,
                                      timeout=30, context=context)
        else:                                              # 587 / 25 → STARTTLS
            server = smtplib.SMTP(settings.SMTP_SERVER, port, timeout=30)

        try:
            server.ehlo()
            if port != 465 and server.has_extn("starttls"):
                server.starttls(context=context)
                server.ehlo()                              # ← REQUIRED after STARTTLS
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            refused = server.send_message(message, to_addrs=recipients)
        finally:
            try:
                server.quit()
            except Exception:
                pass

        if refused:
            raise RuntimeError(f"Rejected by server: {refused}")
        return f"Email sent to {', '.join(recipients)}"


send_email = celery_app.register_task(EmailTask())