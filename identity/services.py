from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.contrib.sessions.models import Session
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import Account, AccountAccessEvent, AccountRecoveryCode, Role


EMAIL_RECOVERY_CODE_LENGTH = 8
EMAIL_RECOVERY_CODE_LIFETIME = timedelta(minutes=15)
EMAIL_VERIFICATION_CODE_LIFETIME = timedelta(minutes=15)
NON_DELIVERABLE_EMAIL_DOMAINS = {
    "localhost",
    "example.com",
    "example.invalid",
    "example.test",
}
NON_DELIVERABLE_EMAIL_SUFFIXES = (".invalid", ".local", ".test", ".example")

logger = logging.getLogger(__name__)


def email_delivery_is_configured() -> bool:
    turbo_backend = "identity.email_backends.TurboSMTPEmailBackend"
    if settings.EMAIL_BACKEND == turbo_backend:
        return bool(
            settings.DEFAULT_FROM_EMAIL
            and settings.TURBOSMTP_CONSUMER_KEY
            and settings.TURBOSMTP_CONSUMER_SECRET
            and settings.TURBOSMTP_API_URL
        )
    smtp_backend = "django.core.mail.backends.smtp.EmailBackend"
    if settings.EMAIL_BACKEND == smtp_backend:
        return bool(settings.DEFAULT_FROM_EMAIL and settings.EMAIL_HOST)
    return bool(settings.DEFAULT_FROM_EMAIL)


class InvalidRecoveryCode(Exception):
    """Raised without disclosing whether a recovery code ever existed."""


class RecoveryEmailDeliveryError(Exception):
    """Raised when a password-recovery email cannot be delivered."""


def _validate_provisioned_email(email: str) -> str:
    normalized = Account.normalize_email(email)
    validate_email(normalized)
    domain = normalized.rsplit("@", 1)[-1]
    if domain in NON_DELIVERABLE_EMAIL_DOMAINS or domain.endswith(
        NON_DELIVERABLE_EMAIL_SUFFIXES
    ):
        raise ValidationError(
            "Indica un correo real que pueda recibir el código de verificación."
        )
    return normalized


def normalize_recovery_code(value: str) -> str:
    return "".join(character for character in value.upper() if character in "0123456789ABCDEF")


def recovery_code_digest(value: str) -> str:
    normalized = normalize_recovery_code(value)
    return salted_hmac(
        "identity.account-recovery",
        normalized,
        algorithm="sha256",
    ).hexdigest()


def _new_email_recovery_code() -> tuple[str, str]:
    code = f"{secrets.randbelow(10 ** EMAIL_RECOVERY_CODE_LENGTH):0{EMAIL_RECOVERY_CODE_LENGTH}d}"
    return code, recovery_code_digest(code)


def _revoke_available_codes(account: Account, kind: str) -> int:
    now = timezone.now()
    return AccountRecoveryCode.objects.filter(
        account=account,
        kind=kind,
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=now)


@transaction.atomic
def issue_email_recovery_code(account: Account) -> tuple[str, datetime]:
    """Create one short-lived code without retaining its plaintext value."""
    if not account.is_active:
        raise PermissionError("La cuenta no está activa.")

    account = Account.objects.select_for_update().get(pk=account.pk)
    revoked = _revoke_available_codes(account, AccountRecoveryCode.Kind.EMAIL)
    if revoked:
        AccountAccessEvent.objects.create(
            account=account,
            event=AccountAccessEvent.Event.CODES_REVOKED,
            summary="Se reemplazó un código de recuperación enviado por correo.",
        )

    expires_at = timezone.now() + EMAIL_RECOVERY_CODE_LIFETIME
    for _ in range(3):
        plain_code, digest = _new_email_recovery_code()
        try:
            with transaction.atomic():
                AccountRecoveryCode.objects.create(
                    account=account,
                    digest=digest,
                    kind=AccountRecoveryCode.Kind.EMAIL,
                    expires_at=expires_at,
                )
        except IntegrityError:
            continue
        break
    else:
        raise RuntimeError("No se pudo generar un código de recuperación único.")

    AccountAccessEvent.objects.create(
        account=account,
        event=AccountAccessEvent.Event.EMAIL_CODE_ISSUED,
        summary="Se envió un código de recuperación por correo con vigencia de 15 minutos.",
    )
    return plain_code, expires_at


