from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from identity.models import Account, Role
from payments.models import (
    Attachment,
    AuditLog,
    Branch,
    Company,
    Creditor,
    DestinationAccount,
    Payable,
    Payment,
    PaymentCommitment,
    ServiceAccount,
)
from payments.services import (
    attach_source_document,
    create_payable,
    generate_monthly_payables,
    manager_month_summary,
    record_payment,
    save_destination_account,
    save_service_account,
    set_payable_suspension,
    update_payable,
    urgency_ordered_payables,
)


class P0PaymentsBaseTestCase(TestCase):
    def setUp(self):
        self._media_directory = TemporaryDirectory()
        self._media_settings = override_settings(MEDIA_ROOT=self._media_directory.name)
        self._media_settings.enable()
        self.addCleanup(self._media_directory.cleanup)
        self.addCleanup(self._media_settings.disable)
        manager_role, _ = Role.objects.get_or_create(
            code=Role.Code.MANAGER, defaults={"name": "Gerente"}
        )
        assistant_role, _ = Role.objects.get_or_create(
            code=Role.Code.ASSISTANT, defaults={"name": "Asistente"}
        )
        self.manager = Account.objects.create_user(
            "manager.p0@pagos.invalid",
            "Contraseña-segura-2026",
            display_name="Gerente P0",
            role=manager_role,
        )
        self.assistant = Account.objects.create_user(
            "assistant.p0@pagos.invalid",
            "Contraseña-segura-2026",
            display_name="Asistente P0",
            role=assistant_role,
        )
        self.company = Company.objects.create(name="Empresa P0")
        self.branch = Branch.objects.create(company=self.company, name="Local P0")
        self.creditor = Creditor.objects.create(name="Proveedor P0")
        self.destination_account = DestinationAccount.objects.create(
            creditor=self.creditor,
            bank_name="Banco Inicial",
            account_holder="Proveedor P0 SAC",
            account_number="001-SECRET-9876",
            created_by=self.manager,
            updated_by=self.manager,
        )
        self.service_account = ServiceAccount.objects.create(
            company=self.company,
            branch=self.branch,
            creditor=self.creditor,
            service_type=ServiceAccount.ServiceType.ELECTRICITY,
            identifier_type=ServiceAccount.IdentifierType.SUPPLY,
            primary_identifier="SUM-SECRET-1234",
            expected_billing_frequency=ServiceAccount.BillingFrequency.MONTHLY,
            created_by=self.manager,
            updated_by=self.manager,
        )

    def make_payable(self, **overrides):
        values = {
            "concept": "Recibo de prueba P0",
            "company": self.company,
            "branch": self.branch,
            "category": PaymentCommitment.Category.SERVICE,
            "creditor": self.creditor,
            "destination_account": self.destination_account,
            "service_account": self.service_account,
            "amount": Decimal("120.00"),
            "due_date": date(2026, 10, 20),
        }
        values.update(overrides)
        return create_payable(actor=self.manager, payable=Payable(**values))

    @staticmethod
    def pdf_upload(name="evidencia.pdf"):
        return SimpleUploadedFile(name, b"%PDF-1.4\nP0 evidence\n%%EOF", content_type="application/pdf")


