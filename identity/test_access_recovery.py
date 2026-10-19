from __future__ import annotations

import re
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AccountAccessEvent, AccountRecoveryCode, Role
from .services import recovery_code_digest


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="PagoControl <no-reply@example.test>",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
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

    def request_email_code(self, account):
        response = self.client.post(
            reverse("access-recovery-email"),
            {"email": account.email},
        )
        self.assertRedirects(
            response,
            reverse("access-recovery-email-sent"),
            fetch_redirect_response=False,
        )
        match = re.search(r"\b(\d{8})\b", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

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

    def test_email_recovery_sends_a_short_lived_code_without_exposing_the_account(self):
        response = self.client.post(
            reverse("access-recovery-email"),
            {"email": "  Gerente@PagoControl.Local  "},
        )

        self.assertRedirects(
            response,
            reverse("access-recovery-email-sent"),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.get(reverse("access-recovery-email-sent")).status_code,
            200,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.manager.email])
        match = re.search(r"\b(\d{8})\b", mail.outbox[0].body)
        self.assertIsNotNone(match)
        code = match.group(1)
        record = AccountRecoveryCode.objects.get(
            account=self.manager,
            kind=AccountRecoveryCode.Kind.EMAIL,
        )
        self.assertTrue(record.is_available)
        self.assertIsNotNone(record.expires_at)

        recovered = self.client.post(
            reverse("access-recovery"),
            {
                "recovery_code": code,
                "new_password": "Lima-Cedro-2846!",
                "confirm_password": "Lima-Cedro-2846!",
            },
        )

        self.assertRedirects(
            recovered,
            reverse("access-recovery-complete"),
            fetch_redirect_response=False,
        )
        record.refresh_from_db()
        self.assertIsNotNone(record.used_at)

    def test_unknown_email_has_the_same_generic_response_and_sends_nothing(self):
        response = self.client.post(
            reverse("access-recovery-email"),
            {"email": "no-existe@example.test"},
        )

        self.assertRedirects(
            response,
            reverse("access-recovery-email-sent"),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(
            AccountRecoveryCode.objects.filter(kind=AccountRecoveryCode.Kind.EMAIL).exists()
        )

    def test_recovery_request_within_cooldown_preserves_the_active_code(self):
        first_code = self.request_email_code(self.manager)
        first_record = AccountRecoveryCode.objects.get(
            account=self.manager,
            kind=AccountRecoveryCode.Kind.EMAIL,
        )

        repeated = self.client.post(
            reverse("access-recovery-email"),
            {"email": self.manager.email},
        )

        self.assertRedirects(
            repeated,
            reverse("access-recovery-email-sent"),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            AccountRecoveryCode.objects.filter(
                account=self.manager,
                kind=AccountRecoveryCode.Kind.EMAIL,
            ).count(),
            1,
        )
        first_record.refresh_from_db()
        self.assertTrue(first_record.is_available)
        self.assertEqual(
            AccountAccessEvent.objects.filter(
                account=self.manager,
                event=AccountAccessEvent.Event.EMAIL_CODE_ISSUED,
            ).count(),
            1,
        )

        recovered = self.client.post(
            reverse("access-recovery"),
            {
                "recovery_code": first_code,
                "new_password": "Marea-Clara-2026!",
                "confirm_password": "Marea-Clara-2026!",
            },
        )

        self.assertRedirects(
            recovered,
            reverse("access-recovery-complete"),
            fetch_redirect_response=False,
        )

    def test_recovery_event_is_created_only_after_the_provider_accepts_the_email(self):
        self.request_email_code(self.manager)

        event = AccountAccessEvent.objects.get(
            account=self.manager,
            event=AccountAccessEvent.Event.EMAIL_CODE_ISSUED,
        )

        self.assertIn("aceptó el código de recuperación", event.summary)
        self.assertIn("ms", event.summary)

    def test_authenticated_user_can_change_password_and_keep_the_current_session(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("access-change-password"),
            {
                "current_password": self.manager_password,
                "new_password": "Cobre-Niebla-8547!",
                "confirm_password": "Cobre-Niebla-8547!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tu contraseña fue actualizada")
        self.assertIsNone(
            authenticate(username=self.manager.email, password=self.manager_password)
        )
        self.assertIsNotNone(
            authenticate(username=self.manager.email, password="Cobre-Niebla-8547!")
        )
        self.assertEqual(self.client.get(reverse("access-security")).status_code, 200)

    def test_recovery_rejects_a_legacy_external_code(self):
        legacy_code = "A" * 32
        record = AccountRecoveryCode.objects.create(
            account=self.manager,
            digest=recovery_code_digest(legacy_code),
            kind=AccountRecoveryCode.Kind.EMERGENCY,
        )

        response = self.client.post(
            reverse("access-recovery"),
            {
                "recovery_code": legacy_code,
                "new_password": "Nube-Cobalto-8734!",
                "confirm_password": "Nube-Cobalto-8734!",
            },
        )

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertIsNone(record.used_at)
        self.assertIsNotNone(
            authenticate(username=self.manager.email, password=self.manager_password)
        )

    def test_recovery_code_is_single_use_and_response_does_not_reveal_an_account(self):
        code = self.request_email_code(self.assistant)
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
        self.assertNotContains(reused, "Ana Valenzuela")

    def test_password_recovery_revokes_existing_sessions(self):
        logged_client = Client()
        self.assertTrue(logged_client.login(email=self.manager.email, password=self.manager_password))
        self.assertGreater(Session.objects.count(), 0)
        code = self.request_email_code(self.manager)

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

    def test_expired_email_code_is_rejected(self):
        code = self.request_email_code(self.assistant)
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

    def test_weak_password_is_rejected_without_consuming_email_code(self):
        code = self.request_email_code(self.manager)

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

    def test_plain_email_code_is_never_stored(self):
        code = self.request_email_code(self.manager)
        record = AccountRecoveryCode.objects.get(account=self.manager)

        self.assertNotEqual(record.digest, code)
        self.assertNotIn(code, record.digest)

    def test_recovery_attempts_are_temporarily_limited(self):
        valid_code = self.request_email_code(self.manager)
        password = "Mar-Celeste-8642!"
        invalid_payload = {
            "recovery_code": "00000000",
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

    def test_security_screen_no_longer_offers_saved_codes(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("access-security"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recuperación por correo")
        self.assertNotContains(response, "Códigos personales de emergencia")
        self.assertNotContains(response, "Emitir código temporal")

    def test_legacy_code_endpoints_are_removed(self):
        self.client.force_login(self.manager)

        self.assertEqual(self.client.post("/mi-acceso/codigos/").status_code, 404)
        self.assertEqual(
            self.client.post("/mi-acceso/asistente/codigo/").status_code,
            404,
        )

    def test_recovery_page_is_public_and_security_page_requires_login(self):
        recovery = self.client.get(reverse("access-recovery"))
        security = self.client.get(reverse("access-security"))

        self.assertEqual(recovery.status_code, 200)
        self.assertContains(recovery, "que enviamos al correo de tu cuenta")
        self.assertNotContains(recovery, "códigos de respaldo")
        self.assertEqual(security.status_code, 302)
        self.assertIn(reverse("login"), security.url)
