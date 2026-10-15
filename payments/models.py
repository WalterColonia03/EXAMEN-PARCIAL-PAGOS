from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


def private_document_path(instance: "Attachment", filename: str) -> str:
    """Keep documents outside the public static/media URL space."""
    suffix = Path(filename).suffix.lower()
    return f"payments/{timezone.localdate():%Y/%m}/{uuid.uuid4().hex}{suffix}"


class Company(models.Model):
    name = models.CharField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "empresa"
        verbose_name_plural = "empresas"

    def __str__(self) -> str:
        return self.name


class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="branches")
    name = models.CharField(max_length=140)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=("company", "name"), name="payment_branch_name_per_company"),
        ]
        verbose_name = "local"
        verbose_name_plural = "locales"

    def __str__(self) -> str:
        return f"{self.company.name} · {self.name}"


class Creditor(models.Model):
    name = models.CharField(max_length=160, unique=True)
    tax_id = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "acreedor"
        verbose_name_plural = "acreedores"

    def __str__(self) -> str:
        return self.name


class DestinationAccount(models.Model):
    creditor = models.ForeignKey(Creditor, on_delete=models.PROTECT, related_name="destination_accounts")
    bank_name = models.CharField(max_length=100)
    account_holder = models.CharField(max_length=160)
    account_number = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_destination_accounts",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="updated_destination_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["creditor__name", "bank_name", "account_number"]
        constraints = [
            models.UniqueConstraint(
                fields=("creditor", "account_number"), name="payment_destination_account_unique_per_creditor"
            ),
        ]
        verbose_name = "cuenta de destino"
        verbose_name_plural = "cuentas de destino"

    def __str__(self) -> str:
        return f"{self.creditor.name} · {self.bank_name} · {self.account_number}"


class PaymentCommitment(models.Model):
    class Category(models.TextChoices):
        SERVICE = "SERVICE", "Servicio"
        TAX = "TAX", "Impuesto"
        SUPPLIER = "SUPPLIER", "Proveedor"
        LOAN = "LOAN", "Préstamo"
        OTHER = "OTHER", "Otro"

    class Frequency(models.TextChoices):
        ONE_TIME = "ONE_TIME", "Pago único"
        MONTHLY = "MONTHLY", "Mensual"

    class AmountMode(models.TextChoices):
        FIXED = "FIXED", "Monto fijo"
        VARIABLE = "VARIABLE", "Monto variable"

    name = models.CharField(max_length=180)
    category = models.CharField(max_length=12, choices=Category.choices)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="payment_commitments")
    branch = models.ForeignKey(
        Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="payment_commitments"
    )
    creditor = models.ForeignKey(Creditor, on_delete=models.PROTECT, related_name="payment_commitments")
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.ONE_TIME)
    usual_due_day = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    amount_mode = models.CharField(max_length=10, choices=AmountMode.choices, default=AmountMode.FIXED)
    fixed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    destination_account = models.ForeignKey(
        DestinationAccount,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_commitments",
    )
    supply_code = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="código de suministro / cliente",
        help_text="Código fijo de suministro, conexión, cliente o contrato para pago bancario.",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_payment_commitments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(usual_due_day__isnull=True) | Q(usual_due_day__gte=1, usual_due_day__lte=31),
                name="payment_commitment_due_day_valid",
            ),
        ]
        verbose_name = "compromiso de pago"
        verbose_name_plural = "compromisos de pago"

    def clean(self) -> None:
        super().clean()
        if self.branch_id and self.company_id and self.branch.company_id != self.company_id:
            raise ValidationError({"branch": "El local debe pertenecer a la empresa seleccionada."})
        if self.destination_account_id and self.creditor_id:
            if self.destination_account.creditor_id != self.creditor_id:
                raise ValidationError({"destination_account": "La cuenta debe pertenecer al acreedor seleccionado."})
        if self.frequency == self.Frequency.MONTHLY and not self.usual_due_day:
            raise ValidationError({"usual_due_day": "Indique el día de vencimiento para un compromiso mensual."})
        if self.amount_mode == self.AmountMode.FIXED and self.fixed_amount is None:
            raise ValidationError({"fixed_amount": "Indique el monto fijo del compromiso."})

    def __str__(self) -> str:
        return self.name


