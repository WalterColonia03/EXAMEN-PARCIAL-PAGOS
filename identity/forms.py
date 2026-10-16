from __future__ import annotations

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Account, Role


class RecoverAccessForm(forms.Form):
    recovery_code = forms.CharField(
        label="Código de recuperación",
        max_length=64,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "autocapitalize": "characters",
                "spellcheck": "false",
                "placeholder": "XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
            }
        ),
    )
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


class CurrentPasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Confirma tu contraseña actual",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "class": "control"}
        ),
    )


class TemporaryAssistantCodeForm(CurrentPasswordForm):
    assistant = forms.ModelChoiceField(
        label="Asistente",
        queryset=Account.objects.none(),
        empty_label=None,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assistant"].widget.attrs["class"] = "control"
        self.fields["assistant"].queryset = Account.objects.filter(
            role__code=Role.Code.ASSISTANT,
            is_active=True,
        ).select_related("role")
