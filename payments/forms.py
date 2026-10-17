from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Branch,
    Company,
    Creditor,
    DestinationAccount,
    FundingSource,
    Payable,
    Payment,
    PaymentCommitment,
    PaymentContext,
    ServiceAccount,
)
from .services import actor_is_manager, visible_contexts_for

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# Accepted MIME types for <input type="file" accept="...">
ACCEPTED_FILE_TYPES = ".pdf,.jpg,.jpeg,.png"


def validate_payment_document(upload) -> None:
    """Reject oversized/unsupported uploads before anything is written to storage."""
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError("Solo se admiten archivos PDF, JPG o PNG.")
    if upload.size > MAX_DOCUMENT_BYTES:
        raise ValidationError("El archivo no puede superar los 10 MB.")
    if upload.size == 0:
        raise ValidationError("El archivo adjunto está vacío.")

    header = upload.read(16)
    upload.seek(0)
    valid_signatures = {
        ".pdf": header.startswith(b"%PDF-"),
        ".png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": header.startswith(b"\xff\xd8\xff"),
        ".jpeg": header.startswith(b"\xff\xd8\xff"),
    }
    if not valid_signatures[extension]:
        raise ValidationError("El contenido del archivo no coincide con el tipo declarado.")


class StyledModelForm(forms.ModelForm):
    """A small form base that keeps the server-rendered experience consistent."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(
                field.widget,
                (
                    forms.Select,
                    forms.TextInput,
                    forms.NumberInput,
                    forms.DateInput,
                    forms.Textarea,
                    forms.FileInput,
                ),
            ):
                field.widget.attrs.setdefault("class", "control")


class ContextSelect(forms.Select):
    """Expose only the context type needed for progressive disclosure in the browser."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-context-kind"] = instance.kind
        return option


def configure_context_field(field, queryset) -> None:
    field.queryset = queryset
    field.widget = ContextSelect(attrs={"class": "control"})


class ServiceAccountForm(StyledModelForm):
    additional_identifiers_text = forms.CharField(
        required=False,
        label="Identificadores adicionales",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Ej. Número de medidor: 123456\nCódigo de predio: 987654",
                "maxlength": "900",
            }
        ),
        help_text="Uno por línea, en formato Nombre: valor. Son opcionales.",
    )

    class Meta:
        model = ServiceAccount
        fields = (
            "context",
            "company",
            "branch",
            "creditor",
            "service_type",
            "identifier_type",
            "primary_identifier",
            "account_holder",
            "expected_billing_frequency",
            "usual_billing_day",
            "acquisition_channel",
            "status",
        )
        widgets = {
            "primary_identifier": forms.TextInput(
                attrs={"placeholder": "Código de suministro, cliente o contrato", "maxlength": "100"}
            ),
            "account_holder": forms.TextInput(
                attrs={"placeholder": "Titular del servicio (opcional)", "maxlength": "160"}
            ),
            "usual_billing_day": forms.NumberInput(
                attrs={"min": "1", "max": "31", "step": "1", "placeholder": "Ej. 15"}
            ),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        contexts = visible_contexts_for(actor).filter(is_active=True) if actor is not None else PaymentContext.objects.filter(is_active=True)
        configure_context_field(self.fields["context"], contexts)
        self.fields["context"].label = "¿A quién corresponde?"
        self.fields["context"].required = False
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).select_related("company")
        self.fields["creditor"].queryset = Creditor.objects.filter(is_active=True)
        self.fields["branch"].required = False
        self.fields["company"].required = False
        self.fields["company"].help_text = "Solo se usa para ámbitos empresariales."
        self.fields["account_holder"].required = False
        self.fields["usual_billing_day"].required = False
        self.fields["usual_billing_day"].help_text = "Opcional: día habitual de emisión o vencimiento (1–31)."
        if self.instance.pk and self.instance.additional_identifiers and not self.is_bound:
            self.initial["additional_identifiers_text"] = "\n".join(
                f"{key}: {value}" for key, value in self.instance.additional_identifiers.items()
            )

    def clean_primary_identifier(self):
        identifier = self.cleaned_data["primary_identifier"].strip()
        if not identifier:
            raise ValidationError("El identificador principal no puede estar vacío.")
        return identifier

    def clean(self):
        cleaned = super().clean()
        context = cleaned.get("context")
        company = cleaned.get("company")
        if context is None and company is not None:
            context = PaymentContext.objects.filter(company=company).first()
            if context is not None:
                cleaned["context"] = context
                self.instance.context = context
        if context is None:
            self.add_error("context", "Seleccione a quién corresponde esta cuenta.")
        elif context.kind == PaymentContext.Kind.BUSINESS:
            cleaned["company"] = context.company
            self.instance.company = context.company
        else:
            cleaned["company"] = None
            cleaned["branch"] = None
            self.instance.company = None
            self.instance.branch = None
        if cleaned.get("expected_billing_frequency") == ServiceAccount.BillingFrequency.ON_DEMAND:
            cleaned["usual_billing_day"] = None
            self.instance.usual_billing_day = None
        return cleaned

    def clean_additional_identifiers_text(self):
        raw_value = self.cleaned_data.get("additional_identifiers_text", "")
        identifiers = {}
        for line in raw_value.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                raise ValidationError("Use una línea por identificador con el formato Nombre: valor.")
            label, value = (part.strip() for part in line.split(":", 1))
            if not label or not value:
                raise ValidationError("Cada identificador adicional debe tener nombre y valor.")
            if label in identifiers:
                raise ValidationError(f"El identificador «{label}» está repetido.")
            identifiers[label] = value
        return identifiers

    def save(self, commit=True):
        account = super().save(commit=False)
        account.additional_identifiers = self.cleaned_data.get("additional_identifiers_text", {})
        if commit:
            account.save()
        return account


# ─────────────────────────────────────────────────────────────────────────────
# PaymentCommitmentForm
# ─────────────────────────────────────────────────────────────────────────────

