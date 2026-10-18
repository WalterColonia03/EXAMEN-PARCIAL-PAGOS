from __future__ import annotations

from django.shortcuts import redirect


class RequireAssistantOnboardingMiddleware:
    """Keep a newly provisioned assistant outside operational pages until verified."""

    allowed_view_names = {
        "account_onboarding",
        "logout_view",
        "csrf_failure",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        if not user.is_authenticated or not getattr(user, "must_change_password", False):
            return None
        if (
            view_func.__module__ == "identity.views"
            and view_func.__name__ in self.allowed_view_names
        ):
            return None
        return redirect("account-onboarding")