@transaction.atomic
def revoke_email_recovery_codes(account: Account) -> None:
    revoked = _revoke_available_codes(account, AccountRecoveryCode.Kind.EMAIL)
    if revoked:
        AccountAccessEvent.objects.create(
            account=account,
            event=AccountAccessEvent.Event.EMAIL_DELIVERY_FAILED,
            summary="Se revocó el código porque no pudo enviarse el correo de recuperación.",
        )


def send_email_recovery_code(account: Account, code: str, expires_at: datetime) -> None:
    """Send a plaintext code once; only its HMAC digest is stored in the database."""
    if not email_delivery_is_configured():
        raise RecoveryEmailDeliveryError("El proveedor de correo de recuperación no está configurado.")

    minutes = max(1, round((expires_at - timezone.now()).total_seconds() / 60))
    subject = "Código para restablecer tu contraseña de PagoControl"
    message = (
        f"Hola, {account.get_short_name()}.\n\n"
        "Solicitaste restablecer la contraseña de tu cuenta de PagoControl. "
        f"Tu código es: {code}\n\n"
        f"El código vence en {minutes} minutos y solo puede usarse una vez. "
        "Si no solicitaste este cambio, ignora este correo; tu contraseña no se modificará.\n"
    )
    try:
        delivered = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [account.email],
            fail_silently=False,
        )
    except Exception as error:
        logger.exception("No se pudo enviar el correo de recuperación.")
        raise RecoveryEmailDeliveryError from error
    if delivered != 1:
        raise RecoveryEmailDeliveryError("El proveedor de correo no aceptó el mensaje.")


@transaction.atomic
def issue_email_verification_code(
    account: Account,
    *,
    actor: Account | None,
) -> tuple[str, datetime]:
    """Issue an inbox-ownership challenge without storing its plaintext value."""
    if not account.is_active:
        raise PermissionError("La cuenta no está activa.")

    account = Account.objects.select_for_update().get(pk=account.pk)
    _revoke_available_codes(account, AccountRecoveryCode.Kind.EMAIL_VERIFY)
    expires_at = timezone.now() + EMAIL_VERIFICATION_CODE_LIFETIME
    for _ in range(3):
        plain_code, digest = _new_email_recovery_code()
        try:
            with transaction.atomic():
                AccountRecoveryCode.objects.create(
                    account=account,
                    digest=digest,
                    kind=AccountRecoveryCode.Kind.EMAIL_VERIFY,
                    created_by=actor,
                    expires_at=expires_at,
                )
        except IntegrityError:
            continue
        break
    else:
        raise RuntimeError("No se pudo generar un código de verificación único.")

    AccountAccessEvent.objects.create(
        account=account,
        actor=actor,
        event=AccountAccessEvent.Event.EMAIL_VERIFICATION_CODE_ISSUED,
        summary="Se envió un código para verificar el correo de la cuenta.",
    )
    return plain_code, expires_at


def send_email_verification_code(account: Account, code: str, expires_at: datetime) -> None:
    """Send the first-access code only to the address that is being verified."""
    if not email_delivery_is_configured():
        raise RecoveryEmailDeliveryError("El proveedor de correo de verificación no está configurado.")

    minutes = max(1, round((expires_at - timezone.now()).total_seconds() / 60))
    subject = "Verifica tu correo y activa PagoControl"
    message = (
        f"Hola, {account.get_short_name()}.\n\n"
        "Se preparó una cuenta para ti en PagoControl. "
        f"Tu código de verificación es: {code}\n\n"
        f"Vence en {minutes} minutos y solo puede usarse una vez. "
        "Inicia sesión con la contraseña temporal que te entregaron, "
        "ingresa este código y crea tu propia contraseña. "
        "No compartas el código ni tu contraseña con nadie.\n"
    )
    try:
        delivered = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [account.email],
            fail_silently=False,
        )
    except Exception as error:
        logger.exception("No se pudo enviar el correo de verificación.")
        raise RecoveryEmailDeliveryError from error
    if delivered != 1:
        raise RecoveryEmailDeliveryError("El proveedor de correo no aceptó el mensaje.")