class PaymentCommitmentForm(StyledModelForm):
    creditor = forms.ModelChoiceField(
        queryset=Creditor.objects.none(),
        required=False,
        label="Acreedor",
    )
    new_creditor_name = forms.CharField(
        required=False,
        max_length=160,
        label="Nombre del nuevo acreedor",
        widget=forms.TextInput(attrs={
            "placeholder": "Ej. Google / Gemini Pro",
            "maxlength": "160",
            "autocomplete": "off",
        }),
    )
    new_creditor_tax_id = forms.CharField(
        required=False,
        max_length=32,
        label="RUC / Identificador fiscal (opcional)",
        widget=forms.TextInput(attrs={
            "placeholder": "Opcional",
            "maxlength": "32",
            "autocomplete": "off",
        }),
    )
    card_issuer = forms.CharField(required=False, max_length=120, label="Emisor de la tarjeta")
    card_last_four = forms.CharField(
        required=False,
        max_length=4,
        min_length=4,
        label="Últimos cuatro dígitos",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "pattern": "[0-9]{4}", "maxlength": "4"}),
    )
    loan_contract = forms.CharField(required=False, max_length=120, label="Contrato del préstamo")
    insurance_policy = forms.CharField(required=False, max_length=120, label="Póliza")
    property_reference = forms.CharField(required=False, max_length=160, label="Predio, dirección o referencia")
    travel_subject = forms.CharField(required=False, max_length=160, label="Viajero o evento")
    investment_vehicle = forms.CharField(required=False, max_length=160, label="Vehículo o inversión")

    DETAIL_FIELDS_BY_CATEGORY = {
        PaymentCommitment.Category.CREDIT_CARD: ("card_issuer", "card_last_four"),
        PaymentCommitment.Category.LOAN: ("loan_contract",),
        PaymentCommitment.Category.INSURANCE: ("insurance_policy",),
        PaymentCommitment.Category.HOUSING: ("property_reference",),
        PaymentCommitment.Category.TRAVEL_EVENT: ("travel_subject",),
        PaymentCommitment.Category.INVESTMENT: ("investment_vehicle",),
    }

    class Meta:
        model = PaymentCommitment
        fields = (
            "context",
            "name",
            "category",
            "company",
            "branch",
            "holder_name",
            "beneficiary_name",
            "payment_nature",
            "service_account",
            "frequency",
            "interval_count",
            "interval_unit",
            "start_date",
            "end_date",
            "usual_due_day",
            "amount_mode",
            "fixed_amount",
            "currency",
            "funding_source",
            "destination_account",
        )
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Ej. Internet sede central",
                "maxlength": "180",
                "required": True,
                "autocomplete": "off",
            }),
            "usual_due_day": forms.NumberInput(attrs={
                "min": "1",
                "max": "31",
                "step": "1",
                "placeholder": "Ej. 15",
            }),
            "fixed_amount": forms.NumberInput(attrs={
                "min": "0.01",
                "step": "0.01",
                "placeholder": "0.00",
            }),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "holder_name": forms.TextInput(attrs={"placeholder": "Quien asumió la obligación"}),
            "beneficiary_name": forms.TextInput(attrs={"placeholder": "Quien recibe el beneficio"}),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        contexts = visible_contexts_for(actor).filter(is_active=True) if actor is not None else PaymentContext.objects.filter(is_active=True)
        configure_context_field(self.fields["context"], contexts)
        self.fields["context"].label = "¿A quién corresponde?"
        self.fields["context"].required = False
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).select_related("company")
        self.fields["creditor"].queryset = Creditor.objects.filter(is_active=True)
        self.fields["destination_account"].queryset = DestinationAccount.objects.filter(
            is_active=True
        ).select_related("creditor")
        self.fields["service_account"].queryset = ServiceAccount.objects.filter(
            status=ServiceAccount.Status.ACTIVE,
            context_id__in=contexts.values("pk"),
        ).select_related("context", "company", "branch", "creditor")
        funding_sources = FundingSource.objects.filter(
            is_active=True,
            context_id__in=contexts.values("pk"),
        )
        if actor is not None and not actor_is_manager(actor):
            funding_sources = funding_sources.filter(assistant_visible=True)
        self.fields["funding_source"].queryset = funding_sources.select_related("context")
        self.fields["creditor"].required = False
        self.fields["company"].required = False
        self.fields["branch"].required = False
        self.fields["destination_account"].required = False
        self.fields["service_account"].required = False
        self.fields["funding_source"].required = False
        self.fields["holder_name"].required = False
        self.fields["beneficiary_name"].required = False
        self.fields["interval_count"].required = False
        self.fields["interval_unit"].required = False
        self.fields["start_date"].required = False
        self.fields["end_date"].required = False
        self.fields["usual_due_day"].help_text = "Obligatorio solo para pagos mensuales (1–31)."
        self.fields["fixed_amount"].help_text = "Obligatorio cuando el monto es fijo."
        self.new_creditor_payload = None
        if self.instance.pk and self.instance.creditor_id and not self.is_bound:
            self.initial["creditor"] = self.instance.creditor_id
        if self.instance.pk and self.instance.details and not self.is_bound:
            for field_name in self.DETAIL_FIELDS_BY_CATEGORY.get(self.instance.category, ()):
                if field_name in self.instance.details:
                    self.initial[field_name] = self.instance.details[field_name]

    def _details_from_cleaned_data(self, category):
        return {
            field_name: value
            for field_name in self.DETAIL_FIELDS_BY_CATEGORY.get(category, ())
            if (value := self.cleaned_data.get(field_name)) not in (None, "")
        }

    def clean(self):
        cleaned = super().clean()
        new_name = (cleaned.get("new_creditor_name") or "").strip()
        new_tax_id = (cleaned.get("new_creditor_tax_id") or "").strip()
        creditor = cleaned.get("creditor")
        if new_name and creditor:
            self.add_error("creditor", "Seleccione un acreedor existente o ingrese uno nuevo, no ambos.")
        elif new_name:
            self.new_creditor_payload = {"name": new_name, "tax_id": new_tax_id}
        elif not creditor:
            self.add_error("creditor", "Seleccione un acreedor existente o registre uno nuevo.")

        frequency = cleaned.get("frequency")
        usual_due_day = cleaned.get("usual_due_day")
        amount_mode = cleaned.get("amount_mode")
        fixed_amount = cleaned.get("fixed_amount")
        context = cleaned.get("context")
        company = cleaned.get("company")
        if context is None and company is not None:
            context = PaymentContext.objects.filter(company=company).first()
            if context is not None:
                cleaned["context"] = context
                self.instance.context = context
        if context is None:
            self.add_error("context", "Seleccione a quién corresponde este compromiso.")
        elif context.kind == PaymentContext.Kind.BUSINESS:
            cleaned["company"] = context.company
            self.instance.company = context.company
        else:
            cleaned["company"] = None
            cleaned["branch"] = None
            self.instance.company = None
            self.instance.branch = None
        if context:
            if not cleaned.get("holder_name"):
                cleaned["holder_name"] = context.default_holder_name
                self.instance.holder_name = context.default_holder_name
            if not cleaned.get("beneficiary_name"):
                cleaned["beneficiary_name"] = context.default_beneficiary_name
                self.instance.beneficiary_name = context.default_beneficiary_name
            source = cleaned.get("funding_source")
            if source and source.context_id != context.pk:
                self.add_error("funding_source", "Seleccione una fuente del mismo ámbito.")

        # Replicate model-level cross-field rules so the error surfaces
        # in the form before hitting the DB constraint.
        if frequency == PaymentCommitment.Frequency.MONTHLY and not usual_due_day:
            self.add_error(
                "usual_due_day",
                "Indique el día de vencimiento para un compromiso mensual (1–31).",
            )
        if frequency == PaymentCommitment.Frequency.CUSTOM and not cleaned.get("interval_unit"):
            self.add_error("interval_unit", "Seleccione días, semanas o meses.")
        if frequency == PaymentCommitment.Frequency.CUSTOM and not cleaned.get("interval_count"):
            self.add_error("interval_count", "Indique cada cuántos días, semanas o meses se repite.")
        elif frequency != PaymentCommitment.Frequency.CUSTOM:
            cleaned["interval_count"] = 1
            cleaned["interval_unit"] = ""
            self.instance.interval_count = 1
            self.instance.interval_unit = ""
        if frequency == PaymentCommitment.Frequency.ONE_TIME:
            for field_name in ("start_date", "end_date", "usual_due_day"):
                cleaned[field_name] = None
                setattr(self.instance, field_name, None)
            self.instance.next_occurrence = None
        elif frequency in {
            PaymentCommitment.Frequency.WEEKLY,
            PaymentCommitment.Frequency.BIWEEKLY,
        } or (
            frequency == PaymentCommitment.Frequency.CUSTOM
            and cleaned.get("interval_unit") != PaymentCommitment.IntervalUnit.MONTHS
        ):
            cleaned["usual_due_day"] = None
            self.instance.usual_due_day = None
        if frequency != PaymentCommitment.Frequency.ONE_TIME and not cleaned.get("start_date"):
            self.add_error("start_date", "Indique cuándo empieza la recurrencia.")
        if amount_mode == PaymentCommitment.AmountMode.FIXED and fixed_amount is None:
            self.add_error("fixed_amount", "Indique el monto fijo del compromiso.")
        elif amount_mode == PaymentCommitment.AmountMode.VARIABLE:
            cleaned["fixed_amount"] = None
            self.instance.fixed_amount = None
        category = cleaned.get("category")
        if category == PaymentCommitment.Category.SERVICE and not cleaned.get("service_account"):
            self.add_error(
                "service_account",
                "Seleccione una cuenta de servicio o créela antes de configurar su recurrencia.",
            )
        elif category != PaymentCommitment.Category.SERVICE:
            cleaned["service_account"] = None
            self.instance.service_account = None
        required_detail = {
            PaymentCommitment.Category.CREDIT_CARD: (
                ("card_issuer", "Identifique el banco o emisor de la tarjeta."),
                ("card_last_four", "Indique los últimos cuatro dígitos de la tarjeta."),
            ),
            PaymentCommitment.Category.LOAN: (("loan_contract", "Identifique el contrato o préstamo."),),
            PaymentCommitment.Category.INSURANCE: (("insurance_policy", "Identifique la póliza."),),
            PaymentCommitment.Category.HOUSING: (
                ("property_reference", "Identifique la vivienda o propiedad."),
            ),
            PaymentCommitment.Category.TRAVEL_EVENT: (
                ("travel_subject", "Identifique el viaje, viajero o evento."),
            ),
            PaymentCommitment.Category.INVESTMENT: (
                ("investment_vehicle", "Identifique la inversión o vehículo patrimonial."),
            ),
        }
        for field_name, message in required_detail.get(category, ()):
            if not cleaned.get(field_name):
                self.add_error(field_name, message)
        last_four = cleaned.get("card_last_four")
        if last_four and (not last_four.isascii() or not last_four.isdigit()):
            self.add_error("card_last_four", "Ingrese exactamente cuatro dígitos numéricos.")
        self.instance.details = self._details_from_cleaned_data(category)
        return cleaned

    def save(self, commit=True):
        commitment = super().save(commit=False)
        creditor = self.cleaned_data.get("creditor")
        if creditor is not None:
            commitment.creditor = creditor
        elif self.new_creditor_payload:
            commitment._new_creditor_payload = self.new_creditor_payload
        commitment.details = self._details_from_cleaned_data(commitment.category)
        if commitment.frequency != PaymentCommitment.Frequency.ONE_TIME and not commitment.next_occurrence:
            commitment.next_occurrence = commitment.start_date
        if commit:
            if self.new_creditor_payload:
                raise ValueError("Los acreedores nuevos deben persistirse mediante el servicio transaccional.")
            commitment.save()
        return commitment


