from __future__ import annotations

import mimetypes
import calendar as month_calendar
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from identity.authorization import roles_required
from identity.models import Role

from .forms import (
    AttachmentWithdrawalForm,
    BalanceMovementForm,
    DestinationAccountForm,
    FundingSourceForm,
    FundsUnavailableReportForm,
    MonthlyGenerationForm,
    PayableFilterForm,
    PayableForm,
    PayableImportForm,
    PayableReviewStatusForm,
    PaymentCommitmentForm,
    PaymentContextForm,
    RecordPaymentForm,
    ServiceAccountFilterForm,
    ServiceAccountForm,
    ServiceAccountImportForm,
    SourceDocumentForm,
    SuspensionForm,
    VoidMovementForm,
)
from .importing import ServiceAccountImportError, parse_service_account_import
from .payable_importing import PayableImportError, parse_payable_import
from .models import (
    Attachment,
    AuditLog,
    Branch,
    Company,
    Creditor,
    DestinationAccount,
    FundingSource,
    InternalReminder,
    Payable,
    PayableImportBatch,
    Payment,
    PaymentCommitment,
    PaymentContext,
    ServiceAccount,
    missing_required_payment_details,
)
from .services import (
    actor_is_manager,
    attach_source_document,
    create_commitment,
    create_payable,
    generate_monthly_payables,
    generate_scheduled_payables,
    link_service_account_to_payable,
    manager_month_summary,
    record_payment,
    record_balance_movement,
    record_audit,
    report_funds_unavailable,
    resolve_funds_unavailable,
    reveal_payment_instruction,
    save_funding_source,
    save_payment_context,
    save_destination_account,
    save_service_account,
    set_commitment_active,
    set_commitment_paused,
    set_payable_suspension,
    set_payable_review_status,
    set_reminder_status,
    update_payable,
    update_commitment,
    urgency_ordered_payables,
    payable_queryset_for,
    possible_duplicate_payables,
    visible_contexts_for,
    void_payment_movement,
    withdraw_source_document,
    skip_next_occurrence,
)

PAYMENT_ROLES = (Role.Code.MANAGER, Role.Code.ASSISTANT)


def _payable_queryset(actor):
    return payable_queryset_for(actor).select_related(
        "context",
        "company",
        "branch",
        "creditor",
        "commitment",
        "created_by",
        "service_account",
        "destination_account",
        "funding_source",
        "funds_unavailable_reported_by",
    ).prefetch_related(
        "attachments",
        Prefetch(
            "payment_movements",
            queryset=Payment.objects.select_related("receipt", "registered_by", "funding_source").order_by(
                "-paid_on", "-pk"
            ),
        ),
    )


def _apply_exception_filter(queryset, exception: str | None):
    if exception == "MISSING_SERVICE_ACCOUNT":
        return queryset.filter(category=PaymentCommitment.Category.SERVICE, service_account__isnull=True)
    if exception == "MISSING_SOURCE_DOCUMENT":
        return queryset.exclude(
            attachments__in=Attachment.objects.filter(
                kind=Attachment.Kind.SOURCE,
                withdrawn_at__isnull=True,
            )
        )
    if exception == "FUNDS_UNAVAILABLE":
        return queryset.filter(funds_unavailable_reported_at__isnull=False)
    if exception == "INCOMPLETE":
        return queryset.filter(Q(is_incomplete=True) | Q(amount__isnull=True))
    if exception == "READY_TO_PAY":
        return (
            queryset.filter(
                amount__isnull=False,
                is_incomplete=False,
                attachments__kind=Attachment.Kind.SOURCE,
                attachments__withdrawn_at__isnull=True,
            )
            .filter(~Q(category=PaymentCommitment.Category.SERVICE) | Q(service_account__isnull=False))
            .distinct()
        )
    return queryset


def _apply_board_filters(queryset, filter_form):
    """Keep the board in its required pending-only scope while filtering visual status."""
    if not filter_form.is_valid():
        return queryset
    data = filter_form.cleaned_data
    queryset = _apply_scope_filters(queryset, filter_form)

    today = timezone.localdate()
    state = data.get("state")
    if state == "OVERDUE":
        queryset = queryset.filter(due_date__lt=today)
    elif state == "DUE_TODAY":
        queryset = queryset.filter(due_date=today)
    elif state == "DUE_SOON":
        queryset = queryset.filter(due_date__gt=today, due_date__lte=today + timedelta(days=5))
    elif state == "PENDING":
        queryset = queryset.filter(due_date__gt=today + timedelta(days=5))
    return _apply_exception_filter(queryset, data.get("exception"))


def _apply_scope_filters(queryset, filter_form):
    """Apply the shared operational dimensions without changing a view's purpose."""
    if not filter_form.is_valid():
        return queryset
    if filter_form.cleaned_data.get("context"):
        queryset = queryset.filter(context=filter_form.cleaned_data["context"])
    if filter_form.cleaned_data.get("company"):
        queryset = queryset.filter(company=filter_form.cleaned_data["company"])
    if filter_form.cleaned_data.get("branch"):
        queryset = queryset.filter(branch=filter_form.cleaned_data["branch"])
    if filter_form.cleaned_data.get("creditor"):
        queryset = queryset.filter(creditor=filter_form.cleaned_data["creditor"])
    if filter_form.cleaned_data.get("category"):
        queryset = queryset.filter(category=filter_form.cleaned_data["category"])
    if filter_form.cleaned_data.get("currency"):
        queryset = queryset.filter(currency=filter_form.cleaned_data["currency"])
    if filter_form.cleaned_data.get("person"):
        person = filter_form.cleaned_data["person"].strip()
        queryset = queryset.filter(Q(holder_name__icontains=person) | Q(beneficiary_name__icontains=person))
    if filter_form.cleaned_data.get("due_from"):
        queryset = queryset.filter(due_date__gte=filter_form.cleaned_data["due_from"])
    if filter_form.cleaned_data.get("due_to"):
        queryset = queryset.filter(due_date__lte=filter_form.cleaned_data["due_to"])
    if filter_form.cleaned_data.get("sensitive") in {"0", "1"}:
        queryset = queryset.filter(is_sensitive=filter_form.cleaned_data["sensitive"] == "1")
    return queryset


def _money_summary(payables, *, remaining_balance: bool = False):
    """Small presentational summary; unknown amounts remain visible as zero in totals."""
    return {
        "count": len(payables),
        "amount": sum(
            (
                (payable.balance_due if remaining_balance else payable.amount) or Decimal("0.00")
                for payable in payables
            ),
            Decimal("0.00"),
        ),
    }


