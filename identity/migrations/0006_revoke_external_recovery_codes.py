from django.db import migrations
from django.utils import timezone


def revoke_external_recovery_codes(apps, schema_editor):
    recovery_code = apps.get_model("identity", "AccountRecoveryCode")
    recovery_code.objects.filter(
        kind__in=("EMERGENCY", "TEMPORARY"),
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0005_legacy_account_deactivation_event"),
    ]

    operations = [
        migrations.RunPython(revoke_external_recovery_codes, migrations.RunPython.noop),
    ]
