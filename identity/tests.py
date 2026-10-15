import re

from django.test import Client, TestCase
from django.urls import reverse


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
