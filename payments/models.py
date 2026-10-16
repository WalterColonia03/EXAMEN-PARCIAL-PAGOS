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


def mask_sensitive_value(value: str | None) -> str:
    """Expose at most the final four characters of an identifier or account."""
    value = (value or "").strip()
    if not value:
        return "No disponible"
    if len(value) <= 4:
        return "*" * max(4, len(value))
    return f"{'*' * max(4, len(value) - 4)}{value[-4:]}"


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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Runtime-created companies immediately receive their neutral operating scope.
        PaymentContext.for_company(self)


class PaymentContext(models.Model):
    """Person, household, business or patrimonial scope administered in PagoControl."""

    class Kind(models.TextChoices):
        BUSINESS = "BUSINESS", "Empresa"
        PERSONAL = "PERSONAL", "Personal"
        HOUSEHOLD = "HOUSEHOLD", "Hogar o propiedad"
        THIRD_PARTY = "THIRD_PARTY", "Familiar o tercero"
        PATRIMONIAL = "PATRIMONIAL", "Entidad patrimonial"

    name = models.CharField(max_length=160, unique=True)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    company = models.OneToOneField(
        Company,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_context",
    )
    default_holder_name = models.CharField(max_length=160, blank=True)
    default_beneficiary_name = models.CharField(max_length=160, blank=True)
    assistant_access = models.BooleanField(
        default=True,
        help_text="Permite al asistente consultar y operar las obligaciones no sensibles de este ámbito.",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_payment_contexts",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="updated_payment_contexts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(kind="BUSINESS", company__isnull=False) | ~Q(kind="BUSINESS")),
                name="payment_business_context_has_company",
            ),
            models.CheckConstraint(
                condition=(Q(kind="BUSINESS") | Q(company__isnull=True)),
                name="payment_nonbusiness_context_without_company",
            ),
        ]
        verbose_name = "ámbito administrado"
        verbose_name_plural = "ámbitos administrados"

    def clean(self) -> None:
        super().clean()
        if self.kind == self.Kind.BUSINESS and not self.company_id:
            raise ValidationError({"company": "Un ámbito empresarial necesita una empresa."})
        if self.kind != self.Kind.BUSINESS and self.company_id:
            raise ValidationError({"company": "Solo un ámbito empresarial puede vincular una empresa."})
        if self.kind == self.Kind.THIRD_PARTY and not self.default_beneficiary_name.strip():
            raise ValidationError(
                {"default_beneficiary_name": "Identifique a la persona beneficiaria de este ámbito."}
            )

    @classmethod
    def for_company(cls, company: Company) -> "PaymentContext":
        existing = cls.objects.filter(company=company).first()
        if existing is not None:
            return existing
        context_name = company.name
        if cls.objects.filter(name=context_name).exists():
            base_name = f"{company.name} · Empresa"
            context_name = base_name
            suffix = 2
            while cls.objects.filter(name=context_name).exists():
                context_name = f"{base_name} {suffix}"
                suffix += 1
        context, _ = cls.objects.get_or_create(
            company=company,
            defaults={
                "name": context_name,
                "kind": cls.Kind.BUSINESS,
                "assistant_access": True,
            },
        )
        return context

    def __str__(self) -> str:
        return self.name


class FundingSource(models.Model):
    class Kind(models.TextChoices):
        ACCOUNT = "ACCOUNT", "Cuenta bancaria"
        CARD = "CARD", "Tarjeta"
        CASH = "CASH", "Efectivo"
        OTHER = "OTHER", "Otra fuente"

    class Currency(models.TextChoices):
        PEN = "PEN", "PEN · Soles"
        USD = "USD", "USD · Dólares"

    context = models.ForeignKey(PaymentContext, on_delete=models.PROTECT, related_name="funding_sources")
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    institution = models.CharField(max_length=120, blank=True)
    account_holder = models.CharField(max_length=160, blank=True)
    identifier = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.PEN)
    assistant_visible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_funding_sources",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="updated_funding_sources",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["context__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=("context", "name"), name="payment_funding_source_name_per_context")
        ]
        verbose_name = "fuente de fondos"
        verbose_name_plural = "fuentes de fondos"

    @property
    def masked_identifier(self) -> str:
        return mask_sensitive_value(self.identifier)

    def __str__(self) -> str:
        return f"{self.context.name} · {self.name}"


