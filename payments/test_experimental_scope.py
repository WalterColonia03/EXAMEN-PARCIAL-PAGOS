from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from payments.models import (
    Attachment,
    FundingSource,
    Payable,
    PayableImportBatch,
    Payment,
    PaymentCommitment,
    PaymentContext,
)
from payments.services import (
    attach_source_document,
    create_commitment,
    create_payable,
    generate_scheduled_payables,
    next_recurrence_date,
    record_balance_movement,
    record_payment,
    set_commitment_paused,
    skip_next_occurrence,
    void_payment_movement,
)
from payments.test_p0_regressions import P0PaymentsBaseTestCase


class ContextAndPrivacyTests(P0PaymentsBaseTestCase):
    def test_personal_and_family_obligations_do_not_need_fake_companies(self):
        home = PaymentContext.objects.create(
            name="Casa de mamá",
            kind=PaymentContext.Kind.HOUSEHOLD,
            default_holder_name="Madre del gerente",
            default_beneficiary_name="Madre del gerente",
            assistant_access=True,
            created_by=self.manager,
            updated_by=self.manager,
        )
        payable = create_payable(
            actor=self.manager,
            payable=Payable(
                context=home,
                concept="Electricidad de la casa de mamá",
                category=PaymentCommitment.Category.SERVICE,
                creditor=self.creditor,
                amount=Decimal("95.40"),
                currency=FundingSource.Currency.PEN,
                due_date=date(2026, 10, 24),
            ),
        )

        self.assertIsNone(payable.company)
        self.assertIsNone(payable.branch)
        self.assertEqual(payable.holder_name, "Madre del gerente")
        self.assertEqual(payable.beneficiary_name, "Madre del gerente")

    def test_assistant_cannot_list_open_or_download_private_scope_data(self):
        private_context = PaymentContext.objects.create(
            name="Patrimonio reservado",
            kind=PaymentContext.Kind.PATRIMONIAL,
            assistant_access=False,
            created_by=self.manager,
            updated_by=self.manager,
        )
        payable = create_payable(
            actor=self.manager,
            payable=Payable(
                context=private_context,
                concept="Aporte patrimonial reservado",
                category=PaymentCommitment.Category.INVESTMENT,
                creditor=self.creditor,
                amount=Decimal("500.00"),
                due_date=date(2026, 10, 25),
                details={"investment_vehicle": "Patrimonio reservado"},
            ),
        )
        document = attach_source_document(
            actor=self.manager,
            payable=payable,
            upload=self.pdf_upload("reservado.pdf"),
        )

        self.client.force_login(self.assistant)
        board = self.client.get(reverse("payments-board"))
        self.assertNotContains(board, payable.concept)
        self.assertEqual(self.client.get(reverse("payment-payable-detail", args=[payable.pk])).status_code, 404)
        self.assertEqual(
            self.client.get(reverse("payment-attachment-download", args=[document.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("payment-attachment-preview", args=[document.pk])).status_code,
            404,
        )

        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("payment-payable-detail", args=[payable.pk])).status_code, 200)

    def test_sensitive_record_is_private_inside_a_shared_context(self):
        sensitive = create_payable(
            actor=self.manager,
            payable=Payable(
                context=self.company.payment_context,
                company=self.company,
                branch=self.branch,
                concept="Consulta médica privada",
                category=PaymentCommitment.Category.HEALTH,
                creditor=self.creditor,
                amount=Decimal("220.00"),
                due_date=date(2026, 10, 26),
                is_sensitive=True,
            ),
        )
        self.client.force_login(self.assistant)
        self.assertEqual(self.client.get(reverse("payment-payable-detail", args=[sensitive.pk])).status_code, 404)


