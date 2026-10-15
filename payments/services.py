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

from .models import Attachment, AuditLog, DestinationAccount, Payable, Payment, PaymentCommitment

ALERT_DAYS = 5


def ensure_payment_user(actor) -> None:
    if not actor.is_authenticated or actor.role.code not in {Role.Code.MANAGER, Role.Code.ASSISTANT}:
        raise PermissionDenied("No tiene permiso para operar el control de pagos.")


def ensure_manager(actor) -> None:
    if not actor.is_authenticated or actor.role.code != Role.Code.MANAGER:
        raise PermissionDenied("Solo el gerente puede realizar esta operación.")


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
    return queryset.filter(status=Payable.Status.PENDING).annotate(urgency_rank=urgency).order_by(
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


def create_commitment(*, actor, commitment: PaymentCommitment) -> PaymentCommitment:
    ensure_payment_user(actor)
    commitment.created_by = actor
    commitment.full_clean()
    commitment.save()
    record_audit(actor, AuditLog.Action.COMMITMENT_CREATED, commitment, f"Creó el compromiso «{commitment.name}».")
    return commitment


def set_commitment_active(*, actor, commitment: PaymentCommitment, is_active: bool) -> PaymentCommitment:
    ensure_manager(actor)
    commitment.is_active = is_active
    commitment.save(update_fields=("is_active", "updated_at"))
    state = "activó" if is_active else "desactivó"
    record_audit(actor, AuditLog.Action.COMMITMENT_STATUS, commitment, f"{state.capitalize()} el compromiso «{commitment.name}».")
    return commitment


def create_payable(*, actor, payable: Payable) -> Payable:
    ensure_payment_user(actor)
    if payable.commitment_id:
        if not payable.destination_account_id:
            payable.destination_account = payable.commitment.destination_account
        if not payable.supply_code and payable.commitment.supply_code:
            payable.supply_code = payable.commitment.supply_code
    payable.created_by = actor
    payable.full_clean()
    payable.save()
    record_audit(actor, AuditLog.Action.PAYABLE_CREATED, payable, f"Creó la obligación «{payable.concept}».")
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
        is_active=True, frequency=PaymentCommitment.Frequency.MONTHLY
    )
    created: list[Payable] = []
    skipped = 0
    for commitment in source:
        if not commitment.is_active or commitment.frequency != PaymentCommitment.Frequency.MONTHLY:
            continue
        due_date = _monthly_due_date(first_day.year, first_day.month, commitment.usual_due_day or 1)
        defaults = {
            "concept": commitment.name,
            "company": commitment.company,
            "branch": commitment.branch,
            "category": commitment.category,
            "creditor": commitment.creditor,
            "supply_code": commitment.supply_code,
            "destination_account": commitment.destination_account,
            "amount": commitment.fixed_amount if commitment.amount_mode == PaymentCommitment.AmountMode.FIXED else None,
            "due_date": due_date,
            "is_incomplete": commitment.amount_mode == PaymentCommitment.AmountMode.VARIABLE,
            "created_by": actor,
        }
        payable, made = Payable.objects.get_or_create(commitment=commitment, period=first_day, defaults=defaults)
        if made:
            created.append(payable)
            record_audit(
                actor,
                AuditLog.Action.PAYABLE_CREATED,
                payable,
                f"Generó la obligación mensual «{payable.concept}» para {first_day:%m/%Y}.",
            )
        else:
            skipped += 1
    return created, skipped


def attach_source_document(*, actor, payable: Payable, upload) -> Attachment:
    ensure_payment_user(actor)
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
    record_audit(actor, AuditLog.Action.DOCUMENT_UPLOADED, attachment, f"Adjuntó un documento a «{payable.concept}».")
    return attachment


