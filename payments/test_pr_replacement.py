from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from identity.models import Account, Role
from payments.models import Attachment, AuditLog, FundingSource, Payable, PaymentCommitment
from payments.services import (
    attach_source_document,
    create_commitment,
    create_payable,
    record_payment,
    report_funds_unavailable,
    resolve_funds_unavailable,
    save_funding_source,
    update_payable,
    withdraw_source_document,
)
from payments.test_p0_regressions import P0PaymentsBaseTestCase


class FundsUnavailableAndDocumentRetentionTests(P0PaymentsBaseTestCase):
    def test_assistant_reports_shortage_without_suspending_and_manager_resolves(self):
        payable = self.make_payable()

        reported = report_funds_unavailable(
            actor=self.assistant,
            payable=payable,
            note="La fuente prevista aún no tiene saldo.",
        )
        self.assertEqual(reported.status, Payable.Status.PENDING)
        self.assertEqual(reported.funds_unavailable_reported_by, self.assistant)
        self.assertTrue(reported.funds_unavailable_reported_at)
        self.assertEqual(
            AuditLog.objects.filter(
                target_id=str(payable.pk), action=AuditLog.Action.FUNDS_UNAVAILABLE
            ).count(),
            1,
        )

        report_funds_unavailable(
            actor=self.assistant,
            payable=payable,
            note="Reintento que no debe duplicar el aviso.",
        )
        self.assertEqual(
            AuditLog.objects.filter(
                target_id=str(payable.pk), action=AuditLog.Action.FUNDS_UNAVAILABLE
            ).count(),
            1,
        )

        resolved = resolve_funds_unavailable(actor=self.manager, payable=payable)
        self.assertEqual(resolved.status, Payable.Status.PENDING)
        self.assertIsNone(resolved.funds_unavailable_reported_at)
        self.assertEqual(resolved.funds_unavailable_note, "")
        self.assertTrue(
            AuditLog.objects.filter(
                target_id=str(payable.pk), action=AuditLog.Action.FUNDS_RESOLVED
            ).exists()
        )

    def test_report_endpoint_is_assistant_only(self):
        payable = self.make_payable()
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("payment-funds-unavailable-report", args=[payable.pk]),
            {"note": "Intento de gerente."},
        )
        self.assertEqual(response.status_code, 403)
        with self.assertRaises(PermissionDenied):
            report_funds_unavailable(actor=self.manager, payable=payable, note="No corresponde")

    def test_source_document_is_withdrawn_not_deleted_and_cannot_pay_afterward(self):
        payable = self.make_payable()
        source = attach_source_document(
            actor=self.assistant,
            payable=payable,
            upload=self.pdf_upload("sustento-equivocado.pdf"),
        )
        file_name = source.file.name

        withdrawn = withdraw_source_document(
            actor=self.assistant,
            attachment_id=source.pk,
            reason="Se adjuntó el documento de otro proveedor.",
        )
        payable.refresh_from_db()
        self.assertEqual(withdrawn.pk, source.pk)
        self.assertTrue(withdrawn.withdrawn_at)
        self.assertEqual(withdrawn.withdrawn_by, self.assistant)
        self.assertEqual(payable.status, Payable.Status.PENDING)
        self.assertTrue(Attachment.objects.filter(pk=source.pk).exists())
        self.assertTrue(source.file.storage.exists(file_name))
        self.assertTrue(
            AuditLog.objects.filter(
                target_id=str(payable.pk), action=AuditLog.Action.DOCUMENT_WITHDRAWN
            ).exists()
        )
        with self.assertRaisesMessage(ValidationError, "documento de sustento"):
            record_payment(
                actor=self.assistant,
                payable_id=payable.pk,
                amount=Decimal("120.00"),
                paid_on=date(2026, 10, 15),
                operation_reference="PAY-AFTER-WITHDRAW",
                receipt_upload=self.pdf_upload("comprobante.pdf"),
            )

    def test_source_document_cannot_be_withdrawn_after_a_movement(self):
        payable = self.make_payable()
        source = attach_source_document(
            actor=self.manager,
            payable=payable,
            upload=self.pdf_upload("sustento-vigente.pdf"),
        )
        record_payment(
            actor=self.manager,
            payable_id=payable.pk,
            amount=Decimal("20.00"),
            paid_on=date(2026, 10, 15),
            operation_reference="PARTIAL-1",
            receipt_upload=self.pdf_upload("comprobante-parcial.pdf"),
            allow_partial=True,
        )
        with self.assertRaisesMessage(ValidationError, "movimiento financiero"):
            withdraw_source_document(
                actor=self.manager,
                attachment_id=source.pk,
                reason="No debe ser posible.",
            )


class PenOnlyNewOperationsTests(P0PaymentsBaseTestCase):
    def test_services_force_pen_for_new_records_and_block_legacy_operations(self):
        source = save_funding_source(
            actor=self.manager,
            source=FundingSource(
                context=self.company.payment_context,
                name="Caja nueva",
                kind=FundingSource.Kind.CASH,
                currency=FundingSource.Currency.USD,
            ),
        )
        self.assertEqual(source.currency, FundingSource.Currency.PEN)

        commitment = create_commitment(
            actor=self.manager,
            commitment=PaymentCommitment(
                context=self.company.payment_context,
                name="Compromiso nuevo",
                category=PaymentCommitment.Category.OTHER,
                company=self.company,
                creditor=self.creditor,
                frequency=PaymentCommitment.Frequency.ONE_TIME,
                amount_mode=PaymentCommitment.AmountMode.FIXED,
                fixed_amount=Decimal("40.00"),
                currency=FundingSource.Currency.USD,
            ),
        )
        self.assertEqual(commitment.currency, FundingSource.Currency.PEN)

        payable = create_payable(
            actor=self.manager,
            payable=Payable(
                context=self.company.payment_context,
                concept="Obligación nueva",
                company=self.company,
                category=PaymentCommitment.Category.OTHER,
                creditor=self.creditor,
                amount=Decimal("40.00"),
                currency=FundingSource.Currency.USD,
                due_date=date(2026, 10, 20),
            ),
        )
        self.assertEqual(payable.currency, FundingSource.Currency.PEN)

        Payable.objects.filter(pk=payable.pk).update(currency=FundingSource.Currency.USD)
        legacy = Payable.objects.get(pk=payable.pk)
        legacy.concept = "Obligación histórica en USD"
        legacy.currency = FundingSource.Currency.PEN
        with self.assertRaisesMessage(ValidationError, "solo de consulta"):
            update_payable(actor=self.manager, payable=legacy)
        with self.assertRaisesMessage(ValidationError, "solo de consulta"):
            report_funds_unavailable(actor=self.assistant, payable=legacy, note="No debe operar USD histórico")


class InitialManagerCommandTests(TestCase):
    @patch("payments.management.commands.create_initial_manager.getpass")
    def test_creates_a_manager_without_putting_password_in_command_arguments(self, mocked_getpass):
        mocked_getpass.side_effect = ["Gerente-inicial-2026!", "Gerente-inicial-2026!"]

        call_command(
            "create_initial_manager",
            email="gerente.inicial@example.com",
            display_name="Gerente inicial",
        )

        account = Account.objects.get(email="gerente.inicial@example.com")
        self.assertEqual(account.role.code, Role.Code.MANAGER)
        self.assertTrue(account.check_password("Gerente-inicial-2026!"))
