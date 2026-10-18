from __future__ import annotations

from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from identity.models import Account, Role


class Command(BaseCommand):
    help = "Crea de forma interactiva el primer usuario con rol Gerente."

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Correo del gerente inicial.")
        parser.add_argument("--display-name", help="Nombre visible del gerente inicial.")

    def handle(self, *args, **options):
        if Account.objects.filter(role__code=Role.Code.MANAGER).exists():
            raise CommandError("Ya existe un gerente. Use el flujo administrativo autorizado para gestionar cuentas.")

        email = (options.get("email") or input("Correo del gerente: ")).strip()
        display_name = (options.get("display_name") or input("Nombre visible: ")).strip()
        if not email or not display_name:
            raise CommandError("El correo y el nombre visible son obligatorios.")
        if Account.objects.filter(email_normalized=Account.normalize_email(email)).exists():
            raise CommandError("Ya existe una cuenta con ese correo.")

        password = getpass("Contraseña: ")
        confirmation = getpass("Repite la contraseña: ")
        if password != confirmation:
            raise CommandError("Las contraseñas no coinciden.")

        candidate = Account(email=email, display_name=display_name)
        try:
            validate_password(password, candidate)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error

        role, _ = Role.objects.get_or_create(
            code=Role.Code.MANAGER,
            defaults={"name": "Gerente"},
        )
        account = Account.objects.create_user(
            email,
            password,
            display_name=display_name,
            role=role,
        )
        self.stdout.write(self.style.SUCCESS(f"Gerente inicial creado: {account.email}"))
