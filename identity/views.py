from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Account, Role


@never_cache
def csrf_failure(request, reason=""):
    return render(request, "identity/csrf_failure.html", status=403)


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error_message = None
    if request.method == "POST":
        action = request.POST.get("action")
        # Quick demo login buttons
        if action == "demo_manager":
            user = Account.objects.filter(role__code=Role.Code.MANAGER).first()
            if user:
                login(request, user)
                return redirect("payment-manager-dashboard")
        elif action == "demo_assistant":
            user = Account.objects.filter(role__code=Role.Code.ASSISTANT).first()
            if user:
                login(request, user)
                return redirect("payments-board")
        else:
            email = request.POST.get("email", "").strip()
            password = request.POST.get("password", "")
            user = authenticate(request, username=email, password=password)
            if user is not None and user.is_active:
                login(request, user)
                next_url = request.GET.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect("dashboard")
            else:
                error_message = "Credenciales inválidas. Verifica tu correo y contraseña."

    return render(request, "identity/login.html", {"error_message": error_message})


@login_required
@require_GET
@never_cache
def dashboard(request):
    user_role = getattr(request.user, "role", None)
    if user_role and user_role.code == Role.Code.MANAGER:
        return redirect("payment-manager-dashboard")
    return redirect("payments-board")


@never_cache
@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect("login")


@never_cache
@login_required
@require_GET
def switch_role(request, role_code):
    """Convenience helper to switch between Gerente and Asistente during local testing."""
    target_user = Account.objects.filter(role__code=role_code.upper()).first()
    if target_user:
        login(request, target_user)
    if role_code.upper() == Role.Code.MANAGER:
        return redirect("payment-manager-dashboard")
    return redirect("payments-board")
