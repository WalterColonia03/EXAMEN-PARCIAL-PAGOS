from __future__ import annotations

import mimetypes
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from identity.authorization import roles_required
from identity.models import Role

from .forms import (
    DestinationAccountForm,
    MonthlyGenerationForm,
    PayableFilterForm,
    PayableForm,
    PaymentCommitmentForm,
    RecordPaymentForm,
    SourceDocumentForm,
    SuspensionForm,
)
from .models import Attachment, AuditLog, DestinationAccount, Payable, Payment, PaymentCommitment
from .services import (
    attach_source_document,
    create_commitment,
    create_payable,
    generate_monthly_payables,
    manager_month_summary,
    record_payment,
    save_destination_account,
    set_commitment_active,
    set_payable_suspension,
    urgency_ordered_payables,
)

PAYMENT_ROLES = (Role.Code.MANAGER, Role.Code.ASSISTANT)


def _payable_queryset():
    return Payable.objects.select_related("company", "branch", "creditor", "commitment", "created_by").prefetch_related(
        "attachments"
    )


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
    return queryset


def _apply_scope_filters(queryset, filter_form):
    """Apply the shared company/local scope without changing a view's purpose."""
    if not filter_form.is_valid():
        return queryset
    if filter_form.cleaned_data.get("company"):
        queryset = queryset.filter(company=filter_form.cleaned_data["company"])
    if filter_form.cleaned_data.get("branch"):
        queryset = queryset.filter(branch=filter_form.cleaned_data["branch"])
    return queryset


def _money_summary(payables):
    """Small presentational summary; unknown amounts remain visible as zero in totals."""
    return {
        "count": len(payables),
        "amount": sum((payable.amount or Decimal("0.00") for payable in payables), Decimal("0.00")),
    }


@roles_required(*PAYMENT_ROLES)
@require_GET
@never_cache
def board(request):
    filter_form = PayableFilterForm(request.GET or None)
    base = _apply_board_filters(_payable_queryset(), filter_form)
    payables = list(urgency_ordered_payables(base))
    queue_payables = list(urgency_ordered_payables(_apply_scope_filters(_payable_queryset(), filter_form)))
    counts = Counter(payable.visual_status() for payable in queue_payables)
    without_source_document = sum(
        not any(attachment.kind == Attachment.Kind.SOURCE for attachment in payable.attachments.all())
        for payable in queue_payables
    )
    incomplete = sum(payable.is_incomplete or payable.amount is None for payable in queue_payables)
    ready_to_pay = sum(
        payable.amount is not None
        and not payable.is_incomplete
        for payable in queue_payables
    )
    generation_form = MonthlyGenerationForm(initial={"period": timezone.localdate().replace(day=1)})
    commitments = PaymentCommitment.objects.select_related("company", "branch", "creditor").order_by("is_active", "name")
    return render(
        request,
        "payments/board.html",
        {
            "payables": payables,
            "filter_form": filter_form,
            "counts": counts,
            "generation_form": generation_form,
            "commitments": commitments,
            "alert_days": 5,
            "work_summary": {
                "without_source_document": without_source_document,
                "incomplete": incomplete,
                "ready_to_pay": ready_to_pay,
            },
        },
    )


@roles_required(*PAYMENT_ROLES)
@require_http_methods(["GET", "POST"])
@never_cache
def commitment_create(request):
    form = PaymentCommitmentForm(request.POST or None)
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
@require_POST
def commitment_toggle(request, commitment_id):
    commitment = get_object_or_404(PaymentCommitment, pk=commitment_id)
    should_activate = request.POST.get("activate") == "1"
    set_commitment_active(actor=request.user, commitment=commitment, is_active=should_activate)
    messages.success(request, f"Compromiso {'activado' if should_activate else 'desactivado'} sin borrar su historial.")
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
@require_http_methods(["GET", "POST"])
@never_cache
def payable_create(request):
    selected_commitment = None
    commitment_id = request.GET.get("commitment")
    if commitment_id and commitment_id.isdigit():
        selected_commitment = PaymentCommitment.objects.filter(pk=int(commitment_id), is_active=True).first()
    form = PayableForm(request.POST or None, selected_commitment=selected_commitment)
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
@require_GET
@never_cache
def payable_detail(request, payable_id):
    payable = get_object_or_404(
        _payable_queryset().select_related("payment__receipt", "payment__registered_by"), pk=payable_id
    )
    audit_logs = AuditLog.objects.filter(target_type="payments.payable", target_id=str(payable.pk)).select_related("actor")[:12]
    return render(
        request,
        "payments/payable_detail.html",
        {
            "payable": payable,
            "source_form": SourceDocumentForm(),
            "payment_form": RecordPaymentForm(payable=payable),
            "suspension_form": SuspensionForm(initial={"note": payable.suspension_note}),
            "audit_logs": audit_logs,
        },
    )


