"""발주서 발송(이메일 SMTP / 웹훅) 및 운영 알림(텔레그램 / 디스코드)."""
import smtplib
from email.message import EmailMessage

import requests

from ..common import log


def send_email(smtp: dict, to: str, subject: str, body: str, attachments: list[tuple[str, bytes, str]]) -> None:
    if not smtp.get("host"):
        raise RuntimeError("SMTP 설정이 없어 이메일을 발송할 수 없습니다.")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = smtp["sender"], to, subject
    msg.set_content(body)
    for filename, data, mime in attachments:
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
    with smtplib.SMTP(smtp["host"], smtp["port"], timeout=20) as server:
        if smtp.get("use_tls"):
            server.starttls()
        if smtp.get("user"):
            server.login(smtp["user"], smtp["password"])
        server.send_message(msg)


def send_webhook(url: str, payload: dict) -> None:
    res = requests.post(url, json=payload, timeout=15)
    res.raise_for_status()


def notify(text: str, *, telegram_token: str = "", telegram_chat_id: str = "", discord_url: str = "") -> None:
    """운영 알림 봇. 설정된 채널로만 전송하며 실패해도 본 작업은 계속 진행."""
    try:
        if telegram_token and telegram_chat_id:
            requests.post(f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                          json={"chat_id": telegram_chat_id, "text": text}, timeout=10)
        if discord_url:
            requests.post(discord_url, json={"content": text}, timeout=10)
    except requests.RequestException as exc:
        log.warning("알림 전송 실패: %s", exc)