def synchronize_context_scope(instance, *, create_missing: bool = False) -> None:
    """Keep legacy company fields compatible while the UI moves to neutral contexts."""
    if getattr(instance, "context_id", None):
        context = instance.context
        if context.kind == PaymentContext.Kind.BUSINESS:
            instance.company = context.company
        else:
            instance.company = None
            if hasattr(instance, "branch"):
                instance.branch = None
    elif getattr(instance, "company_id", None):
        context = PaymentContext.objects.filter(company_id=instance.company_id).first()
        if context is None and create_missing:
            context = PaymentContext.for_company(instance.company)
        if context is not None:
            instance.context = context


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

    @property
    def masked_account_number(self) -> str:
        return mask_sensitive_value(self.account_number)

    def __str__(self) -> str:
        return f"{self.creditor.name} / {self.bank_name} / {self.masked_account_number}"


class ServiceAccount(models.Model):
    """Permanent identifier for a service, independent from any monthly bill."""

    class ServiceType(models.TextChoices):
        ELECTRICITY = "ELECTRICITY", "Electricidad"
        WATER = "WATER", "Agua"
        GAS = "GAS", "Gas"
        INTERNET = "INTERNET", "Internet"
        TELECOM = "TELECOM", "Telecomunicaciones"
        MUNICIPAL = "MUNICIPAL", "Municipal / arbitrios"
        TAX = "TAX", "Tributo"
        OTHER = "OTHER", "Otro"

    class IdentifierType(models.TextChoices):
        SUPPLY = "SUPPLY", "Suministro"
        CLIENT = "CLIENT", "Cliente"
        CONTRACT = "CONTRACT", "Contrato"
        PROPERTY = "PROPERTY", "Predio"
        TAXPAYER = "TAXPAYER", "Contribuyente"
        OTHER = "OTHER", "Otro"

    class BillingFrequency(models.TextChoices):
        MONTHLY = "MONTHLY", "Mensual"
        BIMONTHLY = "BIMONTHLY", "Bimestral"
        QUARTERLY = "QUARTERLY", "Trimestral"
        ON_DEMAND = "ON_DEMAND", "Según consumo / eventual"

    class AcquisitionChannel(models.TextChoices):
        EMAIL = "EMAIL", "Correo"
        PORTAL = "PORTAL", "Portal del proveedor"
        API = "API", "Integración"
        OCR = "OCR", "Documento digitalizado"
        MANUAL = "MANUAL", "Registro manual"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activa"
        SUSPENDED = "SUSPENDED", "Suspendida"
        CLOSED = "CLOSED", "Cerrada"

    context = models.ForeignKey(
        PaymentContext, null=True, blank=True, on_delete=models.PROTECT, related_name="service_accounts"
    )
    creditor = models.ForeignKey(Creditor, on_delete=models.PROTECT, related_name="service_accounts")
    company = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT, related_name="service_accounts"
    )
    branch = models.ForeignKey(
        Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="service_accounts"
    )
    service_type = models.CharField(max_length=16, choices=ServiceType.choices)
    identifier_type = models.CharField(max_length=12, choices=IdentifierType.choices)
    primary_identifier = models.CharField(max_length=100)
    additional_identifiers = models.JSONField(default=dict, blank=True)
    account_holder = models.CharField(max_length=160, blank=True)
    expected_billing_frequency = models.CharField(
        max_length=12, choices=BillingFrequency.choices, default=BillingFrequency.MONTHLY
    )
    usual_billing_day = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    acquisition_channel = models.CharField(
        max_length=12, choices=AcquisitionChannel.choices, default=AcquisitionChannel.MANUAL
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_service_accounts",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="updated_service_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["context__name", "branch__name", "creditor__name", "primary_identifier"]
        constraints = [
            models.CheckConstraint(
                condition=Q(context__isnull=False),
                name="payment_service_account_context_required",
            ),
            models.UniqueConstraint(
                fields=("context", "branch", "creditor", "identifier_type", "primary_identifier"),
                name="payment_service_account_unique_identifier",
            ),
            models.CheckConstraint(
                condition=Q(usual_billing_day__isnull=True) | Q(usual_billing_day__gte=1, usual_billing_day__lte=31),
                name="payment_service_account_billing_day_valid",
            ),
        ]
        verbose_name = "cuenta de servicio"
        verbose_name_plural = "cuentas de servicio"

    def clean(self) -> None:
        super().clean()
        synchronize_context_scope(self)
        if not self.context_id:
            raise ValidationError({"context": "Seleccione a quién corresponde esta cuenta de servicio."})
        if self.branch_id and self.company_id and self.branch.company_id != self.company_id:
            raise ValidationError({"branch": "El local debe pertenecer a la empresa seleccionada."})
        if self.branch_id and not self.company_id:
            raise ValidationError({"branch": "Los locales solo se usan en ámbitos empresariales."})
        if not self.primary_identifier.strip():
            raise ValidationError({"primary_identifier": "El identificador principal no puede estar vacío."})
        if not isinstance(self.additional_identifiers, dict):
            raise ValidationError({"additional_identifiers": "Los identificadores adicionales deben guardarse como pares nombre-valor."})
        if any(not str(key).strip() or not str(value).strip() for key, value in self.additional_identifiers.items()):
            raise ValidationError({"additional_identifiers": "Cada identificador adicional debe tener nombre y valor."})

    @property
    def masked_primary_identifier(self) -> str:
        return mask_sensitive_value(self.primary_identifier)

    def save(self, *args, **kwargs):
        synchronize_context_scope(self, create_missing=True)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        location = f" / {self.branch.name}" if self.branch_id else ""
        return f"{self.get_service_type_display()} / {self.masked_primary_identifier}{location}"


class PaymentCommitment(models.Model):
    class Category(models.TextChoices):
        SERVICE = "SERVICE", "Servicio"
        HOUSING = "HOUSING", "Vivienda o propiedad"
        CREDIT_CARD = "CREDIT_CARD", "Tarjeta de crédito"
        LOAN = "LOAN", "Préstamo"
        TAX = "TAX", "Impuesto"
        INSURANCE = "INSURANCE", "Seguro"
        EDUCATION = "EDUCATION", "Educación"
        HEALTH = "HEALTH", "Salud"
        FAMILY_SUPPORT = "FAMILY_SUPPORT", "Apoyo familiar"
        DOMESTIC_STAFF = "DOMESTIC_STAFF", "Personal doméstico"
        VEHICLE = "VEHICLE", "Vehículo"
        TRAVEL_EVENT = "TRAVEL_EVENT", "Viaje o evento"
        INVESTMENT = "INVESTMENT", "Inversión"
        DONATION = "DONATION", "Donación"
        LEGAL = "LEGAL", "Legal"
        SUBSCRIPTION = "SUBSCRIPTION", "Suscripción"
        SUPPLIER = "SUPPLIER", "Proveedor"
        EMERGENCY = "EMERGENCY", "Emergencia"
        OTHER = "OTHER", "Otro"

    class Frequency(models.TextChoices):
        ONE_TIME = "ONE_TIME", "Pago único"
        WEEKLY = "WEEKLY", "Semanal"
        BIWEEKLY = "BIWEEKLY", "Quincenal"
        MONTHLY = "MONTHLY", "Mensual"
        BIMONTHLY = "BIMONTHLY", "Bimestral"
        QUARTERLY = "QUARTERLY", "Trimestral"
        SEMIANNUAL = "SEMIANNUAL", "Semestral"
        ANNUAL = "ANNUAL", "Anual"
        CUSTOM = "CUSTOM", "Intervalo personalizado"

    class IntervalUnit(models.TextChoices):
        DAYS = "DAYS", "Días"
        WEEKS = "WEEKS", "Semanas"
        MONTHS = "MONTHS", "Meses"

    class Nature(models.TextChoices):
        OWN = "OWN", "Propio"
        SHARED = "SHARED", "Compartido"
        SUPPORT = "SUPPORT", "Apoyo no reembolsable"
        REIMBURSABLE = "REIMBURSABLE", "Reembolsable"
        PERSONAL_LOAN = "PERSONAL_LOAN", "Préstamo a un tercero"

    class AmountMode(models.TextChoices):
        FIXED = "FIXED", "Monto fijo"
        VARIABLE = "VARIABLE", "Monto variable"

    context = models.ForeignKey(
        PaymentContext, null=True, blank=True, on_delete=models.PROTECT, related_name="payment_commitments"
    )
    name = models.CharField(max_length=180)
    category = models.CharField(max_length=20, choices=Category.choices)
    company = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT, related_name="payment_commitments"
    )
    branch = models.ForeignKey(
        Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="payment_commitments"
    )
    creditor = models.ForeignKey(Creditor, on_delete=models.PROTECT, related_name="payment_commitments")
    frequency = models.CharField(max_length=16, choices=Frequency.choices, default=Frequency.ONE_TIME)
    interval_count = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    interval_unit = models.CharField(max_length=8, choices=IntervalUnit.choices, blank=True)
    start_date = models.DateField(null=True, blank=True)
    next_occurrence = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_paused = models.BooleanField(default=False)
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
    currency = models.CharField(max_length=3, choices=FundingSource.Currency.choices, default=FundingSource.Currency.PEN)
    holder_name = models.CharField(max_length=160, blank=True)
    beneficiary_name = models.CharField(max_length=160, blank=True)
    payment_nature = models.CharField(max_length=16, choices=Nature.choices, default=Nature.OWN)
    details = models.JSONField(default=dict, blank=True)
    funding_source = models.ForeignKey(
        FundingSource,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_commitments",
    )
    destination_account = models.ForeignKey(
        DestinationAccount,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_commitments",
    )
    service_account = models.ForeignKey(
        ServiceAccount,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="commitments",
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
        ordering = ["context__name", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(context__isnull=False),
                name="payment_commitment_context_required",
            ),
            models.CheckConstraint(
                condition=Q(usual_due_day__isnull=True) | Q(usual_due_day__gte=1, usual_due_day__lte=31),
                name="payment_commitment_due_day_valid",
            ),
        ]
        verbose_name = "compromiso de pago"
        verbose_name_plural = "compromisos de pago"

    def clean(self) -> None:
        super().clean()
        synchronize_context_scope(self)
        if not self.context_id:
            raise ValidationError({"context": "Seleccione a quién corresponde este compromiso."})
        if self.context_id:
            if not self.holder_name:
                self.holder_name = self.context.default_holder_name
            if not self.beneficiary_name:
                self.beneficiary_name = self.context.default_beneficiary_name
        if self.branch_id and self.company_id and self.branch.company_id != self.company_id:
            raise ValidationError({"branch": "El local debe pertenecer a la empresa seleccionada."})
        if self.branch_id and not self.company_id:
            raise ValidationError({"branch": "Los locales solo se usan en ámbitos empresariales."})
        if self.destination_account_id and self.creditor_id:
            if self.destination_account.creditor_id != self.creditor_id:
                raise ValidationError({"destination_account": "La cuenta debe pertenecer al acreedor seleccionado."})
        if self.service_account_id:
            service_account = self.service_account
            mismatches = []
            if service_account.context_id != self.context_id:
                mismatches.append("ámbito")
            if service_account.branch_id != self.branch_id:
                mismatches.append("local")
            if service_account.creditor_id != self.creditor_id:
                mismatches.append("acreedor")
            if self.category != self.Category.SERVICE:
                mismatches.append("categoría")
            if mismatches:
                raise ValidationError(
                    "La cuenta de servicio debe coincidir con el compromiso: " + ", ".join(mismatches) + "."
                )
        if self.frequency == self.Frequency.MONTHLY and not self.usual_due_day:
            raise ValidationError({"usual_due_day": "Indique el día de vencimiento para un compromiso mensual."})
        if self.frequency == self.Frequency.CUSTOM and not self.interval_unit:
            raise ValidationError({"interval_unit": "Seleccione días, semanas o meses para el intervalo."})
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "La fecha final no puede ser anterior a la fecha inicial."})
        if self.funding_source_id and self.funding_source.context_id != self.context_id:
            raise ValidationError({"funding_source": "La fuente de fondos debe pertenecer al mismo ámbito."})
        if self.funding_source_id and self.funding_source.currency != self.currency:
            raise ValidationError({"funding_source": "La fuente de fondos debe usar la misma moneda."})
        if not isinstance(self.details, dict):
            raise ValidationError({"details": "Los datos específicos de la obligación no son válidos."})
        missing_details = missing_required_commitment_details(self.category, self.details)
        if missing_details:
            raise ValidationError(
                "Complete los datos que identifican este tipo de compromiso."
            )
        if self.category == self.Category.CREDIT_CARD:
            last_four = str(self.details.get("card_last_four", ""))
            if len(last_four) != 4 or not last_four.isascii() or not last_four.isdigit():
                raise ValidationError(
                    "Los últimos cuatro dígitos de la tarjeta deben ser numéricos."
                )
        if self.amount_mode == self.AmountMode.FIXED and self.fixed_amount is None:
            raise ValidationError({"fixed_amount": "Indique el monto fijo del compromiso."})

    def save(self, *args, **kwargs):
        synchronize_context_scope(self, create_missing=True)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