class Payable(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        PAID = "PAID", "Pagado"
        SUSPENDED = "SUSPENDED", "Suspendido"

    commitment = models.ForeignKey(
        PaymentCommitment,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payables",
    )
    external_document_number = models.CharField(max_length=80, blank=True)
    supply_code = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="código de suministro / cliente",
        help_text="Código fijo de suministro o cliente para pago bancario.",
    )
    concept = models.CharField(max_length=180)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="payables")
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="payables")
    category = models.CharField(max_length=12, choices=PaymentCommitment.Category.choices)
    creditor = models.ForeignKey(Creditor, on_delete=models.PROTECT, related_name="payables")
    # Snapshot the authorized destination account on each concrete obligation.
    # Editing a commitment later therefore never rewrites historical records.
    destination_account = models.ForeignKey(
        DestinationAccount,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payables",
    )
    period = models.DateField(null=True, blank=True, help_text="Use el primer día del mes correspondiente.")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    is_incomplete = models.BooleanField(default=False)
    suspension_note = models.CharField(max_length=280, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_payables"
    )
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="suspended_payables",
    )
    suspended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=("commitment", "period"),
                name="payment_single_payable_per_commitment_period",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("PENDING", "PAID", "SUSPENDED")),
                name="payment_payable_valid_status",
            ),
        ]
        verbose_name = "cuenta por pagar"
        verbose_name_plural = "cuentas por pagar"

    def clean(self) -> None:
        super().clean()
        if self.branch_id and self.company_id and self.branch.company_id != self.company_id:
            raise ValidationError({"branch": "El local debe pertenecer a la empresa seleccionada."})
        if self.commitment_id:
            commitment = self.commitment
            mismatches = []
            if self.company_id and commitment.company_id != self.company_id:
                mismatches.append("empresa")
            if self.branch_id != commitment.branch_id:
                mismatches.append("local")
            if self.creditor_id and commitment.creditor_id != self.creditor_id:
                mismatches.append("acreedor")
            if self.category != commitment.category:
                mismatches.append("categoría")
            if mismatches:
                raise ValidationError(
                    "Los datos de la obligación deben coincidir con su compromiso: " + ", ".join(mismatches) + "."
                )
        if self.destination_account_id and self.creditor_id:
            if self.destination_account.creditor_id != self.creditor_id:
                raise ValidationError({"destination_account": "La cuenta debe pertenecer al acreedor seleccionado."})

    def visual_status(self, today=None) -> str:
        today = today or timezone.localdate()
        if self.status == self.Status.PAID:
            return "PAID"
        if self.status == self.Status.SUSPENDED:
            return "SUSPENDED"
        if self.due_date < today:
            return "OVERDUE"
        if self.due_date == today:
            return "DUE_TODAY"
        if self.due_date <= today + timedelta(days=5):
            return "DUE_SOON"
        return "PENDING"

    @property
    def visual_status_label(self) -> str:
        return {
            "PAID": "Pagado",
            "SUSPENDED": "Suspendido",
            "OVERDUE": "Vencido",
            "DUE_TODAY": "Vence hoy",
            "DUE_SOON": "Próximo a vencer",
            "PENDING": "Pendiente",
        }[self.visual_status()]

    def __str__(self) -> str:
        return f"#{self.pk} · {self.concept}"


class Attachment(models.Model):
    class Kind(models.TextChoices):
        SOURCE = "SOURCE", "Documento por pagar"
        RECEIPT = "RECEIPT", "Comprobante de pago"

    payable = models.ForeignKey(Payable, on_delete=models.PROTECT, related_name="attachments")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    file = models.FileField(upload_to=private_document_path, max_length=300)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=80)
    size_bytes = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_payment_documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "documento de pago"
        verbose_name_plural = "documentos de pago"

    def __str__(self) -> str:
        return f"{self.get_kind_display()} · {self.original_name}"


class Payment(models.Model):
    payable = models.OneToOneField(Payable, on_delete=models.PROTECT, related_name="payment")
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    paid_on = models.DateField()
    operation_reference = models.CharField(max_length=120, blank=True)
    receipt = models.ForeignKey(Attachment, on_delete=models.PROTECT, related_name="payment_receipts")
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registered_payments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-pk"]
        verbose_name = "pago realizado"
        verbose_name_plural = "pagos realizados"

    def clean(self) -> None:
        super().clean()
        if self.receipt_id:
            if self.receipt.kind != Attachment.Kind.RECEIPT:
                raise ValidationError({"receipt": "El pago requiere un comprobante de pago válido."})
            if self.receipt.payable_id != self.payable_id:
                raise ValidationError({"receipt": "El comprobante debe pertenecer a esta obligación."})

    def __str__(self) -> str:
        return f"Pago #{self.pk} · {self.payable}"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        COMMITMENT_CREATED = "COMMITMENT_CREATED", "Compromiso creado"
        COMMITMENT_STATUS = "COMMITMENT_STATUS", "Estado de compromiso cambiado"
        PAYABLE_CREATED = "PAYABLE_CREATED", "Obligación creada"
        PAYABLE_STATUS = "PAYABLE_STATUS", "Estado de obligación cambiado"
        DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED", "Documento adjuntado"
        PAYMENT_RECORDED = "PAYMENT_RECORDED", "Pago registrado"
        DESTINATION_ACCOUNT = "DESTINATION_ACCOUNT", "Cuenta de destino actualizada"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_audit_logs")
    action = models.CharField(max_length=24, choices=Action.choices)
    target_type = models.CharField(max_length=40)
    target_id = models.CharField(max_length=40)
    summary = models.CharField(max_length=280)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=("target_type", "target_id"), name="payment_audit_target_idx")]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self) -> str:
        return self.summary