class DestinationSnapshotRegressionTests(P0PaymentsBaseTestCase):
    def test_creation_freezes_values_and_normal_detail_masks_them(self):
        payable = self.make_payable()
        self.assertEqual(payable.destination_bank_name_snapshot, "Banco Inicial")
        self.assertEqual(payable.destination_account_holder_snapshot, "Proveedor P0 SAC")
        self.assertEqual(payable.destination_account_number_snapshot, "001-SECRET-9876")
        self.assertEqual(payable.destination_snapshot_origin, Payable.DestinationSnapshotOrigin.CREATED)

        self.destination_account.bank_name = "Banco Cambiado"
        self.destination_account.account_number = "002-CHANGED-4321"
        save_destination_account(actor=self.manager, account=self.destination_account)
        payable.refresh_from_db()

        self.assertEqual(payable.destination_bank_name_snapshot, "Banco Inicial")
        self.assertEqual(payable.destination_account_number_snapshot, "001-SECRET-9876")

        self.client.force_login(self.manager)
        detail = self.client.get(reverse("payment-payable-detail", args=[payable.pk]))
        self.assertContains(detail, payable.masked_destination_account_number_snapshot)
        self.assertContains(detail, self.service_account.masked_primary_identifier)
        self.assertNotContains(detail, "001-SECRET-9876")
        self.assertNotContains(detail, "SUM-SECRET-1234")

        revealed = self.client.post(reverse("payment-instruction-reveal", args=[payable.pk]))
        self.assertEqual(revealed.status_code, 200)
        self.assertContains(revealed, "001-SECRET-9876")
        self.assertContains(revealed, "SUM-SECRET-1234")
        access_log = AuditLog.objects.get(
            target_id=str(payable.pk), action=AuditLog.Action.PAYMENT_INSTRUCTION_VIEW
        )
        self.assertNotIn("001-SECRET-9876", access_log.summary)
        self.assertNotIn("001-SECRET-9876", str(access_log.metadata))
        self.assertNotIn("SUM-SECRET-1234", str(access_log.metadata))

    def test_monthly_generation_is_idempotent_and_keeps_each_period_snapshot(self):
        commitment = PaymentCommitment.objects.create(
            name="Servicio recurrente P0",
            category=PaymentCommitment.Category.SERVICE,
            company=self.company,
            branch=self.branch,
            creditor=self.creditor,
            frequency=PaymentCommitment.Frequency.MONTHLY,
            usual_due_day=15,
            amount_mode=PaymentCommitment.AmountMode.FIXED,
            fixed_amount=Decimal("85.00"),
            destination_account=self.destination_account,
            service_account=self.service_account,
            created_by=self.manager,
        )

        created, skipped = generate_monthly_payables(
            actor=self.manager, period=date(2026, 10, 1), commitments=[commitment]
        )
        self.assertEqual((len(created), skipped), (1, 0))
        october = created[0]
        self.assertEqual(october.destination_account_number_snapshot, "001-SECRET-9876")
        self.assertEqual(october.amount, Decimal("85.00"))
        attach_source_document(actor=self.manager, payable=october, upload=self.pdf_upload("october-source.pdf"))

        self.destination_account.account_number = "002-CHANGED-4321"
        save_destination_account(actor=self.manager, account=self.destination_account)
        commitment.fixed_amount = Decimal("95.00")
        commitment.save(update_fields=("fixed_amount", "updated_at"))
        duplicate, skipped = generate_monthly_payables(
            actor=self.manager, period=date(2026, 10, 1), commitments=[commitment]
        )
        self.assertEqual((len(duplicate), skipped), (0, 1))
        october.refresh_from_db()
        self.assertEqual(october.destination_account_number_snapshot, "001-SECRET-9876")

        november, skipped = generate_monthly_payables(
            actor=self.manager, period=date(2026, 11, 1), commitments=[commitment]
        )
        self.assertEqual((len(november), skipped), (1, 0))
        self.assertEqual(november[0].destination_account_number_snapshot, "002-CHANGED-4321")
        self.assertEqual(november[0].amount, Decimal("95.00"))
        self.assertEqual(october.attachments.filter(kind=Attachment.Kind.SOURCE).count(), 1)
        self.assertEqual(november[0].attachments.count(), 0)

    def test_update_preserves_existing_historical_instruction(self):
        payable = self.make_payable()
        candidate = Payable.objects.get(pk=payable.pk)
        candidate.concept = "Recibo de prueba actualizado"
        candidate.destination_account = None

        updated = update_payable(actor=self.manager, payable=candidate)

        self.assertEqual(updated.destination_account_id, self.destination_account.pk)
        self.assertEqual(updated.destination_account_number_snapshot, "001-SECRET-9876")
        log = AuditLog.objects.get(target_id=str(payable.pk), action=AuditLog.Action.PAYABLE_UPDATED)
        self.assertIn("before", log.metadata)
        self.assertIn("after", log.metadata)