def _has_active_source_document(payable: Payable) -> bool:
    return any(
        attachment.kind == Attachment.Kind.SOURCE and attachment.withdrawn_at is None
        for attachment in payable.attachments.all()
    )


@roles_required(*PAYMENT_ROLES)
@require_GET
@never_cache
def board(request):
    filter_form = PayableFilterForm(request.GET or None, actor=request.user)
    operational_payables = _payable_queryset(request.user).filter(currency=FundingSource.Currency.PEN)
    base = _apply_board_filters(operational_payables, filter_form)
    payables = list(urgency_ordered_payables(base))
    queue_payables = list(
        urgency_ordered_payables(_apply_scope_filters(operational_payables, filter_form))
    )
    historical_payables = list(
        _payable_queryset(request.user)
        .exclude(currency=FundingSource.Currency.PEN)
        .order_by("-due_date", "-pk")[:50]
    )
    for payable in (*payables, *queue_payables):
        payable.has_active_source_document = _has_active_source_document(payable)
    counts = Counter(payable.visual_status() for payable in queue_payables)
    counts["UPCOMING"] = counts["DUE_TODAY"] + counts["DUE_SOON"]
    without_source_document = sum(
        not payable.has_active_source_document
        for payable in queue_payables
    )
    without_service_account = sum(
        payable.category == PaymentCommitment.Category.SERVICE and not payable.service_account_id
        for payable in queue_payables
    )
    incomplete = sum(payable.is_incomplete or payable.amount is None for payable in queue_payables)
    ready_to_pay = sum(
        payable.amount is not None
        and not payable.is_incomplete
        and payable.has_active_source_document
        and (payable.category != PaymentCommitment.Category.SERVICE or payable.service_account_id is not None)
        for payable in queue_payables
    )
    generation_form = MonthlyGenerationForm(initial={"period": timezone.localdate().replace(day=1)})
    commitments = PaymentCommitment.objects.filter(
        context_id__in=visible_contexts_for(request.user).values("pk"),
        currency=FundingSource.Currency.PEN,
    ).select_related("context", "company", "branch", "creditor").order_by("is_active", "name")
    historical_commitments = PaymentCommitment.objects.filter(
        context_id__in=visible_contexts_for(request.user).values("pk")
    ).exclude(currency=FundingSource.Currency.PEN).select_related(
        "context", "company", "branch", "creditor"
    ).order_by("name")
    return render(
        request,
        "payments/board.html",
        {
            "payables": payables,
            "filter_form": filter_form,
            "counts": counts,
            "generation_form": generation_form,
            "scheduled_through": timezone.localdate() + timedelta(days=30),
            "commitments": commitments,
            "historical_commitments": historical_commitments,
            "historical_payables": historical_payables,
            "alert_days": 5,
            "work_summary": {
                "without_source_document": without_source_document,
                "without_service_account": without_service_account,
                "incomplete": incomplete,
                "ready_to_pay": ready_to_pay,
            },
        },
    )