class MovementAndRecurrenceTests(P0PaymentsBaseTestCase):
    def test_partial_payments_refund_and_void_keep_the_full_history(self):
        payable = self.make_payable(amount=Decimal("120.00"))
        attach_source_document(
            actor=self.manager,
            payable=payable,
            upload=self.pdf_upload("sustento.pdf"),
        )
        first = record_payment(
            actor=self.manager,
            payable_id=payable.pk,
            amount=Decimal("40.00"),
            paid_on=date(2026, 10, 15),
            operation_reference="ABONO-1",
            receipt_upload=self.pdf_upload("abono-1.pdf"),
            allow_partial=True,
        )
        payable.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.PARTIAL)
        self.assertEqual(payable.balance_due, Decimal("80.00"))
        with self.assertRaisesMessage(ValidationError, "superar"):
            record_payment(
                actor=self.manager,
                payable_id=payable.pk,
                amount=Decimal("80.01"),
                paid_on=date(2026, 10, 15),
                operation_reference="EXCESO",
                receipt_upload=self.pdf_upload("exceso.pdf"),
                allow_partial=True,
            )
        second = record_payment(
            actor=self.manager,
            payable_id=payable.pk,
            amount=Decimal("80.00"),
            paid_on=date(2026, 10, 16),
            operation_reference="ABONO-2",
            receipt_upload=self.pdf_upload("abono-2.pdf"),
            allow_partial=True,
        )
        payable.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.PAID)
        self.assertEqual(payable.payment_movements.count(), 2)
        self.assertEqual(payable.balance_due, Decimal("0.00"))

        refund = record_balance_movement(
            actor=self.manager,
            payable_id=payable.pk,
            kind=Payment.Kind.REFUND,
            amount=Decimal("120.00"),
            movement_on=date(2026, 10, 17),
            reason="El acreedor devolvió el cobro.",
        )
        payable.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.PENDING)
        self.assertEqual(payable.balance_due, Decimal("120.00"))
        void_payment_movement(actor=self.manager, movement_id=refund.pk, reason="Registro duplicado")
        payable.refresh_from_db()
        refund.refresh_from_db()
        self.assertEqual(payable.status, Payable.Status.PAID)
        self.assertTrue(refund.is_void)
        self.assertEqual(Payment.objects.filter(pk__in=(first.pk, second.pk, refund.pk)).count(), 3)

    def test_weekly_generation_is_idempotent_and_month_end_is_clamped(self):
        personal = PaymentContext.objects.create(
            name="Personal del gerente",
            kind=PaymentContext.Kind.PERSONAL,
            assistant_access=True,
            created_by=self.manager,
            updated_by=self.manager,
        )
        start = date(2026, 1, 31)
        commitment = create_commitment(
            actor=self.manager,
            commitment=PaymentCommitment(
                context=personal,
                name="Apoyo semanal",
                category=PaymentCommitment.Category.FAMILY_SUPPORT,
                creditor=self.creditor,
                frequency=PaymentCommitment.Frequency.WEEKLY,
                start_date=start,
                next_occurrence=start,
                amount_mode=PaymentCommitment.AmountMode.FIXED,
                fixed_amount=Decimal("50.00"),
            ),
        )
        created, _ = generate_scheduled_payables(
            actor=self.manager,
            through=start + timedelta(days=14),
        )
        self.assertEqual(len(created), 3)
        again, _ = generate_scheduled_payables(
            actor=self.manager,
            through=start + timedelta(days=14),
        )
        self.assertEqual(len(again), 0)
        self.assertEqual(Payable.objects.filter(commitment=commitment).count(), 3)

        commitment.frequency = PaymentCommitment.Frequency.MONTHLY
        commitment.interval_count = 1
        self.assertEqual(next_recurrence_date(commitment, start), date(2026, 2, 28))

    def test_manager_can_pause_and_skip_a_future_occurrence(self):
        commitment = create_commitment(
            actor=self.manager,
            commitment=PaymentCommitment(
                context=self.company.payment_context,
                company=self.company,
                branch=self.branch,
                name="Cuota mensual flexible",
                category=PaymentCommitment.Category.LOAN,
                details={"loan_contract": "PRESTAMO-001"},
                creditor=self.creditor,
                frequency=PaymentCommitment.Frequency.MONTHLY,
                start_date=date(2026, 10, 31),
                next_occurrence=date(2026, 10, 31),
                usual_due_day=31,
                amount_mode=PaymentCommitment.AmountMode.FIXED,
                fixed_amount=Decimal("200.00"),
            ),
        )
        skip_next_occurrence(
            actor=self.manager,
            commitment_id=commitment.pk,
            reason="El banco otorgó un mes de gracia.",
        )
        commitment.refresh_from_db()
        self.assertEqual(commitment.next_occurrence, date(2026, 11, 30))
        set_commitment_paused(actor=self.manager, commitment_id=commitment.pk, paused=True)
        created, _ = generate_scheduled_payables(actor=self.manager, through=date(2027, 1, 31))
        self.assertEqual(created, [])
        self.assertFalse(Payable.objects.filter(commitment=commitment).exists())