@transaction.atomic
def create_assistant_account(
    *,
    actor: Account,
    display_name: str,
    email: str,
    temporary_password: str,
) -> tuple[Account, datetime]:
    """Create a pending assistant and prove inbox ownership before access is granted."""
    if actor.role.code != Role.Code.MANAGER or not actor.is_active:
        raise PermissionError("Solo un gerente activo puede crear asistentes.")

    normalized_email = _validate_provisioned_email(email)
    if Account.objects.filter(email_normalized=normalized_email).exists():
        raise ValueError("Ya existe una cuenta con ese correo.")

    assistant_role, _ = Role.objects.get_or_create(
        code=Role.Code.ASSISTANT,
        defaults={"name": "Asistente"},
    )
    candidate = Account(
        email=normalized_email,
        email_normalized=normalized_email,
        display_name=display_name.strip(),
        role=assistant_role,
    )
    validate_password(temporary_password, user=candidate)
    assistant = Account.objects.create_user(
        normalized_email,
        temporary_password,
        display_name=display_name.strip(),
        role=assistant_role,
        must_change_password=True,
    )
    code, expires_at = issue_email_verification_code(assistant, actor=actor)
    send_email_verification_code(assistant, code, expires_at)
    AccountAccessEvent.objects.create(
        account=assistant,
        actor=actor,
        event=AccountAccessEvent.Event.ASSISTANT_ACCOUNT_CREATED,
        summary="El gerente creó la cuenta y solicitó verificar el correo antes del acceso.",
    )
    return assistant, expires_at


@transaction.atomic
def complete_assistant_onboarding(
    *,
    account: Account,
    code: str,
    new_password: str,
    keep_session_key: str | None,
) -> Account:
    normalized = normalize_recovery_code(code)
    if len(normalized) != EMAIL_RECOVERY_CODE_LENGTH:
        raise InvalidRecoveryCode

    try:
        verification = (
            AccountRecoveryCode.objects.select_for_update()
            .select_related("account")
            .get(
                account=account,
                digest=recovery_code_digest(normalized),
                kind=AccountRecoveryCode.Kind.EMAIL_VERIFY,
            )
        )
    except AccountRecoveryCode.DoesNotExist as error:
        raise InvalidRecoveryCode from error

    now = timezone.now()
    if (
        verification.used_at is not None
        or verification.revoked_at is not None
        or verification.expires_at is None
        or verification.expires_at <= now
        or not verification.account.is_active
    ):
        raise InvalidRecoveryCode

    account = Account.objects.select_for_update().get(pk=account.pk)
    validate_password(new_password, user=account)
    account.set_password(new_password)
    account.email_verified_at = now
    account.must_change_password = False
    account.save(
        update_fields=(
            "password",
            "email_verified_at",
            "must_change_password",
            "updated_at",
        )
    )
    verification.used_at = now
    verification.save(update_fields=("used_at",))
    _revoke_available_codes(account, AccountRecoveryCode.Kind.EMAIL_VERIFY)
    revoke_account_sessions(account, keep_session_key=keep_session_key)
    AccountAccessEvent.objects.create(
        account=account,
        actor=account,
        event=AccountAccessEvent.Event.EMAIL_VERIFIED,
        summary="El asistente verificó su correo y definió su contraseña personal.",
    )
    return account


@transaction.atomic
def resend_assistant_verification(account: Account, *, actor: Account) -> datetime:
    if actor.role.code != Role.Code.MANAGER or not actor.is_active:
        raise PermissionError("Solo un gerente activo puede gestionar asistentes.")

    account = Account.objects.select_for_update().select_related("role").get(pk=account.pk)
    if account.role.code != Role.Code.ASSISTANT or not account.is_active:
        raise PermissionError("La cuenta seleccionada no es un asistente activo.")
    if not account.must_change_password:
        raise ValueError("El correo de este asistente ya fue verificado.")

    code, expires_at = issue_email_verification_code(account, actor=actor)
    send_email_verification_code(account, code, expires_at)
    return expires_at


