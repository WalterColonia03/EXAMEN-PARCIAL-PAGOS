import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_legacy_supply_codes(apps, schema_editor):
    """Promote non-empty legacy supply codes without inventing identifiers."""
    ServiceAccount = apps.get_model("payments", "ServiceAccount")
    PaymentCommitment = apps.get_model("payments", "PaymentCommitment")
    Payable = apps.get_model("payments", "Payable")

    def account_for(*, company_id, branch_id, creditor_id, code, created_by_id, frequency="ON_DEMAND"):
        code = (code or "").strip()
        if not code:
            return None
        account = ServiceAccount.objects.filter(
            company_id=company_id,
            branch_id=branch_id,
            creditor_id=creditor_id,
            identifier_type="SUPPLY",
            primary_identifier=code,
        ).first()
        if account is not None:
            return account
        return ServiceAccount.objects.create(
            company_id=company_id,
            branch_id=branch_id,
            creditor_id=creditor_id,
            service_type="OTHER",
            identifier_type="SUPPLY",
            primary_identifier=code,
            additional_identifiers={},
            expected_billing_frequency=frequency,
            acquisition_channel="MANUAL",
            status="ACTIVE",
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )

    for commitment in PaymentCommitment.objects.exclude(supply_code="").iterator():
        frequency = "MONTHLY" if commitment.frequency == "MONTHLY" else "ON_DEMAND"
        account = account_for(
            company_id=commitment.company_id,
            branch_id=commitment.branch_id,
            creditor_id=commitment.creditor_id,
            code=commitment.supply_code,
            created_by_id=commitment.created_by_id,
            frequency=frequency,
        )
        if account is not None:
            commitment.service_account_id = account.pk
            commitment.save(update_fields=["service_account"])

    for payable in Payable.objects.all().iterator():
        account = None
        if payable.commitment_id:
            account = PaymentCommitment.objects.filter(pk=payable.commitment_id).values_list(
                "service_account_id", flat=True
            ).first()
        if account is None:
            account_obj = account_for(
                company_id=payable.company_id,
                branch_id=payable.branch_id,
                creditor_id=payable.creditor_id,
                code=payable.supply_code,
                created_by_id=payable.created_by_id,
            )
            account = account_obj.pk if account_obj is not None else None
        if account is not None:
            payable.service_account_id = account
            payable.save(update_fields=["service_account"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("payments", "0002_payable_supply_code_paymentcommitment_supply_code"),
    ]

    operations = [
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
                ],
                max_length=24,
            ),
        ),
        migrations.CreateModel(
            name="ServiceAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "service_type",
                    models.CharField(
                        choices=[
                            ("ELECTRICITY", "Electricidad"),
                            ("WATER", "Agua"),
                            ("GAS", "Gas"),
                            ("INTERNET", "Internet"),
                            ("TELECOM", "Telecomunicaciones"),
                            ("MUNICIPAL", "Municipal / arbitrios"),
                            ("TAX", "Tributo"),
                            ("OTHER", "Otro"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "identifier_type",
                    models.CharField(
                        choices=[
                            ("SUPPLY", "Suministro"),
                            ("CLIENT", "Cliente"),
                            ("CONTRACT", "Contrato"),
                            ("PROPERTY", "Predio"),
                            ("TAXPAYER", "Contribuyente"),
                            ("OTHER", "Otro"),
                        ],
                        max_length=12,
                    ),
                ),
                ("primary_identifier", models.CharField(max_length=100)),
                ("additional_identifiers", models.JSONField(blank=True, default=dict)),
                ("account_holder", models.CharField(blank=True, max_length=160)),
                (
                    "expected_billing_frequency",
                    models.CharField(
                        choices=[
                            ("MONTHLY", "Mensual"),
                            ("BIMONTHLY", "Bimestral"),
                            ("QUARTERLY", "Trimestral"),
                            ("ON_DEMAND", "Según consumo / eventual"),
                        ],
                        default="MONTHLY",
                        max_length=12,
                    ),
                ),
                (
                    "usual_billing_day",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)],
                    ),
                ),
                (
                    "acquisition_channel",
                    models.CharField(
                        choices=[
                            ("EMAIL", "Correo"),
                            ("PORTAL", "Portal del proveedor"),
                            ("API", "Integración"),
                            ("OCR", "Documento digitalizado"),
                            ("MANUAL", "Registro manual"),
                        ],
                        default="MANUAL",
                        max_length=12,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Activa"), ("SUSPENDED", "Suspendida"), ("CLOSED", "Cerrada")],
                        default="ACTIVE",
                        max_length=12,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="service_accounts",
                        to="payments.branch",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="service_accounts",
                        to="payments.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_service_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "creditor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="service_accounts",
                        to="payments.creditor",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="updated_service_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "cuenta de servicio",
                "verbose_name_plural": "cuentas de servicio",
                "ordering": ["company__name", "branch__name", "creditor__name", "primary_identifier"],
            },
        ),
        migrations.AddField(
            model_name="payable",
            name="service_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payables",
                to="payments.serviceaccount",
            ),
        ),
        migrations.AddField(
            model_name="paymentcommitment",
            name="service_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="commitments",
                to="payments.serviceaccount",
            ),
        ),
        migrations.AddConstraint(
            model_name="serviceaccount",
            constraint=models.UniqueConstraint(
                fields=("company", "branch", "creditor", "identifier_type", "primary_identifier"),
                name="payment_service_account_unique_identifier",
            ),
        ),
        migrations.AddConstraint(
            model_name="serviceaccount",
            constraint=models.CheckConstraint(
                condition=models.Q(("usual_billing_day__isnull", True), models.Q(("usual_billing_day__gte", 1), ("usual_billing_day__lte", 31)), _connector="OR"),
                name="payment_service_account_billing_day_valid",
            ),
        ),
        migrations.RunPython(migrate_legacy_supply_codes, migrations.RunPython.noop),
    ]