@transaction.atomic
def record_payment(
    *,
    actor,
    payable_id: int,
    amount: Decimal,
    paid_on: date,
    operation_reference: str,
    receipt_upload,
) -> Payment:
    """Record one externally executed payment, always with its uploaded evidence."""
    ensure_payment_user(actor)
    if receipt_upload is None:
        raise ValidationError("Adjunte el comprobante antes de confirmar el pago.")
    payable = Payable.objects.select_for_update().get(pk=payable_id)
    if payable.status == Payable.Status.PAID or Payment.objects.filter(payable=payable).exists():
        raise ValidationError("La obligación ya fue pagada y no admite un segundo pago completo.")
    if payable.status == Payable.Status.SUSPENDED:
        raise ValidationError("Reactive la obligación antes de registrar su pago.")
    if payable.amount is None:
        raise ValidationError("Defina el monto de la obligación antes de registrar el pago.")
    if amount != payable.amount:
        raise ValidationError("El pago completo debe coincidir con el monto registrado de la obligación.")

    receipt = Attachment.objects.create(
        payable=payable,
        kind=Attachment.Kind.RECEIPT,
        file=receipt_upload,
        original_name=receipt_upload.name,
        content_type=getattr(receipt_upload, "content_type", "application/octet-stream") or "application/octet-stream",
        size_bytes=receipt_upload.size,
        uploaded_by=actor,
    )
    payment = Payment(
        payable=payable,
        amount=amount,
        paid_on=paid_on,
        operation_reference=operation_reference,
        receipt=receipt,
        registered_by=actor,
    )
    payment.full_clean()
    payment.save()
    payable.status = Payable.Status.PAID
    payable.suspension_note = ""
    payable.suspended_by = None
    payable.suspended_at = None
    payable.save(update_fields=("status", "suspension_note", "suspended_by", "suspended_at", "updated_at"))
    record_audit(actor, AuditLog.Action.PAYMENT_RECORDED, payment, f"Registró el pago de «{payable.concept}».")
    return payment


@transaction.atomic
def set_payable_suspension(*, actor, payable: Payable, suspend: bool, note: str = "") -> Payable:
    ensure_manager(actor)
    if payable.status == Payable.Status.PAID:
        raise ValidationError("No puede suspender una obligación que ya fue pagada.")
    if suspend:
        payable.status = Payable.Status.SUSPENDED
        payable.suspension_note = note.strip()
        payable.suspended_by = actor
        payable.suspended_at = timezone.now()
        wording = "suspendió"
    else:
        payable.status = Payable.Status.PENDING
        payable.suspension_note = ""
        payable.suspended_by = None
        payable.suspended_at = None
        wording = "reactivó"
    payable.save(
        update_fields=("status", "suspension_note", "suspended_by", "suspended_at", "updated_at")
    )
    record_audit(actor, AuditLog.Action.PAYABLE_STATUS, payable, f"{wording.capitalize()} «{payable.concept}».")
    return payable


@transaction.atomic
def save_destination_account(*, actor, account: DestinationAccount) -> DestinationAccount:
    ensure_manager(actor)
    is_new = account.pk is None
    account.updated_by = actor
    if is_new:
        account.created_by = actor
    account.full_clean()
    account.save()
    verb = "Creó" if is_new else "Actualizó"
    record_audit(actor, AuditLog.Action.DESTINATION_ACCOUNT, account, f"{verb} una cuenta de destino para {account.creditor.name}.")
    return account


def manager_month_summary(queryset: QuerySet[Payable]) -> dict[str, dict[str, Decimal | int]]:
    """Calculate each payable exactly once; unknown amounts contribute zero to money totals."""
    buckets: dict[str, dict[str, Decimal | int]] = {
        "paid": {"count": 0, "amount": Decimal("0.00")},
        "pending": {"count": 0, "amount": Decimal("0.00")},
        "overdue": {"count": 0, "amount": Decimal("0.00")},
        "suspended": {"count": 0, "amount": Decimal("0.00")},
    }
    today = timezone.localdate()
    for payable in queryset:
        if payable.status == Payable.Status.PAID:
            key = "paid"
        elif payable.status == Payable.Status.SUSPENDED:
            key = "suspended"
        elif payable.due_date < today:
            key = "overdue"
        else:
            key = "pending"
        buckets[key]["count"] = int(buckets[key]["count"]) + 1
        buckets[key]["amount"] = Decimal(buckets[key]["amount"]) + (payable.amount or Decimal("0.00"))
    return buckets