# ─────────────────────────────────────────────────────────────────────────────
# PayableForm
# ─────────────────────────────────────────────────────────────────────────────

class PayableForm(StyledModelForm):
    creditor = forms.ModelChoiceField(
        queryset=Creditor.objects.none(),
        required=False,
        label="Acreedor",
    )
    new_creditor_name = forms.CharField(
        required=False,
        max_length=160,
        label="Nombre del nuevo acreedor",
        widget=forms.TextInput(attrs={
            "placeholder": "Ej. Google / Gemini Pro",
            "maxlength": "160",
            "autocomplete": "off",
        }),
    )
    new_creditor_tax_id = forms.CharField(
        required=False,
        max_length=32,
        label="RUC / Identificador fiscal (opcional)",
        widget=forms.TextInput(attrs={
            "placeholder": "Opcional",
            "maxlength": "32",
            "autocomplete": "off",
        }),
    )
    card_issuer = forms.CharField(required=False, max_length=120, label="Emisor de la tarjeta")
    card_last_four = forms.CharField(
        required=False,
        max_length=4,
        min_length=4,
        label="Últimos cuatro dígitos",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "pattern": "[0-9]{4}", "maxlength": "4"}),
    )
    card_cycle_start = forms.DateField(
        required=False, label="Inicio del ciclo", widget=forms.DateInput(attrs={"type": "date"})
    )
    card_cycle_end = forms.DateField(
        required=False, label="Fin del ciclo", widget=forms.DateInput(attrs={"type": "date"})
    )
    card_statement_total = forms.DecimalField(
        required=False, min_value=0.01, max_digits=12, decimal_places=2, label="Pago total del estado"
    )
    card_minimum_payment = forms.DecimalField(
        required=False, min_value=0.01, max_digits=12, decimal_places=2, label="Pago mínimo"
    )
    loan_contract = forms.CharField(required=False, max_length=120, label="Contrato del préstamo")
    loan_installment_number = forms.IntegerField(required=False, min_value=1, label="Número de cuota")
    loan_total_installments = forms.IntegerField(required=False, min_value=1, label="Total de cuotas")
    loan_principal = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label="Capital")
    loan_interest = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label="Interés")
    loan_insurance = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label="Seguro")
    insurance_policy = forms.CharField(required=False, max_length=120, label="Póliza")
    insurance_insured_name = forms.CharField(required=False, max_length=160, label="Persona o bien asegurado")
    insurance_start = forms.DateField(required=False, label="Inicio de vigencia", widget=forms.DateInput(attrs={"type": "date"}))
    insurance_end = forms.DateField(required=False, label="Fin de vigencia", widget=forms.DateInput(attrs={"type": "date"}))
    insurance_suspension_risk = forms.BooleanField(required=False, label="Existe riesgo de suspensión de cobertura")
    property_reference = forms.CharField(required=False, max_length=160, label="Predio, dirección o referencia")
    travel_subject = forms.CharField(required=False, max_length=160, label="Viajero o evento")
    travel_date = forms.DateField(required=False, label="Fecha o hito", widget=forms.DateInput(attrs={"type": "date"}))
    travel_advance = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label="Anticipo")
    travel_balance = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, label="Saldo del proveedor")
    investment_vehicle = forms.CharField(required=False, max_length=160, label="Vehículo o inversión")
    capital_call_reference = forms.CharField(required=False, max_length=120, label="Llamada de capital")
    capital_call_deadline = forms.DateField(required=False, label="Fecha límite", widget=forms.DateInput(attrs={"type": "date"}))
    confirm_possible_duplicate = forms.BooleanField(
        required=False,
        label="Revisé la coincidencia y confirmo que es una obligación diferente",
    )
    duplicate_reason = forms.CharField(
        required=False,
        max_length=280,
        label="Motivo para continuar",
        widget=forms.Textarea(attrs={"rows": 2, "maxlength": "280"}),
    )

    DETAIL_FIELDS_BY_CATEGORY = {
        PaymentCommitment.Category.CREDIT_CARD: (
            "card_issuer",
            "card_last_four",
            "card_cycle_start",
            "card_cycle_end",
            "card_statement_total",
            "card_minimum_payment",
        ),
        PaymentCommitment.Category.LOAN: (
            "loan_contract",
            "loan_installment_number",
            "loan_total_installments",
            "loan_principal",
            "loan_interest",
            "loan_insurance",
        ),
        PaymentCommitment.Category.INSURANCE: (
            "insurance_policy",
            "insurance_insured_name",
            "insurance_start",
            "insurance_end",
            "insurance_suspension_risk",
        ),
        PaymentCommitment.Category.HOUSING: ("property_reference",),
        PaymentCommitment.Category.TRAVEL_EVENT: (
            "travel_subject",
            "travel_date",
            "travel_advance",
            "travel_balance",
        ),
        PaymentCommitment.Category.INVESTMENT: (
            "investment_vehicle",
            "capital_call_reference",
            "capital_call_deadline",
        ),
    }

    class Meta:
        model = Payable
        fields = (
            "commitment",
            "context",
            "concept",
            "company",
            "branch",
            "category",
            "holder_name",
            "beneficiary_name",
            "payment_nature",
            "service_account",
            "external_document_number",
            "period",
            "amount",
            "currency",
            "due_date",
            "funding_source",
            "is_sensitive",
            "is_incomplete",
        )
        widgets = {
            "concept": forms.TextInput(attrs={
                "placeholder": "Ej. Servicio de agua — octubre",
                "maxlength": "180",
                "required": True,
                "autocomplete": "off",
            }),
            "external_document_number": forms.TextInput(attrs={
                "placeholder": "Factura, recibo u otro (opcional)",
                "maxlength": "80",
                "autocomplete": "off",
            }),
            "period": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={
                "min": "0.01",
                "step": "0.01",
                "placeholder": "0.00",
            }),
            "due_date": forms.DateInput(attrs={
                "type": "date",
                "required": True,
            }),
            "holder_name": forms.TextInput(attrs={"placeholder": "Quien asumió la obligación"}),
            "beneficiary_name": forms.TextInput(attrs={"placeholder": "Quien recibe el beneficio"}),
        }

    def __init__(self, *args, selected_commitment: PaymentCommitment | None = None, actor=None, **kwargs):
        if selected_commitment and "initial" not in kwargs:
            today = timezone.localdate()
            due_day = selected_commitment.usual_due_day or today.day
            initial = {
                "commitment": selected_commitment,
                "context": selected_commitment.context,
                "concept": selected_commitment.name,
                "company": selected_commitment.company,
                "branch": selected_commitment.branch,
                "category": selected_commitment.category,
                "holder_name": selected_commitment.holder_name,
                "beneficiary_name": selected_commitment.beneficiary_name,
                "payment_nature": selected_commitment.payment_nature,
                "creditor": selected_commitment.creditor,
                "service_account": selected_commitment.service_account,
                "period": today.replace(day=1),
                "amount": selected_commitment.fixed_amount,
                "funding_source": selected_commitment.funding_source,
                "due_date": today.replace(day=min(due_day, 28)),
                "is_incomplete": selected_commitment.amount_mode == PaymentCommitment.AmountMode.VARIABLE,
            }
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        contexts = visible_contexts_for(actor).filter(is_active=True) if actor is not None else PaymentContext.objects.filter(is_active=True)
        configure_context_field(self.fields["context"], contexts)
        self.fields["context"].label = "¿A quién corresponde?"
        self.fields["context"].required = False
        self.fields["commitment"].queryset = PaymentCommitment.objects.filter(
            is_active=True, context_id__in=contexts.values("pk")
        ).select_related("context", "company", "branch", "creditor")
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).select_related("company")
        self.fields["creditor"].queryset = Creditor.objects.filter(is_active=True)
        self.fields["service_account"].queryset = ServiceAccount.objects.filter(
            status=ServiceAccount.Status.ACTIVE, context_id__in=contexts.values("pk")
        ).select_related("context", "company", "branch", "creditor")
        funding_sources = FundingSource.objects.filter(
            is_active=True, context_id__in=contexts.values("pk")
        )
        if actor is not None and not actor_is_manager(actor):
            funding_sources = funding_sources.filter(assistant_visible=True)
        self.fields["funding_source"].queryset = funding_sources.select_related("context")
        self.fields["creditor"].required = False
        self.fields["commitment"].required = False
        self.fields["company"].required = False
        self.fields["branch"].required = False
        self.fields["service_account"].required = False
        self.fields["funding_source"].required = False
        self.fields["holder_name"].required = False
        self.fields["beneficiary_name"].required = False
        self.fields["period"].required = False
        self.fields["amount"].required = False
        self.fields["is_incomplete"].label = "La información todavía está incompleta"
        self.fields["is_incomplete"].help_text = (
            "Úselo cuando falta monto o documento definitivo de una cuenta periódica."
        )
        if actor is not None and not actor_is_manager(actor):
            self.fields["is_sensitive"].disabled = True
            self.fields["is_sensitive"].help_text = "Solo el gerente puede crear obligaciones privadas."
        self.new_creditor_payload = None
        if self.instance.pk and self.instance.creditor_id and not self.is_bound:
            self.initial["creditor"] = self.instance.creditor_id
        if self.instance.pk and self.instance.details and not self.is_bound:
            details = self.instance.details
            for field_name in (
                "card_issuer",
                "card_last_four",
                "card_cycle_start",
                "card_cycle_end",
                "card_statement_total",
                "card_minimum_payment",
                "loan_contract",
                "loan_installment_number",
                "loan_total_installments",
                "loan_principal",
                "loan_interest",
                "loan_insurance",
                "insurance_policy",
                "insurance_insured_name",
                "insurance_start",
                "insurance_end",
                "insurance_suspension_risk",
                "property_reference",
                "travel_subject",
                "travel_date",
                "travel_advance",
                "travel_balance",
                "investment_vehicle",
                "capital_call_reference",
                "capital_call_deadline",
            ):
                if field_name in details:
                    self.initial[field_name] = details[field_name]

    def _details_from_cleaned_data(self, category):
        def json_value(value):
            if isinstance(value, date):
                return value.isoformat()
            if isinstance(value, Decimal):
                return str(value)
            return value

        return {
            name: json_value(value)
            for name in self.DETAIL_FIELDS_BY_CATEGORY.get(category, ())
            if (value := self.cleaned_data.get(name)) not in (None, "")
        }

    def clean(self):
        cleaned = super().clean()
        new_name = (cleaned.get("new_creditor_name") or "").strip()
        new_tax_id = (cleaned.get("new_creditor_tax_id") or "").strip()
        creditor = cleaned.get("creditor")
        if new_name and creditor:
            self.add_error("creditor", "Seleccione un acreedor existente o ingrese uno nuevo, no ambos.")
        elif new_name:
            self.new_creditor_payload = {"name": new_name, "tax_id": new_tax_id}
        elif not creditor:
            self.add_error("creditor", "Seleccione un acreedor existente o registre uno nuevo.")
        context = cleaned.get("context")
        company = cleaned.get("company")
        commitment = cleaned.get("commitment")
        if commitment is not None:
            context = commitment.context
            cleaned["context"] = context
            self.instance.context = context
        if context is None and company is not None:
            context = PaymentContext.objects.filter(company=company).first()
            if context is not None:
                cleaned["context"] = context
                self.instance.context = context
        if context is None:
            self.add_error("context", "Seleccione a quién corresponde esta obligación.")
        elif context.kind == PaymentContext.Kind.BUSINESS:
            cleaned["company"] = context.company
            self.instance.company = context.company
        else:
            cleaned["company"] = None
            cleaned["branch"] = None
            self.instance.company = None
            self.instance.branch = None
        if context:
            if not cleaned.get("holder_name"):
                cleaned["holder_name"] = context.default_holder_name
                self.instance.holder_name = context.default_holder_name
            if not cleaned.get("beneficiary_name"):
                cleaned["beneficiary_name"] = context.default_beneficiary_name
                self.instance.beneficiary_name = context.default_beneficiary_name
            source = cleaned.get("funding_source")
            if source and source.context_id != context.pk:
                self.add_error("funding_source", "Seleccione una fuente del mismo ámbito.")

        category = cleaned.get("category")
        incomplete = cleaned.get("is_incomplete", False)
        if category != PaymentCommitment.Category.SERVICE:
            cleaned["service_account"] = None
            self.instance.service_account = None
        last_four = cleaned.get("card_last_four")
        if last_four and (not last_four.isascii() or not last_four.isdigit()):
            self.add_error("card_last_four", "Ingrese exactamente cuatro dígitos numéricos.")
        if category == PaymentCommitment.Category.CREDIT_CARD:
            if not incomplete:
                for field_name in ("card_issuer", "card_last_four", "card_statement_total", "card_minimum_payment"):
                    if not cleaned.get(field_name):
                        self.add_error(field_name, "Complete este dato del estado de cuenta.")
            minimum = cleaned.get("card_minimum_payment")
            total = cleaned.get("card_statement_total")
            if minimum and total and minimum > total:
                self.add_error("card_minimum_payment", "El pago mínimo no puede superar el total.")
            if total and cleaned.get("amount") is None:
                cleaned["amount"] = total
                self.instance.amount = total
            elif total:
                # El total del estado de cuenta es la única fuente de monto
                # para tarjetas; el campo genérico no se presenta en la UI.
                cleaned["amount"] = total
                self.instance.amount = total
            cycle_start = cleaned.get("card_cycle_start")
            cycle_end = cleaned.get("card_cycle_end")
            if cycle_start and cycle_end and cycle_end < cycle_start:
                self.add_error("card_cycle_end", "El fin del ciclo no puede ser anterior al inicio.")
        elif category == PaymentCommitment.Category.LOAN and not incomplete and not cleaned.get("loan_contract"):
            self.add_error("loan_contract", "Identifique el contrato o préstamo.")
        elif category == PaymentCommitment.Category.INSURANCE and not incomplete and not cleaned.get("insurance_policy"):
            self.add_error("insurance_policy", "Identifique la póliza.")
        elif category == PaymentCommitment.Category.HOUSING and not incomplete and not cleaned.get("property_reference"):
            self.add_error("property_reference", "Identifique la vivienda o propiedad.")
        elif category == PaymentCommitment.Category.TRAVEL_EVENT and not incomplete and not cleaned.get("travel_subject"):
            self.add_error("travel_subject", "Identifique el viaje, viajero o evento.")
        elif category == PaymentCommitment.Category.INVESTMENT and not incomplete and not cleaned.get("investment_vehicle"):
            self.add_error("investment_vehicle", "Identifique la inversión o vehículo patrimonial.")
        if category and category != PaymentCommitment.Category.CREDIT_CARD and not incomplete and cleaned.get("amount") is None:
            self.add_error("amount", "Indique el monto o marque que la información todavía está incompleta.")
        installment = cleaned.get("loan_installment_number")
        total_installments = cleaned.get("loan_total_installments")
        if installment and total_installments and installment > total_installments:
            self.add_error("loan_installment_number", "La cuota no puede superar el total de cuotas.")
        if cleaned.get("insurance_start") and cleaned.get("insurance_end"):
            if cleaned["insurance_end"] < cleaned["insurance_start"]:
                self.add_error("insurance_end", "El fin de vigencia no puede ser anterior al inicio.")
        self.instance.details = self._details_from_cleaned_data(category)
        return cleaned

    def save(self, commit=True):
        payable = super().save(commit=False)
        creditor = self.cleaned_data.get("creditor")
        if creditor is not None:
            payable.creditor = creditor
        elif self.new_creditor_payload:
            payable._new_creditor_payload = self.new_creditor_payload
        payable.details = self._details_from_cleaned_data(payable.category)
        payable._duplicate_confirmed = self.cleaned_data.get("confirm_possible_duplicate", False)
        payable._duplicate_reason = (self.cleaned_data.get("duplicate_reason") or "").strip()
        if commit:
            if self.new_creditor_payload:
                raise ValueError("Los acreedores nuevos deben persistirse mediante el servicio transaccional.")
            payable.save()
        return payable

    def clean_due_date(self) -> date:
        due = self.cleaned_data.get("due_date")
        if due is None:
            raise ValidationError("La fecha de vencimiento es obligatoria.")
        return due

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise ValidationError("El monto debe ser mayor que cero.")
        return amount


