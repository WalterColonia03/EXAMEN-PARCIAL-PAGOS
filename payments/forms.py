from __future__ import annotations

from datetime import date
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Branch, Company, Creditor, DestinationAccount, Payable, PaymentCommitment

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


# ─────────────────────────────────────────────────────────────────────────────
# PaymentCommitmentForm
# ─────────────────────────────────────────────────────────────────────────────

class PaymentCommitmentForm(StyledModelForm):
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

    class Meta:
        model = PaymentCommitment
        fields = (
            "name",
            "category",
            "company",
            "branch",
            "creditor",
            "supply_code",
            "frequency",
            "usual_due_day",
            "amount_mode",
            "fixed_amount",
            "destination_account",
        )
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Ej. Internet sede central",
                "maxlength": "180",
                "required": True,
                "autocomplete": "off",
            }),
            "supply_code": forms.TextInput(attrs={
                "placeholder": "Ej. 2194810-8 (Suministro, Contrato o N° Cliente)",
                "maxlength": "80",
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).select_related("company")
        self.fields["creditor"].queryset = Creditor.objects.filter(is_active=True)
        self.fields["destination_account"].queryset = DestinationAccount.objects.filter(
            is_active=True
        ).select_related("creditor")
        self.fields["creditor"].required = False
        self.fields["branch"].required = False
        self.fields["destination_account"].required = False
        self.fields["usual_due_day"].help_text = "Obligatorio solo para pagos mensuales (1–31)."
        self.fields["fixed_amount"].help_text = "Obligatorio cuando el monto es fijo."

    def clean(self):
        cleaned = super().clean()
        new_name = (cleaned.get("new_creditor_name") or "").strip()
        new_tax_id = (cleaned.get("new_creditor_tax_id") or "").strip()
        creditor = cleaned.get("creditor")
        if new_name:
            creditor_obj, _ = Creditor.objects.get_or_create(
                name=new_name,
                defaults={"tax_id": new_tax_id, "is_active": True}
            )
            if new_tax_id and not creditor_obj.tax_id:
                creditor_obj.tax_id = new_tax_id
                creditor_obj.save(update_fields=["tax_id"])
            cleaned["creditor"] = creditor_obj
            self.instance.creditor = creditor_obj
        elif not creditor:
            self.add_error("creditor", "Seleccione un acreedor existente o registre uno nuevo.")

        frequency = cleaned.get("frequency")
        usual_due_day = cleaned.get("usual_due_day")
        amount_mode = cleaned.get("amount_mode")
        fixed_amount = cleaned.get("fixed_amount")

        # Replicate model-level cross-field rules so the error surfaces
        # in the form before hitting the DB constraint.
        if frequency == PaymentCommitment.Frequency.MONTHLY and not usual_due_day:
            self.add_error(
                "usual_due_day",
                "Indique el día de vencimiento para un compromiso mensual (1–31).",
            )
        if amount_mode == PaymentCommitment.AmountMode.FIXED and fixed_amount is None:
            self.add_error("fixed_amount", "Indique el monto fijo del compromiso.")
        return cleaned


# ─────────────────────────────────────────────────────────────────────────────
# PayableForm
# ─────────────────────────────────────────────────────────────────────────────

class PayableForm(StyledModelForm):
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

    class Meta:
        model = Payable
        fields = (
            "commitment",
            "concept",
            "company",
            "branch",
            "category",
            "creditor",
            "supply_code",
            "external_document_number",
            "period",
            "amount",
            "due_date",
            "is_incomplete",
        )
        widgets = {
            "concept": forms.TextInput(attrs={
                "placeholder": "Ej. Servicio de agua — octubre",
                "maxlength": "180",
                "required": True,
                "autocomplete": "off",
            }),
            "supply_code": forms.TextInput(attrs={
                "placeholder": "Ej. 2194810-8 (Suministro, Contrato o N° Cliente)",
                "maxlength": "80",
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
        }

    def __init__(self, *args, selected_commitment: PaymentCommitment | None = None, **kwargs):
        if selected_commitment and "initial" not in kwargs:
            today = timezone.localdate()
            due_day = selected_commitment.usual_due_day or today.day
            initial = {
                "commitment": selected_commitment,
                "concept": selected_commitment.name,
                "company": selected_commitment.company,
                "branch": selected_commitment.branch,
                "category": selected_commitment.category,
                "creditor": selected_commitment.creditor,
                "supply_code": selected_commitment.supply_code,
                "period": today.replace(day=1),
                "amount": selected_commitment.fixed_amount,
                "due_date": today.replace(day=min(due_day, 28)),
                "is_incomplete": selected_commitment.amount_mode == PaymentCommitment.AmountMode.VARIABLE,
            }
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        self.fields["commitment"].queryset = PaymentCommitment.objects.filter(is_active=True).select_related(
            "company", "branch", "creditor"
        )
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).select_related("company")
        self.fields["creditor"].queryset = Creditor.objects.filter(is_active=True)
        self.fields["creditor"].required = False
        self.fields["commitment"].required = False
        self.fields["branch"].required = False
        self.fields["supply_code"].required = False
        self.fields["period"].required = False
        self.fields["amount"].required = False
        self.fields["is_incomplete"].label = "La información todavía está incompleta"
        self.fields["is_incomplete"].help_text = (
            "Úselo cuando falta monto o documento definitivo de una cuenta periódica."
        )

    def clean(self):
        cleaned = super().clean()
        new_name = (cleaned.get("new_creditor_name") or "").strip()
        new_tax_id = (cleaned.get("new_creditor_tax_id") or "").strip()
        creditor = cleaned.get("creditor")
        if new_name:
            creditor_obj, _ = Creditor.objects.get_or_create(
                name=new_name,
                defaults={"tax_id": new_tax_id, "is_active": True}
            )
            if new_tax_id and not creditor_obj.tax_id:
                creditor_obj.tax_id = new_tax_id
                creditor_obj.save(update_fields=["tax_id"])
            cleaned["creditor"] = creditor_obj
            self.instance.creditor = creditor_obj
        elif not creditor:
            self.add_error("creditor", "Seleccione un acreedor existente o registre uno nuevo.")
        return cleaned

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
        }),
    )


