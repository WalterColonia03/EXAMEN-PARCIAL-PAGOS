from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payable",
            name="supply_code",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Código fijo de suministro o cliente para pago bancario.",
                max_length=80,
                verbose_name="código de suministro / cliente",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="paymentcommitment",
            name="supply_code",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Código fijo de suministro, conexión, cliente o contrato para pago bancario.",
                max_length=80,
                verbose_name="código de suministro / cliente",
            ),
            preserve_default=False,
        ),
    ]
