from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from payments.forms import PayableForm, PaymentCommitmentForm
from payments.models import (
    Company,
    FundingSource,
    InternalReminder,
    Payable,
    Payment,
    PaymentCommitment,
    PaymentContext,
)
from payments.services import (
    attach_source_document,
    create_payable,
    create_commitment,
    generate_scheduled_payables,
    manager_month_summary,
    record_balance_movement,
    record_payment,
    update_payable,
)
from payments.test_p0_regressions import P0PaymentsBaseTestCase


class ReminderAndMovementIntegrityTests(P0PaymentsBaseTestCase):
    def test_due_date_change_reprograms_the_active_reminder(self):
        payable = self.make_payable(due_date=date(2026, 10, 20))
        original = InternalReminder.objects.get(payable=payable)

        candidate = Payable.objects.get(pk=payable.pk)
        candidate.due_date = date(2026, 10, 25)
        update_payable(actor=self.manager, payable=candidate)

        original.refresh_from_db()
        replacement = InternalReminder.objects.get(
            payable=payable,
            remind_on=date(2026, 10, 20),
        )
        self.assertEqual(original.status, InternalReminder.Status.SKIPPED)
        self.assertEqual(replacement.status, InternalReminder.Status.ACTIVE)

    def test_full_payment_closes_reminder_and_full_return_reopens_balance(self):
        payable = self.make_payable()
        attach_source_document(
            actor=self.manager,
            payable=payable,
            upload=self.pdf_upload("sustento.pdf"),
        )
        record_payment(
            actor=self.manager,
            payable_id=payable.pk,
            amount=Decimal("120.00"),
            paid_on=date(2026, 10, 16),
            operation_reference="PAGO-1",
            receipt_upload=self.pdf_upload("pago.pdf"),
            allow_partial=True,
        )
        self.assertFalse(
            InternalReminder.objects.filter(
                payable=payable,
                status=InternalReminder.Status.ACTIVE,
            ).exists()
        )

        record_balance_movement(
            actor=self.manager,
            payable_id=payable.pk,
            kind=Payment.Kind.REFUND,
            amount=Decimal("120.00"),
            movement_on=date(2026, 10, 17),
            reason="El acreedor devolvió el pago.",
        )
        payable.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.PENDING)
        self.assertEqual(payable.balance_due, Decimal("120.00"))
        self.assertTrue(
            InternalReminder.objects.filter(
                payable=payable,
                status=InternalReminder.Status.ACTIVE,
            ).exists()
        )

    def test_full_reimbursement_closes_a_reimbursable_expense(self):
        payable = self.make_payable(payment_nature=PaymentCommitment.Nature.REIMBURSABLE)
        attach_source_document(
            actor=self.manager,
            payable=payable,
            upload=self.pdf_upload("sustento-reembolso.pdf"),
        )
        record_payment(
            actor=self.manager,
            payable_id=payable.pk,
            amount=Decimal("120.00"),
            paid_on=date(2026, 10, 16),
            operation_reference="PAGO-REEMB",
            receipt_upload=self.pdf_upload("pago-reembolso.pdf"),
            allow_partial=True,
        )
        record_balance_movement(
            actor=self.manager,
            payable_id=payable.pk,
            kind=Payment.Kind.REIMBURSEMENT,
            amount=Decimal("120.00"),
            movement_on=date(2026, 10, 18),
            reason="La persona beneficiaria devolvió el importe.",
        )

        payable.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.REFUNDED)
        self.assertEqual(payable.balance_due, Decimal("0.00"))
        self.assertEqual(payable.reimbursement_pending, Decimal("0.00"))


