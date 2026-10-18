from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

from django.core.mail import EmailMultiAlternatives, get_connection
from django.test import SimpleTestCase, override_settings


class FakeResponse(BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


@override_settings(
    EMAIL_BACKEND="identity.email_backends.TurboSMTPEmailBackend",
    DEFAULT_FROM_EMAIL="PagoControl <acceso@example.com>",
    TURBOSMTP_API_URL="https://mail.example.test/api/v2/mail/send",
    TURBOSMTP_CONSUMER_KEY="consumer-key-test",
    TURBOSMTP_CONSUMER_SECRET="consumer-secret-test",
    TURBOSMTP_TIMEOUT=7,
)
class TurboSMTPEmailBackendTests(SimpleTestCase):
    @patch("identity.email_backends.urlopen")
    def test_sends_json_with_consumer_headers(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeResponse(b'{"message":"OK","mid":"message-1"}')
        message = EmailMultiAlternatives(
            subject="Código de prueba",
            body="Texto seguro",
            to=["destinatario@example.com"],
        )
        message.attach_alternative("<strong>Texto seguro</strong>", "text/html")

        sent = get_connection().send_messages([message])

        self.assertEqual(sent, 1)
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 7)
        self.assertEqual(request.full_url, "https://mail.example.test/api/v2/mail/send")
        self.assertEqual(request.get_header("Consumerkey"), "consumer-key-test")
        self.assertEqual(request.get_header("Consumersecret"), "consumer-secret-test")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["from"], "acceso@example.com")
        self.assertEqual(payload["to"], "destinatario@example.com")
        self.assertEqual(payload["html_content"], "<strong>Texto seguro</strong>")

    @override_settings(TURBOSMTP_CONSUMER_SECRET="")
    def test_rejects_missing_consumer_secret(self):
        message = EmailMultiAlternatives(
            subject="Código de prueba",
            body="Texto seguro",
            to=["destinatario@example.com"],
        )

        with self.assertRaisesMessage(Exception, "TurboSMTP no está configurado"):
            get_connection().send_messages([message])

    @patch("identity.email_backends.urlopen")
    def test_logs_provider_http_status_without_sensitive_request_data(self, mocked_urlopen):
        mocked_urlopen.side_effect = HTTPError(
            "https://mail.example.test/api/v2/mail/send",
            401,
            "Unauthorized",
            None,
            BytesIO(b'{"message":"error"}'),
        )
        message = EmailMultiAlternatives(
            subject="Código de prueba",
            body="Texto seguro",
            to=["destinatario@example.com"],
        )

        with self.assertLogs("identity.email_backends", level="WARNING") as captured:
            with self.assertRaisesMessage(Exception, "No se pudo enviar el correo transaccional"):
                get_connection().send_messages([message])

        log_output = "\n".join(captured.output)
        self.assertIn("status=401", log_output)
        self.assertIn("outcome=ERROR", log_output)
        self.assertNotIn("consumer-key-test", log_output)
        self.assertNotIn("destinatario@example.com", log_output)
