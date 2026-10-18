from __future__ import annotations

import re

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AccountAccessEvent, AccountRecoveryCode, Role


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="PagoControl <acceso@example.test>",
)
class AssistantAccountManagementTests(TestCase):
    manager_password = "Gerente-Seguro-2048!"
    temporary_password = "Temporal-Segura-2048!"

    def setUp(self):
        manager_role, _ = Role.objects.get_or_create(
            code=Role.Code.MANAGER,
            defaults={"name": "Gerente"},
        )
        assistant_role, _ = Role.objects.get_or_create(
            code=Role.Code.ASSISTANT,
            defaults={"name": "Asistente"},
        )
        account_model = get_user_model()
        self.manager = account_model.objects.create_user(
            "gerente@example.com",
            self.manager_password,
            display_name="Gerente de pruebas",
            role=manager_role,
        )
        self.existing_assistant = account_model.objects.create_user(
            "asistente.existente@example.com",
            "Asistente-Seguro-2048!",
            display_name="Asistente existente",
            role=assistant_role,
            email_verified_at=timezone.now(),
        )

    def create_payload(self, **overrides):
        payload = {
            "display_name": "Ana Verificada",
            "email": "ana.verificada@gmail.com",
            "new_password": self.temporary_password,
            "confirm_password": self.temporary_password,
            "manager_password": self.manager_password,
        }
        payload.update(overrides)
        return payload

    def test_manager_creates_pending_assistant_and_inbox_code(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("manager-assistant-accounts"),
            self.create_payload(),
        )

        self.assertRedirects(
            response,
            reverse("manager-assistant-accounts"),
            fetch_redirect_response=False,
        )
        assistant = get_user_model().objects.get(email="ana.verificada@gmail.com")
        self.assertTrue(assistant.is_active)
        self.assertTrue(assistant.must_change_password)
        self.assertIsNone(assistant.email_verified_at)
        self.assertTrue(assistant.check_password(self.temporary_password))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [assistant.email])
        code = re.search(r"\b(\d{8})\b", mail.outbox[0].body).group(1)
        record = AccountRecoveryCode.objects.get(account=assistant)
        self.assertEqual(record.kind, AccountRecoveryCode.Kind.EMAIL_VERIFY)
        self.assertNotIn(code, record.digest)
        self.assertTrue(
            AccountAccessEvent.objects.filter(
                account=assistant,
                actor=self.manager,
                event=AccountAccessEvent.Event.ASSISTANT_ACCOUNT_CREATED,
            ).exists()
        )

    def test_pending_assistant_must_verify_email_and_replace_temporary_password(self):
        self.client.force_login(self.manager)
        self.client.post(reverse("manager-assistant-accounts"), self.create_payload())
        assistant = get_user_model().objects.get(email="ana.verificada@gmail.com")
        code = re.search(r"\b(\d{8})\b", mail.outbox[0].body).group(1)

        assistant_client = Client()
        login_response = assistant_client.post(
            reverse("login"),
            {"email": assistant.email, "password": self.temporary_password},
        )
        self.assertRedirects(
            login_response,
            reverse("account-onboarding"),
            fetch_redirect_response=False,
        )
        protected = assistant_client.get(reverse("payments-board"))
        self.assertRedirects(
            protected,
            reverse("account-onboarding"),
            fetch_redirect_response=False,
        )

        own_password = "Personal-Resguardada-2048!"
        activation = assistant_client.post(
            reverse("account-onboarding"),
            {
                "verification_code": code,
                "new_password": own_password,
                "confirm_password": own_password,
            },
        )
        self.assertRedirects(activation, reverse("dashboard"), fetch_redirect_response=False)
        assistant.refresh_from_db()
        self.assertFalse(assistant.must_change_password)
        self.assertIsNotNone(assistant.email_verified_at)
        self.assertIsNone(authenticate(username=assistant.email, password=self.temporary_password))
        self.assertIsNotNone(authenticate(username=assistant.email, password=own_password))

    def test_manager_can_deactivate_and_reactivate_an_assistant(self):
        assistant_client = Client()
        self.assertTrue(
            assistant_client.login(
                email=self.existing_assistant.email,
                password="Asistente-Seguro-2048!",
            )
        )
        self.client.force_login(self.manager)

        deactivated = self.client.post(
            reverse("manager-assistant-deactivate", args=[self.existing_assistant.pk])
        )
        self.assertRedirects(
            deactivated,
            reverse("manager-assistant-accounts"),
            fetch_redirect_response=False,
        )
        self.existing_assistant.refresh_from_db()
        self.assertFalse(self.existing_assistant.is_active)
        self.assertEqual(
            assistant_client.get(reverse("payments-board")).status_code,
            302,
        )

        reactivated = self.client.post(
            reverse("manager-assistant-reactivate", args=[self.existing_assistant.pk])
        )
        self.assertRedirects(
            reactivated,
            reverse("manager-assistant-accounts"),
            fetch_redirect_response=False,
        )
        self.existing_assistant.refresh_from_db()
        self.assertTrue(self.existing_assistant.is_active)
        self.assertTrue(
            AccountAccessEvent.objects.filter(
                account=self.existing_assistant,
                event=AccountAccessEvent.Event.ASSISTANT_ACCOUNT_REACTIVATED,
            ).exists()
        )

    def test_creation_rejects_reserved_or_test_email_domains(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("manager-assistant-accounts"),
            self.create_payload(email="asistente@pagocontrol.invalid"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "correo real", status_code=400)
        self.assertFalse(
            get_user_model().objects.filter(email="asistente@pagocontrol.invalid").exists()
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_creation_requires_a_strong_temporary_password(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("manager-assistant-accounts"),
            self.create_payload(new_password="Corta123", confirm_password="Corta123"),
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "10 caracteres", status_code=400)
        self.assertFalse(get_user_model().objects.filter(email="ana.verificada@gmail.com").exists())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="",
        EMAIL_HOST="",
    )
    def test_creation_is_rolled_back_when_email_verification_cannot_be_sent(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("manager-assistant-accounts"),
            self.create_payload(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "cuenta no fue creada", status_code=400)
        self.assertFalse(get_user_model().objects.filter(email="ana.verificada@gmail.com").exists())

    def test_assistant_cannot_open_the_management_panel(self):
        self.client.force_login(self.existing_assistant)

        response = self.client.get(reverse("manager-assistant-accounts"))

        self.assertEqual(response.status_code, 403)
