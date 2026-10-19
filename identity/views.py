from __future__ import annotations

import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import (
    AccountOnboardingForm,
    AssistantAccountForm,
    ChangePasswordForm,
    RecoverAccessForm,
    RequestEmailRecoveryForm,
)
from .authorization import roles_required
from .models import Account, AccountAccessEvent, Role
from .services import (
    complete_assistant_onboarding,
    create_assistant_account,
    InvalidRecoveryCode,
    change_account_password,
    issue_email_recovery_code,
    RecoveryEmailResendTooSoon,
    recover_account_access,
    RecoveryEmailDeliveryError,
    resend_assistant_verification,
    revoke_email_recovery_codes,
    send_email_recovery_code,
    set_assistant_account_active,
)


DEMO_EMAIL_SETTINGS = {
    Role.Code.MANAGER: "DEMO_MANAGER_EMAIL",
    Role.Code.ASSISTANT: "DEMO_ASSISTANT_EMAIL",
}

RECOVERY_ATTEMPT_LIMIT = 6
RECOVERY_ATTEMPT_WINDOW_SECONDS = 15 * 60
LOGIN_ATTEMPT_LIMIT = 8
LOGIN_ATTEMPT_WINDOW_SECONDS = 15 * 60
EMAIL_RECOVERY_REQUEST_LIMIT = 5
EMAIL_RECOVERY_REQUEST_WINDOW_SECONDS = 15 * 60


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
    if user.must_change_password:
        return "account-onboarding"
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


def _email_recovery_rate_key(request, email: str) -> str:
    remote_address = request.META.get("REMOTE_ADDR", "unknown")
    fingerprint = hashlib.sha256(
        f"{remote_address}|{email}".encode("utf-8")
    ).hexdigest()
    return f"access-email-recovery:{fingerprint}"


@never_cache
@require_http_methods(["GET", "POST"])
def request_email_recovery(request):
    if request.user.is_authenticated:
        return redirect("access-security")

    form = RequestEmailRecoveryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        key = _email_recovery_rate_key(request, email)
        requests = int(cache.get(key, 0))
        if requests < EMAIL_RECOVERY_REQUEST_LIMIT:
            account = (
                Account.objects.filter(email_normalized=email, is_active=True)
                .select_related("role")
                .first()
            )
            if account:
                try:
                    code, expires_at = issue_email_recovery_code(account)
                except RecoveryEmailResendTooSoon:
                    pass
                else:
                    try:
                        send_email_recovery_code(account, code, expires_at)
                    except RecoveryEmailDeliveryError:
                        revoke_email_recovery_codes(account)
            cache.set(
                key,
                requests + 1,
                EMAIL_RECOVERY_REQUEST_WINDOW_SECONDS,
            )
        return redirect("access-recovery-email-sent")

    return render(
        request,
        "identity/request_email_recovery.html",
        {
            "form": form,
            "resend_cooldown_seconds": settings.EMAIL_RECOVERY_RESEND_COOLDOWN_SECONDS,
        },
    )


@never_cache
@require_GET
def recovery_email_sent(request):
    return render(
        request,
        "identity/recovery_email_sent.html",
        {"resend_cooldown_seconds": settings.EMAIL_RECOVERY_RESEND_COOLDOWN_SECONDS},
    )


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

    return render(
        request,
        "identity/recover_access.html",
        {
            "form": form,
            "resend_cooldown_seconds": settings.EMAIL_RECOVERY_RESEND_COOLDOWN_SECONDS,
        },
    )


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


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def account_onboarding(request):
    """Require a newly created assistant to prove mailbox ownership first."""
    if not request.user.must_change_password:
        return redirect("dashboard")

    form = AccountOnboardingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            account = complete_assistant_onboarding(
                account=request.user,
                code=form.cleaned_data["verification_code"],
                new_password=form.cleaned_data["new_password"],
                keep_session_key=request.session.session_key,
            )
        except InvalidRecoveryCode:
            form.add_error(
                "verification_code",
                "No pudimos validar el código. Solicita al gerente uno nuevo si venció.",
            )
        except ValidationError as error:
            form.add_error("new_password", error)
        else:
            update_session_auth_hash(request, account)
            messages.success(
                request,
                "Correo verificado y contraseña personal creada. Ya puedes usar PagoControl.",
            )
            return redirect("dashboard")

    return render(request, "identity/account_onboarding.html", {"form": form})


