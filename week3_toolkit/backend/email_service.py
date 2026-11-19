import os
import smtplib
from email.message import EmailMessage


class EmailConfigurationError(RuntimeError):
    pass


def send_email(
    recipient: str,
    subject: str,
    content: str,
) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.qq.com").strip()
    port = int(os.environ.get("SMTP_PORT", "465"))
    username = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip() or username
    sender_name = (
        os.environ.get("SMTP_FROM_NAME", "情绪感知空间")
        .replace("\r", "")
        .replace("\n", "")
        .strip()
    )

    if not username or not password or not sender:
        raise EmailConfigurationError(
            "SMTP_USER、SMTP_PASSWORD 或 SMTP_FROM 未配置"
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{sender}>"
    message["To"] = recipient
    message.set_content(content)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise RuntimeError(f"邮件发送失败: {exc}") from exc