class RecordPaymentForm(forms.Form):
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
        }),
    )

    def __init__(self, *args, payable: Payable | None = None, **kwargs):
        if payable and "initial" not in kwargs:
            kwargs["initial"] = {"amount": payable.amount, "paid_on": timezone.localdate()}
        super().__init__(*args, **kwargs)

    def clean_paid_on(self) -> date:
        paid_on = self.cleaned_data.get("paid_on")
        if paid_on and paid_on > timezone.localdate():
            raise ValidationError("La fecha de pago no puede ser futura.")
        return paid_on

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise ValidationError("El monto pagado debe ser mayor que cero.")
        return amount


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


# ─────────────────────────────────────────────────────────────────────────────
# DestinationAccountForm
# ─────────────────────────────────────────────────────────────────────────────

class DestinationAccountForm(StyledModelForm):
    class Meta:
        model = DestinationAccount
        fields = ("creditor", "bank_name", "account_holder", "account_number", "is_active")
        widgets = {
            "bank_name": forms.TextInput(attrs={
                "placeholder": "Banco de demostraci\u00f3n",
                "maxlength": "100",
                "required": True,
                "autocomplete": "off",
            }),
            "account_holder": forms.TextInput(attrs={
                "placeholder": "Titular de demostraci\u00f3n",
                "maxlength": "160",
                "required": True,
                "autocomplete": "off",
            }),
            "account_number": forms.TextInput(attrs={
                "placeholder": "Ej. DEMO-00123456789",
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

    company = forms.ModelChoiceField(queryset=Company.objects.none(), required=False, label="Empresa")
    branch = forms.ModelChoiceField(queryset=Branch.objects.none(), required=False, label="Local")
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False, label="Estado")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.filter(is_active=True)
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).select_related("company")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "control")