# ─────────────────────────────────────────────────────────────────────────────
# Document / Payment forms
# ─────────────────────────────────────────────────────────────────────────────

class SourceDocumentForm(forms.Form):
    document = forms.FileField(
        label="Documento por pagar",
        validators=[validate_payment_document],
        widget=forms.FileInput(attrs={
            "accept": ACCEPTED_FILE_TYPES,
            "class": "control",
            "data-file-policy": "payment-document",
        }),
    )


class RecordPaymentForm(forms.Form):
    funding_source = forms.ModelChoiceField(
        queryset=FundingSource.objects.none(),
        required=False,
        label="Fuente de fondos",
    )
    amount = forms.DecimalField(
        label="Monto pagado",
        min_value=0.01,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={
            "min": "0.01",
            "step": "0.01",
            "placeholder": "0.00",
            "required": True,
            "class": "control",
        }),
    )
    paid_on = forms.DateField(
        label="Fecha de pago",
        widget=forms.DateInput(attrs={
            "type": "date",
            "required": True,
            "class": "control",
        }),
    )
    operation_reference = forms.CharField(
        label="Referencia de operaci\u00f3n",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Opcional",
            "maxlength": "120",
            "autocomplete": "off",
            "class": "control",
        }),
    )
    receipt = forms.FileField(
        label="Comprobante de pago",
        validators=[validate_payment_document],
        widget=forms.FileInput(attrs={
            "accept": ACCEPTED_FILE_TYPES,
            "required": True,
            "class": "control",
            "data-file-policy": "payment-document",
        }),
    )

    def __init__(self, *args, payable: Payable | None = None, actor=None, **kwargs):
        if payable and "initial" not in kwargs:
            kwargs["initial"] = {
                "amount": payable.balance_due,
                "paid_on": timezone.localdate(),
                "funding_source": payable.funding_source,
            }
        super().__init__(*args, **kwargs)
        sources = FundingSource.objects.filter(is_active=True)
        if payable and payable.context_id:
            sources = sources.filter(context=payable.context)
        if actor is not None and not actor_is_manager(actor):
            sources = sources.filter(assistant_visible=True)
        self.fields["funding_source"].queryset = sources.select_related("context")
        self.payable = payable

    def clean_paid_on(self) -> date:
        paid_on = self.cleaned_data.get("paid_on")
        if paid_on and paid_on > timezone.localdate():
            raise ValidationError("La fecha de pago no puede ser futura.")
        return paid_on

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise ValidationError("El monto pagado debe ser mayor que cero.")
        if amount is not None and self.payable and self.payable.balance_due is not None:
            if amount > self.payable.balance_due:
                raise ValidationError("El pago no puede superar el saldo pendiente.")
        return amount


