import base64
import logging
from typing import List, Optional, Dict, Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def send_email_brevo(
    to_emails: List[str],
    subject: str,
    html_content: Optional[str] = None,
    text_content: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    sender_email: Optional[str] = None,
    sender_name: Optional[str] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    Envía email mediante la API de Brevo (HTTPS).
    - to_emails: lista de destinatarios
    - subject: asunto
    - html_content: contenido HTML (recomendado)
    - text_content: contenido plano (opcional)
    - attachments: lista [{ "name": "file.pdf", "content": "<base64>", "contentType": "application/pdf" }]
    """

    if not settings.BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY no está configurada.")

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    sender_email = sender_email or getattr(settings, "DEFAULT_FROM_EMAIL", None)
    sender_name = sender_name or getattr(settings, "SENDER_NAME", None)

    if not sender_email:
        raise ValueError("DEFAULT_FROM_EMAIL no está configurado.")

    payload: Dict[str, Any] = {
        "sender": {"email": sender_email},
        "to": [{"email": e} for e in to_emails],
        "subject": subject,
    }
    if sender_name:
        payload["sender"]["name"] = sender_name
    if html_content:
        payload["htmlContent"] = html_content
    if text_content:
        payload["textContent"] = text_content
    if attachments:
        payload["attachment"] = attachments

    resp = requests.post(BREVO_API_URL, headers=headers, json=payload, timeout=timeout)

    # Brevo normalmente devuelve 201 Created al enviar
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        # Log detallado para depurar
        logger.error("Brevo API error %s: %s", resp.status_code, data)
        raise RuntimeError(f"Error Brevo API ({resp.status_code}): {data}")

    return data


def make_pdf_attachment(filename: str, pdf_bytes: bytes) -> Dict[str, str]:
    """Crea el dict de adjunto en el formato que espera Brevo."""
    return {
        "name": filename,
        "content": _to_b64(pdf_bytes),
        "contentType": "application/pdf",
    }


def send_mail_api(
    subject: str,
    message: str,
    recipient_list: List[str],
    *,
    html_message: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Reemplazo sencillo para django.core.mail.send_mail usando Brevo API.
    - message → textContent
    - html_message → htmlContent
    """
    return send_email_brevo(
        to_emails=recipient_list,
        subject=subject,
        html_content=html_message,
        text_content=message,
        attachments=attachments,
    )
