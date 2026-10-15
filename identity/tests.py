from django.test import SimpleTestCase
from django.urls import reverse


class PublicRoutesTests(SimpleTestCase):
    def test_root_redirects_to_login_for_anonymous_users(self):
        response = self.client.get(reverse("root"))

        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)

    def test_login_page_is_available(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