class BalanceMovementForm(forms.Form):
    kind = forms.ChoiceField(
        choices=(
            (Payment.Kind.REFUND, "Devolución del acreedor"),
            (Payment.Kind.REIMBURSEMENT, "Reembolso recibido"),
            (Payment.Kind.CHARGEBACK, "Contracargo"),
            (Payment.Kind.ADJUSTMENT, "Ajuste que reabre saldo"),
        ),
        label="Tipo de movimiento",
    )
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        label="Importe",
        widget=forms.NumberInput(attrs={"min": "0.01", "step": "0.01", "class": "control"}),
    )
    movement_on = forms.DateField(
        label="Fecha",
        widget=forms.DateInput(attrs={"type": "date", "class": "control"}),
        initial=timezone.localdate,
    )
    reason = forms.CharField(
        max_length=280,
        label="Motivo",
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": "280", "class": "control"}),
    )
    operation_reference = forms.CharField(required=False, max_length=120, label="Referencia")

    def clean_movement_on(self):
        value = self.cleaned_data["movement_on"]
        if value > timezone.localdate():
            raise ValidationError("La fecha no puede ser futura.")
        return value


class VoidMovementForm(forms.Form):
    reason = forms.CharField(
        max_length=280,
        label="Motivo de la anulación",
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": "280", "class": "control"}),
    )