COMMITMENT_DETAIL_REQUIREMENTS = {
    PaymentCommitment.Category.CREDIT_CARD: ("card_issuer", "card_last_four"),
    PaymentCommitment.Category.LOAN: ("loan_contract",),
    PaymentCommitment.Category.INSURANCE: ("insurance_policy",),
    PaymentCommitment.Category.HOUSING: ("property_reference",),
    PaymentCommitment.Category.TRAVEL_EVENT: ("travel_subject",),
    PaymentCommitment.Category.INVESTMENT: ("investment_vehicle",),
}


def missing_required_commitment_details(category: str, details: dict | None) -> tuple[str, ...]:
    values = details if isinstance(details, dict) else {}
    return tuple(
        field
        for field in COMMITMENT_DETAIL_REQUIREMENTS.get(category, ())
        if values.get(field) in (None, "")
    )


CATEGORY_DETAIL_REQUIREMENTS = {
    PaymentCommitment.Category.CREDIT_CARD: COMMITMENT_DETAIL_REQUIREMENTS[
        PaymentCommitment.Category.CREDIT_CARD
    ] + (
        "card_statement_total",
        "card_minimum_payment",
    ),
    PaymentCommitment.Category.LOAN: COMMITMENT_DETAIL_REQUIREMENTS[PaymentCommitment.Category.LOAN],
    PaymentCommitment.Category.INSURANCE: COMMITMENT_DETAIL_REQUIREMENTS[PaymentCommitment.Category.INSURANCE],
    PaymentCommitment.Category.HOUSING: COMMITMENT_DETAIL_REQUIREMENTS[PaymentCommitment.Category.HOUSING],
    PaymentCommitment.Category.TRAVEL_EVENT: COMMITMENT_DETAIL_REQUIREMENTS[
        PaymentCommitment.Category.TRAVEL_EVENT
    ],
    PaymentCommitment.Category.INVESTMENT: COMMITMENT_DETAIL_REQUIREMENTS[PaymentCommitment.Category.INVESTMENT],
}


