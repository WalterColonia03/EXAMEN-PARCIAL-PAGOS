from __future__ import annotations

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("identity.urls")),
    path("", root_redirect, name="root"),
    path("pagos/", include("payments.urls")),
]