class SuspensionForm(forms.Form):
    note = forms.CharField(
        label="Motivo de la suspensi\u00f3n",
        max_length=280,
        required=False,
        widget=forms.Textarea(attrs={
            "rows": "3",
            "maxlength": "280",
            "placeholder": "Describa brevemente el motivo (opcional, m\u00e1x. 280 caracteres).",
            "class": "control",
        }),
    )


class PayableReviewStatusForm(forms.Form):
    status = forms.ChoiceField(
        label="Nuevo estado",
        choices=(
            (Payable.Status.PENDING, "Reactivar"),
            (Payable.Status.DISPUTED, "Marcar en disputa"),
            (Payable.Status.CANCELLED, "Anular obligación"),
        ),
    )
    note = forms.CharField(
        label="Motivo",
        required=False,
        max_length=280,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": "280", "class": "control"}),
    )


    def __init__(self, *args, payable=None, **kwargs):
        super().__init__(*args, **kwargs)
        if payable is None:
            return
        choices_by_status = {
            Payable.Status.PENDING: (
                (Payable.Status.DISPUTED, "Marcar en disputa"),
                (Payable.Status.CANCELLED, "Anular obligación"),
            ),
            Payable.Status.PARTIAL: (
                (Payable.Status.DISPUTED, "Marcar en disputa"),
            ),
            Payable.Status.SUSPENDED: (
                (Payable.Status.CANCELLED, "Anular obligación"),
            ),
            Payable.Status.DISPUTED: (
                (Payable.Status.PENDING, "Resolver y reactivar"),
                (Payable.Status.CANCELLED, "Anular obligación"),
            ),
            Payable.Status.CANCELLED: (
                (Payable.Status.PENDING, "Reactivar obligación"),
            ),
        }
        self.fields["status"].choices = choices_by_status.get(payable.status, ())

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") in {Payable.Status.DISPUTED, Payable.Status.CANCELLED}:
            if not (cleaned.get("note") or "").strip():
                self.add_error("note", "Explique el motivo para completar este cambio.")
        return cleaned