def missing_required_payment_details(category: str, details: dict | None) -> tuple[str, ...]:
    values = details if isinstance(details, dict) else {}
    return tuple(
        field
        for field in CATEGORY_DETAIL_REQUIREMENTS.get(category, ())
        if values.get(field) in (None, "")
    )


class Payable(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        PARTIAL = "PARTIAL", "Pago parcial"
        PAID = "PAID", "Pagado"
        SUSPENDED = "SUSPENDED", "Suspendido"
        DISPUTED = "DISPUTED", "En disputa"
        CANCELLED = "CANCELLED", "Anulado"
        REFUNDED = "REFUNDED", "Reembolsado"

    class DestinationSnapshotOrigin(models.TextChoices):
        NONE = "NONE", "Sin cuenta de destino"
        CREATED = "CREATED", "Capturada al crear la obligación"
        BACKFILLED = "BACKFILLED", "Congelada durante migración"

    commitment = models.ForeignKey(
        PaymentCommitment,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payables",
    )
    context = models.ForeignKey(
        PaymentContext, null=True, blank=True, on_delete=models.PROTECT, related_name="payables"
    )
    external_document_number = models.CharField(max_length=80, blank=True)
    supply_code = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="código de suministro / cliente",
        help_text="Código fijo de suministro o cliente para pago bancario.",
    )
    concept = models.CharField(max_length=180)
    company = models.ForeignKey(
        Company, null=True, blank=True, on_delete=models.PROTECT, related_name="payables"
    )
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="payables")
    category = models.CharField(max_length=20, choices=PaymentCommitment.Category.choices)
    creditor = models.ForeignKey(Creditor, on_delete=models.PROTECT, related_name="payables")
    holder_name = models.CharField(max_length=160, blank=True)
    beneficiary_name = models.CharField(max_length=160, blank=True)
    payment_nature = models.CharField(
        max_length=16,
        choices=PaymentCommitment.Nature.choices,
        default=PaymentCommitment.Nature.OWN,
    )
    currency = models.CharField(max_length=3, choices=FundingSource.Currency.choices, default=FundingSource.Currency.PEN)
    details = models.JSONField(default=dict, blank=True)
    funding_source = models.ForeignKey(
        FundingSource,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="planned_payables",
    )
    is_sensitive = models.BooleanField(
        default=False,
        help_text="Solo el gerente puede ver esta obligación, incluso en un ámbito compartido.",
    )
    duplicate_override_reason = models.CharField(max_length=280, blank=True)
    # Snapshot the authorized destination account on each concrete obligation.
    # Editing a commitment later therefore never rewrites historical records.
    destination_account = models.ForeignKey(
        DestinationAccount,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payables",
    )
    destination_bank_name_snapshot = models.CharField(max_length=100, null=True, blank=True, editable=False)
    destination_account_holder_snapshot = models.CharField(max_length=160, null=True, blank=True, editable=False)
    destination_account_number_snapshot = models.CharField(max_length=80, null=True, blank=True, editable=False)
    destination_snapshot_origin = models.CharField(
        max_length=10,
        choices=DestinationSnapshotOrigin.choices,
        default=DestinationSnapshotOrigin.NONE,
        editable=False,
    )
    destination_snapshot_captured_at = models.DateTimeField(null=True, blank=True, editable=False)
    service_account = models.ForeignKey(
        ServiceAccount,
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
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
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
            models.CheckConstraint(
                condition=Q(context__isnull=False),
                name="payment_payable_context_required",
            ),
            models.UniqueConstraint(
                fields=("commitment", "period"),
                name="payment_single_payable_per_commitment_period",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=("PENDING", "PARTIAL", "PAID", "SUSPENDED", "DISPUTED", "CANCELLED", "REFUNDED")
                ),
                name="payment_payable_valid_status",
            ),
        ]
        verbose_name = "cuenta por pagar"
        verbose_name_plural = "cuentas por pagar"

    def clean(self) -> None:
        super().clean()
        synchronize_context_scope(self)
        if not self.context_id:
            raise ValidationError({"context": "Seleccione a quién corresponde esta obligación."})
        if self.context_id:
            if not self.holder_name:
                self.holder_name = self.context.default_holder_name
            if not self.beneficiary_name:
                self.beneficiary_name = self.context.default_beneficiary_name
        if self.branch_id and self.company_id and self.branch.company_id != self.company_id:
            raise ValidationError({"branch": "El local debe pertenecer a la empresa seleccionada."})
        if self.branch_id and not self.company_id:
            raise ValidationError({"branch": "Los locales solo se usan en ámbitos empresariales."})
        if self.commitment_id:
            commitment = self.commitment
            mismatches = []
            if commitment.context_id != self.context_id:
                mismatches.append("ámbito")
            if self.company_id and commitment.company_id != self.company_id:
                mismatches.append("empresa")
            if self.branch_id != commitment.branch_id:
                mismatches.append("local")
            if self.creditor_id and commitment.creditor_id != self.creditor_id:
                mismatches.append("acreedor")
            if self.category != commitment.category:
                mismatches.append("categoría")
            if self.service_account_id != commitment.service_account_id:
                mismatches.append("cuenta de servicio")
            if self.currency != commitment.currency:
                mismatches.append("moneda")
            if mismatches:
                raise ValidationError(
                    "Los datos de la obligación deben coincidir con su compromiso: " + ", ".join(mismatches) + "."
                )
        if self.destination_account_id and self.creditor_id:
            if self.destination_account.creditor_id != self.creditor_id:
                raise ValidationError({"destination_account": "La cuenta debe pertenecer al acreedor seleccionado."})
        if self.service_account_id:
            service_account = self.service_account
            mismatches = []
            if service_account.context_id != self.context_id:
                mismatches.append("ámbito")
            if service_account.branch_id != self.branch_id:
                mismatches.append("local")
            if service_account.creditor_id != self.creditor_id:
                mismatches.append("acreedor")
            if self.category != PaymentCommitment.Category.SERVICE:
                mismatches.append("categoría")
            if mismatches:
                raise ValidationError(
                    "La cuenta de servicio debe coincidir con la obligación: " + ", ".join(mismatches) + "."
                )
        if self.funding_source_id and self.funding_source.context_id != self.context_id:
            raise ValidationError({"funding_source": "La fuente de fondos debe pertenecer al mismo ámbito."})
        if self.funding_source_id and self.funding_source.currency != self.currency:
            raise ValidationError({"funding_source": "La fuente de fondos debe usar la misma moneda."})
        if not isinstance(self.details, dict):
            raise ValidationError({"details": "Los datos específicos de la obligación no son válidos."})
        missing_details = missing_required_payment_details(self.category, self.details)
        if missing_details and not self.is_incomplete:
            raise ValidationError(
                "Complete los datos propios de la categoría o marque la información como incompleta."
            )
        if self.category == PaymentCommitment.Category.CREDIT_CARD and self.details.get("card_last_four"):
            last_four = str(self.details["card_last_four"])
            if len(last_four) != 4 or not last_four.isascii() or not last_four.isdigit():
                raise ValidationError(
                    "Los últimos cuatro dígitos de la tarjeta deben ser numéricos."
                )

    def visual_status(self, today=None) -> str:
        today = today or timezone.localdate()
        if self.status == self.Status.PAID:
            return "PAID"
        if self.status in {
            self.Status.SUSPENDED,
            self.Status.DISPUTED,
            self.Status.CANCELLED,
            self.Status.REFUNDED,
        }:
            return self.status
        if self.due_date < today:
            return "OVERDUE"
        if self.status == self.Status.PARTIAL:
            return "PARTIAL"
        if self.due_date == today:
            return "DUE_TODAY"
        if self.due_date <= today + timedelta(days=5):
            return "DUE_SOON"
        return "PENDING"

    @property
    def has_destination_snapshot(self) -> bool:
        return self.destination_snapshot_origin != self.DestinationSnapshotOrigin.NONE

    @property
    def masked_destination_account_number_snapshot(self) -> str:
        return mask_sensitive_value(self.destination_account_number_snapshot)

    @property
    def masked_supply_code(self) -> str:
        return mask_sensitive_value(self.supply_code)

    @property
    def currency_symbol(self) -> str:
        return "S/" if self.currency == FundingSource.Currency.PEN else "US$"

    @property
    def net_paid(self) -> Decimal:
        decrease = Decimal("0.00")
        increase = Decimal("0.00")
        for movement in self.payment_movements.filter(is_void=False):
            if movement.balance_effect == Payment.BalanceEffect.DECREASE:
                decrease += movement.amount
            elif movement.balance_effect == Payment.BalanceEffect.INCREASE:
                increase += movement.amount
        return decrease - increase

    @property
    def balance_due(self) -> Decimal | None:
        if self.amount is None:
            return None
        if self.status in {self.Status.CANCELLED, self.Status.REFUNDED}:
            return Decimal("0.00")
        return max(self.amount - self.net_paid, Decimal("0.00"))

    @property
    def reimbursements_received(self) -> Decimal:
        return sum(
            (
                movement.amount
                for movement in self.payment_movements.filter(
                    kind=Payment.Kind.REIMBURSEMENT,
                    is_void=False,
                )
            ),
            Decimal("0.00"),
        )

    @property
    def reimbursement_pending(self) -> Decimal:
        if self.payment_nature != PaymentCommitment.Nature.REIMBURSABLE:
            return Decimal("0.00")
        return max(self.net_paid - self.reimbursements_received, Decimal("0.00"))

    @property
    def payment(self):
        """Backward-compatible access to the latest active payment movement."""
        return self.payment_movements.filter(
            kind=Payment.Kind.PAYMENT,
            is_void=False,
        ).select_related("receipt", "registered_by").order_by("-paid_on", "-pk").first()

    @property
    def payments_count(self) -> int:
        return self.payment_movements.filter(is_void=False).count()

    @property
    def visual_status_label(self) -> str:
        if self.status == self.Status.PARTIAL and self.due_date < timezone.localdate():
            return "Pago parcial vencido"
        return {
            "PAID": "Pagado",
            "PARTIAL": "Pago parcial",
            "SUSPENDED": "Suspendido",
            "DISPUTED": "En disputa",
            "CANCELLED": "Anulado",
            "REFUNDED": "Reembolsado",
            "OVERDUE": "Vencido",
            "DUE_TODAY": "Vence hoy",
            "DUE_SOON": "Próximo a vencer",
            "PENDING": "Pendiente",
        }[self.visual_status()]

    def save(self, *args, **kwargs):
        synchronize_context_scope(self, create_missing=True)
        return super().save(*args, **kwargs)

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

    @property
    def preview_type(self) -> str:
        """Return the safe inline preview supported for this private attachment."""
        suffix = Path(self.original_name).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png"}:
            return "image"
        if suffix == ".pdf":
            return "pdf"
        return ""

    def __str__(self) -> str:
        return f"{self.get_kind_display()} · {self.original_name}"