@never_cache
@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
def manager_assistant_accounts(request):
    form = AssistantAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not request.user.check_password(form.cleaned_data["manager_password"]):
            form.add_error("manager_password", "La contraseña de gerente no es correcta.")
        else:
            try:
                assistant, _ = create_assistant_account(
                    actor=request.user,
                    display_name=form.cleaned_data["display_name"],
                    email=form.cleaned_data["email"],
                    temporary_password=form.cleaned_data["new_password"],
                )
            except RecoveryEmailDeliveryError:
                form.add_error(
                    None,
                    "No se pudo enviar el código de verificación. La cuenta no fue creada.",
                )
            except (ValidationError, ValueError) as error:
                form.add_error("email", error)
            else:
                messages.success(
                    request,
                    f"Cuenta creada para {assistant.display_name}. El asistente debe verificar su correo y reemplazar la contraseña temporal.",
                )
                return redirect("manager-assistant-accounts")

    status = 400 if request.method == "POST" and form.errors else 200
    assistants = Account.objects.filter(role__code=Role.Code.ASSISTANT).order_by(
        "is_active", "email_normalized"
    )
    return render(
        request,
        "identity/manager_assistant_accounts.html",
        {"form": form, "assistants": assistants},
        status=status,
    )


@never_cache
@roles_required(Role.Code.MANAGER)
@require_POST
def resend_assistant_account_verification(request, account_id):
    assistant = get_object_or_404(
        Account.objects.select_related("role"),
        pk=account_id,
        role__code=Role.Code.ASSISTANT,
    )
    try:
        resend_assistant_verification(assistant, actor=request.user)
    except RecoveryEmailDeliveryError:
        messages.error(
            request,
            "No se pudo enviar el código de verificación. Revisa la configuración SMTP antes de reintentar.",
        )
    except (PermissionError, ValueError) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Se envió un nuevo código de verificación a {assistant.email}.")
    return redirect("manager-assistant-accounts")


@never_cache
@roles_required(Role.Code.MANAGER)
@require_POST
def set_managed_assistant_active(request, account_id, active):
    assistant = get_object_or_404(
        Account.objects.select_related("role"),
        pk=account_id,
        role__code=Role.Code.ASSISTANT,
    )
    try:
        set_assistant_account_active(assistant, actor=request.user, active=active)
    except RecoveryEmailDeliveryError:
        messages.error(
            request,
            "No se pudo reactivar la cuenta porque falló el envío de verificación. La cuenta sigue desactivada.",
        )
    except PermissionError as error:
        messages.error(request, str(error))
    else:
        action = "reactivada" if active else "desactivada"
        messages.success(request, f"La cuenta de {assistant.display_name} fue {action}.")
    return redirect("manager-assistant-accounts")


def _security_context(request, **extra):
    context = {
        "password_form": ChangePasswordForm(),
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
def change_password(request):
    form = ChangePasswordForm(request.POST)
    if not form.is_valid() or not request.user.check_password(
        form.cleaned_data.get("current_password", "")
    ):
        if form.is_valid():
            form.add_error("current_password", "La contraseña actual no es correcta.")
        return render(
            request,
            "identity/access_security.html",
            _security_context(request, password_form=form),
            status=400,
        )

    account = change_account_password(
        request.user,
        form.cleaned_data["new_password"],
        keep_session_key=request.session.session_key,
    )
    update_session_auth_hash(request, account)
    return render(
        request,
        "identity/access_security.html",
        _security_context(request, password_change_success=True),
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