@transaction.atomic
def set_assistant_account_active(
    assistant: Account,
    *,
    actor: Account,
    active: bool,
) -> Account:
    if actor.role.code != Role.Code.MANAGER or not actor.is_active:
        raise PermissionError("Solo un gerente activo puede gestionar asistentes.")

    assistant = Account.objects.select_for_update().select_related("role").get(pk=assistant.pk)
    if assistant.role.code != Role.Code.ASSISTANT:
        raise PermissionError("Solo pueden gestionarse cuentas de asistentes.")
    if assistant.is_active == active:
        return assistant

    assistant.is_active = active
    assistant.save(update_fields=("is_active", "updated_at"))
    if active:
        if assistant.must_change_password:
            code, expires_at = issue_email_verification_code(assistant, actor=actor)
            send_email_verification_code(assistant, code, expires_at)
        AccountAccessEvent.objects.create(
            account=assistant,
            actor=actor,
            event=AccountAccessEvent.Event.ASSISTANT_ACCOUNT_REACTIVATED,
            summary="El gerente reactivó la cuenta del asistente.",
        )
    else:
        AccountRecoveryCode.objects.filter(
            account=assistant,
            used_at__isnull=True,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        revoke_account_sessions(assistant)
        AccountAccessEvent.objects.create(
            account=assistant,
            actor=actor,
            event=AccountAccessEvent.Event.ASSISTANT_ACCOUNT_DEACTIVATED,
            summary="El gerente desactivó la cuenta y cerró sus sesiones activas.",
        )
    return assistant


def revoke_account_sessions(account: Account, keep_session_key: str | None = None) -> int:
    session_ids: list[str] = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        try:
            session_account_id = session.get_decoded().get(SESSION_KEY)
        except Exception:
            continue
        if str(session_account_id) == str(account.pk):
            if session.session_key == keep_session_key:
                continue
            session_ids.append(session.session_key)
    if not session_ids:
        return 0
    deleted, _ = Session.objects.filter(session_key__in=session_ids).delete()
    return deleted


@transaction.atomic
def recover_account_access(code: str, new_password: str) -> Account:
    normalized = normalize_recovery_code(code)
    if len(normalized) != EMAIL_RECOVERY_CODE_LENGTH:
        raise InvalidRecoveryCode

    try:
        recovery_code = (
            AccountRecoveryCode.objects.select_for_update()
            .select_related("account")
            .get(
                digest=recovery_code_digest(normalized),
                kind=AccountRecoveryCode.Kind.EMAIL,
            )
        )
    except AccountRecoveryCode.DoesNotExist as error:
        raise InvalidRecoveryCode from error

    now = timezone.now()
    if (
        recovery_code.used_at is not None
        or recovery_code.revoked_at is not None
        or (recovery_code.expires_at is not None and recovery_code.expires_at <= now)
        or not recovery_code.account.is_active
    ):
        raise InvalidRecoveryCode

    account = Account.objects.select_for_update().get(pk=recovery_code.account_id)
    validate_password(new_password, user=account)

    account.set_password(new_password)
    account.email_verified_at = now
    account.must_change_password = False
    account.save(
        update_fields=("password", "email_verified_at", "must_change_password", "updated_at")
    )
    recovery_code.used_at = now
    recovery_code.save(update_fields=("used_at",))
    revoke_account_sessions(account)
    AccountAccessEvent.objects.create(
        account=account,
        actor=account,
        event=AccountAccessEvent.Event.RECOVERY_SUCCEEDED,
        summary="La cuenta restableció su contraseña con un código de un solo uso.",
    )
    return account


@transaction.atomic
def change_account_password(
    account: Account,
    new_password: str,
    *,
    keep_session_key: str | None,
) -> Account:
    account = Account.objects.select_for_update().get(pk=account.pk)
    validate_password(new_password, user=account)
    account.set_password(new_password)
    account.save(update_fields=("password", "updated_at"))
    revoke_account_sessions(account, keep_session_key=keep_session_key)
    AccountAccessEvent.objects.create(
        account=account,
        actor=account,
        event=AccountAccessEvent.Event.RECOVERY_SUCCEEDED,
        summary="La cuenta cambió su contraseña desde Mi acceso.",
    )
    return account