class Payment(models.Model):
    class Kind(models.TextChoices):
        PAYMENT = "PAYMENT", "Pago"
        REFUND = "REFUND", "Devolución del acreedor"
        REIMBURSEMENT = "REIMBURSEMENT", "Reembolso recibido"
        CHARGEBACK = "CHARGEBACK", "Contracargo"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"

    class BalanceEffect(models.TextChoices):
        DECREASE = "DECREASE", "Reduce el saldo"
        INCREASE = "INCREASE", "Aumenta el saldo"
        NONE = "NONE", "No cambia el saldo"

    payable = models.ForeignKey(Payable, on_delete=models.PROTECT, related_name="payment_movements")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.PAYMENT)
    balance_effect = models.CharField(
        max_length=8,
        choices=BalanceEffect.choices,
        default=BalanceEffect.DECREASE,
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    currency = models.CharField(max_length=3, choices=FundingSource.Currency.choices, default=FundingSource.Currency.PEN)
    paid_on = models.DateField()
    operation_reference = models.CharField(max_length=120, blank=True)
    reason = models.CharField(max_length=280, blank=True)
    receipt = models.ForeignKey(
        Attachment,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_receipts",
    )
    funding_source = models.ForeignKey(
        FundingSource,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_movements",
    )
    funding_source_name_snapshot = models.CharField(max_length=160, blank=True)
    funding_source_identifier_snapshot = models.CharField(max_length=100, blank=True)
    reverses = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="corrections",
    )
    is_void = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=280, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="voided_payments",
    )
    voided_at = models.DateTimeField(null=True, blank=True)
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
        if self.currency != self.payable.currency:
            raise ValidationError({"currency": "El movimiento debe usar la misma moneda que la obligación."})
        if self.kind == self.Kind.PAYMENT and not self.receipt_id:
            raise ValidationError({"receipt": "El pago requiere un comprobante de pago."})
        if self.kind != self.Kind.PAYMENT and not self.reason.strip():
            raise ValidationError({"reason": "Explique el motivo de este movimiento."})
        if self.receipt_id:
            if self.receipt.kind != Attachment.Kind.RECEIPT:
                raise ValidationError({"receipt": "El pago requiere un comprobante de pago válido."})
            if self.receipt.payable_id != self.payable_id:
                raise ValidationError({"receipt": "El comprobante debe pertenecer a esta obligación."})
        if self.funding_source_id and self.funding_source.context_id != self.payable.context_id:
            raise ValidationError({"funding_source": "La fuente de fondos debe pertenecer al mismo ámbito."})
        if self.funding_source_id and self.funding_source.currency != self.currency:
            raise ValidationError({"funding_source": "La fuente de fondos debe usar la misma moneda."})
        if self.reverses_id and self.reverses.payable_id != self.payable_id:
            raise ValidationError({"reverses": "El movimiento corregido debe pertenecer a la misma obligación."})
        if self.is_void and not self.void_reason.strip():
            raise ValidationError({"void_reason": "La anulación requiere un motivo."})

    def __str__(self) -> str:
        return f"{self.get_kind_display()} #{self.pk} · {self.payable}"