class PaymentFlowRegressionTests(P0PaymentsBaseTestCase):
    def test_payment_requires_source_then_records_receipt_and_history(self):
        payable = self.make_payable()
        with self.assertRaisesMessage(ValidationError, "comprobante"):
            record_payment(
                actor=self.assistant,
                payable_id=payable.pk,
                amount=Decimal("120.00"),
                paid_on=date(2026, 10, 15),
                operation_reference="P0-NO-RECEIPT",
                receipt_upload=None,
            )
        with self.assertRaisesMessage(ValidationError, "documento de sustento"):
            record_payment(
                actor=self.assistant,
                payable_id=payable.pk,
                amount=Decimal("120.00"),
                paid_on=date(2026, 10, 15),
                operation_reference="P0-REF-1",
                receipt_upload=self.pdf_upload("comprobante.pdf"),
            )
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(Attachment.objects.filter(payable=payable).count(), 0)

        source = attach_source_document(actor=self.assistant, payable=payable, upload=self.pdf_upload("sustento.pdf"))
        self.client.force_login(self.assistant)
        invalid_form = self.client.post(
            reverse("payment-record", args=[payable.pk]),
            {"amount": "120.00", "paid_on": "2026-10-15", "operation_reference": "P0-UI-ERROR"},
        )
        self.assertEqual(invalid_form.status_code, 400)
        self.assertContains(invalid_form, "detail-error-summary", status_code=400)
        self.assertContains(invalid_form, "P0-UI-ERROR", status_code=400)
        with self.assertRaisesMessage(ValidationError, "debe coincidir"):
            record_payment(
                actor=self.assistant,
                payable_id=payable.pk,
                amount=Decimal("119.99"),
                paid_on=date(2026, 10, 15),
                operation_reference="P0-MISMATCH",
                receipt_upload=self.pdf_upload("mismatch.pdf"),
            )
        payment = record_payment(
            actor=self.assistant,
            payable_id=payable.pk,
            amount=Decimal("120.00"),
            paid_on=date(2026, 10, 15),
            operation_reference="P0-REF-2",
            receipt_upload=self.pdf_upload("comprobante.pdf"),
        )
        payable.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.PAID)
        self.assertEqual(payment.receipt.kind, Attachment.Kind.RECEIPT)
        with self.assertRaisesMessage(ValidationError, "segundo pago"):
            record_payment(
                actor=self.assistant,
                payable_id=payable.pk,
                amount=Decimal("120.00"),
                paid_on=date(2026, 10, 15),
                operation_reference="P0-SECOND",
                receipt_upload=self.pdf_upload("second.pdf"),
            )

        history = self.client.get(reverse("payment-history"))
        self.assertContains(history, payable.concept)
        private_download = self.client.get(reverse("payment-attachment-download", args=[source.pk]))
        self.assertEqual(private_download.status_code, 200)
        private_download.close()
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("payment-attachment-download", args=[source.pk])).status_code,
            302,
        )

        self.client.force_login(self.manager)
        dashboard = self.client.get(reverse("payment-manager-dashboard"))
        self.assertEqual(dashboard.status_code, 200)

    def test_uploaded_file_is_compensated_when_audit_fails(self):
        payable = self.make_payable()
        with TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root), patch(
                "payments.services.record_audit", side_effect=RuntimeError("audit unavailable")
            ):
                with self.assertRaisesMessage(RuntimeError, "audit unavailable"):
                    attach_source_document(actor=self.manager, payable=payable, upload=self.pdf_upload("rollback.pdf"))
            self.assertEqual(Attachment.objects.filter(payable=payable).count(), 0)
            self.assertEqual([path for path in Path(media_root).rglob("*") if path.is_file()], [])

    def test_manager_can_suspend_and_reactivate_but_assistant_cannot(self):
        payable = self.make_payable()
        with self.assertRaises(PermissionDenied):
            set_payable_suspension(actor=self.assistant, payable=payable, suspend=True, note="No autorizado")

        set_payable_suspension(actor=self.manager, payable=payable, suspend=True, note="En revisión")
        payable.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.SUSPENDED)
        set_payable_suspension(actor=self.manager, payable=payable, suspend=False)
        payable.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.PENDING)


