import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Role


class PublicRoutesTests(TestCase):
    def test_root_redirects_to_login_for_anonymous_users(self):
        response = self.client.get(reverse("root"))

        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)

    def test_login_page_is_available(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])

    def test_login_accepts_a_fresh_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        login_url = reverse("login")
        page = csrf_client.get(login_url)
        token_match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content.decode(),
        )

        self.assertIsNotNone(token_match)
        response = csrf_client.post(
            login_url,
            {
                "email": "inexistente@ejemplo.invalid",
                "password": "contraseña-inválida",
                "csrfmiddlewaretoken": token_match.group(1),
            },
        )

        self.assertNotEqual(response.status_code, 403)

    def test_invalid_csrf_shows_a_recovery_page(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(reverse("login"), {"email": "inexistente@ejemplo.invalid"})

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Recarga la página", status_code=403)


class DemoAccessSecurityTests(TestCase):
    manager_email = "gerente.demo@pagos.invalid"
    assistant_email = "asistente.demo@pagos.invalid"

    def setUp(self):
        manager_role, _ = Role.objects.get_or_create(
            code=Role.Code.MANAGER, defaults={"name": "Gerente"}
        )
        assistant_role, _ = Role.objects.get_or_create(
            code=Role.Code.ASSISTANT, defaults={"name": "Asistente"}
        )
        admin_role, _ = Role.objects.get_or_create(
            code=Role.Code.ADMIN, defaults={"name": "Administrador"}
        )
        account_model = get_user_model()
        self.manager = account_model.objects.create_user(
            self.manager_email,
            "Contraseña-segura-2026",
            display_name="Gerente demo",
            role=manager_role,
        )
        self.assistant = account_model.objects.create_user(
            self.assistant_email,
            "Contraseña-segura-2026",
            display_name="Asistente demo",
            role=assistant_role,
        )
        self.admin = account_model.objects.create_user(
            "admin@pagos.invalid",
            "Contraseña-segura-2026",
            display_name="Administrador",
            role=admin_role,
            is_staff=True,
            is_superuser=True,
        )

    def test_demo_shortcuts_are_hidden_and_cannot_authenticate_by_default(self):
        page = self.client.get(reverse("login"))
        self.assertNotContains(page, "Acceso de demostración")

        response = self.client.post(reverse("login"), {"action": "demo_manager"})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "no está disponible")

    @override_settings(
        DEMO_ACCESS_ENABLED=True,
        DEMO_ACCESS_ALLOWED_HOSTS={"testserver"},
        DEBUG=True,
    )
    def test_development_shortcut_is_not_rendered_in_the_login_screen(self):
        page = self.client.get(reverse("login"))
        self.assertNotContains(page, "Acceso de demostración")

        response = self.client.post(reverse("login"), {"action": "demo_manager"})

        self.assertRedirects(
            response,
            reverse("payment-manager-dashboard"),
            fetch_redirect_response=False,
        )
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.manager.pk))

    @override_settings(DEBUG=False)
    def test_role_switch_is_post_only_and_disabled_by_default(self):
        self.client.force_login(self.manager)
        url = reverse("switch-role", args=[Role.Code.ASSISTANT])

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.manager.pk))

    @override_settings(
        DEMO_ACCESS_ENABLED=True,
        DEMO_ACCESS_ALLOWED_HOSTS={"testserver"},
        DEBUG=True,
    )
    def test_only_a_superuser_can_switch_configured_demo_roles(self):
        url = reverse("switch-role", args=[Role.Code.ASSISTANT])
        self.client.force_login(self.manager)
        self.assertEqual(self.client.post(url).status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.post(url)

        self.assertRedirects(response, reverse("payments-board"), fetch_redirect_response=False)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.assistant.pk))
