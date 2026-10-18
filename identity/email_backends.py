from __future__ import annotations

import json
import logging
from email.utils import parseaddr
from smtplib import SMTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


logger = logging.getLogger(__name__)


class TurboSMTPEmailBackend(BaseEmailBackend):
    """Deliver transactional messages through TurboSMTP's v2 JSON API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endpoint = settings.TURBOSMTP_API_URL
        self.consumer_key = settings.TURBOSMTP_CONSUMER_KEY
        self.consumer_secret = settings.TURBOSMTP_CONSUMER_SECRET
        self.timeout = settings.TURBOSMTP_TIMEOUT

    def _configuration_error(self) -> SMTPException | None:
        if not self.endpoint or not self.consumer_key or not self.consumer_secret:
            return SMTPException("TurboSMTP no está configurado para el envío de correo.")
        return None

    def _message_payload(self, message) -> dict[str, str]:
        sender = message.from_email or settings.DEFAULT_FROM_EMAIL
        _, sender_address = parseaddr(sender)
        payload = {
            "from": sender_address or sender,
            "to": ",".join(message.to),
            "subject": message.subject or "",
            "content": message.body or "",
        }
        if message.cc:
            payload["cc"] = ",".join(message.cc)
        if message.bcc:
            payload["bcc"] = ",".join(message.bcc)
        for alternative in message.alternatives:
            if alternative.mimetype == "text/html":
                payload["html_content"] = alternative.content
                break
        return payload

    @staticmethod
    def _provider_outcome(response_body: str) -> str:
        """Return a log-safe provider outcome without retaining response data."""
        try:
            payload = json.loads(response_body)
        except (TypeError, ValueError):
            return "INVALID_JSON"

        if not isinstance(payload, dict):
            return "UNEXPECTED_JSON"

        outcome = payload.get("message")
        if isinstance(outcome, str) and outcome.strip():
            return outcome.strip().upper()[:32]
        return "MISSING_MESSAGE"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        configuration_error = self._configuration_error()
        if configuration_error:
            if self.fail_silently:
                logger.error("No se envió correo: TurboSMTP no está configurado.")
                return 0
            raise configuration_error

        sent_count = 0
        for message in email_messages:
            if not message.recipients():
                continue
            request = Request(
                self.endpoint,
                data=json.dumps(self._message_payload(message)).encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "consumerKey": self.consumer_key,
                    "consumerSecret": self.consumer_secret,
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    response_body = response.read().decode("utf-8", errors="replace")
                result = json.loads(response_body) if response_body else {}
                if not 200 <= response.status < 300 or str(result.get("message", "")).upper() != "OK":
                    logger.warning(
                        "TurboSMTP rechazó un correo transaccional "
                        "(status=%s, outcome=%s).",
                        response.status,
                        self._provider_outcome(response_body),
                    )
                    raise SMTPException("TurboSMTP rechazó el envío del correo.")
            except HTTPError as error:
                response_body = error.read().decode("utf-8", errors="replace")
                logger.warning(
                    "TurboSMTP rechazó un correo transaccional "
                    "(status=%s, outcome=%s).",
                    error.code,
                    self._provider_outcome(response_body),
                )
                if not self.fail_silently:
                    raise SMTPException("No se pudo enviar el correo transaccional.") from error
            except (URLError, TimeoutError, ValueError, SMTPException) as error:
                logger.warning(
                    "TurboSMTP no aceptó un correo transaccional (category=%s).",
                    type(error).__name__,
                )
                if not self.fail_silently:
                    raise SMTPException("No se pudo enviar el correo transaccional.") from error
            else:
                sent_count += 1
        return sent_count