class PaymentContextForm(StyledModelForm):
    class Meta:
        model = PaymentContext
        fields = (
            "name",
            "kind",
            "company",
            "default_holder_name",
            "default_beneficiary_name",
            "assistant_access",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ej. Casa de mamá", "maxlength": "160"}),
            "default_holder_name": forms.TextInput(attrs={"placeholder": "Titular habitual (opcional)"}),
            "default_beneficiary_name": forms.TextInput(attrs={"placeholder": "Persona beneficiaria (opcional)"}),
        }
        labels = {
            "name": "Nombre del ámbito",
            "kind": "Tipo de ámbito",
            "company": "Empresa vinculada",
            "default_holder_name": "Titular habitual",
            "default_beneficiary_name": "Persona beneficiaria",
            "assistant_access": "Permitir acceso al asistente",
            "is_active": "Ámbito activo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["company"].required = False
        self.fields["default_holder_name"].required = False
        self.fields["default_beneficiary_name"].required = False

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        matches = PaymentContext.objects.filter(name__iexact=name)
        if self.instance.pk:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise ValidationError("Ya existe un ámbito con este nombre.")
        return name

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        if kind == PaymentContext.Kind.BUSINESS:
            if not cleaned.get("company"):
                self.add_error("company", "Seleccione la empresa de este ámbito.")
        else:
            cleaned["company"] = None
            self.instance.company = None
        if kind == PaymentContext.Kind.THIRD_PARTY:
            if not (cleaned.get("default_beneficiary_name") or "").strip():
                self.add_error("default_beneficiary_name", "Identifique a la persona beneficiaria.")
        return cleaned


class FundingSourceForm(StyledModelForm):
    class Meta:
        model = FundingSource
        fields = (
            "context",
            "name",
            "kind",
            "institution",
            "account_holder",
            "identifier",
            "assistant_visible",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ej. Cuenta personal principal"}),
            "institution": forms.TextInput(attrs={"placeholder": "Banco o institución (opcional)"}),
            "account_holder": forms.TextInput(attrs={"placeholder": "Titular (opcional)"}),
            "identifier": forms.TextInput(attrs={"placeholder": "Cuenta o últimos dígitos; se mostrará enmascarado"}),
        }
        labels = {
            "context": "Ámbito",
            "name": "Nombre de la fuente",
            "kind": "Tipo de fuente",
            "institution": "Banco o institución",
            "account_holder": "Titular",
            "identifier": "Cuenta o identificación",
            "assistant_visible": "Visible para el asistente",
            "is_active": "Fuente activa",
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        contexts = visible_contexts_for(actor).filter(is_active=True) if actor is not None else PaymentContext.objects.filter(is_active=True)
        configure_context_field(self.fields["context"], contexts)
        for name in ("institution", "account_holder", "identifier"):
            self.fields[name].required = False

    def clean(self):
        cleaned = super().clean()
        context = cleaned.get("context")
        name = (cleaned.get("name") or "").strip()
        if cleaned.get("kind") == FundingSource.Kind.CASH:
            for field_name in ("institution", "account_holder", "identifier"):
                cleaned[field_name] = ""
                setattr(self.instance, field_name, "")
        if context and name:
            matches = FundingSource.objects.filter(context=context, name__iexact=name)
            if self.instance.pk:
                matches = matches.exclude(pk=self.instance.pk)
            if matches.exists():
                self.add_error("name", "Ya existe una fuente con este nombre en el ámbito.")
        cleaned["name"] = name
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# DestinationAccountForm
# ─────────────────────────────────────────────────────────────────────────────

class DestinationAccountForm(StyledModelForm):
    class Meta:
        model = DestinationAccount
        fields = ("creditor", "bank_name", "account_holder", "account_number", "is_active")
        widgets = {
            "bank_name": forms.TextInput(attrs={
                "placeholder": "Ej. Banco Continental",
                "maxlength": "100",
                "required": True,
                "autocomplete": "off",
            }),
            "account_holder": forms.TextInput(attrs={
                "placeholder": "Ej. Comercial Andina S.A.C.",
                "maxlength": "160",
                "required": True,
                "autocomplete": "off",
            }),
            "account_number": forms.TextInput(attrs={
                "placeholder": "Ej. 001234567890",
                "maxlength": "80",
                "required": True,
                "autocomplete": "off",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["creditor"].queryset = Creditor.objects.filter(is_active=True)

    def clean_account_number(self):
        number = self.cleaned_data.get("account_number", "").strip()
        if not number:
            raise ValidationError("El n\u00famero de cuenta no puede estar vac\u00edo.")
        return number

    def clean_bank_name(self):
        name = self.cleaned_data.get("bank_name", "").strip()
        if not name:
            raise ValidationError("El nombre del banco no puede estar vac\u00edo.")
        return name

    def clean_account_holder(self):
        holder = self.cleaned_data.get("account_holder", "").strip()
        if not holder:
            raise ValidationError("El titular de la cuenta no puede estar vac\u00edo.")
        return holder


# ─────────────────────────────────────────────────────────────────────────────
# Utility forms
# ─────────────────────────────────────────────────────────────────────────────

class MonthlyGenerationForm(forms.Form):
    period = forms.DateField(
        label="Mes a generar",
        input_formats=["%Y-%m"],
        widget=forms.DateInput(attrs={
            "type": "month",
            "required": True,
            "class": "control",
        }),
    )

    def clean_period(self) -> date:
        return self.cleaned_data["period"].replace(day=1)


class PayableFilterForm(forms.Form):
    STATE_CHOICES = (
        ("", "Todos los pendientes"),
        ("OVERDUE", "Vencidos"),
        ("DUE_TODAY", "Vencen hoy"),
        ("DUE_SOON", "Pr\u00f3ximos a vencer"),
        ("PENDING", "Sin urgencia"),
    )
    EXCEPTION_CHOICES = (
        ("", "Todas"),
        ("MISSING_SERVICE_ACCOUNT", "Sin cuenta de servicio"),
        ("MISSING_SOURCE_DOCUMENT", "Sin documento de sustento"),
        ("INCOMPLETE", "Datos incompletos"),
        ("READY_TO_PAY", "Listas para pagar"),
    )

    context = forms.ModelChoiceField(queryset=PaymentContext.objects.none(), required=False, label="Ámbito")
    company = forms.ModelChoiceField(queryset=Company.objects.none(), required=False, label="Empresa")
    branch = forms.ModelChoiceField(queryset=Branch.objects.none(), required=False, label="Local")
    creditor = forms.ModelChoiceField(queryset=Creditor.objects.none(), required=False, label="Acreedor")
    category = forms.ChoiceField(
        choices=(("", "Todas las categorías"), *PaymentCommitment.Category.choices),
        required=False,
        label="Categoría",
    )

    person = forms.CharField(required=False, max_length=160, label="Titular o beneficiario")
    due_from = forms.DateField(required=False, label="Vence desde", widget=forms.DateInput(attrs={"type": "date"}))
    due_to = forms.DateField(required=False, label="Vence hasta", widget=forms.DateInput(attrs={"type": "date"}))
    sensitive = forms.ChoiceField(
        choices=(("", "Cualquier privacidad"), ("0", "Compartidas"), ("1", "Solo gerente")),
        required=False,
        label="Privacidad",
    )
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False, label="Estado")
    exception = forms.ChoiceField(choices=EXCEPTION_CHOICES, required=False, label="Excepción")

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["context"].queryset = (
            visible_contexts_for(actor).filter(is_active=True) if actor is not None else PaymentContext.objects.filter(is_active=True)
        )
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).select_related("company")
        self.fields["creditor"].queryset = Creditor.objects.filter(is_active=True)
        self.fields["company"].empty_label = "Todas las empresas"
        self.fields["context"].empty_label = "Todos los ámbitos"
        self.fields["branch"].empty_label = "Todos los locales"
        self.fields["creditor"].empty_label = "Todos los acreedores"
        self.fields["person"].widget.attrs.update({"placeholder": "Buscar persona"})
        if actor is not None and not actor_is_manager(actor):
            self.fields.pop("sensitive")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "control")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("due_from") and cleaned.get("due_to") and cleaned["due_to"] < cleaned["due_from"]:
            self.add_error("due_to", "La fecha final no puede ser anterior a la inicial.")
        return cleaned


class ServiceAccountFilterForm(forms.Form):
    context = forms.ModelChoiceField(queryset=PaymentContext.objects.none(), required=False, label="Ámbito")
    company = forms.ModelChoiceField(queryset=Company.objects.none(), required=False, label="Empresa")
    branch = forms.ModelChoiceField(queryset=Branch.objects.none(), required=False, label="Local")
    creditor = forms.ModelChoiceField(queryset=Creditor.objects.none(), required=False, label="Proveedor")
    status = forms.ChoiceField(
        choices=(("", "Todas"), *ServiceAccount.Status.choices), required=False, label="Estado"
    )
    search = forms.CharField(required=False, max_length=100, label="Buscar")

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["context"].queryset = (
            visible_contexts_for(actor).filter(is_active=True) if actor is not None else PaymentContext.objects.filter(is_active=True)
        )
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).select_related("company")
        self.fields["creditor"].queryset = Creditor.objects.filter(is_active=True)
        self.fields["search"].widget = forms.TextInput(
            attrs={"class": "control", "placeholder": "Proveedor, código o titular"}
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "control")


class ServiceAccountImportForm(forms.Form):
    workbook = forms.FileField(
        label="Archivo de cuentas",
        widget=forms.FileInput(
            attrs={
                "class": "control",
                "accept": ".csv,.xlsx",
                "data-file-policy": "service-account-import",
            }
        ),
        help_text="CSV UTF-8 o Excel .xlsx; máximo 2 MB.",
    )

    def clean_workbook(self):
        workbook = self.cleaned_data["workbook"]
        suffix = Path(workbook.name).suffix.lower()
        if suffix not in {".csv", ".xlsx"}:
            raise ValidationError("Seleccione un archivo CSV o Excel .xlsx.")
        if workbook.size == 0:
            raise ValidationError("El archivo está vacío.")
        if workbook.size > 2 * 1024 * 1024:
            raise ValidationError("El archivo no puede superar los 2 MB.")
        return workbook


class PayableImportForm(forms.Form):
    workbook = forms.FileField(
        label="Archivo de obligaciones",
        widget=forms.FileInput(
            attrs={
                "class": "control",
                "accept": ".csv,.xlsx",
                "data-file-policy": "payable-import",
            }
        ),
        help_text="CSV UTF-8 o Excel .xlsx; máximo 2 MB. Primero se revisará, sin crear obligaciones.",
    )

    def clean_workbook(self):
        workbook = self.cleaned_data["workbook"]
        suffix = Path(workbook.name).suffix.lower()
        if suffix not in {".csv", ".xlsx"}:
            raise ValidationError("Seleccione un archivo CSV o Excel .xlsx.")
        if workbook.size == 0:
            raise ValidationError("El archivo está vacío.")
        if workbook.size > 2 * 1024 * 1024:
            raise ValidationError("El archivo no puede superar los 2 MB.")
        return workbook