@roles_required(*PAYMENT_ROLES)
@require_http_methods(["GET", "POST"])
@never_cache
def commitment_create(request):
    form = PaymentCommitmentForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            commitment = create_commitment(actor=request.user, commitment=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Compromiso «{commitment.name}» creado.")
            return redirect("payments-board")
    return render(request, "payments/commitment_form.html", {"form": form})


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def commitment_edit(request, commitment_id):
    commitment = get_object_or_404(
        PaymentCommitment.objects.filter(context_id__in=visible_contexts_for(request.user).values("pk")),
        pk=commitment_id,
    )
    if commitment.currency != FundingSource.Currency.PEN:
        messages.info(request, "Los compromisos históricos en USD son solo de consulta.")
        return redirect("payments-board")
    form = PaymentCommitmentForm(request.POST or None, instance=commitment, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            commitment = update_commitment(actor=request.user, commitment=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Reglas futuras de «{commitment.name}» actualizadas.")
            return redirect("payments-board")
    return render(
        request,
        "payments/commitment_form.html",
        {"form": form, "editing_commitment": commitment},
    )


@roles_required(Role.Code.MANAGER)
@require_POST
def commitment_toggle(request, commitment_id):
    commitment = get_object_or_404(
        PaymentCommitment.objects.filter(context_id__in=visible_contexts_for(request.user).values("pk")),
        pk=commitment_id,
    )
    should_activate = request.POST.get("activate") == "1"
    try:
        set_commitment_active(actor=request.user, commitment=commitment, is_active=should_activate)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, f"Compromiso {'activado' if should_activate else 'desactivado'} sin borrar su historial.")
    return redirect("payments-board")


@roles_required(Role.Code.MANAGER)
@require_POST
def commitment_pause(request, commitment_id):
    try:
        commitment = set_commitment_paused(
            actor=request.user,
            commitment_id=commitment_id,
            paused=request.POST.get("paused") == "1",
        )
    except (ValidationError, PaymentCommitment.DoesNotExist) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Recurrencia pausada." if commitment.is_paused else "Recurrencia reanudada.")
    return redirect("payments-board")


@roles_required(Role.Code.MANAGER)
@require_POST
def commitment_skip(request, commitment_id):
    try:
        commitment = skip_next_occurrence(
            actor=request.user,
            commitment_id=commitment_id,
            reason=request.POST.get("reason", ""),
        )
    except (ValidationError, PaymentCommitment.DoesNotExist) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Se omitió una ocurrencia; la próxima será {commitment.next_occurrence:%d/%m/%Y}.")
    return redirect("payments-board")


@roles_required(*PAYMENT_ROLES)
@require_POST
def monthly_generation(request):
    form = MonthlyGenerationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Seleccione un mes válido para generar las obligaciones.")
        return redirect("payments-board")
    created, skipped = generate_monthly_payables(actor=request.user, period=form.cleaned_data["period"])
    messages.success(request, f"Se generaron {len(created)} obligaciones; {skipped} ya existían para ese período.")
    return redirect("payments-board")


@roles_required(*PAYMENT_ROLES)
@require_POST
def scheduled_generation(request):
    raw_date = request.POST.get("through", "")
    try:
        through = date.fromisoformat(raw_date)
    except ValueError:
        messages.error(request, "Seleccione una fecha válida para generar las ocurrencias.")
        return redirect("payments-board")
    try:
        created, skipped = generate_scheduled_payables(actor=request.user, through=through)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("payments-board")
    messages.success(
        request,
        f"Se generaron {len(created)} ocurrencias programadas; {skipped} ya existían.",
    )
    return redirect("payments-board")


@roles_required(*PAYMENT_ROLES)
@require_http_methods(["GET", "POST"])
@never_cache
def payable_create(request):
    selected_commitment = None
    commitment_id = request.GET.get("commitment")
    if commitment_id and commitment_id.isdigit():
        selected_commitment = PaymentCommitment.objects.filter(
            pk=int(commitment_id),
            is_active=True,
            context__is_active=True,
            currency=FundingSource.Currency.PEN,
            context_id__in=visible_contexts_for(request.user).values("pk"),
        ).first()
    form = PayableForm(request.POST or None, selected_commitment=selected_commitment, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            payable = create_payable(actor=request.user, payable=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Obligación creada. Puede adjuntar su documento ahora.")
            return redirect("payment-payable-detail", payable_id=payable.pk)
    return render(request, "payments/payable_form.html", {"form": form, "selected_commitment": selected_commitment})


@roles_required(*PAYMENT_ROLES)
@require_http_methods(["GET", "POST"])
@never_cache
def payable_edit(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    if payable.currency != FundingSource.Currency.PEN:
        messages.info(request, "Las obligaciones históricas en USD son solo de consulta.")
        return redirect("payment-payable-detail", payable_id=payable.pk)
    if payable.status not in {Payable.Status.PENDING, Payable.Status.PARTIAL}:
        messages.error(request, "Solo se pueden editar obligaciones abiertas.")
        return redirect("payment-payable-detail", payable_id=payable.pk)
    form = PayableForm(request.POST or None, instance=payable, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            payable = update_payable(actor=request.user, payable=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Obligación actualizada correctamente.")
            return redirect("payment-payable-detail", payable_id=payable.pk)
    return render(
        request,
        "payments/payable_form.html",
        {"form": form, "selected_commitment": payable.commitment, "editing_payable": payable},
    )


def _render_payable_detail(
    request,
    payable,
    *,
    source_form=None,
    payment_form=None,
    suspension_form=None,
    movement_form=None,
    void_form=None,
    review_form=None,
    funds_unavailable_form=None,
    status=200,
):
    audit_logs = AuditLog.objects.filter(
        target_type="payments.payable", target_id=str(payable.pk)
    ).select_related("actor")[:50]
    source_documents = payable.attachments.filter(
        kind=Attachment.Kind.SOURCE,
        withdrawn_at__isnull=True,
    ).select_related("uploaded_by")
    withdrawn_source_documents = (
        payable.attachments.filter(
            kind=Attachment.Kind.SOURCE,
            withdrawn_at__isnull=False,
        ).select_related("uploaded_by", "withdrawn_by")
        if actor_is_manager(request.user)
        else Attachment.objects.none()
    )
    has_financial_movements = payable.payment_movements.exists()
    can_operate_payable = payable.currency == FundingSource.Currency.PEN
    return render(
        request,
        "payments/payable_detail.html",
        {
            "payable": payable,
            "has_source_document": source_documents.exists(),
            "source_documents": source_documents,
            "withdrawn_source_documents": withdrawn_source_documents,
            "can_operate_payable": can_operate_payable,
            "can_withdraw_source_documents": (
                can_operate_payable
                and not has_financial_movements
                and payable.status in {Payable.Status.PENDING, Payable.Status.SUSPENDED}
                and (actor_is_manager(request.user) or payable.status == Payable.Status.PENDING)
            ),
            "source_form": source_form or SourceDocumentForm(),
            "withdrawal_form": AttachmentWithdrawalForm(),
            "payment_form": payment_form or RecordPaymentForm(payable=payable, actor=request.user),
            "suspension_form": suspension_form or SuspensionForm(initial={"note": payable.suspension_note}),
            "movement_form": movement_form or BalanceMovementForm(),
            "void_form": void_form or VoidMovementForm(),
            "review_form": review_form or PayableReviewStatusForm(
                payable=payable,
                initial={"note": payable.suspension_note},
            ),
            "funds_unavailable_form": funds_unavailable_form or FundsUnavailableReportForm(),
            "movements": payable.payment_movements.select_related(
                "receipt", "registered_by", "funding_source", "voided_by"
            ).order_by("-paid_on", "-pk"),
            "audit_logs": audit_logs,
        },
        status=status,
    )


@roles_required(*PAYMENT_ROLES)
@require_GET
@never_cache
def payable_detail(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    if payable.is_sensitive:
        record_audit(
            request.user,
            AuditLog.Action.SENSITIVE_ACCESS,
            payable,
            "Consultó una obligación privada.",
            {"surface": "detail"},
        )
    return _render_payable_detail(request, payable)


@roles_required(*PAYMENT_ROLES)
@require_POST
@never_cache
def payment_instruction_reveal(request, payable_id):
    get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    try:
        payable = reveal_payment_instruction(actor=request.user, payable_id=payable_id)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("payment-payable-detail", payable_id=payable_id)
    return render(request, "payments/payment_instruction_reveal.html", {"payable": payable})


@roles_required(*PAYMENT_ROLES)
@require_POST
def source_document_upload(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    form = SourceDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            attach_source_document(actor=request.user, payable=payable, upload=form.cleaned_data["document"])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Documento por pagar adjuntado.")
            return redirect("payment-payable-detail", payable_id=payable.pk)
    return _render_payable_detail(request, payable, source_form=form, status=400)


@roles_required(*PAYMENT_ROLES)
@require_POST
def source_document_withdraw(request, payable_id, attachment_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    attachment = get_object_or_404(
        Attachment,
        pk=attachment_id,
        payable=payable,
        kind=Attachment.Kind.SOURCE,
    )
    form = AttachmentWithdrawalForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Indique un motivo válido para retirar el documento.")
        return redirect("payment-payable-detail", payable_id=payable.pk)
    was_withdrawn = attachment.withdrawn_at is not None
    try:
        withdraw_source_document(
            actor=request.user,
            attachment_id=attachment.pk,
            reason=form.cleaned_data["reason"],
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(
            request,
            "El documento ya estaba retirado."
            if was_withdrawn
            else "Documento retirado sin borrar la evidencia histórica.",
        )
    return redirect("payment-payable-detail", payable_id=payable.pk)


@roles_required(Role.Code.ASSISTANT)
@require_POST
def payable_funds_unavailable_report(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    form = FundsUnavailableReportForm(request.POST)
    if not form.is_valid():
        return _render_payable_detail(
            request,
            payable,
            funds_unavailable_form=form,
            status=400,
        )
    was_open = payable.funds_unavailable_reported_at is not None
    try:
        report_funds_unavailable(
            actor=request.user,
            payable=payable,
            note=form.cleaned_data["note"],
        )
    except ValidationError as error:
        form.add_error(None, error)
        return _render_payable_detail(
            request,
            payable,
            funds_unavailable_form=form,
            status=400,
        )
    messages.success(
        request,
        "La falta de fondos ya estaba reportada."
        if was_open
        else "Falta de fondos reportada al gerente sin suspender la obligación.",
    )
    return redirect("payment-payable-detail", payable_id=payable.pk)


@roles_required(Role.Code.MANAGER)
@require_POST
def payable_funds_unavailable_resolve(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    was_open = payable.funds_unavailable_reported_at is not None
    try:
        resolve_funds_unavailable(actor=request.user, payable=payable)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("payment-payable-detail", payable_id=payable.pk)
    messages.success(
        request,
        "Aviso de falta de fondos marcado como atendido."
        if was_open
        else "El aviso ya estaba atendido.",
    )
    return redirect("payment-payable-detail", payable_id=payable.pk)


@roles_required(*PAYMENT_ROLES)
@require_POST
def payment_record(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    form = RecordPaymentForm(request.POST, request.FILES, payable=payable, actor=request.user)
    if form.is_valid():
        try:
            record_payment(
                actor=request.user,
                payable_id=payable.pk,
                amount=form.cleaned_data["amount"],
                paid_on=form.cleaned_data["paid_on"],
                operation_reference=form.cleaned_data["operation_reference"],
                receipt_upload=form.cleaned_data["receipt"],
                funding_source=form.cleaned_data["funding_source"],
                allow_partial=True,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Pago registrado. El saldo de la obligación se actualizó correctamente.")
            return redirect("payment-payable-detail", payable_id=payable.pk)
    return _render_payable_detail(request, payable, payment_form=form, status=400)


@roles_required(Role.Code.MANAGER)
@require_POST
def payment_movement_record(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    form = BalanceMovementForm(request.POST)
    if form.is_valid():
        try:
            record_balance_movement(
                actor=request.user,
                payable_id=payable.pk,
                kind=form.cleaned_data["kind"],
                amount=form.cleaned_data["amount"],
                movement_on=form.cleaned_data["movement_on"],
                reason=form.cleaned_data["reason"],
                operation_reference=form.cleaned_data["operation_reference"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Movimiento registrado sin alterar la evidencia anterior.")
            return redirect("payment-payable-detail", payable_id=payable.pk)
    return _render_payable_detail(request, payable, movement_form=form, status=400)


@roles_required(Role.Code.MANAGER)
@require_POST
def payment_movement_void(request, payable_id, movement_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    movement = get_object_or_404(Payment, pk=movement_id, payable=payable)
    form = VoidMovementForm(request.POST)
    if form.is_valid():
        try:
            void_payment_movement(
                actor=request.user,
                movement_id=movement.pk,
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Movimiento anulado; permanece visible en el historial.")
            return redirect("payment-payable-detail", payable_id=payable.pk)
    return _render_payable_detail(request, payable, void_form=form, status=400)


@roles_required(Role.Code.MANAGER)
@require_POST
def payable_suspension(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    form = SuspensionForm(request.POST)
    if not form.is_valid():
        return _render_payable_detail(request, payable, suspension_form=form, status=400)
    try:
        set_payable_suspension(
            actor=request.user,
            payable=payable,
            suspend=payable.status != Payable.Status.SUSPENDED,
            note=form.cleaned_data["note"],
        )
    except ValidationError as error:
        form.add_error(None, error)
        return _render_payable_detail(request, payable, suspension_form=form, status=400)
    messages.success(request, "Obligación suspendida." if payable.status == Payable.Status.SUSPENDED else "Obligación reactivada.")
    return redirect("payment-payable-detail", payable_id=payable.pk)


@roles_required(Role.Code.MANAGER)
@require_POST
def payable_review_status(request, payable_id):
    payable = get_object_or_404(_payable_queryset(request.user), pk=payable_id)
    form = PayableReviewStatusForm(request.POST, payable=payable)
    if form.is_valid():
        try:
            set_payable_review_status(
                actor=request.user,
                payable=payable,
                status=form.cleaned_data["status"],
                note=form.cleaned_data["note"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Estado de la obligación actualizado.")
            return redirect("payment-payable-detail", payable_id=payable.pk)
    return _render_payable_detail(request, payable, review_form=form, status=400)


@roles_required(*PAYMENT_ROLES)
@require_GET
@never_cache
def payment_history(request):
    filters = PayableFilterForm(request.GET or None, actor=request.user)
    payables = _apply_scope_filters(
        _payable_queryset(request.user).filter(
            payment_movements__kind=Payment.Kind.PAYMENT,
            payment_movements__is_void=False,
        ).distinct(),
        filters,
    ).annotate(latest_payment_on=Max("payment_movements__paid_on"))
    return render(
        request,
        "payments/history.html",
        {"payables": payables.order_by("-latest_payment_on", "-pk"), "filter_form": filters},
    )


def _selected_month(raw_month: str | None):
    if raw_month:
        try:
            return datetime.strptime(raw_month, "%Y-%m").date().replace(day=1)
        except ValueError:
            pass
    return timezone.localdate().replace(day=1)


@roles_required(Role.Code.MANAGER)
@require_GET
@never_cache
def manager_dashboard(request):
    selected_month = _selected_month(request.GET.get("month"))
    next_month = (selected_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    filters = PayableFilterForm(request.GET or None, actor=request.user)
    payables = _apply_scope_filters(
        _payable_queryset(request.user).filter(due_date__gte=selected_month, due_date__lt=next_month), filters
    ).order_by("due_date", "pk")
    payables = list(payables)

    today = timezone.localdate()
    cashflow_payables = list(
        _apply_scope_filters(
            _payable_queryset(request.user).filter(
                status__in=(Payable.Status.PENDING, Payable.Status.PARTIAL),
                due_date__gte=today,
                due_date__lte=today + timedelta(days=30),
            ),
            filters,
        ).order_by("due_date", "pk")
    )
    next_week = [payable for payable in cashflow_payables if payable.due_date <= today + timedelta(days=7)]
    attention_payables = list(
        _apply_scope_filters(
            _payable_queryset(request.user).filter(
                status__in=(Payable.Status.PENDING, Payable.Status.PARTIAL),
                due_date__lte=today + timedelta(days=30),
            ),
            filters,
        ).order_by("due_date", "pk")
    )
    attention_items = [
        payable
        for payable in attention_payables
        if payable.due_date < today
        or (payable.category == PaymentCommitment.Category.SERVICE and not payable.service_account_id)
        or payable.is_incomplete
        or payable.amount is None
        or not any(attachment.kind == Attachment.Kind.SOURCE for attachment in payable.attachments.all())
    ][:5]
    exception_scope = list(
        _apply_scope_filters(
            _payable_queryset(request.user).filter(status__in=(Payable.Status.PENDING, Payable.Status.PARTIAL)),
            filters,
        )
    )
    exception_summary = {
        "overdue": sum(payable.due_date < today for payable in exception_scope),
        "without_service_account": sum(
            payable.category == PaymentCommitment.Category.SERVICE and not payable.service_account_id
            for payable in exception_scope
        ),
        "without_source_document": sum(
            not any(attachment.kind == Attachment.Kind.SOURCE for attachment in payable.attachments.all())
            for payable in exception_scope
        ),
        "incomplete": sum(payable.is_incomplete or payable.amount is None for payable in exception_scope),
    }
    currency_labels = dict(FundingSource.Currency.choices)
    summary_by_currency = {
        code: {
            "label": currency_labels[code],
            "buckets": manager_month_summary([item for item in payables if item.currency == code]),
            "reimbursement_pending": _money_summary(
                [
                    item
                    for item in payables
                    if item.currency == code and item.reimbursement_pending > Decimal("0.00")
                ]
            ),
            "reimbursement_pending_amount": sum(
                (
                    item.reimbursement_pending
                    for item in payables
                    if item.currency == code
                ),
                Decimal("0.00"),
            ),
            "reimbursement_received_amount": sum(
                (
                    item.reimbursements_received
                    for item in payables
                    if item.currency == code
                ),
                Decimal("0.00"),
            ),
        }
        for code in currency_labels
        if any(item.currency == code for item in payables)
    }
    cashflow_by_currency = {
        code: {
            "label": currency_labels[code],
            "next_week": _money_summary(
                [item for item in next_week if item.currency == code], remaining_balance=True
            ),
            "next_month": _money_summary(
                [item for item in cashflow_payables if item.currency == code], remaining_balance=True
            ),
        }
        for code in currency_labels
        if any(item.currency == code for item in cashflow_payables)
    }
    return render(
        request,
        "payments/manager_dashboard.html",
        {
            "payables": payables,
            "summary": manager_month_summary(payables),
            "summary_by_currency": summary_by_currency,
            "filter_form": filters,
            "selected_month": selected_month,
            "cashflow": {
                "next_week": _money_summary(next_week, remaining_balance=True),
                "next_month": _money_summary(cashflow_payables, remaining_balance=True),
            },
            "cashflow_by_currency": cashflow_by_currency,
            "attention_items": attention_items,
            "exception_summary": exception_summary,
            "today": today,
        },
    )


@roles_required(*PAYMENT_ROLES)
@require_GET
@never_cache
def payment_calendar(request):
    selected_month = _selected_month(request.GET.get("month"))
    next_month = (selected_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    previous_month = (selected_month - timedelta(days=1)).replace(day=1)
    payables = list(
        _payable_queryset(request.user)
        .filter(due_date__gte=selected_month, due_date__lt=next_month)
        .order_by("due_date", "pk")
    )
    by_day: dict[date, list[Payable]] = {}
    for payable in payables:
        by_day.setdefault(payable.due_date, []).append(payable)
    weeks = []
    for week in month_calendar.Calendar(firstweekday=0).monthdatescalendar(
        selected_month.year, selected_month.month
    ):
        weeks.append(
            [
                {
                    "date": day,
                    "in_month": day.month == selected_month.month,
                    "payables": by_day.get(day, []),
                }
                for day in week
            ]
        )
    reminders = InternalReminder.objects.filter(
        payable_id__in=payable_queryset_for(request.user).values("pk"),
        remind_on__gte=selected_month,
        remind_on__lt=next_month,
    ).select_related("payable__context").order_by("remind_on", "payable__due_date")
    return render(
        request,
        "payments/calendar.html",
        {
            "selected_month": selected_month,
            "previous_month": previous_month,
            "next_month": next_month,
            "weeks": weeks,
            "payables": payables,
            "reminders": reminders,
        },
    )


@roles_required(*PAYMENT_ROLES)
@require_POST
def reminder_update(request, reminder_id):
    status = request.POST.get("status", "")
    try:
        set_reminder_status(actor=request.user, reminder_id=reminder_id, status=status)
    except (ValidationError, InternalReminder.DoesNotExist) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Recordatorio actualizado.")
    month = request.POST.get("month", "")
    return redirect(f"{reverse('payment-calendar')}?month={month}" if month else "payment-calendar")


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def payment_contexts(request):
    form = PaymentContextForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            context = save_payment_context(actor=request.user, context=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Ámbito «{context.name}» guardado.")
            return redirect("payment-contexts")
    contexts = PaymentContext.objects.select_related("company").annotate(
        payable_count=Count("payables", distinct=True)
    )
    return render(request, "payments/contexts.html", {"form": form, "contexts": contexts})


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def payment_context_edit(request, context_id):
    context = get_object_or_404(PaymentContext, pk=context_id)
    form = PaymentContextForm(request.POST or None, instance=context)
    if request.method == "POST" and form.is_valid():
        try:
            save_payment_context(actor=request.user, context=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Ámbito actualizado.")
            return redirect("payment-contexts")
    return render(request, "payments/context_form.html", {"form": form, "context": context})


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def funding_sources(request):
    form = FundingSourceForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            source = save_funding_source(actor=request.user, source=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Fuente «{source.name}» guardada.")
            return redirect("payment-funding-sources")
    sources = FundingSource.objects.select_related("context", "updated_by")
    return render(request, "payments/funding_sources.html", {"form": form, "sources": sources})


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def funding_source_edit(request, source_id):
    source = get_object_or_404(FundingSource, pk=source_id)
    if source.currency != FundingSource.Currency.PEN:
        messages.info(request, "Las fuentes históricas en USD son solo de consulta.")
        return redirect("payment-funding-sources")
    form = FundingSourceForm(request.POST or None, instance=source, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            save_funding_source(actor=request.user, source=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Fuente de fondos actualizada.")
            return redirect("payment-funding-sources")
    return render(request, "payments/funding_source_form.html", {"form": form, "source": source})


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def payable_import(request):
    form = PayableImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["workbook"]
        try:
            rows = parse_payable_import(upload)
        except PayableImportError as error:
            form.add_error("workbook", str(error))
        else:
            valid_context_ids = set(visible_contexts_for(request.user).values_list("pk", flat=True))
            category_labels = dict(PaymentCommitment.Category.choices)
            duplicate_count = 0
            error_count = 0
            for row in rows:
                row["category_label"] = category_labels.get(row["category"], "Otra")
                context = PaymentContext.objects.filter(name__iexact=row["context_name"], is_active=True).first()
                creditor = Creditor.objects.filter(name__iexact=row["creditor_name"], is_active=True).first()
                if context is None or context.pk not in valid_context_ids:
                    row["errors"].append(f"No existe el ámbito activo «{row['context_name']}»")
                if creditor is None:
                    row["errors"].append(f"No existe el acreedor activo «{row['creditor_name']}»")
                row["context_id"] = context.pk if context else None
                row["creditor_id"] = creditor.pk if creditor else None
                row["duplicate_ids"] = []
                if context and creditor and row["due_date"]:
                    candidate = Payable(
                        context=context,
                        company=context.company,
                        concept=row["concept"],
                        category=row["category"],
                        creditor=creditor,
                        external_document_number=row["external_document_number"],
                        period=date.fromisoformat(row["period"]) if row["period"] else None,
                        amount=Decimal(row["amount"]) if row["amount"] else None,
                        currency=row["currency"],
                        due_date=date.fromisoformat(row["due_date"]),
                    )
                    candidates = possible_duplicate_payables(candidate)
                    row["duplicate_ids"] = list(candidates.values_list("pk", flat=True)[:10])
                    if row["duplicate_ids"]:
                        duplicate_count += 1
                        if row["external_document_number"] and candidates.filter(
                            external_document_number__iexact=row["external_document_number"]
                        ).exists():
                            row["errors"].append("Ya existe una obligación con el mismo número de documento")
                if row["errors"]:
                    error_count += 1
            batch = PayableImportBatch.objects.create(
                original_name=upload.name,
                status=PayableImportBatch.Status.REJECTED if error_count else PayableImportBatch.Status.PREVIEW,
                rows=rows,
                valid_count=len(rows) - error_count,
                error_count=error_count,
                duplicate_count=duplicate_count,
                created_by=request.user,
            )
            return redirect(f"{reverse('payment-payable-import')}?batch={batch.pk}")
    selected_batch = None
    raw_batch = request.GET.get("batch", "")
    if raw_batch.isdigit():
        selected_batch = PayableImportBatch.objects.filter(
            pk=int(raw_batch), created_by=request.user
        ).first()
    batches = PayableImportBatch.objects.filter(created_by=request.user)[:10]
    return render(
        request,
        "payments/payable_import.html",
        {"form": form, "batch": selected_batch, "batches": batches},
        status=400 if request.method == "POST" and form.errors else 200,
    )


@roles_required(Role.Code.MANAGER)
@require_POST
@never_cache
def payable_import_preview(request):
    form = PayableImportForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = form.errors.get("workbook") or form.non_field_errors()
        return JsonResponse(
            {"error": str(errors[0]) if errors else "No fue posible revisar el archivo."},
            status=400,
        )
    try:
        rows = parse_payable_import(form.cleaned_data["workbook"])
    except PayableImportError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse(
        {
            "headers": ["Ámbito", "Concepto", "Acreedor", "Monto", "Vencimiento"],
            "rows": [
                [
                    row["context_name"],
                    row["concept"],
                    row["creditor_name"],
                    f"{row['currency']} {row['amount']}" if row["amount"] else "Por definir",
                    row["due_date"] or "Con error",
                ]
                for row in rows[:4]
            ],
            "total": len(rows),
        }
    )


@roles_required(Role.Code.MANAGER)
@require_POST
def payable_import_confirm(request, batch_id):
    batch = get_object_or_404(
        PayableImportBatch.objects.all(),
        pk=batch_id,
        created_by=request.user,
    )
    if batch.status != PayableImportBatch.Status.PREVIEW or batch.error_count:
        messages.error(request, "Este lote necesita correcciones y no puede confirmarse.")
        return redirect(f"{reverse('payment-payable-import')}?batch={batch.pk}")
    confirmed_duplicates = request.POST.get("confirm_duplicates") == "1"
    duplicate_reason = request.POST.get("duplicate_reason", "").strip()
    if batch.duplicate_count and (not confirmed_duplicates or not duplicate_reason):
        messages.error(request, "Revise las coincidencias e indique por qué deben importarse.")
        return redirect(f"{reverse('payment-payable-import')}?batch={batch.pk}")
    try:
        with transaction.atomic():
            batch = PayableImportBatch.objects.select_for_update().get(
                pk=batch.pk, created_by=request.user, status=PayableImportBatch.Status.PREVIEW
            )
            for row in batch.rows:
                context = PaymentContext.objects.get(pk=row["context_id"], is_active=True)
                creditor = Creditor.objects.get(pk=row["creditor_id"], is_active=True)
                payable = Payable(
                    context=context,
                    company=context.company,
                    concept=row["concept"],
                    category=row["category"],
                    creditor=creditor,
                    external_document_number=row["external_document_number"],
                    period=date.fromisoformat(row["period"]) if row["period"] else None,
                    amount=Decimal(row["amount"]) if row["amount"] else None,
                    currency=row["currency"],
                    due_date=date.fromisoformat(row["due_date"]),
                    holder_name=row["holder_name"],
                    beneficiary_name=row["beneficiary_name"],
                    payment_nature=row["payment_nature"],
                    is_sensitive=row["is_sensitive"],
                    is_incomplete=(
                        not bool(row["amount"])
                        or bool(missing_required_payment_details(row["category"], {}))
                    ),
                )
                payable._duplicate_confirmed = confirmed_duplicates
                payable._duplicate_reason = duplicate_reason
                create_payable(actor=request.user, payable=payable)
            batch.status = PayableImportBatch.Status.CONFIRMED
            batch.confirmed_at = timezone.now()
            batch.error_message = ""
            batch.save(update_fields=("status", "confirmed_at", "error_message"))
            record_audit(
                request.user,
                AuditLog.Action.IMPORT_CONFIRMED,
                batch,
                f"Confirmó {batch.valid_count} obligaciones revisadas.",
                {"row_count": batch.valid_count, "duplicate_count": batch.duplicate_count},
            )
    except (
        ValidationError,
        PaymentContext.DoesNotExist,
        Creditor.DoesNotExist,
        PayableImportBatch.DoesNotExist,
    ) as error:
        # A second confirmation request can lose the row lock after the first
        # one already committed. Never downgrade that confirmed batch.
        current_batch = PayableImportBatch.objects.filter(
            pk=batch_id,
            created_by=request.user,
        ).first()
        if current_batch and current_batch.status == PayableImportBatch.Status.PREVIEW:
            current_batch.status = PayableImportBatch.Status.REJECTED
            current_batch.error_message = str(error)[:280]
            current_batch.save(update_fields=("status", "error_message"))
        batch = current_batch or batch
        messages.error(request, f"No se creó ninguna obligación: {error}")
        return redirect(f"{reverse('payment-payable-import')}?batch={batch.pk}")
    messages.success(request, f"Se importaron {batch.valid_count} obligaciones.")
    return redirect("payments-board")


@roles_required(Role.Code.MANAGER)
@require_GET
def payable_import_template(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="plantilla_obligaciones.csv"'
    response.write(
        "\ufeffámbito,categoría,concepto,acreedor,documento,período,monto,vencimiento,titular,beneficiario,naturaleza,sensible\n"
    )
    response.write(
        "Personal de Carlos,Tarjeta de crédito,Estado de tarjeta octubre,Banco,EST-001,2026-10-01,850.00,2026-10-25,Carlos,Carlos,Propio,No\n"
    )
    return response


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def destination_accounts(request):
    form = DestinationAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            account = save_destination_account(actor=request.user, account=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, f"Cuenta de destino para {account.creditor.name} guardada.")
            return redirect("payment-destination-accounts")
    accounts = DestinationAccount.objects.select_related("creditor", "updated_by").all()
    return render(request, "payments/destination_accounts.html", {"form": form, "accounts": accounts})


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def destination_account_edit(request, account_id):
    account = get_object_or_404(DestinationAccount, pk=account_id)
    form = DestinationAccountForm(request.POST or None, instance=account)
    if request.method == "POST" and form.is_valid():
        try:
            save_destination_account(actor=request.user, account=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Cuenta de destino actualizada correctamente.")
            return redirect("payment-destination-accounts")
    audit_logs = (
        AuditLog.objects.filter(target_type="payments.destinationaccount", target_id=str(account.pk))
        .select_related("actor")[:12]
    )
    return render(
        request,
        "payments/destination_account_form.html",
        {"form": form, "account": account, "audit_logs": audit_logs},
    )


def _service_account_queryset(actor):
    return ServiceAccount.objects.filter(
        context_id__in=visible_contexts_for(actor).values("pk")
    ).select_related("context", "company", "branch", "creditor", "updated_by").annotate(
        commitment_count=Count("commitments", distinct=True)
    )


def _apply_service_account_filters(queryset, filter_form):
    if not filter_form.is_valid():
        return queryset
    data = filter_form.cleaned_data
    if data.get("context"):
        queryset = queryset.filter(context=data["context"])
    if data.get("company"):
        queryset = queryset.filter(company=data["company"])
    if data.get("branch"):
        queryset = queryset.filter(branch=data["branch"])
    if data.get("creditor"):
        queryset = queryset.filter(creditor=data["creditor"])
    if data.get("status"):
        queryset = queryset.filter(status=data["status"])
    if data.get("search"):
        query = data["search"].strip()
        queryset = queryset.filter(
            Q(primary_identifier__icontains=query)
            | Q(account_holder__icontains=query)
            | Q(creditor__name__icontains=query)
        )
    return queryset


def _return_payable_from_request(request):
    raw_id = request.POST.get("return_payable") or request.GET.get("return_payable")
    if raw_id and raw_id.isdigit():
        return payable_queryset_for(request.user).filter(
            pk=int(raw_id), status__in=(Payable.Status.PENDING, Payable.Status.PARTIAL)
        ).first()
    return None


def _render_service_accounts_page(request, *, import_form=None, status=200):
    filter_form = ServiceAccountFilterForm(request.GET or None, actor=request.user)
    accounts = _apply_service_account_filters(_service_account_queryset(request.user), filter_form)
    return render(
        request,
        "payments/service_accounts.html",
        {
            "accounts": accounts,
            "filter_form": filter_form,
            "import_form": import_form or ServiceAccountImportForm(),
        },
        status=status,
    )


@roles_required(*PAYMENT_ROLES)
@require_GET
@never_cache
def service_accounts(request):
    return _render_service_accounts_page(request)


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def service_account_create(request):
    return_payable = _return_payable_from_request(request)
    initial = {}
    if return_payable:
        initial = {
            "context": return_payable.context_id,
            "company": return_payable.company_id,
            "branch": return_payable.branch_id,
            "creditor": return_payable.creditor_id,
            "service_type": ServiceAccount.ServiceType.OTHER,
            "identifier_type": ServiceAccount.IdentifierType.SUPPLY,
        }
    else:
        for field in ("context", "company", "branch", "creditor"):
            value = request.GET.get(field)
            if value and value.isdigit():
                initial[field] = int(value)

    form = ServiceAccountForm(request.POST or None, initial=initial, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                account = save_service_account(actor=request.user, account=form.save(commit=False))
                if return_payable:
                    link_service_account_to_payable(actor=request.user, payable=return_payable, account=account)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            if return_payable:
                messages.success(request, "Cuenta de servicio creada y asociada a la obligación.")
                return redirect("payment-payable-detail", payable_id=return_payable.pk)
            messages.success(request, "Cuenta de servicio creada correctamente.")
            return redirect("payment-service-accounts")
    return render(
        request,
        "payments/service_account_form.html",
        {"form": form, "return_payable": return_payable},
    )


@roles_required(Role.Code.MANAGER)
@require_http_methods(["GET", "POST"])
@never_cache
def service_account_edit(request, account_id):
    account = get_object_or_404(_service_account_queryset(request.user), pk=account_id)
    form = ServiceAccountForm(request.POST or None, instance=account, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            account = save_service_account(actor=request.user, account=form.save(commit=False))
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Cuenta de servicio actualizada correctamente.")
            return redirect("payment-service-accounts")
    audit_logs = (
        AuditLog.objects.filter(target_type="payments.serviceaccount", target_id=str(account.pk))
        .select_related("actor")[:12]
    )
    return render(
        request,
        "payments/service_account_form.html",
        {"form": form, "account": account, "audit_logs": audit_logs},
    )


@roles_required(Role.Code.MANAGER)
@require_POST
@never_cache
def service_account_import_preview(request):
    """Validate an import file and return a small, non-persistent content preview."""
    form = ServiceAccountImportForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = form.errors.get("workbook") or form.non_field_errors()
        message = str(errors[0]) if errors else "No fue posible revisar el archivo seleccionado."
        return JsonResponse({"error": message}, status=400)

    try:
        rows = parse_service_account_import(form.cleaned_data["workbook"])
    except ServiceAccountImportError as error:
        return JsonResponse({"error": str(error)}, status=400)

    service_labels = dict(ServiceAccount.ServiceType.choices)
    identifier_labels = dict(ServiceAccount.IdentifierType.choices)
    preview_rows = [
        [
            row["context_name"],
            row["branch_name"] or "Sin local",
            row["creditor_name"],
            service_labels.get(row["service_type"], row["service_type"]),
            f"{identifier_labels.get(row['identifier_type'], row['identifier_type'])}: {row['primary_identifier']}",
        ]
        for row in rows[:4]
    ]
    return JsonResponse(
        {
            "headers": ["Ámbito", "Local", "Acreedor", "Servicio", "Identificador"],
            "rows": preview_rows,
            "total": len(rows),
        }
    )


@roles_required(Role.Code.MANAGER)
@require_POST
def service_account_import(request):
    form = ServiceAccountImportForm(request.POST, request.FILES)
    if not form.is_valid():
        return _render_service_accounts_page(request, import_form=form, status=400)
    try:
        rows = parse_service_account_import(form.cleaned_data["workbook"])
    except ServiceAccountImportError as error:
        form.add_error("workbook", str(error))
        return _render_service_accounts_page(request, import_form=form, status=400)

    created = 0
    updated = 0
    try:
        with transaction.atomic():
            for row in rows:
                row_number = row["row_number"]
                context = PaymentContext.objects.filter(
                    name__iexact=row["context_name"].strip(),
                    is_active=True,
                ).first()
                if context is None and row["company_name"]:
                    company_match = Company.objects.filter(
                        name__iexact=row["company_name"].strip(),
                        is_active=True,
                    ).first()
                    context = PaymentContext.for_company(company_match) if company_match else None
                if context is None:
                    raise ServiceAccountImportError(
                        f"Fila {row_number}: no existe el ámbito activo «{row['context_name']}»."
                    )
                company = context.company
                branch = None
                if row["branch_name"]:
                    if company is None:
                        raise ServiceAccountImportError(
                            f"Fila {row_number}: un ámbito no empresarial no puede usar un local."
                        )
                    branch = Branch.objects.filter(
                        company=company, name__iexact=row["branch_name"].strip()
                    ).first()
                    if branch is None:
                        raise ServiceAccountImportError(
                            f"Fila {row_number}: no existe el local «{row['branch_name']}» para {company.name}."
                        )
                creditor = Creditor.objects.filter(
                    name__iexact=row["creditor_name"].strip()
                ).first()
                if creditor is None:
                    creditor = Creditor.objects.create(
                        name=row["creditor_name"].strip(),
                        is_active=True,
                    )
                elif not creditor.is_active:
                    raise ServiceAccountImportError(
                        f"Fila {row_number}: el acreedor «{row['creditor_name']}» está inactivo."
                    )
                account = ServiceAccount.objects.filter(
                    context=context,
                    branch=branch,
                    creditor=creditor,
                    identifier_type=row["identifier_type"],
                    primary_identifier=row["primary_identifier"],
                ).first()
                is_new = account is None
                if account is None:
                    account = ServiceAccount(
                        context=context,
                        company=company,
                        branch=branch,
                        creditor=creditor,
                        identifier_type=row["identifier_type"],
                        primary_identifier=row["primary_identifier"],
                    )
                for field in (
                    "service_type",
                    "account_holder",
                    "expected_billing_frequency",
                    "usual_billing_day",
                    "acquisition_channel",
                    "status",
                    "additional_identifiers",
                ):
                    setattr(account, field, row[field])
                save_service_account(actor=request.user, account=account)
                if is_new:
                    created += 1
                else:
                    updated += 1
    except (ServiceAccountImportError, ValidationError) as error:
        form.add_error(None, error)
        return _render_service_accounts_page(request, import_form=form, status=400)

    messages.success(request, f"Importación terminada: {created} creadas y {updated} actualizadas.")
    return redirect("payment-service-accounts")


@roles_required(*PAYMENT_ROLES)
@require_GET
def service_account_import_template(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="plantilla_cuentas_servicio.csv"'
    response.write("\ufeffámbito,empresa,local,acreedor,tipo de servicio,tipo de identificador,identificador principal,titular,frecuencia,día habitual,canal,estado,identificadores adicionales\n")
    response.write("Empresa Central,Empresa Central,Sede Principal,Proveedor de ejemplo,Electricidad,Suministro,12345678,Titular de la cuenta,Mensual,15,Manual,Activa,Número de medidor: 98765 | Código de predio: 4321\n")
    return response


def _open_private_attachment(actor, attachment_id: int) -> Attachment:
    attachment = get_object_or_404(
        Attachment.objects.select_related("payable__context").filter(
            payable_id__in=payable_queryset_for(actor).values("pk")
        ),
        pk=attachment_id,
    )
    if not attachment.file:
        raise Http404("El archivo ya no está disponible.")
    if attachment.withdrawn_at is not None and not actor_is_manager(actor):
        raise Http404("El documento ya no está disponible para la operación.")
    if settings.USE_SUPABASE_STORAGE:
        if not attachment.file.storage.exists(attachment.file.name):
            raise Http404("El archivo ya no está disponible.")
    else:
        try:
            attachment.file.open("rb")
        except FileNotFoundError as error:
            raise Http404("El archivo ya no está disponible.") from error
    if attachment.payable.is_sensitive:
        record_audit(
            actor,
            AuditLog.Action.SENSITIVE_ACCESS,
            attachment.payable,
            "Consultó un documento privado.",
            {"surface": "attachment", "attachment_id": attachment.pk},
        )
    return attachment


@roles_required(*PAYMENT_ROLES)
@require_GET
def attachment_download(request, attachment_id):
    attachment = _open_private_attachment(request.user, attachment_id)
    if settings.USE_SUPABASE_STORAGE:
        disposition = f"attachment; filename*=UTF-8''{quote(attachment.original_name, safe='')}"
        return redirect(
            attachment.file.storage.url(
                attachment.file.name,
                parameters={"ResponseContentDisposition": disposition},
            )
        )
    content_type = attachment.content_type or mimetypes.guess_type(attachment.original_name)[0] or "application/octet-stream"
    return FileResponse(attachment.file, as_attachment=True, filename=attachment.original_name, content_type=content_type)


@roles_required(*PAYMENT_ROLES)
@require_GET
@never_cache
@xframe_options_sameorigin
def attachment_preview(request, attachment_id):
    """Serve an allowed payment document inline without making private storage public."""
    attachment = _open_private_attachment(request.user, attachment_id)
    if not attachment.preview_type:
        raise Http404("Este tipo de archivo no admite vista previa.")

    content_types = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    content_type = content_types.get(
        attachment.original_name[attachment.original_name.rfind(".") :].lower(),
        "application/octet-stream",
    )
    if settings.USE_SUPABASE_STORAGE:
        disposition = f"inline; filename*=UTF-8''{quote(attachment.original_name, safe='')}"
        return redirect(
            attachment.file.storage.url(
                attachment.file.name,
                parameters={
                    "ResponseContentDisposition": disposition,
                    "ResponseContentType": content_type,
                },
            )
        )
    response = FileResponse(
        attachment.file,
        as_attachment=False,
        filename=attachment.original_name,
        content_type=content_type,
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response