@roles_required(*PAYMENT_ROLES)
@require_POST
def source_document_upload(request, payable_id):
    payable = get_object_or_404(Payable, pk=payable_id)
    form = SourceDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        attach_source_document(actor=request.user, payable=payable, upload=form.cleaned_data["document"])
        messages.success(request, "Documento por pagar adjuntado de forma privada.")
    else:
        messages.error(request, "No se pudo adjuntar el documento. Revise el tipo, firma y tamaño del archivo.")
    return redirect("payment-payable-detail", payable_id=payable.pk)


@roles_required(*PAYMENT_ROLES)
@require_POST
def payment_record(request, payable_id):
    payable = get_object_or_404(Payable, pk=payable_id)
    form = RecordPaymentForm(request.POST, request.FILES, payable=payable)
    if form.is_valid():
        try:
            record_payment(
                actor=request.user,
                payable_id=payable.pk,
                amount=form.cleaned_data["amount"],
                paid_on=form.cleaned_data["paid_on"],
                operation_reference=form.cleaned_data["operation_reference"],
                receipt_upload=form.cleaned_data["receipt"],
            )
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        else:
            messages.success(request, "Pago registrado con su comprobante. La obligación salió del tablero pendiente.")
            return redirect("payment-payable-detail", payable_id=payable.pk)
    else:
        messages.error(request, "No se registró el pago: adjunte un comprobante PDF, JPG o PNG válido.")
    return redirect("payment-payable-detail", payable_id=payable.pk)


@roles_required(Role.Code.MANAGER)
@require_POST
def payable_suspension(request, payable_id):
    payable = get_object_or_404(Payable, pk=payable_id)
    form = SuspensionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revise el motivo de suspensión.")
        return redirect("payment-payable-detail", payable_id=payable.pk)
    try:
        set_payable_suspension(
            actor=request.user,
            payable=payable,
            suspend=payable.status != Payable.Status.SUSPENDED,
            note=form.cleaned_data["note"],
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Obligación suspendida." if payable.status == Payable.Status.SUSPENDED else "Obligación reactivada.")
    return redirect("payment-payable-detail", payable_id=payable.pk)


@roles_required(*PAYMENT_ROLES)
@require_GET
@never_cache
def payment_history(request):
    filters = PayableFilterForm(request.GET or None)
    payables = _payable_queryset().filter(status=Payable.Status.PAID).select_related(
        "payment__receipt", "payment__registered_by"
    )
    if filters.is_valid():
        if filters.cleaned_data.get("company"):
            payables = payables.filter(company=filters.cleaned_data["company"])
        if filters.cleaned_data.get("branch"):
            payables = payables.filter(branch=filters.cleaned_data["branch"])
    return render(request, "payments/history.html", {"payables": payables.order_by("-payment__paid_on", "-pk"), "filter_form": filters})


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
    filters = PayableFilterForm(request.GET or None)
    payables = _apply_scope_filters(
        _payable_queryset().filter(due_date__gte=selected_month, due_date__lt=next_month), filters
    ).order_by("due_date", "pk")
    payables = list(payables)

    today = timezone.localdate()
    cashflow_payables = list(
        _apply_scope_filters(
            _payable_queryset().filter(
                status=Payable.Status.PENDING,
                due_date__gte=today,
                due_date__lte=today + timedelta(days=30),
            ),
            filters,
        ).order_by("due_date", "pk")
    )
    next_week = [payable for payable in cashflow_payables if payable.due_date <= today + timedelta(days=7)]
    attention_payables = list(
        _apply_scope_filters(
            _payable_queryset().filter(
                status=Payable.Status.PENDING,
                due_date__lte=today + timedelta(days=30),
            ),
            filters,
        ).order_by("due_date", "pk")
    )
    attention_items = [
        payable
        for payable in attention_payables
        if payable.due_date < today
        or payable.is_incomplete
        or payable.amount is None
        or not any(attachment.kind == Attachment.Kind.SOURCE for attachment in payable.attachments.all())
    ][:5]
    return render(
        request,
        "payments/manager_dashboard.html",
        {
            "payables": payables,
            "summary": manager_month_summary(payables),
            "filter_form": filters,
            "selected_month": selected_month,
            "cashflow": {"next_week": _money_summary(next_week), "next_month": _money_summary(cashflow_payables)},
            "attention_items": attention_items,
            "today": today,
        },
    )


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
            messages.success(request, "Cuenta de destino actualizada y trazada.")
            return redirect("payment-destination-accounts")
    return render(request, "payments/destination_account_form.html", {"form": form, "account": account})


@roles_required(*PAYMENT_ROLES)
@require_GET
def attachment_download(request, attachment_id):
    attachment = get_object_or_404(Attachment.objects.select_related("payable"), pk=attachment_id)
    if not attachment.file:
        raise Http404("El archivo ya no está disponible.")
    try:
        attachment.file.open("rb")
    except FileNotFoundError as error:
        raise Http404("El archivo ya no está disponible.") from error
    content_type = attachment.content_type or mimetypes.guess_type(attachment.original_name)[0] or "application/octet-stream"
    return FileResponse(attachment.file, as_attachment=True, filename=attachment.original_name, content_type=content_type)
