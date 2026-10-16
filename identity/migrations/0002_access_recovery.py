import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountRecoveryCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("digest", models.CharField(editable=False, max_length=64, unique=True)),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("EMERGENCY", "Código personal de emergencia"),
                            ("TEMPORARY", "Código temporal emitido por el gerente"),
                        ],
                        max_length=12,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recovery_codes",
                        to="identity.account",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="issued_recovery_codes",
                        to="identity.account",
                    ),
                ),
            ],
            options={
                "verbose_name": "código de recuperación",
                "verbose_name_plural": "códigos de recuperación",
                "ordering": ["-created_at", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="AccountAccessEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "event",
                    models.CharField(
                        choices=[
                            ("EMERGENCY_CODES_ISSUED", "Códigos de emergencia emitidos"),
                            ("TEMPORARY_CODE_ISSUED", "Código temporal emitido"),
                            ("RECOVERY_SUCCEEDED", "Acceso recuperado"),
                            ("RECOVERY_FAILED", "Recuperación rechazada"),
                            ("CODES_REVOKED", "Códigos revocados"),
                        ],
                        max_length=32,
                    ),
                ),
                ("summary", models.CharField(max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="access_events",
                        to="identity.account",
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="performed_access_events",
                        to="identity.account",
                    ),
                ),
            ],
            options={
                "verbose_name": "evento de acceso",
                "verbose_name_plural": "eventos de acceso",
                "ordering": ["-created_at", "-pk"],
            },
        ),
        migrations.AddIndex(
            model_name="accountrecoverycode",
            index=models.Index(
                fields=["account", "kind", "used_at", "revoked_at"],
                name="identity_recovery_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="accountaccessevent",
            index=models.Index(
                fields=["account", "event"],
                name="identity_access_event_idx",
            ),
        ),
    ]