class ExperimentalUiAndImportTests(P0PaymentsBaseTestCase):
    def test_new_customer_pages_render_for_their_authorized_roles(self):
        self.client.force_login(self.manager)
        for name in (
            "payment-contexts",
            "payment-funding-sources",
            "payment-calendar",
            "payment-payable-import",
        ):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

        self.client.force_login(self.assistant)
        self.assertEqual(self.client.get(reverse("payment-calendar")).status_code, 200)
        self.assertEqual(self.client.get(reverse("payment-contexts")).status_code, 403)
        self.assertEqual(self.client.get(reverse("payment-payable-import")).status_code, 403)

    def test_import_reviews_then_confirms_as_one_batch(self):
        self.client.force_login(self.manager)
        before = Payable.objects.count()
        upload = SimpleUploadedFile(
            "obligaciones.csv",
            (
                "ámbito,categoría,concepto,acreedor,monto,moneda,vencimiento,naturaleza,sensible\n"
                f"{self.company.payment_context.name},Proveedor,Compra eventual,{self.creditor.name},75.50,PEN,2026-10-29,Propio,No\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse("payment-payable-import"), {"workbook": upload})
        self.assertEqual(response.status_code, 302)
        batch = PayableImportBatch.objects.latest("pk")
        self.assertEqual(batch.status, PayableImportBatch.Status.PREVIEW)
        self.assertEqual(Payable.objects.count(), before)
        preview = self.client.get(f"{reverse('payment-payable-import')}?batch={batch.pk}")
        self.assertContains(preview, "Proveedor")
        self.assertNotContains(preview, ">SUPPLIER<")

        confirmed = self.client.post(reverse("payment-payable-import-confirm", args=[batch.pk]))
        self.assertRedirects(confirmed, reverse("payments-board"))
        batch.refresh_from_db()
        self.assertEqual(batch.status, PayableImportBatch.Status.CONFIRMED)
        self.assertEqual(Payable.objects.count(), before + 1)

        self.client.post(reverse("payment-payable-import-confirm", args=[batch.pk]))
        batch.refresh_from_db()
        self.assertEqual(batch.status, PayableImportBatch.Status.CONFIRMED)
        self.assertEqual(Payable.objects.count(), before + 1)

    def test_import_with_unknown_scope_creates_nothing(self):
        self.client.force_login(self.manager)
        before = Payable.objects.count()
        upload = SimpleUploadedFile(
            "invalido.csv",
            (
                "ámbito,categoría,concepto,acreedor,monto,moneda,vencimiento\n"
                f"Ámbito inexistente,Servicio,Luz ajena,{self.creditor.name},80,PEN,2026-10-30\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )
        self.client.post(reverse("payment-payable-import"), {"workbook": upload})
        batch = PayableImportBatch.objects.latest("pk")
        self.assertEqual(batch.status, PayableImportBatch.Status.REJECTED)
        self.client.post(reverse("payment-payable-import-confirm", args=[batch.pk]))
        self.assertEqual(Payable.objects.count(), before)
