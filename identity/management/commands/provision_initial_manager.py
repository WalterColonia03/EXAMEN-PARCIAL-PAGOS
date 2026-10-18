from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from identity.forms import validate_real_email_address
from identity.models import Account, Role
from identity.services import (
    RecoveryEmailDeliveryError,
    issue_email_recovery_code,
    send_email_recovery_code,
)


class Command(BaseCommand):
    help = (
        "Crea el primer gerente sin contraseña inicial y le envía un código "
        "de activación por correo."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Correo real del gerente inicial.")
        parser.add_argument("--display-name", help="Nombre visible del gerente inicial.")

    def handle(self, *args, **options):
        if Account.objects.filter(role__code=Role.Code.MANAGER, is_active=True).exists():
            raise CommandError(
                "Ya existe un gerente. Use el panel Equipo de asistentes para gestionar cuentas."
            )

        raw_email = (options.get("email") or input("Correo del gerente: ")).strip()
        display_name = (options.get("display_name") or input("Nombre visible: ")).strip()
        if not raw_email or not display_name:
            raise CommandError("El correo y el nombre visible son obligatorios.")

        try:
            email = validate_real_email_address(raw_email)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        if Account.objects.filter(email_normalized=email).exists():
            raise CommandError("Ya existe una cuenta con ese correo.")

        try:
            with transaction.atomic():
                role, _ = Role.objects.get_or_create(
                    code=Role.Code.MANAGER,
                    defaults={"name": "Gerente"},
                )
                account = Account.objects.create_user(
                    email,
                    password=None,
                    display_name=display_name,
                    role=role,
                    must_change_password=True,
                )
                code, expires_at = issue_email_recovery_code(account)
                send_email_recovery_code(account, code, expires_at)
        except RecoveryEmailDeliveryError as error:
            raise CommandError(
                "No se pudo enviar el código de activación; la cuenta no fue creada."
            ) from error

        self.stdout.write(
            self.style.SUCCESS(
                "Gerente inicial creado. Debe usar el código enviado a su correo "
                "en Recuperar acceso para definir su contraseña."
            )
        )