class ServiceAccountSecurityAndImportTests(P0PaymentsBaseTestCase):
    def test_assistant_cannot_maintain_service_accounts_and_list_is_masked(self):
        self.client.force_login(self.assistant)
        before_accounts = ServiceAccount.objects.count()
        before_audits = AuditLog.objects.count()
        account_payload = {
            "company": self.company.pk,
            "branch": self.branch.pk,
            "creditor": self.creditor.pk,
            "service_type": ServiceAccount.ServiceType.WATER,
            "identifier_type": ServiceAccount.IdentifierType.CLIENT,
            "primary_identifier": "CLI-UNAUTHORIZED-001",
            "expected_billing_frequency": ServiceAccount.BillingFrequency.MONTHLY,
            "acquisition_channel": ServiceAccount.AcquisitionChannel.MANUAL,
            "status": ServiceAccount.Status.ACTIVE,
        }
        self.assertEqual(self.client.get(reverse("payment-service-account-create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("payment-service-account-create"), account_payload).status_code, 403)
        self.assertEqual(self.client.post(reverse("payment-service-account-import"), {}).status_code, 403)
        self.assertEqual(ServiceAccount.objects.count(), before_accounts)
        self.assertEqual(AuditLog.objects.count(), before_audits)

        forbidden = ServiceAccount(
            company=self.company,
            branch=self.branch,
            creditor=self.creditor,
            service_type=ServiceAccount.ServiceType.WATER,
            identifier_type=ServiceAccount.IdentifierType.CLIENT,
            primary_identifier="CLI-UNAUTHORIZED-002",
        )
        with self.assertRaises(PermissionDenied):
            save_service_account(actor=self.assistant, account=forbidden)
        self.assertEqual(ServiceAccount.objects.count(), before_accounts)

        listing = self.client.get(reverse("payment-service-accounts"))
        self.assertContains(listing, self.service_account.masked_primary_identifier)
        self.assertNotContains(listing, self.service_account.primary_identifier)
        self.assertNotContains(listing, "btn-nueva-cuenta-servicio")

    def test_manager_can_open_maintenance_and_audit_never_stores_raw_identifier(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("payment-service-account-create")).status_code, 200)
        account = ServiceAccount(
            company=self.company,
            branch=self.branch,
            creditor=self.creditor,
            service_type=ServiceAccount.ServiceType.WATER,
            identifier_type=ServiceAccount.IdentifierType.CLIENT,
            primary_identifier="CLI-MANAGER-7788",
        )
        saved = save_service_account(actor=self.manager, account=account)
        log = AuditLog.objects.get(target_id=str(saved.pk), action=AuditLog.Action.SERVICE_ACCOUNT)
        self.assertNotIn(saved.primary_identifier, log.summary)
        self.assertNotIn(saved.primary_identifier, str(log.metadata))
        self.assertEqual(log.metadata["after"]["primary_identifier"], saved.masked_primary_identifier)

    def test_corrupt_xlsx_and_mid_import_error_return_controlled_rollback(self):
        self.client.force_login(self.manager)
        before_accounts = ServiceAccount.objects.count()
        before_creditors = Creditor.objects.count()
        before_audits = AuditLog.objects.count()
        corrupt = SimpleUploadedFile(
            "corrupt.xlsx",
            b"this is not an xlsx archive",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = self.client.post(reverse("payment-service-account-import"), {"workbook": corrupt})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ServiceAccount.objects.count(), before_accounts)
        self.assertEqual(AuditLog.objects.count(), before_audits)

        data = (
            "company,creditor,service type,identifier type,primary identifier\n"
            f"{self.company.name},Proveedor temporal,Water,Client,CLI-ROLLBACK-1\n"
            "Empresa inexistente,Proveedor temporal,Water,Client,CLI-ROLLBACK-2\n"
        ).encode("utf-8")
        csv_upload = SimpleUploadedFile("mixed.csv", data, content_type="text/csv")
        response = self.client.post(reverse("payment-service-account-import"), {"workbook": csv_upload})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ServiceAccount.objects.count(), before_accounts)
        self.assertEqual(Creditor.objects.count(), before_creditors)
        self.assertEqual(AuditLog.objects.count(), before_audits)

    def test_invalid_new_creditor_form_never_creates_a_creditor(self):
        self.client.force_login(self.manager)
        before_creditors = Creditor.objects.count()
        response = self.client.post(
            reverse("payment-payable-create"),
            {
                "concept": "Obligación inválida",
                "company": self.company.pk,
                "branch": self.branch.pk,
                "category": PaymentCommitment.Category.SUPPLIER,
                "new_creditor_name": "Acreedor que no debe persistir",
                "amount": "45.00",
                # due_date is intentionally absent.
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Creditor.objects.count(), before_creditors)
        self.assertFalse(Creditor.objects.filter(name="Acreedor que no debe persistir").exists())


class OperationalRuleRegressionTests(P0PaymentsBaseTestCase):
    def test_urgency_boundaries_are_ordered_for_minus_one_zero_plus_five_and_plus_six(self):
        today = timezone.localdate()
        overdue = self.make_payable(concept="-1 día", due_date=today - timedelta(days=1))
        due_today = self.make_payable(concept="0 días", due_date=today)
        due_soon = self.make_payable(concept="+5 días", due_date=today + timedelta(days=5))
        pending = self.make_payable(concept="+6 días", due_date=today + timedelta(days=6))

        ordered = list(urgency_ordered_payables(Payable.objects.all(), today=today))
        self.assertEqual(
            [payable.pk for payable in ordered],
            [overdue.pk, due_today.pk, due_soon.pk, pending.pk],
        )

    def test_company_and_branch_filters_and_known_amount_totals_are_consistent(self):
        known = self.make_payable(concept="Visible en filtro", amount=Decimal("100.00"))
        without_amount = self.make_payable(
            concept="Sin monto", amount=None, is_incomplete=True, due_date=date(2026, 10, 25)
        )
        other_company = Company.objects.create(name="Empresa ajena")
        other_branch = Branch.objects.create(company=other_company, name="Local ajeno")
        other_creditor = Creditor.objects.create(name="Proveedor ajeno")
        other_payable = create_payable(
            actor=self.manager,
            payable=Payable(
                concept="Fuera del filtro",
                company=other_company,
                branch=other_branch,
                category=PaymentCommitment.Category.SUPPLIER,
                creditor=other_creditor,
                amount=Decimal("60.00"),
                due_date=date(2026, 10, 25),
            ),
        )

        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("payments-board"), {"company": self.company.pk, "branch": self.branch.pk}
        )
        self.assertContains(response, known.concept)
        self.assertContains(response, without_amount.concept)
        self.assertNotContains(response, other_payable.concept)

        summary = manager_month_summary(Payable.objects.filter(pk__in=[known.pk, without_amount.pk, other_payable.pk]))
        self.assertEqual(sum(bucket["count"] for bucket in summary.values()), 3)
        self.assertEqual(sum(bucket["amount"] for bucket in summary.values()), Decimal("160.00"))
        self.assertEqual(summary["pending"]["count"], 3)
