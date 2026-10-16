from datetime import date
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from identity.models import Account, Role
from payments.importing import parse_service_account_import
from payments.models import Branch, Company, Creditor, Payable, PaymentCommitment, ServiceAccount
from payments.services import generate_monthly_payables, link_service_account_to_payable


class PaymentSchemaTests(TestCase):
    def test_supply_code_columns_are_present(self):
        with connection.cursor() as cursor:
            payable_columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, Payable._meta.db_table)
            }
            commitment_columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, PaymentCommitment._meta.db_table
                )
            }

        self.assertIn("supply_code", payable_columns)
        self.assertIn("supply_code", commitment_columns)

    def test_service_account_columns_are_present(self):
        with connection.cursor() as cursor:
            payable_columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, Payable._meta.db_table)
            }
            commitment_columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, PaymentCommitment._meta.db_table
                )
            }

        self.assertIn("service_account_id", payable_columns)
        self.assertIn("service_account_id", commitment_columns)


class ServiceAccountStageOneTests(TestCase):
    def setUp(self):
        manager_role, _ = Role.objects.get_or_create(
            code=Role.Code.MANAGER, defaults={"name": "Gerente"}
        )
        self.actor = Account.objects.create_user(
            "manager.stage1@pagos.invalid",
            "Contraseña-segura-2026",
            display_name="Gerente de pruebas",
            role=manager_role,
        )
        self.company = Company.objects.create(name="Empresa de pruebas")
        self.branch = Branch.objects.create(company=self.company, name="Local de pruebas")
        self.creditor = Creditor.objects.create(name="Proveedor de pruebas")
        self.service_account = ServiceAccount.objects.create(
            company=self.company,
            branch=self.branch,
            creditor=self.creditor,
            service_type=ServiceAccount.ServiceType.ELECTRICITY,
            identifier_type=ServiceAccount.IdentifierType.SUPPLY,
            primary_identifier="SUM-0001",
            expected_billing_frequency=ServiceAccount.BillingFrequency.MONTHLY,
            created_by=self.actor,
            updated_by=self.actor,
        )

    def test_monthly_generation_copies_the_service_account_from_commitment(self):
        commitment = PaymentCommitment.objects.create(
            name="Luz mensual",
            category=PaymentCommitment.Category.SERVICE,
            company=self.company,
            branch=self.branch,
            creditor=self.creditor,
            service_account=self.service_account,
            frequency=PaymentCommitment.Frequency.MONTHLY,
            usual_due_day=15,
            amount_mode=PaymentCommitment.AmountMode.FIXED,
            fixed_amount="120.00",
            created_by=self.actor,
        )

        created, skipped = generate_monthly_payables(
            actor=self.actor,
            period=date(2026, 10, 1),
            commitments=[commitment],
        )

        self.assertEqual(skipped, 0)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].service_account_id, self.service_account.pk)

    def test_account_must_match_payable_scope(self):
        other_company = Company.objects.create(name="Otra empresa")
        other_account = ServiceAccount.objects.create(
            company=other_company,
            creditor=self.creditor,
            service_type=ServiceAccount.ServiceType.WATER,
            identifier_type=ServiceAccount.IdentifierType.CLIENT,
            primary_identifier="CLI-9",
            created_by=self.actor,
            updated_by=self.actor,
        )
        payable = Payable(
            concept="Recibo de luz",
            company=self.company,
            branch=self.branch,
            category=PaymentCommitment.Category.SERVICE,
            creditor=self.creditor,
            service_account=other_account,
            due_date=date(2026, 10, 20),
            created_by=self.actor,
        )

        with self.assertRaises(ValidationError):
            payable.full_clean()

    def test_create_and_associate_account_from_missing_account_exception(self):
        payable = Payable.objects.create(
            concept="Recibo pendiente de asociar",
            company=self.company,
            branch=self.branch,
            category=PaymentCommitment.Category.SERVICE,
            creditor=self.creditor,
            due_date=date(2026, 10, 20),
            created_by=self.actor,
        )
        self.client.force_login(self.actor)

        response = self.client.post(
            reverse("payment-service-account-create"),
            {
                "return_payable": payable.pk,
                "company": self.company.pk,
                "branch": self.branch.pk,
                "creditor": self.creditor.pk,
                "service_type": ServiceAccount.ServiceType.ELECTRICITY,
                "identifier_type": ServiceAccount.IdentifierType.SUPPLY,
                "primary_identifier": "SUM-0002",
                "account_holder": "Empresa de pruebas",
                "expected_billing_frequency": ServiceAccount.BillingFrequency.MONTHLY,
                "usual_billing_day": "20",
                "acquisition_channel": ServiceAccount.AcquisitionChannel.MANUAL,
                "status": ServiceAccount.Status.ACTIVE,
                "additional_identifiers_text": "Medidor: MED-2",
            },
        )

        payable.refresh_from_db()
        self.assertRedirects(response, reverse("payment-payable-detail", args=[payable.pk]))
        self.assertEqual(payable.service_account.primary_identifier, "SUM-0002")
        self.assertEqual(payable.service_account.additional_identifiers, {"Medidor": "MED-2"})

    def test_board_filters_missing_service_accounts(self):
        payable = Payable.objects.create(
            concept="Servicio sin cuenta",
            company=self.company,
            branch=self.branch,
            category=PaymentCommitment.Category.SERVICE,
            creditor=self.creditor,
            due_date=date(2026, 10, 20),
            created_by=self.actor,
        )
        self.client.force_login(self.actor)

        response = self.client.get(reverse("payments-board"), {"exception": "MISSING_SERVICE_ACCOUNT"})

        self.assertContains(response, payable.concept)
        self.assertContains(response, "Sin cuenta de servicio")


class ServiceAccountImportTests(TestCase):
    def test_csv_parser_normalizes_spanish_headers_and_values(self):
        upload = SimpleUploadedFile(
            "cuentas.csv",
            (
                "Empresa,Local,Proveedor,Tipo de servicio,Tipo de identificador,Identificador principal,Frecuencia,Día habitual,Canal,Estado,Identificadores adicionales\n"
                "Empresa Uno,Local Uno,Proveedor Uno,Electricidad,Suministro,SUM-10,Mensual,15,Correo,Activa,Medidor: 123 | Predio: 456\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        rows = parse_service_account_import(upload)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["service_type"], ServiceAccount.ServiceType.ELECTRICITY)
        self.assertEqual(rows[0]["identifier_type"], ServiceAccount.IdentifierType.SUPPLY)
        self.assertEqual(rows[0]["usual_billing_day"], 15)
        self.assertEqual(rows[0]["additional_identifiers"], {"Medidor": "123", "Predio": "456"})

    def test_xlsx_parser_accepts_the_same_template_columns(self):
        from openpyxl import Workbook

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(
            [
                "Empresa",
                "Proveedor",
                "Tipo de servicio",
                "Tipo de identificador",
                "Identificador principal",
            ]
        )
        worksheet.append(["Empresa Uno", "Proveedor Uno", "Agua", "Cliente", "CLI-10"])
        content = BytesIO()
        workbook.save(content)
        upload = SimpleUploadedFile(
            "cuentas.xlsx",
            content.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        rows = parse_service_account_import(upload)

        self.assertEqual(rows[0]["service_type"], ServiceAccount.ServiceType.WATER)
        self.assertEqual(rows[0]["identifier_type"], ServiceAccount.IdentifierType.CLIENT)
