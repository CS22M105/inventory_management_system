"""Transactional email delivery helpers."""

from email.message import EmailMessage
import smtplib


def send_email(
    to,
    subject,
    body,
    *,
    provider,
    email_from,
    smtp_host,
    smtp_port,
    smtp_username,
    smtp_password,
    smtp_use_tls,
    smtp_use_ssl,
    app_env,
    logger,
):
    if provider == "smtp":
        if not smtp_host or not email_from:
            raise RuntimeError("SMTP_HOST and EMAIL_FROM must be set to send email.")

        message = EmailMessage()
        message["From"] = email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        if smtp_use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as smtp:
                if smtp_username:
                    smtp.login(smtp_username, smtp_password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
                if smtp_use_tls:
                    smtp.starttls()
                if smtp_username:
                    smtp.login(smtp_username, smtp_password)
                smtp.send_message(message)

        return True

    if provider:
        raise RuntimeError(
            f"Unsupported EMAIL_PROVIDER={provider!r}. Use EMAIL_PROVIDER=smtp."
        )

    if app_env == "production":
        raise RuntimeError("EMAIL_PROVIDER=smtp must be configured in production.")

    logger.info(
        "DEV EMAIL (not actually sent)\nTo: %s\nSubject: %s\n\n%s",
        to,
        subject,
        body,
    )
    return False