class InternalReminder(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Pendiente"
        DONE = "DONE", "Atendido"
        SKIPPED = "SKIPPED", "Omitido"

    payable = models.ForeignKey(Payable, on_delete=models.PROTECT, related_name="reminders")
    remind_on = models.DateField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    note = models.CharField(max_length=280, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_payment_reminders",
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="resolved_payment_reminders",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["remind_on", "payable__due_date", "pk"]
        constraints = [
            models.UniqueConstraint(fields=("payable", "remind_on"), name="payment_reminder_unique_day")
        ]
        verbose_name = "recordatorio interno"
        verbose_name_plural = "recordatorios internos"


class PayableImportBatch(models.Model):
    class Status(models.TextChoices):
        PREVIEW = "PREVIEW", "Pendiente de confirmación"
        CONFIRMED = "CONFIRMED", "Confirmado"
        REJECTED = "REJECTED", "Requiere corrección"

    original_name = models.CharField(max_length=255)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PREVIEW)
    rows = models.JSONField(default=list)
    valid_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    error_message = models.CharField(max_length=280, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payable_import_batches",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "lote de importación de obligaciones"
        verbose_name_plural = "lotes de importación de obligaciones"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        COMMITMENT_CREATED = "COMMITMENT_CREATED", "Compromiso creado"
        COMMITMENT_UPDATED = "COMMITMENT_UPDATED", "Compromiso actualizado"
        COMMITMENT_STATUS = "COMMITMENT_STATUS", "Estado de compromiso cambiado"
        RECURRENCE_SKIPPED = "RECURRENCE_SKIPPED", "Ocurrencia omitida"
        PAYABLE_CREATED = "PAYABLE_CREATED", "Obligación creada"
        PAYABLE_STATUS = "PAYABLE_STATUS", "Estado de obligación cambiado"
        DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED", "Documento adjuntado"
        PAYMENT_RECORDED = "PAYMENT_RECORDED", "Pago registrado"
        DESTINATION_ACCOUNT = "DESTINATION_ACCOUNT", "Cuenta de destino actualizada"
        SERVICE_ACCOUNT = "SERVICE_ACCOUNT", "Cuenta de servicio actualizada"
        PAYABLE_UPDATED = "PAYABLE_UPDATED", "Obligación actualizada"
        CONTEXT_UPDATED = "CONTEXT_UPDATED", "Ámbito actualizado"
        FUNDING_SOURCE = "FUNDING_SOURCE", "Fuente de fondos actualizada"
        PAYMENT_VOIDED = "PAYMENT_VOIDED", "Movimiento anulado"
        DUPLICATE_OVERRIDE = "DUPLICATE_OVERRIDE", "Duplicado aceptado"
        IMPORT_CONFIRMED = "IMPORT_CONFIRMED", "Importación confirmada"
        REMINDER_STATUS = "REMINDER_STATUS", "Recordatorio actualizado"
        SENSITIVE_ACCESS = "SENSITIVE_ACCESS", "Acceso a información privada"

        PAYMENT_INSTRUCTION_VIEW = "PAYMENT_INSTRUCTION_VIEW", "Consulta de instrucción de pago"

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