class ScopeAndHistoryIntegrityTests(P0PaymentsBaseTestCase):
    def test_company_gets_a_distinct_context_when_its_name_is_already_in_use(self):
        PaymentContext.objects.create(
            name="Patrimonio familiar",
            kind=PaymentContext.Kind.PATRIMONIAL,
            created_by=self.manager,
            updated_by=self.manager,
        )
        company = Company.objects.create(name="Patrimonio familiar")

        self.assertEqual(company.payment_context.kind, PaymentContext.Kind.BUSINESS)
        self.assertEqual(company.payment_context.name, "Patrimonio familiar · Empresa")

    def test_assistant_cannot_pay_with_a_hidden_funding_source(self):
        source = FundingSource.objects.create(
            context=self.company.payment_context,
            name="Cuenta reservada",
            kind=FundingSource.Kind.ACCOUNT,
            currency=FundingSource.Currency.PEN,
            assistant_visible=False,
            created_by=self.manager,
            updated_by=self.manager,
        )
        payable = self.make_payable()
        attach_source_document(
            actor=self.manager,
            payable=payable,
            upload=self.pdf_upload("sustento-privado.pdf"),
        )

        with self.assertRaisesMessage(ValidationError, "disponible para el asistente"):
            record_payment(
                actor=self.assistant,
                payable_id=payable.pk,
                amount=Decimal("120.00"),
                paid_on=date(2026, 10, 16),
                operation_reference="NO-AUTORIZADO",
                receipt_upload=self.pdf_upload("no-autorizado.pdf"),
                funding_source=source,
                allow_partial=True,
            )
        self.assertFalse(payable.payment_movements.exists())

    def test_financial_identity_is_locked_after_first_movement(self):
        payable = self.make_payable()
        attach_source_document(
            actor=self.manager,
            payable=payable,
            upload=self.pdf_upload("sustento-bloqueo.pdf"),
        )
        record_payment(
            actor=self.manager,
            payable_id=payable.pk,
            amount=Decimal("20.00"),
            paid_on=date(2026, 10, 16),
            operation_reference="ABONO",
            receipt_upload=self.pdf_upload("abono.pdf"),
            allow_partial=True,
        )

        candidate = Payable.objects.get(pk=payable.pk)
        candidate.amount = Decimal("130.00")
        with self.assertRaisesMessage(ValidationError, "Después de registrar un movimiento"):
            update_payable(actor=self.manager, payable=candidate)
        payable.refresh_from_db()
        self.assertEqual(payable.amount, Decimal("120.00"))

    def test_overdue_partial_uses_the_open_balance_in_manager_summary(self):
        payable = self.make_payable(due_date=timezone.localdate() - timedelta(days=1))
        attach_source_document(
            actor=self.manager,
            payable=payable,
            upload=self.pdf_upload("sustento-vencido.pdf"),
        )
        record_payment(
            actor=self.manager,
            payable_id=payable.pk,
            amount=Decimal("20.00"),
            paid_on=timezone.localdate(),
            operation_reference="ABONO-VENCIDO",
            receipt_upload=self.pdf_upload("abono-vencido.pdf"),
            allow_partial=True,
        )

        summary = manager_month_summary(Payable.objects.filter(pk=payable.pk))
        self.assertEqual(summary["overdue"]["count"], 1)
        self.assertEqual(summary["overdue"]["amount"], Decimal("100.00"))
        self.assertEqual(summary["partial"]["count"], 0)

    def test_specialized_category_requires_details_or_incomplete_flag(self):
        card_statement = Payable(
            context=self.company.payment_context,
            company=self.company,
            concept="Estado de tarjeta",
            category=PaymentCommitment.Category.CREDIT_CARD,
            creditor=self.creditor,
            amount=Decimal("900.00"),
            due_date=date(2026, 10, 28),
            details={},
            is_incomplete=False,
        )
        with self.assertRaisesMessage(ValidationError, "datos propios de la categoría"):
            create_payable(actor=self.manager, payable=card_statement)

        card_statement.is_incomplete = True
        created = create_payable(actor=self.manager, payable=card_statement)
        self.assertTrue(created.is_incomplete)

    def test_recurring_loan_keeps_its_contract_in_generated_obligations(self):
        form = PaymentCommitmentForm(
            data={
                "context": self.company.payment_context.pk,
                "name": "Préstamo hipotecario personal",
                "category": PaymentCommitment.Category.LOAN,
                "holder_name": "Carlos Mendoza",
                "beneficiary_name": "Carlos Mendoza",
                "payment_nature": PaymentCommitment.Nature.OWN,
                "frequency": PaymentCommitment.Frequency.MONTHLY,
                "interval_count": 1,
                "start_date": "2026-10-20",
                "usual_due_day": 20,
                "amount_mode": PaymentCommitment.AmountMode.FIXED,
                "fixed_amount": "1450.00",
                "currency": FundingSource.Currency.PEN,
                "creditor": self.creditor.pk,
                "loan_contract": "HIP-2026-001",
            },
            actor=self.manager,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())
        commitment = create_commitment(actor=self.manager, commitment=form.save(commit=False))

        created, skipped = generate_scheduled_payables(
            actor=self.manager,
            through=date(2026, 10, 20),
        )

        self.assertEqual(skipped, 0)
        self.assertEqual(commitment.details, {"loan_contract": "HIP-2026-001"})
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].details, commitment.details)
        self.assertFalse(created[0].is_incomplete)

    def test_specialized_forms_report_fields_and_build_structured_details(self):
        incomplete_commitment = PaymentCommitmentForm(
            data={
                "context": self.company.payment_context.pk,
                "name": "Préstamo sin identificar",
                "category": PaymentCommitment.Category.LOAN,
                "payment_nature": PaymentCommitment.Nature.OWN,
                "frequency": PaymentCommitment.Frequency.MONTHLY,
                "interval_count": 1,
                "start_date": "2026-10-20",
                "usual_due_day": 20,
                "amount_mode": PaymentCommitment.AmountMode.FIXED,
                "fixed_amount": "500.00",
                "currency": FundingSource.Currency.PEN,
                "creditor": self.creditor.pk,
            },
            actor=self.manager,
        )
        self.assertFalse(incomplete_commitment.is_valid())
        self.assertIn("loan_contract", incomplete_commitment.errors)

        card_form = PayableForm(
            data={
                "context": self.company.payment_context.pk,
                "concept": "Estado de cuenta octubre",
                "category": PaymentCommitment.Category.CREDIT_CARD,
                "payment_nature": PaymentCommitment.Nature.OWN,
                "creditor": self.creditor.pk,
                "amount": "900.00",
                "currency": FundingSource.Currency.PEN,
                "due_date": "2026-10-28",
                "card_issuer": "Banco de prueba",
                "card_last_four": "1234",
                "card_statement_total": "900.00",
                "card_minimum_payment": "90.00",
            },
            actor=self.manager,
        )
        self.assertTrue(card_form.is_valid(), card_form.errors.as_json())
        card = card_form.save(commit=False)
        self.assertEqual(card.details["card_last_four"], "1234")
        self.assertEqual(card.details["card_statement_total"], "900.00")
