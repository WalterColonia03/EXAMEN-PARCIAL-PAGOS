from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from django.contrib.auth import SESSION_KEY
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import Account, AccountAccessEvent, AccountRecoveryCode, Role


RECOVERY_CODE_HEX_LENGTH = 32
TEMPORARY_CODE_LIFETIME = timedelta(minutes=30)


class InvalidRecoveryCode(Exception):
    """Raised without disclosing whether a recovery code ever existed."""


def normalize_recovery_code(value: str) -> str:
    return "".join(character for character in value.upper() if character in "0123456789ABCDEF")


def recovery_code_digest(value: str) -> str:
    normalized = normalize_recovery_code(value)
    return salted_hmac(
        "identity.account-recovery",
        normalized,
        algorithm="sha256",
    ).hexdigest()


def _new_recovery_code() -> tuple[str, str]:
    normalized = secrets.token_hex(RECOVERY_CODE_HEX_LENGTH // 2).upper()
    display = "-".join(
        normalized[index : index + 4]
        for index in range(0, len(normalized), 4)
    )
    return display, recovery_code_digest(normalized)


def _revoke_available_codes(account: Account, kind: str) -> int:
    now = timezone.now()
    return AccountRecoveryCode.objects.filter(
        account=account,
        kind=kind,
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=now)


@transaction.atomic
def issue_emergency_codes(
    account: Account,
    *,
    actor: Account,
    count: int = 5,
) -> list[str]:
    if actor.pk != account.pk:
        raise PermissionError("Los códigos personales solo pueden ser renovados por su titular.")
    if not actor.is_active:
        raise PermissionError("La cuenta no está activa.")

    revoked = _revoke_available_codes(account, AccountRecoveryCode.Kind.EMERGENCY)
    if revoked:
        AccountAccessEvent.objects.create(
            account=account,
            actor=actor,
            event=AccountAccessEvent.Event.CODES_REVOKED,
            summary=f"Se revocaron {revoked} códigos personales anteriores.",
        )
    plain_codes: list[str] = []
    for _ in range(count):
        plain_code, digest = _new_recovery_code()
        AccountRecoveryCode.objects.create(
            account=account,
            digest=digest,
            kind=AccountRecoveryCode.Kind.EMERGENCY,
            created_by=actor,
        )
        plain_codes.append(plain_code)

    AccountAccessEvent.objects.create(
        account=account,
        actor=actor,
        event=AccountAccessEvent.Event.EMERGENCY_CODES_ISSUED,
        summary=f"Se emitió un nuevo juego de {count} códigos personales de emergencia.",
    )
    return plain_codes


@transaction.atomic
def issue_temporary_assistant_code(
    assistant: Account,
    *,
    actor: Account,
) -> tuple[str, datetime]:
    if actor.role.code != Role.Code.MANAGER or not actor.is_active:
        raise PermissionError("Solo el gerente puede emitir este código.")
    if assistant.role.code != Role.Code.ASSISTANT or not assistant.is_active:
        raise PermissionError("La cuenta seleccionada no es un asistente activo.")

    revoked = _revoke_available_codes(assistant, AccountRecoveryCode.Kind.TEMPORARY)
    if revoked:
        AccountAccessEvent.objects.create(
            account=assistant,
            actor=actor,
            event=AccountAccessEvent.Event.CODES_REVOKED,
            summary="Se revocó el código temporal anterior del asistente.",
        )
    plain_code, digest = _new_recovery_code()
    expires_at = timezone.now() + TEMPORARY_CODE_LIFETIME
    AccountRecoveryCode.objects.create(
        account=assistant,
        digest=digest,
        kind=AccountRecoveryCode.Kind.TEMPORARY,
        created_by=actor,
        expires_at=expires_at,
    )
    AccountAccessEvent.objects.create(
        account=assistant,
        actor=actor,
        event=AccountAccessEvent.Event.TEMPORARY_CODE_ISSUED,
        summary="El gerente emitió un código temporal de recuperación para el asistente.",
    )
    return plain_code, expires_at


def revoke_account_sessions(account: Account) -> int:
    session_ids: list[str] = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        try:
            session_account_id = session.get_decoded().get(SESSION_KEY)
        except Exception:
            continue
        if str(session_account_id) == str(account.pk):
            session_ids.append(session.session_key)
    if not session_ids:
        return 0
    deleted, _ = Session.objects.filter(session_key__in=session_ids).delete()
    return deleted


@transaction.atomic
def recover_account_access(code: str, new_password: str) -> Account:
    normalized = normalize_recovery_code(code)
    if len(normalized) != RECOVERY_CODE_HEX_LENGTH:
        raise InvalidRecoveryCode

    try:
        recovery_code = (
            AccountRecoveryCode.objects.select_for_update()
            .select_related("account")
            .get(digest=recovery_code_digest(normalized))
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
    account.save(update_fields=("password", "updated_at"))
    recovery_code.used_at = now
    recovery_code.save(update_fields=("used_at",))
    if recovery_code.kind == AccountRecoveryCode.Kind.TEMPORARY:
        revoked = _revoke_available_codes(account, AccountRecoveryCode.Kind.TEMPORARY)
        if revoked:
            AccountAccessEvent.objects.create(
                account=account,
                actor=account,
                event=AccountAccessEvent.Event.CODES_REVOKED,
                summary="Se revocaron los códigos temporales restantes después de recuperar el acceso.",
            )
    revoke_account_sessions(account)
    AccountAccessEvent.objects.create(
        account=account,
        actor=account,
        event=AccountAccessEvent.Event.RECOVERY_SUCCEEDED,
        summary="La cuenta restableció su contraseña con un código de un solo uso.",
    )
    return account


def available_emergency_code_count(account: Account) -> int:
    return AccountRecoveryCode.objects.filter(
        account=account,
        kind=AccountRecoveryCode.Kind.EMERGENCY,
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).count()
