"""Business rules for the payment-control MVP.

Views intentionally remain thin: every state-changing operation comes through
these services so that role checks and audit records also apply to direct URLs.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.utils import timezone

from identity.models import Role

from .models import (
    Attachment,
    AuditLog,
    Creditor,
    DestinationAccount,
    FundingSource,
    InternalReminder,
    Payable,
    Payment,
    PaymentCommitment,
    PaymentContext,
    ServiceAccount,
    mask_sensitive_value,
    missing_required_payment_details,
)

ALERT_DAYS = 5
MAX_GENERATED_OCCURRENCES = 5000
DESTINATION_SNAPSHOT_FIELDS = (
    "destination_bank_name_snapshot",
    "destination_account_holder_snapshot",
    "destination_account_number_snapshot",
    "destination_snapshot_origin",
    "destination_snapshot_captured_at",
)


def ensure_payment_user(actor) -> None:
    if not actor.is_authenticated or actor.role.code not in {Role.Code.MANAGER, Role.Code.ASSISTANT}:
        raise PermissionDenied("No tiene permiso para operar el control de pagos.")


def ensure_manager(actor) -> None:
    if not actor.is_authenticated or actor.role.code != Role.Code.MANAGER:
        raise PermissionDenied("Solo el gerente puede realizar esta operación.")


def actor_is_manager(actor) -> bool:
    return bool(actor.is_authenticated and actor.role.code == Role.Code.MANAGER)


def visible_contexts_for(actor) -> QuerySet[PaymentContext]:
    """Return the scopes an actor may use; this is authorization, not presentation."""
    ensure_payment_user(actor)
    queryset = PaymentContext.objects.all()
    if actor_is_manager(actor):
        return queryset
    return queryset.filter(assistant_access=True)


def ensure_context_access(actor, context: PaymentContext | None, *, sensitive: bool = False) -> None:
    ensure_payment_user(actor)
    if context is None or not visible_contexts_for(actor).filter(pk=context.pk).exists():
        raise PermissionDenied("No tiene acceso a este ámbito.")
    if sensitive and not actor_is_manager(actor):
        raise PermissionDenied("Esta obligación es privada del gerente.")


def ensure_funding_source_access(
    actor,
    source: FundingSource | None,
    *,
    context: PaymentContext,
    currency: str,
) -> None:
    if source is None:
        return
    ensure_context_access(actor, source.context)
    if source.context_id != context.pk:
        raise ValidationError("La fuente de fondos debe pertenecer al mismo ámbito.")
    if not actor_is_manager(actor) and not source.assistant_visible:
        raise ValidationError("Seleccione una fuente de fondos disponible para el asistente.")
    if source.currency != currency:
        raise ValidationError(
            "La fuente y la obligación deben usar la misma moneda mientras no exista conversión registrada."
        )


def ensure_operational_pen(record) -> None:
    """Keep legacy non-PEN records available for consultation without reuse."""
    if getattr(record, "currency", FundingSource.Currency.PEN) != FundingSource.Currency.PEN:
        raise ValidationError("Los registros históricos en USD son solo de consulta y no admiten operaciones nuevas.")


def payable_queryset_for(actor) -> QuerySet[Payable]:
    context_ids = visible_contexts_for(actor).values("pk")
    queryset = Payable.objects.filter(context_id__in=context_ids)
    if not actor_is_manager(actor):
        queryset = queryset.filter(is_sensitive=False)
    return queryset


def urgency_ordered_payables(queryset: QuerySet[Payable], today: date | None = None) -> QuerySet[Payable]:
    """Return open obligations in the required urgency order for America/Lima."""
    today = today or timezone.localdate()
    near_date = today + timedelta(days=ALERT_DAYS)
    urgency = Case(
        When(due_date__lt=today, then=Value(0)),
        When(due_date=today, then=Value(1)),
        When(due_date__gt=today, due_date__lte=near_date, then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )
    return queryset.filter(status__in=(Payable.Status.PENDING, Payable.Status.PARTIAL)).annotate(urgency_rank=urgency).order_by(
        "urgency_rank", "due_date", "pk"
    )


def payable_visual_status(payable: Payable, today: date | None = None) -> str:
    return payable.visual_status(today=today)


def record_audit(actor, action: AuditLog.Action, target, summary: str, metadata: dict | None = None) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target._meta.label_lower,
        target_id=str(target.pk),
        summary=summary,
        metadata=metadata or {},
    )


def create_default_reminder(*, actor, payable: Payable) -> InternalReminder:
    remind_on = payable.due_date - timedelta(days=ALERT_DAYS)
    reminder, _ = InternalReminder.objects.get_or_create(
        payable=payable,
        remind_on=remind_on,
        defaults={"created_by": actor},
    )
    return reminder


def _resolve_active_reminders(*, actor, payable: Payable, note: str) -> None:
    """Close pending reminders while keeping their history available."""
    InternalReminder.objects.filter(
        payable=payable,
        status=InternalReminder.Status.ACTIVE,
    ).update(
        status=InternalReminder.Status.SKIPPED,
        note=note[:280],
        resolved_by=actor,
        resolved_at=timezone.now(),
    )


def _sync_default_reminder(*, actor, payable: Payable, reactivate: bool = False) -> None:
    """Keep one useful reminder aligned with the current due date and status."""
    if payable.status not in {Payable.Status.PENDING, Payable.Status.PARTIAL}:
        _resolve_active_reminders(
            actor=actor,
            payable=payable,
            note="Cerrado automáticamente porque la obligación ya no está pendiente.",
        )
        return

    remind_on = payable.due_date - timedelta(days=ALERT_DAYS)
    InternalReminder.objects.filter(
        payable=payable,
        status=InternalReminder.Status.ACTIVE,
    ).exclude(remind_on=remind_on).update(
        status=InternalReminder.Status.SKIPPED,
        note="Reprogramado automáticamente por cambio de vencimiento.",
        resolved_by=actor,
        resolved_at=timezone.now(),
    )
    reminder, created = InternalReminder.objects.get_or_create(
        payable=payable,
        remind_on=remind_on,
        defaults={"created_by": actor},
    )
    if not created and reactivate and reminder.status != InternalReminder.Status.ACTIVE:
        reminder.status = InternalReminder.Status.ACTIVE
        reminder.note = ""
        reminder.resolved_by = None
        reminder.resolved_at = None
        reminder.save(update_fields=("status", "note", "resolved_by", "resolved_at"))


def _remove_uploaded_file_after_rollback(attachment: Attachment | None) -> None:
    """Compensate storage writes, which Django transactions cannot roll back."""
    if attachment is None or not attachment.file:
        return
    try:
        attachment.file.storage.delete(attachment.file.name)
    except Exception:
        # Do not hide the original domain/audit error with a cleanup failure.
        pass


def _resolve_new_creditor(entity) -> None:
    """Persist a form's deferred creditor choice inside the caller's transaction."""
    payload = getattr(entity, "_new_creditor_payload", None)
    if not payload:
        return

    creditor = Creditor.objects.filter(name__iexact=payload["name"]).first()
    if creditor is None:
        creditor = Creditor.objects.create(
            name=payload["name"],
            tax_id=payload.get("tax_id", ""),
            is_active=True,
        )
    if not creditor.is_active:
        raise ValidationError({"creditor": "El acreedor ya existe, pero está inactivo."})
    tax_id = payload.get("tax_id", "")
    if tax_id and not creditor.tax_id:
        creditor.tax_id = tax_id
        creditor.full_clean()
        creditor.save(update_fields=("tax_id",))
    entity.creditor = creditor


def _resolve_context(entity) -> PaymentContext | None:
    """Populate the neutral scope from a commitment or legacy company when needed."""
    if getattr(entity, "context_id", None):
        return entity.context
    commitment = getattr(entity, "commitment", None)
    if commitment is not None and commitment.context_id:
        entity.context = commitment.context
        return entity.context
    company = getattr(entity, "company", None)
    if company is not None:
        entity.context = PaymentContext.for_company(company)
        return entity.context
    return None


def _destination_snapshot_values(account: DestinationAccount | None) -> dict:
    """Read and freeze the catalog account while creating a concrete obligation."""
    if account is None:
        return {
            "destination_account": None,
            "destination_bank_name_snapshot": None,
            "destination_account_holder_snapshot": None,
            "destination_account_number_snapshot": None,
            "destination_snapshot_origin": Payable.DestinationSnapshotOrigin.NONE,
            "destination_snapshot_captured_at": None,
        }

    locked_account = DestinationAccount.objects.select_for_update().get(pk=account.pk)
    return {
        "destination_account": locked_account,
        "destination_bank_name_snapshot": locked_account.bank_name,
        "destination_account_holder_snapshot": locked_account.account_holder,
        "destination_account_number_snapshot": locked_account.account_number,
        "destination_snapshot_origin": Payable.DestinationSnapshotOrigin.CREATED,
        "destination_snapshot_captured_at": timezone.now(),
    }


def _apply_destination_snapshot(payable: Payable, account: DestinationAccount | None) -> None:
    for field, value in _destination_snapshot_values(account).items():
        setattr(payable, field, value)


def _destination_account_audit_values(account: DestinationAccount) -> dict[str, object]:
    return {
        "creditor_id": account.creditor_id,
        "bank_name": account.bank_name,
        "account_holder": account.account_holder,
        "account_number": mask_sensitive_value(account.account_number),
        "is_active": account.is_active,
    }


def _service_account_audit_values(account: ServiceAccount) -> dict[str, object]:
    """Return traceable service-account values without exposing the identifier."""
    return {
        "context_id": account.context_id,
        "company_id": account.company_id,
        "branch_id": account.branch_id,
        "creditor_id": account.creditor_id,
        "service_type": account.service_type,
        "identifier_type": account.identifier_type,
        "primary_identifier": mask_sensitive_value(account.primary_identifier),
        "expected_billing_frequency": account.expected_billing_frequency,
        "usual_billing_day": account.usual_billing_day,
        "acquisition_channel": account.acquisition_channel,
        "status": account.status,
    }


def _payable_audit_values(payable: Payable) -> dict[str, object]:
    """Keep payable edits traceable while excluding codes and account numbers."""
    return {
        "commitment_id": payable.commitment_id,
        "concept": payable.concept,
        "context_id": payable.context_id,
        "company_id": payable.company_id,
        "branch_id": payable.branch_id,
        "category": payable.category,
        "creditor_id": payable.creditor_id,
        "service_account_id": payable.service_account_id,
        "amount": str(payable.amount) if payable.amount is not None else None,
        "currency": payable.currency,
        "payment_nature": payable.payment_nature,
        "is_sensitive": payable.is_sensitive,
        "due_date": payable.due_date.isoformat() if payable.due_date else None,
        "period": payable.period.isoformat() if payable.period else None,
        "is_incomplete": payable.is_incomplete,
        "destination_snapshot_origin": payable.destination_snapshot_origin,
    }


def _audit_changed_fields(before: dict[str, object], after: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        field: {"before": before.get(field), "after": after.get(field)}
        for field in after
        if before.get(field) != after.get(field)
    }


def possible_duplicate_payables(payable: Payable) -> QuerySet[Payable]:
    """Return active exact/near matches without deciding on behalf of the operator."""
    if not payable.context_id or not payable.creditor_id:
        return Payable.objects.none()
    candidates = Payable.objects.filter(
        context_id=payable.context_id,
        creditor_id=payable.creditor_id,
    ).exclude(status=Payable.Status.CANCELLED)
    if payable.pk:
        candidates = candidates.exclude(pk=payable.pk)
    if payable.external_document_number.strip():
        exact = candidates.filter(
            external_document_number__iexact=payable.external_document_number.strip()
        )
        if exact.exists():
            return exact
    match = Q(concept__iexact=payable.concept.strip())
    if payable.amount is not None:
        match &= Q(amount=payable.amount, currency=payable.currency)
    if payable.period:
        match &= Q(period=payable.period)
    else:
        match &= Q(due_date=payable.due_date)
    if payable.service_account_id and payable.period:
        match |= Q(service_account_id=payable.service_account_id, period=payable.period)
    return candidates.filter(match).distinct()


@transaction.atomic
def create_commitment(*, actor, commitment: PaymentCommitment) -> PaymentCommitment:
    ensure_payment_user(actor)
    # New operational records are standardized in PEN. Historical USD records
    # remain readable but never become new operational records.
    commitment.currency = FundingSource.Currency.PEN
    context = _resolve_context(commitment)
    ensure_context_access(actor, context)
    ensure_funding_source_access(
        actor,
        commitment.funding_source,
        context=context,
        currency=commitment.currency,
    )
    _resolve_new_creditor(commitment)
    commitment.created_by = actor
    commitment.full_clean()
    commitment.save()
    record_audit(actor, AuditLog.Action.COMMITMENT_CREATED, commitment, f"Creó el compromiso «{commitment.name}».")
    return commitment


@transaction.atomic
def update_commitment(*, actor, commitment: PaymentCommitment) -> PaymentCommitment:
    ensure_payment_user(actor)
    existing = PaymentCommitment.objects.select_for_update().get(pk=commitment.pk)
    ensure_operational_pen(existing)
    commitment.currency = existing.currency
    ensure_context_access(actor, existing.context)
    _resolve_new_creditor(commitment)
    _resolve_context(commitment)
    ensure_context_access(actor, commitment.context)
    ensure_funding_source_access(
        actor,
        commitment.funding_source,
        context=commitment.context,
        currency=commitment.currency,
    )
    commitment.created_by = existing.created_by
    commitment.full_clean()
    commitment.save()
    record_audit(
        actor,
        AuditLog.Action.COMMITMENT_UPDATED,
        commitment,
        f"Actualizó las reglas futuras de «{commitment.name}».",
    )
    return commitment


@transaction.atomic
def set_commitment_paused(*, actor, commitment_id: int, paused: bool) -> PaymentCommitment:
    ensure_manager(actor)
    commitment = PaymentCommitment.objects.select_for_update().select_related("context").get(pk=commitment_id)
    ensure_operational_pen(commitment)
    ensure_context_access(actor, commitment.context)
    if commitment.frequency == PaymentCommitment.Frequency.ONE_TIME:
        raise ValidationError("Un pago único no tiene recurrencia para pausar.")
    commitment.is_paused = paused
    commitment.save(update_fields=("is_paused", "updated_at"))
    wording = "Pausó" if paused else "Reanudó"
    record_audit(
        actor,
        AuditLog.Action.COMMITMENT_STATUS,
        commitment,
        f"{wording} la recurrencia de «{commitment.name}».",
    )
    return commitment


@transaction.atomic
def skip_next_occurrence(*, actor, commitment_id: int, reason: str) -> PaymentCommitment:
    ensure_manager(actor)
    commitment = PaymentCommitment.objects.select_for_update().select_related("context").get(pk=commitment_id)
    ensure_operational_pen(commitment)
    ensure_context_access(actor, commitment.context)
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Indique por qué se omite esta ocurrencia.")
    current = commitment.next_occurrence or commitment.start_date
    if commitment.frequency == PaymentCommitment.Frequency.ONE_TIME or current is None:
        raise ValidationError("Este compromiso no tiene una próxima ocurrencia que omitir.")
    if Payable.objects.filter(commitment=commitment, period=current).exists():
        raise ValidationError("La próxima ocurrencia ya se convirtió en obligación y no puede omitirse desde aquí.")
    commitment.next_occurrence = next_recurrence_date(commitment, current)
    commitment.save(update_fields=("next_occurrence", "updated_at"))
    record_audit(
        actor,
        AuditLog.Action.RECURRENCE_SKIPPED,
        commitment,
        f"Omitió la ocurrencia del {current:%d/%m/%Y} de «{commitment.name}».",
        {"occurrence": current.isoformat(), "reason": reason},
    )
    return commitment


@transaction.atomic
def save_service_account(*, actor, account: ServiceAccount) -> ServiceAccount:
    """Create or update the permanent service account with an audit trail."""
    ensure_manager(actor)
    _resolve_context(account)
    is_new = account.pk is None
    previous = None
    if not is_new:
        previous = ServiceAccount.objects.select_for_update().get(pk=account.pk)
        scope_changed = (
            previous.context_id != account.context_id
            or previous.company_id != account.company_id
            or previous.branch_id != account.branch_id
            or previous.creditor_id != account.creditor_id
        )
        if scope_changed and (previous.commitments.exists() or previous.payables.exists()):
            raise ValidationError(
                "No puede cambiar ámbito, empresa, local o proveedor de una cuenta ya vinculada. Cree una nueva cuenta."
            )
    if is_new:
        account.created_by = actor
    account.updated_by = actor
    account.full_clean()
    account.save()
    before = _service_account_audit_values(previous) if previous else {}
    after = _service_account_audit_values(account)
    record_audit(
        actor,
        AuditLog.Action.SERVICE_ACCOUNT,
        account,
        "Creó una cuenta de servicio." if is_new else "Actualizó una cuenta de servicio.",
        {
            "before": before,
            "after": after,
            "changed_fields": _audit_changed_fields(before, after),
        },
    )
    return account


@transaction.atomic
def set_commitment_active(*, actor, commitment: PaymentCommitment, is_active: bool) -> PaymentCommitment:
    ensure_manager(actor)
    commitment = PaymentCommitment.objects.select_for_update().get(pk=commitment.pk)
    ensure_operational_pen(commitment)
    commitment.is_active = is_active
    commitment.save(update_fields=("is_active", "updated_at"))
    state = "activó" if is_active else "desactivó"
    record_audit(actor, AuditLog.Action.COMMITMENT_STATUS, commitment, f"{state.capitalize()} el compromiso «{commitment.name}».")
    return commitment


@transaction.atomic
def create_payable(*, actor, payable: Payable) -> Payable:
    ensure_payment_user(actor)
    _resolve_new_creditor(payable)
    if payable.commitment_id:
        ensure_operational_pen(payable.commitment)
        if not payable.context_id:
            payable.context = payable.commitment.context
        if not payable.holder_name:
            payable.holder_name = payable.commitment.holder_name
        if not payable.beneficiary_name:
            payable.beneficiary_name = payable.commitment.beneficiary_name
        payable.payment_nature = payable.commitment.payment_nature
        payable.currency = payable.commitment.currency
        if not payable.details:
            payable.details = payable.commitment.details
        if not payable.funding_source_id:
            payable.funding_source = payable.commitment.funding_source
        if not payable.destination_account_id:
            payable.destination_account = payable.commitment.destination_account
        if not payable.service_account_id:
            payable.service_account = payable.commitment.service_account
        if not payable.supply_code and payable.commitment.supply_code:
            payable.supply_code = payable.commitment.supply_code
    else:
        payable.currency = FundingSource.Currency.PEN
    context = _resolve_context(payable)
    ensure_context_access(actor, context, sensitive=payable.is_sensitive)
    ensure_funding_source_access(
        actor,
        payable.funding_source,
        context=context,
        currency=payable.currency,
    )
    _apply_destination_snapshot(payable, payable.destination_account)
    payable.created_by = actor
    payable.full_clean()
    duplicates = possible_duplicate_payables(payable)
    duplicate_ids = list(duplicates.values_list("pk", flat=True)[:10])
    if duplicate_ids:
        exact_document = bool(
            payable.external_document_number.strip()
            and duplicates.filter(
                external_document_number__iexact=payable.external_document_number.strip()
            ).exists()
        )
        if exact_document:
            raise ValidationError(
                "Ya existe una obligación activa con el mismo ámbito, acreedor y número de documento."
            )
        if not getattr(payable, "_duplicate_confirmed", False):
            candidate_names = ", ".join(f"#{item.pk} {item.concept}" for item in duplicates[:3])
            raise ValidationError(
                f"Encontramos una posible obligación repetida ({candidate_names}). Revísela y confirme si es diferente."
            )
        reason = getattr(payable, "_duplicate_reason", "").strip()
        if not reason:
            raise ValidationError("Para continuar ante una coincidencia, indique por qué no es un duplicado.")
        payable.duplicate_override_reason = reason
    payable.save()
    create_default_reminder(actor=actor, payable=payable)
    record_audit(actor, AuditLog.Action.PAYABLE_CREATED, payable, f"Creó la obligación «{payable.concept}».")
    if duplicate_ids:
        record_audit(
            actor,
            AuditLog.Action.DUPLICATE_OVERRIDE,
            payable,
            "Confirmó que una coincidencia correspondía a una obligación distinta.",
            {"candidate_ids": duplicate_ids, "reason": payable.duplicate_override_reason},
        )
    return payable


@transaction.atomic
def update_payable(*, actor, payable: Payable) -> Payable:
    """Allow an operator to complete pending records without rewriting payment history."""
    ensure_payment_user(actor)
    existing = payable_queryset_for(actor).select_for_update().get(pk=payable.pk)
    ensure_operational_pen(existing)
    payable.currency = existing.currency
    if existing.status not in {Payable.Status.PENDING, Payable.Status.PARTIAL}:
        raise ValidationError("Solo se pueden editar obligaciones pendientes o parcialmente pagadas.")
    if existing.payment_movements.exists():
        locked_fields = (
            "context_id",
            "company_id",
            "branch_id",
            "commitment_id",
            "category",
            "creditor_id",
            "amount",
            "currency",
            "payment_nature",
        )
        changed_locked = [
            field for field in locked_fields if getattr(payable, field) != getattr(existing, field)
        ]
        if changed_locked:
            raise ValidationError(
                "Después de registrar un movimiento no se puede cambiar el ámbito, acreedor, "
                "categoría, monto, moneda ni naturaleza financiera. Corrija el movimiento o "
                "registre una obligación nueva."
            )
    before = _payable_audit_values(existing)
    payable.created_by = existing.created_by
    payable.context = existing.context if not payable.context_id else payable.context
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_funding_source_access(
        actor,
        payable.funding_source,
        context=payable.context,
        currency=payable.currency,
    )
    _resolve_new_creditor(payable)
    if payable.commitment_id:
        if not payable.service_account_id:
            payable.service_account = payable.commitment.service_account
        if not payable.supply_code and payable.commitment.supply_code:
            payable.supply_code = payable.commitment.supply_code
    payable.destination_account_id = existing.destination_account_id
    for field in DESTINATION_SNAPSHOT_FIELDS:
        setattr(payable, field, getattr(existing, field))
    payable.full_clean()
    duplicates = possible_duplicate_payables(payable)
    if duplicates.exists():
        exact_document = bool(
            payable.external_document_number.strip()
            and duplicates.filter(
                external_document_number__iexact=payable.external_document_number.strip()
            ).exists()
        )
        if exact_document:
            raise ValidationError(
                "Ya existe una obligación activa con el mismo ámbito, acreedor y número de documento."
            )
        if not getattr(payable, "_duplicate_confirmed", False):
            candidate_names = ", ".join(f"#{item.pk} {item.concept}" for item in duplicates[:3])
            raise ValidationError(
                f"Encontramos una posible obligación repetida ({candidate_names}). Revísela y confirme si es diferente."
            )
        reason = getattr(payable, "_duplicate_reason", "").strip()
        if not reason:
            raise ValidationError("Para continuar ante una coincidencia, indique por qué no es un duplicado.")
        payable.duplicate_override_reason = reason
    payable.save()
    if existing.due_date != payable.due_date:
        _sync_default_reminder(actor=actor, payable=payable, reactivate=True)
    after = _payable_audit_values(payable)
    record_audit(
        actor,
        AuditLog.Action.PAYABLE_UPDATED,
        payable,
        f"Actualizó la obligación «{payable.concept}».",
        {"before": before, "after": after, "changed_fields": _audit_changed_fields(before, after)},
    )
    if duplicates.exists():
        record_audit(
            actor,
            AuditLog.Action.DUPLICATE_OVERRIDE,
            payable,
            "Confirmó que una coincidencia correspondía a una obligación distinta.",
            {
                "candidate_ids": list(duplicates.values_list("pk", flat=True)[:10]),
                "reason": payable.duplicate_override_reason,
            },
        )
    return payable


@transaction.atomic
def link_service_account_to_payable(*, actor, payable: Payable, account: ServiceAccount) -> Payable:
    """Resolve a missing-account exception and keep its recurrence rule in sync."""
    ensure_payment_user(actor)
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_operational_pen(payable)
    if payable.status not in {Payable.Status.PENDING, Payable.Status.PARTIAL}:
        raise ValidationError("Solo se puede asociar una cuenta de servicio a una obligación abierta.")
    if payable.category != PaymentCommitment.Category.SERVICE:
        raise ValidationError("Solo las obligaciones de servicio pueden asociarse a una cuenta de servicio.")
    if (
        account.context_id != payable.context_id
        or account.company_id != payable.company_id
        or account.branch_id != payable.branch_id
        or account.creditor_id != payable.creditor_id
    ):
        raise ValidationError("La cuenta de servicio debe coincidir con empresa, local y acreedor de la obligación.")

    if payable.commitment_id:
        commitment = PaymentCommitment.objects.select_for_update().get(pk=payable.commitment_id)
        commitment.service_account = account
        commitment.full_clean()
        commitment.save(update_fields=("service_account", "updated_at"))
        record_audit(
            actor,
            AuditLog.Action.SERVICE_ACCOUNT,
            commitment,
            f"Vinculó una cuenta de servicio al compromiso «{commitment.name}».",
            {"service_account_id": account.pk, "identifier": mask_sensitive_value(account.primary_identifier)},
        )

    payable.service_account = account
    payable.full_clean()
    payable.save(update_fields=("service_account", "updated_at"))
    record_audit(
        actor,
        AuditLog.Action.SERVICE_ACCOUNT,
        payable,
        f"Vinculó una cuenta de servicio a «{payable.concept}».",
        {"service_account_id": account.pk, "identifier": mask_sensitive_value(account.primary_identifier)},
    )
    return payable


def _monthly_due_date(year: int, month: int, usual_day: int) -> date:
    return date(year, month, min(usual_day, calendar.monthrange(year, month)[1]))


@transaction.atomic
def generate_monthly_payables(
    *, actor, period: date, commitments: Iterable[PaymentCommitment] | None = None
) -> tuple[list[Payable], int]:
    """Generate only missing monthly obligations; variable amounts stay incomplete."""
    ensure_payment_user(actor)
    first_day = period.replace(day=1)
    source = commitments if commitments is not None else PaymentCommitment.objects.filter(
        is_active=True,
        is_paused=False,
        context__is_active=True,
        frequency=PaymentCommitment.Frequency.MONTHLY,
        currency=FundingSource.Currency.PEN,
        context_id__in=visible_contexts_for(actor).values("pk"),
    )
    created: list[Payable] = []
    skipped = 0
    for commitment in source:
        if not commitment.is_active or commitment.frequency != PaymentCommitment.Frequency.MONTHLY:
            continue
        ensure_operational_pen(commitment)
        ensure_context_access(actor, commitment.context)
        if Payable.objects.filter(
            commitment=commitment,
            period__year=first_day.year,
            period__month=first_day.month,
        ).exists():
            skipped += 1
            continue
        due_date = _monthly_due_date(first_day.year, first_day.month, commitment.usual_due_day or 1)
        destination_snapshot = _destination_snapshot_values(commitment.destination_account)
        defaults = {
            "concept": commitment.name,
            "context": commitment.context,
            "company": commitment.company,
            "branch": commitment.branch,
            "category": commitment.category,
            "creditor": commitment.creditor,
            "holder_name": commitment.holder_name,
            "beneficiary_name": commitment.beneficiary_name,
            "payment_nature": commitment.payment_nature,
            "currency": commitment.currency,
            "details": commitment.details,
            "funding_source": commitment.funding_source,
            "supply_code": commitment.supply_code,
            "service_account": commitment.service_account,
            "amount": commitment.fixed_amount if commitment.amount_mode == PaymentCommitment.AmountMode.FIXED else None,
            "due_date": due_date,
            "is_incomplete": (
                commitment.amount_mode == PaymentCommitment.AmountMode.VARIABLE
                or bool(missing_required_payment_details(commitment.category, commitment.details))
            ),
            "created_by": actor,
            **destination_snapshot,
        }
        payable, made = Payable.objects.get_or_create(commitment=commitment, period=first_day, defaults=defaults)
        if made:
            created.append(payable)
            create_default_reminder(actor=actor, payable=payable)
            record_audit(
                actor,
                AuditLog.Action.PAYABLE_CREATED,
                payable,
                f"Generó la obligación mensual «{payable.concept}» para {first_day:%m/%Y}.",
            )
        else:
            skipped += 1
    return created, skipped


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_recurrence_date(commitment: PaymentCommitment, current: date) -> date:
    frequency = commitment.frequency
    interval = max(commitment.interval_count or 1, 1)
    if frequency == PaymentCommitment.Frequency.WEEKLY:
        return current + timedelta(days=7 * interval)
    if frequency == PaymentCommitment.Frequency.BIWEEKLY:
        return current + timedelta(days=14 * interval)
    month_steps = {
        PaymentCommitment.Frequency.MONTHLY: 1,
        PaymentCommitment.Frequency.BIMONTHLY: 2,
        PaymentCommitment.Frequency.QUARTERLY: 3,
        PaymentCommitment.Frequency.SEMIANNUAL: 6,
        PaymentCommitment.Frequency.ANNUAL: 12,
    }
    if frequency in month_steps:
        return _add_months(current, month_steps[frequency] * interval)
    if frequency == PaymentCommitment.Frequency.CUSTOM:
        if commitment.interval_unit == PaymentCommitment.IntervalUnit.DAYS:
            return current + timedelta(days=interval)
        if commitment.interval_unit == PaymentCommitment.IntervalUnit.WEEKS:
            return current + timedelta(days=7 * interval)
        if commitment.interval_unit == PaymentCommitment.IntervalUnit.MONTHS:
            return _add_months(current, interval)
    raise ValidationError("La recurrencia no tiene un intervalo válido.")


@transaction.atomic
def generate_scheduled_payables(*, actor, through: date) -> tuple[list[Payable], int]:
    """Materialize all due occurrences through a date without creating duplicates."""
    ensure_payment_user(actor)
    commitments = PaymentCommitment.objects.select_for_update().filter(
        is_active=True,
        is_paused=False,
        context__is_active=True,
        context_id__in=visible_contexts_for(actor).values("pk"),
        currency=FundingSource.Currency.PEN,
    ).exclude(frequency=PaymentCommitment.Frequency.ONE_TIME)
    created: list[Payable] = []
    skipped = 0
    processed = 0
    for commitment in commitments:
        occurrence = commitment.next_occurrence or commitment.start_date
        if occurrence is None:
            continue
        while occurrence <= through and (commitment.end_date is None or occurrence <= commitment.end_date):
            processed += 1
            if processed > MAX_GENERATED_OCCURRENCES:
                raise ValidationError(
                    "El rango produciría demasiadas ocurrencias. Genérelas en períodos más cortos."
                )
            due = occurrence
            if commitment.usual_due_day:
                due = _monthly_due_date(occurrence.year, occurrence.month, commitment.usual_due_day)
            defaults = {
                "concept": commitment.name,
                "context": commitment.context,
                "company": commitment.company,
                "branch": commitment.branch,
                "category": commitment.category,
                "creditor": commitment.creditor,
                "holder_name": commitment.holder_name,
                "beneficiary_name": commitment.beneficiary_name,
                "payment_nature": commitment.payment_nature,
                "currency": commitment.currency,
                "details": commitment.details,
                "funding_source": commitment.funding_source,
                "supply_code": commitment.supply_code,
                "service_account": commitment.service_account,
                "amount": commitment.fixed_amount if commitment.amount_mode == PaymentCommitment.AmountMode.FIXED else None,
                "due_date": due,
                "is_incomplete": (
                    commitment.amount_mode == PaymentCommitment.AmountMode.VARIABLE
                    or bool(missing_required_payment_details(commitment.category, commitment.details))
                ),
                "created_by": actor,
                **_destination_snapshot_values(commitment.destination_account),
            }
            existing_month = None
            if commitment.frequency == PaymentCommitment.Frequency.MONTHLY:
                existing_month = Payable.objects.filter(
                    commitment=commitment,
                    period__year=occurrence.year,
                    period__month=occurrence.month,
                ).first()
            if existing_month is not None:
                payable, made = existing_month, False
            else:
                payable, made = Payable.objects.get_or_create(
                    commitment=commitment,
                    period=occurrence,
                    defaults=defaults,
                )
            if made:
                created.append(payable)
                create_default_reminder(actor=actor, payable=payable)
                record_audit(
                    actor,
                    AuditLog.Action.PAYABLE_CREATED,
                    payable,
                    f"Generó «{payable.concept}» con vencimiento {due:%d/%m/%Y}.",
                )
            else:
                skipped += 1
            occurrence = next_recurrence_date(commitment, occurrence)
        commitment.next_occurrence = occurrence
        commitment.save(update_fields=("next_occurrence", "updated_at"))
    return created, skipped


@transaction.atomic
def attach_source_document(*, actor, payable: Payable, upload) -> Attachment:
    ensure_payment_user(actor)
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_operational_pen(payable)
    attachment = None
    try:
        attachment = Attachment.objects.create(
            payable=payable,
            kind=Attachment.Kind.SOURCE,
            file=upload,
            original_name=upload.name,
            content_type=getattr(upload, "content_type", "application/octet-stream") or "application/octet-stream",
            size_bytes=upload.size,
            uploaded_by=actor,
        )
        if payable.is_incomplete:
            # A source document is one missing datum; do not overwrite a manual incomplete flag.
            payable.save(update_fields=("updated_at",))
        record_audit(
            actor,
            AuditLog.Action.DOCUMENT_UPLOADED,
            payable,
            f"Adjuntó un documento a «{payable.concept}».",
            {"attachment_id": attachment.pk, "kind": attachment.kind},
        )
        return attachment
    except Exception:
        _remove_uploaded_file_after_rollback(attachment)
        raise


@transaction.atomic
def withdraw_source_document(*, actor, attachment_id: int, reason: str) -> Attachment:
    """Retire a mistaken source document without deleting its row or object."""
    ensure_payment_user(actor)
    attachment = (
        Attachment.objects.select_for_update()
        .select_related("payable__context", "uploaded_by")
        .get(pk=attachment_id)
    )
    payable = attachment.payable
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_operational_pen(payable)
    if attachment.kind != Attachment.Kind.SOURCE:
        raise ValidationError("Solo se puede retirar un documento de sustento.")
    if attachment.withdrawn_at is not None:
        return attachment
    if payable.payment_movements.exists():
        raise ValidationError("No se puede retirar evidencia después de registrar un movimiento financiero.")
    allowed_statuses = (
        {Payable.Status.PENDING, Payable.Status.SUSPENDED}
        if actor_is_manager(actor)
        else {Payable.Status.PENDING}
    )
    if payable.status not in allowed_statuses:
        raise ValidationError("El estado actual no permite retirar el documento.")
    if not actor_is_manager(actor) and attachment.uploaded_by_id != actor.pk:
        raise PermissionDenied("El asistente solo puede retirar documentos que él mismo adjuntó.")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Indique el motivo del retiro.")

    attachment.withdrawn_at = timezone.now()
    attachment.withdrawn_by = actor
    attachment.withdrawal_reason = reason
    attachment.save(update_fields=("withdrawn_at", "withdrawn_by", "withdrawal_reason"))
    record_audit(
        actor,
        AuditLog.Action.DOCUMENT_WITHDRAWN,
        payable,
        f"Retiró el documento «{attachment.original_name}» sin eliminar la evidencia.",
        {"attachment_id": attachment.pk, "reason": reason},
    )
    return attachment


@transaction.atomic
def report_funds_unavailable(*, actor, payable: Payable, note: str) -> Payable:
    """Let an assistant raise an audited alert without changing financial status."""
    ensure_payment_user(actor)
    if actor_is_manager(actor):
        raise PermissionDenied("Esta acción corresponde al asistente; el gerente puede resolver el aviso.")
    payable = payable_queryset_for(actor).select_for_update().get(pk=payable.pk)
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_operational_pen(payable)
    if payable.status not in {Payable.Status.PENDING, Payable.Status.PARTIAL}:
        raise ValidationError("Solo se puede reportar falta de fondos en una obligación pendiente.")
    if payable.funds_unavailable_reported_at is not None:
        return payable
    note = (note or "").strip()
    if not note:
        raise ValidationError("Explique brevemente por qué no hay fondos disponibles.")

    payable.funds_unavailable_note = note
    payable.funds_unavailable_reported_at = timezone.now()
    payable.funds_unavailable_reported_by = actor
    payable.save(
        update_fields=(
            "funds_unavailable_note",
            "funds_unavailable_reported_at",
            "funds_unavailable_reported_by",
            "updated_at",
        )
    )
    record_audit(
        actor,
        AuditLog.Action.FUNDS_UNAVAILABLE,
        payable,
        f"Reportó falta de fondos para «{payable.concept}».",
        {"note": note},
    )
    return payable


@transaction.atomic
def resolve_funds_unavailable(*, actor, payable: Payable) -> Payable:
    ensure_manager(actor)
    payable = payable_queryset_for(actor).select_for_update().get(pk=payable.pk)
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_operational_pen(payable)
    if payable.funds_unavailable_reported_at is None:
        return payable
    previous_note = payable.funds_unavailable_note
    payable.funds_unavailable_note = ""
    payable.funds_unavailable_reported_at = None
    payable.funds_unavailable_reported_by = None
    payable.save(
        update_fields=(
            "funds_unavailable_note",
            "funds_unavailable_reported_at",
            "funds_unavailable_reported_by",
            "updated_at",
        )
    )
    record_audit(
        actor,
        AuditLog.Action.FUNDS_RESOLVED,
        payable,
        f"Marcó como atendido el aviso de falta de fondos de «{payable.concept}».",
        {"previous_note": previous_note},
    )
    return payable


@transaction.atomic
def record_payment(
    *,
    actor,
    payable_id: int,
    amount: Decimal,
    paid_on: date,
    operation_reference: str,
    receipt_upload,
    funding_source: FundingSource | None = None,
    allow_partial: bool = False,
) -> Payment:
    """Record an external payment; UI callers may explicitly enable partial payments."""
    ensure_payment_user(actor)
    if receipt_upload is None:
        raise ValidationError("Adjunte el comprobante antes de confirmar el pago.")
    payable = payable_queryset_for(actor).select_for_update().get(pk=payable_id)
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_operational_pen(payable)
    if payable.status == Payable.Status.PAID or payable.balance_due == Decimal("0.00"):
        raise ValidationError("La obligación ya fue pagada y no admite un segundo pago completo.")
    if payable.status in {
        Payable.Status.SUSPENDED,
        Payable.Status.DISPUTED,
        Payable.Status.CANCELLED,
    }:
        raise ValidationError("Reactive o resuelva la obligación antes de registrar su pago.")
    if payable.amount is None:
        raise ValidationError("Defina el monto de la obligación antes de registrar el pago.")
    balance_before = payable.balance_due
    if amount > balance_before:
        raise ValidationError("El pago no puede superar el saldo pendiente de la obligación.")
    if not allow_partial and amount != balance_before:
        raise ValidationError("El pago completo debe coincidir con el monto registrado de la obligación.")
    if not Attachment.objects.filter(
        payable=payable,
        kind=Attachment.Kind.SOURCE,
        withdrawn_at__isnull=True,
    ).exists():
        raise ValidationError("Adjunte el documento de sustento antes de registrar el pago.")

    receipt = None
    try:
        receipt = Attachment.objects.create(
            payable=payable,
            kind=Attachment.Kind.RECEIPT,
            file=receipt_upload,
            original_name=receipt_upload.name,
            content_type=getattr(receipt_upload, "content_type", "application/octet-stream") or "application/octet-stream",
            size_bytes=receipt_upload.size,
            uploaded_by=actor,
        )
        selected_source = funding_source or payable.funding_source
        ensure_funding_source_access(
            actor,
            selected_source,
            context=payable.context,
            currency=payable.currency,
        )
        payment = Payment(
            payable=payable,
            kind=Payment.Kind.PAYMENT,
            balance_effect=Payment.BalanceEffect.DECREASE,
            amount=amount,
            currency=payable.currency,
            paid_on=paid_on,
            operation_reference=operation_reference,
            receipt=receipt,
            funding_source=selected_source,
            registered_by=actor,
        )
        if payment.funding_source_id:
            payment.funding_source_name_snapshot = payment.funding_source.name
            payment.funding_source_identifier_snapshot = payment.funding_source.identifier
        payment.full_clean()
        payment.save()
        remaining = balance_before - amount
        payable.status = Payable.Status.PAID if remaining == Decimal("0.00") else Payable.Status.PARTIAL
        funds_alert_was_open = payable.funds_unavailable_reported_at is not None
        funds_alert_note = payable.funds_unavailable_note
        payable.suspension_note = ""
        payable.suspended_by = None
        payable.suspended_at = None
        payable.funds_unavailable_note = ""
        payable.funds_unavailable_reported_at = None
        payable.funds_unavailable_reported_by = None
        payable.save(update_fields=(
            "status",
            "suspension_note",
            "suspended_by",
            "suspended_at",
            "funds_unavailable_note",
            "funds_unavailable_reported_at",
            "funds_unavailable_reported_by",
            "updated_at",
        ))
        _sync_default_reminder(actor=actor, payable=payable)
        if funds_alert_was_open:
            record_audit(
                actor,
                AuditLog.Action.FUNDS_RESOLVED,
                payable,
                f"El pago atendió el aviso de falta de fondos de «{payable.concept}».",
                {"previous_note": funds_alert_note, "resolution": "payment"},
            )
        record_audit(
            actor,
            AuditLog.Action.PAYMENT_RECORDED,
            payable,
            f"Registró el pago de «{payable.concept}».",
            {
                "payment_id": payment.pk,
                "receipt_id": receipt.pk,
                "amount": str(amount),
                "currency": payable.currency,
                "remaining_balance": str(remaining),
                "destination_snapshot_origin": payable.destination_snapshot_origin,
            },
        )
        return payment
    except Exception:
        _remove_uploaded_file_after_rollback(receipt)
        raise


def _sync_payable_status_from_movements(payable: Payable) -> None:
    if payable.amount is None:
        return
    net_paid = payable.net_paid
    raw_balance = max(payable.amount - net_paid, Decimal("0.00"))
    fully_reimbursed = (
        payable.payment_nature == PaymentCommitment.Nature.REIMBURSABLE
        and net_paid > Decimal("0.00")
        and payable.reimbursements_received >= net_paid
    )
    if raw_balance == Decimal("0.00") and fully_reimbursed:
        payable.status = Payable.Status.REFUNDED
    elif raw_balance == Decimal("0.00"):
        payable.status = Payable.Status.PAID
    elif net_paid > Decimal("0.00"):
        payable.status = Payable.Status.PARTIAL
    else:
        payable.status = Payable.Status.PENDING
    payable.save(update_fields=("status", "updated_at"))


@transaction.atomic
def record_balance_movement(
    *,
    actor,
    payable_id: int,
    kind: str,
    amount: Decimal,
    movement_on: date,
    reason: str,
    operation_reference: str = "",
    reverses: Payment | None = None,
) -> Payment:
    """Append a correction/refund without deleting or rewriting previous evidence."""
    ensure_manager(actor)
    payable = payable_queryset_for(actor).select_for_update().get(pk=payable_id)
    ensure_operational_pen(payable)
    if payable.status in {Payable.Status.CANCELLED, Payable.Status.REFUNDED}:
        raise ValidationError("Una obligación cerrada no admite movimientos nuevos.")
    if kind not in {
        Payment.Kind.REFUND,
        Payment.Kind.REIMBURSEMENT,
        Payment.Kind.CHARGEBACK,
        Payment.Kind.ADJUSTMENT,
    }:
        raise ValidationError("Seleccione un tipo de corrección válido.")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Explique el motivo de la corrección.")
    effect = {
        Payment.Kind.REFUND: Payment.BalanceEffect.INCREASE,
        Payment.Kind.CHARGEBACK: Payment.BalanceEffect.INCREASE,
        Payment.Kind.REIMBURSEMENT: Payment.BalanceEffect.NONE,
        Payment.Kind.ADJUSTMENT: Payment.BalanceEffect.INCREASE,
    }[kind]
    if reverses is not None:
        if (
            reverses.payable_id != payable.pk
            or reverses.is_void
            or reverses.balance_effect != Payment.BalanceEffect.DECREASE
        ):
            raise ValidationError("El movimiento indicado no se puede corregir.")
        if Payment.objects.filter(reverses=reverses, is_void=False).exists():
            raise ValidationError("El movimiento indicado ya tiene una corrección activa.")
        amount = reverses.amount
    if amount <= Decimal("0.00"):
        raise ValidationError("El monto del movimiento debe ser mayor que cero.")
    if kind == Payment.Kind.REIMBURSEMENT:
        if payable.payment_nature != PaymentCommitment.Nature.REIMBURSABLE:
            raise ValidationError("Solo un gasto marcado como reembolsable admite reembolsos recibidos.")
        if amount > payable.reimbursement_pending:
            raise ValidationError("El reembolso no puede superar el importe pendiente de recuperar.")
    elif amount > max(payable.net_paid, Decimal("0.00")):
        raise ValidationError("La corrección no puede superar el importe pagado neto disponible.")
    movement = Payment(
        payable=payable,
        kind=kind,
        balance_effect=effect,
        amount=amount,
        currency=payable.currency,
        paid_on=movement_on,
        operation_reference=operation_reference,
        reason=reason,
        reverses=reverses,
        registered_by=actor,
    )
    movement.full_clean()
    movement.save()
    _sync_payable_status_from_movements(payable)
    _sync_default_reminder(
        actor=actor,
        payable=payable,
        reactivate=payable.status in {Payable.Status.PENDING, Payable.Status.PARTIAL},
    )
    record_audit(
        actor,
        AuditLog.Action.PAYMENT_RECORDED,
        payable,
        f"Registró {movement.get_kind_display().lower()} en «{payable.concept}».",
        {"movement_id": movement.pk, "amount": str(amount), "currency": payable.currency},
    )
    return movement


@transaction.atomic
def void_payment_movement(*, actor, movement_id: int, reason: str) -> Payment:
    ensure_manager(actor)
    movement = Payment.objects.select_for_update().select_related("payable__context").get(pk=movement_id)
    ensure_context_access(actor, movement.payable.context, sensitive=movement.payable.is_sensitive)
    ensure_operational_pen(movement.payable)
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Indique el motivo de la anulación.")
    if movement.is_void:
        raise ValidationError("El movimiento ya está anulado.")
    movement.is_void = True
    movement.void_reason = reason
    movement.voided_by = actor
    movement.voided_at = timezone.now()
    movement.full_clean()
    movement.save(update_fields=("is_void", "void_reason", "voided_by", "voided_at"))
    payable = movement.payable
    _sync_payable_status_from_movements(payable)
    _sync_default_reminder(
        actor=actor,
        payable=payable,
        reactivate=payable.status in {Payable.Status.PENDING, Payable.Status.PARTIAL},
    )
    record_audit(
        actor,
        AuditLog.Action.PAYMENT_VOIDED,
        payable,
        f"Anuló un movimiento de «{payable.concept}» sin borrarlo.",
        {"movement_id": movement.pk, "reason": reason},
    )
    return movement


@transaction.atomic
def reveal_payment_instruction(*, actor, payable_id: int) -> Payable:
    """Log an explicit, authorized access before returning sensitive payment data."""
    ensure_payment_user(actor)
    payable = payable_queryset_for(actor).select_for_update().select_related("service_account").get(pk=payable_id)
    fields = []
    if payable.service_account_id:
        fields.append("service_identifier")
    if payable.has_destination_snapshot:
        fields.extend(("destination_bank", "destination_holder", "destination_account_number"))
    if not fields:
        raise ValidationError("Esta obligación no tiene una instrucción de pago disponible.")
    record_audit(
        actor,
        AuditLog.Action.PAYMENT_INSTRUCTION_VIEW,
        payable,
        "Consultó la instrucción de pago autorizada.",
        {
            "fields": fields,
            "destination_snapshot_origin": payable.destination_snapshot_origin,
        },
    )
    return payable


@transaction.atomic
def set_payable_suspension(*, actor, payable: Payable, suspend: bool, note: str = "") -> Payable:
    ensure_manager(actor)
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_operational_pen(payable)
    if suspend:
        if payable.status not in {Payable.Status.PENDING, Payable.Status.PARTIAL}:
            raise ValidationError("Solo una obligación pendiente puede suspenderse.")
        payable.status = Payable.Status.SUSPENDED
        payable.suspension_note = note.strip()
        payable.suspended_by = actor
        payable.suspended_at = timezone.now()
        wording = "suspendió"
    else:
        if payable.status != Payable.Status.SUSPENDED:
            raise ValidationError("La obligación no está suspendida.")
        payable.status = Payable.Status.PARTIAL if payable.net_paid > Decimal("0.00") else Payable.Status.PENDING
        payable.suspension_note = ""
        payable.suspended_by = None
        payable.suspended_at = None
        wording = "reactivó"
    payable.save(
        update_fields=("status", "suspension_note", "suspended_by", "suspended_at", "updated_at")
    )
    _sync_default_reminder(actor=actor, payable=payable, reactivate=not suspend)
    record_audit(actor, AuditLog.Action.PAYABLE_STATUS, payable, f"{wording.capitalize()} «{payable.concept}».")
    return payable


@transaction.atomic
def set_payable_review_status(*, actor, payable: Payable, status: str, note: str) -> Payable:
    ensure_manager(actor)
    ensure_context_access(actor, payable.context, sensitive=payable.is_sensitive)
    ensure_operational_pen(payable)
    if status not in {Payable.Status.PENDING, Payable.Status.DISPUTED, Payable.Status.CANCELLED}:
        raise ValidationError("Seleccione un estado de revisión válido.")
    note = (note or "").strip()
    if status in {Payable.Status.DISPUTED, Payable.Status.CANCELLED} and not note:
        raise ValidationError("Explique el motivo antes de cambiar el estado.")
    if payable.status in {Payable.Status.PAID, Payable.Status.REFUNDED}:
        raise ValidationError("Una obligación cerrada no puede cambiarse desde la revisión operativa.")
    if status == Payable.Status.CANCELLED and payable.payment_movements.filter(is_void=False).exists():
        raise ValidationError("Anule primero los movimientos activos antes de anular la obligación.")
    if status == Payable.Status.DISPUTED and payable.status not in {
        Payable.Status.PENDING,
        Payable.Status.PARTIAL,
    }:
        raise ValidationError("Solo una obligación pendiente puede pasar a disputa.")
    if status == Payable.Status.CANCELLED and payable.status not in {
        Payable.Status.PENDING,
        Payable.Status.SUSPENDED,
        Payable.Status.DISPUTED,
    }:
        raise ValidationError("El estado actual no permite anular la obligación.")
    if status == Payable.Status.PENDING and payable.status not in {
        Payable.Status.DISPUTED,
        Payable.Status.CANCELLED,
    }:
        raise ValidationError("Solo una obligación en disputa o anulada puede reactivarse.")
    if status == Payable.Status.PENDING:
        raw_balance = (
            max(payable.amount - payable.net_paid, Decimal("0.00"))
            if payable.amount is not None
            else None
        )
        if raw_balance == Decimal("0.00") and payable.net_paid > Decimal("0.00"):
            status = Payable.Status.PAID
        elif payable.net_paid > Decimal("0.00"):
            status = Payable.Status.PARTIAL
        note = ""
    payable.status = status
    payable.suspension_note = note
    payable.suspended_by = actor if note else None
    payable.suspended_at = timezone.now() if note else None
    payable.save(update_fields=("status", "suspension_note", "suspended_by", "suspended_at", "updated_at"))
    _sync_default_reminder(
        actor=actor,
        payable=payable,
        reactivate=payable.status in {Payable.Status.PENDING, Payable.Status.PARTIAL},
    )
    record_audit(
        actor,
        AuditLog.Action.PAYABLE_STATUS,
        payable,
        f"Cambió «{payable.concept}» a {payable.get_status_display().lower()}.",
        {"status": payable.status, "reason": note},
    )
    return payable


@transaction.atomic
def save_destination_account(*, actor, account: DestinationAccount) -> DestinationAccount:
    ensure_manager(actor)
    is_new = account.pk is None
    previous = None
    if not is_new:
        previous = DestinationAccount.objects.select_for_update().get(pk=account.pk)
        if previous.creditor_id != account.creditor_id and (
            previous.payment_commitments.exists() or previous.payables.exists()
        ):
            raise ValidationError(
                {"creditor": "No puede cambiar el acreedor de una cuenta ya usada en compromisos u obligaciones."}
            )
    account.updated_by = actor
    if is_new:
        account.created_by = actor
    account.full_clean()
    account.save()
    verb = "Creó" if is_new else "Actualizó"
    before = _destination_account_audit_values(previous) if previous else {}
    after = _destination_account_audit_values(account)
    changed_fields = {
        field: {"before": before.get(field), "after": after.get(field)}
        for field in after
        if before.get(field) != after.get(field)
    }
    record_audit(
        actor,
        AuditLog.Action.DESTINATION_ACCOUNT,
        account,
        f"{verb} una cuenta de destino para {account.creditor.name}.",
        {"before": before, "after": after, "changed_fields": changed_fields},
    )
    return account


@transaction.atomic
def save_payment_context(*, actor, context: PaymentContext) -> PaymentContext:
    ensure_manager(actor)
    previous = None
    if context.pk:
        previous = PaymentContext.objects.select_for_update().get(pk=context.pk)
        if (
            previous.company_id != context.company_id
            or previous.kind != context.kind
        ) and (
            previous.payables.exists()
            or previous.payment_commitments.exists()
            or previous.service_accounts.exists()
            or previous.funding_sources.exists()
        ):
            raise ValidationError(
                "No puede cambiar el tipo o la empresa de un ámbito que ya tiene información asociada."
            )
    context.created_by = context.created_by or actor
    context.updated_by = actor
    context.full_clean()
    context.save()
    record_audit(
        actor,
        AuditLog.Action.CONTEXT_UPDATED,
        context,
        "Creó un ámbito." if previous is None else "Actualizó un ámbito.",
        {"kind": context.kind, "assistant_access": context.assistant_access, "is_active": context.is_active},
    )
    return context


@transaction.atomic
def save_funding_source(*, actor, source: FundingSource) -> FundingSource:
    ensure_manager(actor)
    previous = FundingSource.objects.select_for_update().filter(pk=source.pk).first() if source.pk else None
    if previous:
        ensure_operational_pen(previous)
    source.currency = previous.currency if previous else FundingSource.Currency.PEN
    if previous and (
        previous.context_id != source.context_id
        or previous.currency != source.currency
    ) and (
        previous.payment_commitments.exists()
        or previous.planned_payables.exists()
        or previous.payment_movements.exists()
    ):
        raise ValidationError(
            "No puede cambiar el ámbito o la moneda de una fuente que ya tiene información asociada."
        )
    source.created_by = source.created_by or actor
    source.updated_by = actor
    source.full_clean()
    source.save()
    record_audit(
        actor,
        AuditLog.Action.FUNDING_SOURCE,
        source,
        "Creó una fuente de fondos." if previous is None else "Actualizó una fuente de fondos.",
        {
            "context_id": source.context_id,
            "kind": source.kind,
            "currency": source.currency,
            "identifier": source.masked_identifier,
            "is_active": source.is_active,
        },
    )
    return source


@transaction.atomic
def set_reminder_status(*, actor, reminder_id: int, status: str) -> InternalReminder:
    ensure_payment_user(actor)
    reminder = InternalReminder.objects.select_for_update().select_related("payable__context").get(pk=reminder_id)
    ensure_context_access(actor, reminder.payable.context, sensitive=reminder.payable.is_sensitive)
    ensure_operational_pen(reminder.payable)
    if status not in {InternalReminder.Status.DONE, InternalReminder.Status.SKIPPED}:
        raise ValidationError("Seleccione un resultado válido para el recordatorio.")
    reminder.status = status
    reminder.resolved_by = actor
    reminder.resolved_at = timezone.now()
    reminder.save(update_fields=("status", "resolved_by", "resolved_at"))
    record_audit(
        actor,
        AuditLog.Action.REMINDER_STATUS,
        reminder.payable,
        f"Marcó un recordatorio como {reminder.get_status_display().lower()}.",
        {"reminder_id": reminder.pk, "status": status},
    )
    return reminder


def manager_month_summary(queryset: QuerySet[Payable]) -> dict[str, dict[str, Decimal | int]]:
    """Calculate each payable exactly once; unknown amounts contribute zero to money totals."""
    buckets: dict[str, dict[str, Decimal | int]] = {
        "paid": {"count": 0, "amount": Decimal("0.00")},
        "partial": {"count": 0, "amount": Decimal("0.00")},
        "pending": {"count": 0, "amount": Decimal("0.00")},
        "overdue": {"count": 0, "amount": Decimal("0.00")},
        "suspended": {"count": 0, "amount": Decimal("0.00")},
        "disputed": {"count": 0, "amount": Decimal("0.00")},
        "refunded": {"count": 0, "amount": Decimal("0.00")},
        "cancelled": {"count": 0, "amount": Decimal("0.00")},
    }
    today = timezone.localdate()
    for payable in queryset:
        if payable.status == Payable.Status.PAID:
            key = "paid"
        elif payable.status == Payable.Status.SUSPENDED:
            key = "suspended"
        elif payable.status == Payable.Status.DISPUTED:
            key = "disputed"
        elif payable.status == Payable.Status.REFUNDED:
            key = "refunded"
        elif payable.status == Payable.Status.CANCELLED:
            key = "cancelled"
        elif payable.status in {Payable.Status.PENDING, Payable.Status.PARTIAL} and payable.due_date < today:
            key = "overdue"
        elif payable.status == Payable.Status.PARTIAL:
            key = "partial"
        else:
            key = "pending"
        buckets[key]["count"] = int(buckets[key]["count"]) + 1
        amount = (
            payable.balance_due
            if key in {"partial", "pending", "overdue", "suspended", "disputed"}
            else payable.amount
        )
        buckets[key]["amount"] = Decimal(buckets[key]["amount"]) + (amount or Decimal("0.00"))
    return buckets
