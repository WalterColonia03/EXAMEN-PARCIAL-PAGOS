from django.db import migrations, models
from django.utils import timezone


def backfill_destination_snapshots(apps, schema_editor):
    """Freeze the current catalog value once, without fabricating older history."""
    alias = schema_editor.connection.alias
    Payable = apps.get_model("payments", "Payable")
    DestinationAccount = apps.get_model("payments", "DestinationAccount")
    accounts = {
        row["id"]: row
        for row in DestinationAccount.objects.using(alias).values(
            "id", "bank_name", "account_holder", "account_number"
        )
    }
    captured_at = timezone.now()
    pending = Payable.objects.using(alias).filter(
        destination_account_id__isnull=False,
        destination_snapshot_origin="NONE",
    )
    for payable in pending.iterator(chunk_size=500):
        account = accounts.get(payable.destination_account_id)
        if account is None:
            continue
        Payable.objects.using(alias).filter(
            pk=payable.pk,
            destination_snapshot_origin="NONE",
        ).update(
            destination_bank_name_snapshot=account["bank_name"],
            destination_account_holder_snapshot=account["account_holder"],
            destination_account_number_snapshot=account["account_number"],
            destination_snapshot_origin="BACKFILLED",
            destination_snapshot_captured_at=captured_at,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0003_stage1_service_accounts"),
    ]

    operations = [
        migrations.AddField(
            model_name="payable",
            name="destination_account_holder_snapshot",
            field=models.CharField(blank=True, editable=False, max_length=160, null=True),
        ),
        migrations.AddField(
            model_name="payable",
            name="destination_account_number_snapshot",
            field=models.CharField(blank=True, editable=False, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name="payable",
            name="destination_bank_name_snapshot",
            field=models.CharField(blank=True, editable=False, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="payable",
            name="destination_snapshot_captured_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="payable",
            name="destination_snapshot_origin",
            field=models.CharField(
                choices=[
                    ("NONE", "Sin cuenta de destino"),
                    ("CREATED", "Capturada al crear la obligación"),
                    ("BACKFILLED", "Congelada durante migración"),
                ],
                default="NONE",
                editable=False,
                max_length=10,
            ),
        ),
        migrations.RunPython(backfill_destination_snapshots, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("COMMITMENT_CREATED", "Compromiso creado"),
                    ("COMMITMENT_STATUS", "Estado de compromiso cambiado"),
                    ("PAYABLE_CREATED", "Obligación creada"),
                    ("PAYABLE_STATUS", "Estado de obligación cambiado"),
                    ("DOCUMENT_UPLOADED", "Documento adjuntado"),
                    ("PAYMENT_RECORDED", "Pago registrado"),
                    ("DESTINATION_ACCOUNT", "Cuenta de destino actualizada"),
                    ("SERVICE_ACCOUNT", "Cuenta de servicio actualizada"),
                    ("PAYABLE_UPDATED", "Obligación actualizada"),
                    ("PAYMENT_INSTRUCTION_VIEW", "Consulta de instrucción de pago"),
                ],
                max_length=24,
            ),
        ),
    ]
