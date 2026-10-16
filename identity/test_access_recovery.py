from __future__ import annotations

import re
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AccountAccessEvent, AccountRecoveryCode, Role
from .services import (
    issue_emergency_codes,
    issue_temporary_assistant_code,
    recovery_code_digest,
)


RECOVERY_CODE_PATTERN = re.compile(r"[A-F0-9]{4}(?:-[A-F0-9]{4}){7}")


class AccessRecoveryTests(TestCase):
    manager_password = "Gerente-Actual-2026!"
    assistant_password = "Asistente-Actual-2026!"

    def setUp(self):
        cache.clear()
        manager_role = Role.objects.create(code=Role.Code.MANAGER, name="Gerente")
        assistant_role = Role.objects.create(code=Role.Code.ASSISTANT, name="Asistente")
        account_model = get_user_model()
        self.manager = account_model.objects.create_user(
            "gerente@pagocontrol.local",
            self.manager_password,
            display_name="Carlos Mendoza",
            role=manager_role,
        )
        self.assistant = account_model.objects.create_user(
            "asistente@pagocontrol.local",
            self.assistant_password,
            display_name="Ana Valenzuela",
            role=assistant_role,
        )

    def test_login_accepts_email_with_mixed_case_and_external_spaces(self):
        response = self.client.post(
            reverse("login"),
            {
                "email": "  Gerente@PagoControl.Local  ",
                "password": self.manager_password,
            },
        )

        self.assertRedirects(
            response,
            reverse("payment-manager-dashboard"),
            fetch_redirect_response=False,
        )

    def test_invalid_login_preserves_email_and_offers_recovery(self):
        response = self.client.post(
            reverse("login"),
            {"email": "Gerente@PagoControl.Local", "password": "incorrecta"},
        )

        self.assertContains(response, "Gerente@PagoControl.Local")
        self.assertContains(response, reverse("access-recovery"))
        self.assertContains(response, "Mostrar")
        self.assertNotContains(response, "incorrecta")

    def test_each_role_reaches_its_expected_destination(self):
        manager_response = self.client.post(
            reverse("login"),
            {"email": self.manager.email, "password": self.manager_password},
        )
        self.assertRedirects(
            manager_response,
            reverse("payment-manager-dashboard"),
            fetch_redirect_response=False,
        )
        self.client.logout()

        assistant_response = self.client.post(
            reverse("login"),
            {"email": self.assistant.email, "password": self.assistant_password},
        )
        self.assertRedirects(
            assistant_response,
            reverse("payments-board"),
            fetch_redirect_response=False,
        )

    def test_login_attempts_are_temporarily_limited_without_revealing_account(self):
        payload = {"email": self.manager.email, "password": "incorrecta"}
        for _ in range(8):
            response = self.client.post(reverse("login"), payload)
            self.assertContains(response, "Credenciales inválidas")

        blocked = self.client.post(
            reverse("login"),
            {"email": self.manager.email, "password": self.manager_password},
        )

        self.assertContains(blocked, "Espera 15 minutos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_emergency_code_recovers_password_and_reveals_email_after_success(self):
        code = issue_emergency_codes(self.manager, actor=self.manager, count=1)[0]
        new_password = "Nube-Cobalto-8734!"

        response = self.client.post(
            reverse("access-recovery"),
            {
                "recovery_code": code.lower().replace("-", " "),
                "new_password": new_password,
                "confirm_password": new_password,
            },
        )

        self.assertRedirects(
            response,
            reverse("access-recovery-complete"),
            fetch_redirect_response=False,
        )
        complete = self.client.get(reverse("access-recovery-complete"))
        self.assertContains(complete, self.manager.email)
        self.assertIsNone(authenticate(username=self.manager.email, password=self.manager_password))
        self.assertIsNotNone(authenticate(username=self.manager.email, password=new_password))
        self.assertIsNotNone(AccountRecoveryCode.objects.get(account=self.manager).used_at)
        self.assertTrue(
            AccountAccessEvent.objects.filter(
                account=self.manager,
                event=AccountAccessEvent.Event.RECOVERY_SUCCEEDED,
            ).exists()
        )

    def test_recovery_code_is_single_use_and_response_does_not_reveal_an_account(self):
        code = issue_emergency_codes(self.assistant, actor=self.assistant, count=1)[0]
        new_password = "Bosque-Ambar-9517!"
        payload = {
            "recovery_code": code,
            "new_password": new_password,
            "confirm_password": new_password,
        }
        self.client.post(reverse("access-recovery"), payload)

        reused = self.client.post(reverse("access-recovery"), payload)

        self.assertEqual(reused.status_code, 200)
        self.assertContains(reused, "No pudimos validar el código")
        self.assertNotContains(reused, self.assistant.email)
        self.assertNotContains(reused, "Asistente")

    def test_password_recovery_revokes_existing_sessions(self):
        logged_client = Client()
        self.assertTrue(logged_client.login(email=self.manager.email, password=self.manager_password))
        self.assertGreater(Session.objects.count(), 0)
        code = issue_emergency_codes(self.manager, actor=self.manager, count=1)[0]

        self.client.post(
            reverse("access-recovery"),
            {
                "recovery_code": code,
                "new_password": "Rio-Verde-4862!",
                "confirm_password": "Rio-Verde-4862!",
            },
        )

        protected = logged_client.get(reverse("access-security"))
        self.assertEqual(protected.status_code, 302)
        self.assertIn(reverse("login"), protected.url)

    def test_expired_temporary_code_is_rejected(self):
        code, _ = issue_temporary_assistant_code(self.assistant, actor=self.manager)
        AccountRecoveryCode.objects.filter(account=self.assistant).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = self.client.post(
            reverse("access-recovery"),
            {
                "recovery_code": code,
                "new_password": "Lago-Azul-7391!",
                "confirm_password": "Lago-Azul-7391!",
            },
        )

        self.assertContains(response, "No pudimos validar el código")
        self.assertIsNotNone(
            authenticate(username=self.assistant.email, password=self.assistant_password)
        )

    def test_manager_can_issue_assistant_code_after_reauthentication(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("access-generate-assistant-code"),
            {"assistant": self.assistant.pk, "current_password": self.manager_password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.content.decode(), RECOVERY_CODE_PATTERN)
        code_record = AccountRecoveryCode.objects.get(account=self.assistant)
        self.assertEqual(code_record.kind, AccountRecoveryCode.Kind.TEMPORARY)
        self.assertEqual(code_record.created_by, self.manager)
        self.assertIsNotNone(code_record.expires_at)

    def test_assistant_cannot_issue_recovery_for_another_account(self):
        self.client.force_login(self.assistant)

        response = self.client.post(
            reverse("access-generate-assistant-code"),
            {"assistant": self.assistant.pk, "current_password": self.assistant_password},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            AccountRecoveryCode.objects.filter(kind=AccountRecoveryCode.Kind.TEMPORARY).exists()
        )

    def test_manager_must_reauthenticate_before_issuing_assistant_code(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("access-generate-assistant-code"),
            {"assistant": self.assistant.pk, "current_password": "incorrecta"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "contraseña actual no es correcta", status_code=400)
        self.assertFalse(
            AccountRecoveryCode.objects.filter(kind=AccountRecoveryCode.Kind.TEMPORARY).exists()
        )

    def test_generating_new_emergency_kit_revokes_previous_codes(self):
        previous = issue_emergency_codes(self.manager, actor=self.manager, count=2)
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("access-generate-emergency-codes"),
            {"current_password": self.manager_password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(RECOVERY_CODE_PATTERN.findall(response.content.decode())), 5)
        for code in previous:
            old_record = AccountRecoveryCode.objects.get(
                digest=recovery_code_digest(code)
            )
            self.assertIsNotNone(old_record.revoked_at)

    def test_weak_password_is_rejected_without_consuming_code(self):
        code = issue_emergency_codes(self.manager, actor=self.manager, count=1)[0]

        response = self.client.post(
            reverse("access-recovery"),
            {
                "recovery_code": code,
                "new_password": "1234567890",
                "confirm_password": "1234567890",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "contraseña es completamente numérica")
        self.assertIsNone(AccountRecoveryCode.objects.get(account=self.manager).used_at)

    def test_plain_recovery_code_is_never_stored(self):
        code = issue_emergency_codes(self.manager, actor=self.manager, count=1)[0]
        record = AccountRecoveryCode.objects.get(account=self.manager)

        self.assertNotEqual(record.digest, code)
        self.assertNotIn(code.replace("-", ""), record.digest.upper())

    def test_recovery_attempts_are_temporarily_limited(self):
        valid_code = issue_emergency_codes(self.manager, actor=self.manager, count=1)[0]
        password = "Mar-Celeste-8642!"
        invalid_payload = {
            "recovery_code": "0000-0000-0000-0000-0000-0000-0000-0000",
            "new_password": password,
            "confirm_password": password,
        }
        for _ in range(6):
            self.client.post(reverse("access-recovery"), invalid_payload)

        blocked = self.client.post(
            reverse("access-recovery"),
            {
                "recovery_code": valid_code,
                "new_password": password,
                "confirm_password": password,
            },
        )

        self.assertContains(blocked, "Espera 15 minutos")
        self.assertIsNone(AccountRecoveryCode.objects.get(account=self.manager).used_at)

    def test_recovery_page_is_public_and_security_page_requires_login(self):
        recovery = self.client.get(reverse("access-recovery"))
        security = self.client.get(reverse("access-security"))

        self.assertEqual(recovery.status_code, 200)
        self.assertContains(recovery, "Si eres asistente")
        self.assertEqual(security.status_code, 302)
        self.assertIn(reverse("login"), security.url)
