from __future__ import annotations

import hashlib

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import CurrentPasswordForm, RecoverAccessForm, TemporaryAssistantCodeForm
from .models import Account, AccountAccessEvent, Role
from .services import (
    InvalidRecoveryCode,
    available_emergency_code_count,
    issue_emergency_codes,
    issue_temporary_assistant_code,
    recover_account_access,
)


DEMO_EMAIL_SETTINGS = {
    Role.Code.MANAGER: "DEMO_MANAGER_EMAIL",
    Role.Code.ASSISTANT: "DEMO_ASSISTANT_EMAIL",
}

RECOVERY_ATTEMPT_LIMIT = 6
RECOVERY_ATTEMPT_WINDOW_SECONDS = 15 * 60
LOGIN_ATTEMPT_LIMIT = 8
LOGIN_ATTEMPT_WINDOW_SECONDS = 15 * 60


def demo_access_is_available(request) -> bool:
    """Return whether the explicitly opt-in local demo shortcuts may be shown."""
    if not settings.DEBUG or not settings.DEMO_ACCESS_ENABLED:
        return False

    host = request.get_host().split(":", 1)[0].rstrip(".").lower()
    return host in settings.DEMO_ACCESS_ALLOWED_HOSTS


def demo_account_for(role_code: str) -> Account | None:
    setting_name = DEMO_EMAIL_SETTINGS.get(role_code)
    if not setting_name:
        return None

    email = getattr(settings, setting_name, "")
    if not email:
        return None
    return (
        Account.objects.select_related("role")
        .filter(
            email_normalized=Account.normalize_email(email),
            role__code=role_code,
            is_active=True,
        )
        .first()
    )


def safe_next_url(request) -> str:
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


def destination_for(user: Account, request) -> str:
    return safe_next_url(request) or (
        "payment-manager-dashboard"
        if user.role.code == Role.Code.MANAGER
        else "payments-board"
    )


@never_cache
def csrf_failure(request, reason=""):
    return render(request, "identity/csrf_failure.html", status=403)


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error_message = None
    submitted_email = ""
    demo_access_enabled = demo_access_is_available(request)
    if request.method == "POST":
        action = request.POST.get("action")
        if action in {"demo_manager", "demo_assistant"}:
            if not demo_access_enabled:
                error_message = "Esta opción de acceso no está disponible."
            else:
                role_code = (
                    Role.Code.MANAGER
                    if action == "demo_manager"
                    else Role.Code.ASSISTANT
                )
                user = demo_account_for(role_code)
                if user:
                    login(request, user)
                    return redirect(destination_for(user, request))
                error_message = "No fue posible acceder con la cuenta seleccionada."
        else:
            submitted_email = request.POST.get("email", "").strip()
            email = Account.normalize_email(submitted_email)
            password = request.POST.get("password", "")
            remote_address = request.META.get("REMOTE_ADDR", "unknown")
            login_fingerprint = hashlib.sha256(
                f"{remote_address}|{email}".encode("utf-8")
            ).hexdigest()
            login_rate_key = f"access-login:{login_fingerprint}"
            failed_attempts = int(cache.get(login_rate_key, 0))
            user = None
            if failed_attempts < LOGIN_ATTEMPT_LIMIT:
                user = authenticate(request, username=email, password=password)
            if user is not None and user.is_active:
                cache.delete(login_rate_key)
                login(request, user)
                return redirect(destination_for(user, request))
            if failed_attempts >= LOGIN_ATTEMPT_LIMIT:
                error_message = (
                    "No pudimos iniciar sesión. Espera 15 minutos antes de intentarlo nuevamente."
                )
            else:
                cache.set(
                    login_rate_key,
                    failed_attempts + 1,
                    LOGIN_ATTEMPT_WINDOW_SECONDS,
                )
                error_message = "Credenciales inválidas. Verifica tu correo y contraseña."

    return render(
        request,
        "identity/login.html",
        {
            "demo_access_enabled": demo_access_enabled,
            "error_message": error_message,
            "submitted_email": submitted_email,
        },
    )


def _recovery_rate_key(request) -> str:
    remote_address = request.META.get("REMOTE_ADDR", "unknown")
    fingerprint = hashlib.sha256(remote_address.encode("utf-8")).hexdigest()
    return f"access-recovery:{fingerprint}"


def _record_failed_recovery(request) -> int:
    key = _recovery_rate_key(request)
    failures = int(cache.get(key, 0)) + 1
    cache.set(key, failures, RECOVERY_ATTEMPT_WINDOW_SECONDS)
    return failures


