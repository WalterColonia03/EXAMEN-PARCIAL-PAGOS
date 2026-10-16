from __future__ import annotations

import uuid
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone


class Role(models.Model):
    class Code(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        MANAGER = "GERENTE", "Gerente"
        ASSISTANT = "ASISTENTE", "Asistente"

    code = models.CharField(max_length=12, unique=True, choices=Code.choices)
    name = models.CharField(max_length=40)

    class Meta:
        ordering = ["code"]
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self) -> str:
        return self.name or self.code


class AccountManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> "Account":
        if not email:
            raise ValueError("El correo es obligatorio.")
        normalized = Account.normalize_email(email)
        account = self.model(email=email.strip(), email_normalized=normalized, **extra_fields)
        if password is None:
            account.set_unusable_password()
        else:
            account.set_password(password)
        account.full_clean()
        account.save(using=self._db)
        return account

    def create_superuser(self, email: str, password: str, **extra_fields: object) -> "Account":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        role, _ = Role.objects.get_or_create(code=Role.Code.ADMIN, defaults={"name": "Administrador"})
        extra_fields.setdefault("role", role)
        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username: str) -> "Account":
        """Authenticate emails without making their letter case significant."""
        return self.get(email_normalized=Account.normalize_email(username))

    async def aget_by_natural_key(self, username: str) -> "Account":
        return await self.aget(email_normalized=Account.normalize_email(username))


class Account(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField(max_length=120)
    email = models.EmailField(max_length=254, unique=True)
    email_normalized = models.CharField(max_length=254, unique=True, editable=False)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="accounts")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name", "role"]

    class Meta:
        ordering = ["email_normalized"]
        verbose_name = "Cuenta"
        verbose_name_plural = "Cuentas"

    @staticmethod
    def normalize_email(value: str) -> str:
        return value.strip().casefold()

    def clean(self) -> None:
        super().clean()
        validate_email(self.email)
        self.email = self.email.strip()
        self.email_normalized = self.normalize_email(self.email)

    @property
    def username(self) -> str:
        return self.email

    def get_short_name(self) -> str:
        return self.display_name or self.email.split("@")[0]

    def get_full_name(self) -> str:
        return self.display_name

    def __str__(self) -> str:
        return f"{self.display_name} ({self.email})"


class AccountRecoveryCode(models.Model):
    class Kind(models.TextChoices):
        EMERGENCY = "EMERGENCY", "Código personal de emergencia"
        TEMPORARY = "TEMPORARY", "Código temporal emitido por el gerente"

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="recovery_codes",
    )
    digest = models.CharField(max_length=64, unique=True, editable=False)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    created_by = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="issued_recovery_codes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=("account", "kind", "used_at", "revoked_at"),
                name="identity_recovery_active_idx",
            )
        ]
        verbose_name = "código de recuperación"
        verbose_name_plural = "códigos de recuperación"

    @property
    def is_available(self) -> bool:
        return (
            self.used_at is None
            and self.revoked_at is None
            and (self.expires_at is None or self.expires_at > timezone.now())
            and self.account.is_active
        )


class AccountAccessEvent(models.Model):
    class Event(models.TextChoices):
        EMERGENCY_CODES_ISSUED = "EMERGENCY_CODES_ISSUED", "Códigos de emergencia emitidos"
        TEMPORARY_CODE_ISSUED = "TEMPORARY_CODE_ISSUED", "Código temporal emitido"
        RECOVERY_SUCCEEDED = "RECOVERY_SUCCEEDED", "Acceso recuperado"
        RECOVERY_FAILED = "RECOVERY_FAILED", "Recuperación rechazada"
        CODES_REVOKED = "CODES_REVOKED", "Códigos revocados"

    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="access_events",
    )
    actor = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="performed_access_events",
    )
    event = models.CharField(max_length=32, choices=Event.choices)
    summary = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=("account", "event"), name="identity_access_event_idx")]
        verbose_name = "evento de acceso"
        verbose_name_plural = "eventos de acceso"
