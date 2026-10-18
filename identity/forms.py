from __future__ import annotations

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Account, Role


NON_DELIVERABLE_EMAIL_DOMAINS = {
    "localhost",
    "example.com",
    "example.invalid",
    "example.test",
}
NON_DELIVERABLE_EMAIL_SUFFIXES = (".invalid", ".local", ".test", ".example")


def validate_real_email_address(value: str) -> str:
    """Reject local/reserved addresses; mailbox ownership is proven by a code."""
    normalized = Account.normalize_email(value)
    domain = normalized.rsplit("@", 1)[-1]
    if domain in NON_DELIVERABLE_EMAIL_DOMAINS or domain.endswith(
        NON_DELIVERABLE_EMAIL_SUFFIXES
    ):
        raise ValidationError(
            "Indica un correo real que pueda recibir el código de verificación."
        )
    return normalized


class PasswordConfirmationForm(forms.Form):
    new_password = forms.CharField(
        label="Nueva contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password", "data-password-input": "true"}
        ),
    )
    confirm_password = forms.CharField(
        label="Repite la nueva contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password")
        confirmation = cleaned_data.get("confirm_password")
        if password and confirmation and password != confirmation:
            self.add_error("confirm_password", "Las contraseñas no coinciden.")
        if password:
            try:
                validate_password(password)
            except ValidationError as error:
                self.add_error("new_password", error)
        return cleaned_data


class RecoverAccessForm(PasswordConfirmationForm):
    recovery_code = forms.CharField(
        label="Código recibido por correo",
        min_length=8,
        max_length=8,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{8}",
                "spellcheck": "false",
                "placeholder": "12345678",
            }
        ),
    )

    def clean_recovery_code(self):
        code = self.cleaned_data["recovery_code"]
        if not code.isascii() or not code.isdigit():
            raise ValidationError("Ingresa los 8 dígitos que recibiste por correo.")
        return code


class RequestEmailRecoveryForm(forms.Form):
    email = forms.EmailField(
        label="Correo electrónico de tu cuenta",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "nombre@correo.com",
            }
        ),
    )

    def clean_email(self):
        return Account.normalize_email(self.cleaned_data["email"])


class ChangePasswordForm(PasswordConfirmationForm):
    current_password = forms.CharField(
        label="Contraseña actual",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class AssistantAccountForm(PasswordConfirmationForm):
    display_name = forms.CharField(
        label="Nombre del asistente",
        max_length=120,
        widget=forms.TextInput(attrs={"autocomplete": "name", "class": "control"}),
    )
    email = forms.EmailField(
        label="Correo electrónico del asistente",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "nombre@correo.com",
                "class": "control",
            }
        ),
    )
    manager_password = forms.CharField(
        label="Confirma tu contraseña de gerente",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "class": "control"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password"].label = "Contraseña temporal para el asistente"
        self.fields["confirm_password"].label = "Repite la contraseña temporal"
        self.fields["new_password"].widget.attrs["class"] = "control"
        self.fields["confirm_password"].widget.attrs["class"] = "control"

    def clean_email(self):
        email = validate_real_email_address(self.cleaned_data["email"])
        if Account.objects.filter(email_normalized=email).exists():
            raise ValidationError("Ya existe una cuenta registrada con este correo.")
        return email


class AccountOnboardingForm(PasswordConfirmationForm):
    verification_code = forms.CharField(
        label="Código de verificación enviado a tu correo",
        min_length=8,
        max_length=8,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{8}",
                "placeholder": "12345678",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password"].label = "Crea tu contraseña personal"
        self.fields["confirm_password"].label = "Repite tu contraseña personal"