@never_cache
@require_http_methods(["GET", "POST"])
def recover_access(request):
    if request.user.is_authenticated:
        return redirect("access-security")

    form = RecoverAccessForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        key = _recovery_rate_key(request)
        if int(cache.get(key, 0)) >= RECOVERY_ATTEMPT_LIMIT:
            AccountAccessEvent.objects.create(
                event=AccountAccessEvent.Event.RECOVERY_FAILED,
                summary="Se bloqueó temporalmente una verificación de recuperación por exceso de intentos.",
            )
            form.add_error(
                "recovery_code",
                "No pudimos validar el código. Espera 15 minutos antes de intentarlo nuevamente.",
            )
        else:
            try:
                account = recover_account_access(
                    form.cleaned_data["recovery_code"],
                    form.cleaned_data["new_password"],
                )
            except InvalidRecoveryCode:
                _record_failed_recovery(request)
                AccountAccessEvent.objects.create(
                    event=AccountAccessEvent.Event.RECOVERY_FAILED,
                    summary="Se rechazó una verificación de recuperación sin identificar una cuenta.",
                )
                form.add_error(
                    "recovery_code",
                    "No pudimos validar el código. Revisa que esté completo, vigente y sin usar.",
                )
            except ValidationError as error:
                form.add_error("new_password", error)
            else:
                cache.delete(key)
                request.session["recovered_account_email"] = account.email
                return redirect("access-recovery-complete")

    return render(request, "identity/recover_access.html", {"form": form})


@never_cache
@require_GET
def recovery_complete(request):
    recovered_email = request.session.pop("recovered_account_email", None)
    if not recovered_email:
        return redirect("access-recovery")
    return render(
        request,
        "identity/recovery_complete.html",
        {"recovered_email": recovered_email},
    )


def _security_context(request, **extra):
    context = {
        "emergency_form": CurrentPasswordForm(),
        "temporary_form": TemporaryAssistantCodeForm()
        if request.user.role.code == Role.Code.MANAGER
        else None,
        "available_code_count": available_emergency_code_count(request.user),
        "access_events": AccountAccessEvent.objects.filter(account=request.user)[:8],
    }
    context.update(extra)
    return context


@never_cache
@login_required
@require_GET
def access_security(request):
    return render(request, "identity/access_security.html", _security_context(request))


@never_cache
@login_required
@require_POST
def generate_emergency_codes(request):
    form = CurrentPasswordForm(request.POST)
    if not form.is_valid() or not request.user.check_password(
        form.cleaned_data.get("current_password", "")
    ):
        if form.is_valid():
            form.add_error("current_password", "La contraseña actual no es correcta.")
        return render(
            request,
            "identity/access_security.html",
            _security_context(request, emergency_form=form),
            status=400,
        )

    codes = issue_emergency_codes(request.user, actor=request.user)
    return render(
        request,
        "identity/access_security.html",
        _security_context(request, new_emergency_codes=codes),
    )


@never_cache
@login_required
@require_POST
def generate_assistant_temporary_code(request):
    if request.user.role.code != Role.Code.MANAGER:
        raise PermissionDenied("Solo el gerente puede recuperar el acceso de un asistente.")

    form = TemporaryAssistantCodeForm(request.POST)
    if not form.is_valid() or not request.user.check_password(
        form.cleaned_data.get("current_password", "")
    ):
        if form.is_valid():
            form.add_error("current_password", "La contraseña actual no es correcta.")
        return render(
            request,
            "identity/access_security.html",
            _security_context(request, temporary_form=form),
            status=400,
        )

    code, expires_at = issue_temporary_assistant_code(
        form.cleaned_data["assistant"],
        actor=request.user,
    )
    return render(
        request,
        "identity/access_security.html",
        _security_context(
            request,
            temporary_code=code,
            temporary_code_account=form.cleaned_data["assistant"],
            temporary_code_expires=timezone.localtime(expires_at),
        ),
    )


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
@require_POST
def switch_role(request, role_code):
    """Let an opted-in local superuser test a configured demo account only."""
    if not demo_access_is_available(request) or not request.user.is_superuser:
        raise PermissionDenied("Esta acción no está disponible.")

    target_role = role_code.upper()
    if target_role not in DEMO_EMAIL_SETTINGS:
        raise Http404("Rol no encontrado.")

    target_user = demo_account_for(target_role)
    if not target_user:
        raise Http404("Cuenta no encontrada.")
    login(request, target_user)
    return redirect(destination_for(target_user, request))
