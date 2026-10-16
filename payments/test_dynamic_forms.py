from datetime import date
from decimal import Decimal

from django.urls import reverse

from payments.forms import (
    FundingSourceForm,
    PayableForm,
    PayableReviewStatusForm,
    PaymentCommitmentForm,
    PaymentContextForm,
    ServiceAccountForm,
)
from payments.models import FundingSource, Payable, PaymentCommitment, PaymentContext, ServiceAccount
from payments.test_p0_regressions import P0PaymentsBaseTestCase


class DynamicFormNormalizationTests(P0PaymentsBaseTestCase):
    def test_on_demand_personal_service_discards_business_only_values(self):
        personal = PaymentContext.objects.create(
            name="Casa personal",
            kind=PaymentContext.Kind.PERSONAL,
            assistant_access=True,
            created_by=self.manager,
            updated_by=self.manager,
        )
        form = ServiceAccountForm(
            data={
                "context": personal.pk,
                "company": self.company.pk,
                "branch": self.branch.pk,
                "creditor": self.creditor.pk,
                "service_type": ServiceAccount.ServiceType.ELECTRICITY,
                "identifier_type": ServiceAccount.IdentifierType.SUPPLY,
                "primary_identifier": "CASA-001",
                "expected_billing_frequency": ServiceAccount.BillingFrequency.ON_DEMAND,
                "usual_billing_day": 15,
                "acquisition_channel": ServiceAccount.AcquisitionChannel.MANUAL,
                "status": ServiceAccount.Status.ACTIVE,
            },
            actor=self.manager,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        account = form.save(commit=False)
        self.assertIsNone(account.company)
        self.assertIsNone(account.branch)
        self.assertIsNone(account.usual_billing_day)

    def test_context_form_discards_company_and_requires_third_party_beneficiary(self):
        personal = PaymentContextForm(
            data={
                "name": "Personal alterno",
                "kind": PaymentContext.Kind.PERSONAL,
                "company": self.company.pk,
                "is_active": "on",
            }
        )
        self.assertTrue(personal.is_valid(), personal.errors.as_json())
        self.assertIsNone(personal.save(commit=False).company)

        third_party = PaymentContextForm(
            data={
                "name": "Apoyo externo",
                "kind": PaymentContext.Kind.THIRD_PARTY,
                "is_active": "on",
            }
        )
        self.assertFalse(third_party.is_valid())
        self.assertIn("default_beneficiary_name", third_party.errors)

    def test_cash_source_discards_bank_details_from_an_edited_source(self):
        source = FundingSource.objects.create(
            context=self.company.payment_context,
            name="Cuenta principal",
            kind=FundingSource.Kind.ACCOUNT,
            institution="Banco anterior",
            account_holder="Titular anterior",
            identifier="001-002-003",
            currency=FundingSource.Currency.PEN,
            created_by=self.manager,
            updated_by=self.manager,
        )
        form = FundingSourceForm(
            data={
                "context": self.company.payment_context.pk,
                "name": source.name,
                "kind": FundingSource.Kind.CASH,
                "institution": "No debe persistir",
                "account_holder": "No debe persistir",
                "identifier": "9999",
                "currency": FundingSource.Currency.PEN,
                "assistant_visible": "on",
                "is_active": "on",
            },
            instance=source,
            actor=self.manager,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        source = form.save(commit=False)
        self.assertEqual((source.institution, source.account_holder, source.identifier), ("", "", ""))

    def test_one_time_variable_commitment_discards_recurrence_amount_and_service_values(self):
        commitment = PaymentCommitment.objects.create(
            context=self.company.payment_context,
            company=self.company,
            branch=self.branch,
            name="Servicio anterior",
            category=PaymentCommitment.Category.SERVICE,
            creditor=self.creditor,
            service_account=self.service_account,
            frequency=PaymentCommitment.Frequency.MONTHLY,
            start_date=date(2026, 10, 1),
            next_occurrence=date(2026, 11, 1),
            end_date=date(2027, 10, 1),
            usual_due_day=15,
            amount_mode=PaymentCommitment.AmountMode.FIXED,
            fixed_amount=Decimal("120.00"),
            currency=FundingSource.Currency.PEN,
            created_by=self.manager,
        )
        form = PaymentCommitmentForm(
            data={
                "context": self.company.payment_context.pk,
                "name": "Compra eventual",
                "category": PaymentCommitment.Category.SUPPLIER,
                "company": self.company.pk,
                "branch": self.branch.pk,
                "creditor": self.creditor.pk,
                "service_account": self.service_account.pk,
                "payment_nature": PaymentCommitment.Nature.OWN,
                "frequency": PaymentCommitment.Frequency.ONE_TIME,
                "interval_count": 8,
                "interval_unit": PaymentCommitment.IntervalUnit.DAYS,
                "start_date": "2026-10-20",
                "end_date": "2026-12-20",
                "usual_due_day": 20,
                "amount_mode": PaymentCommitment.AmountMode.VARIABLE,
                "fixed_amount": "999.00",
                "currency": FundingSource.Currency.PEN,
            },
            instance=commitment,
            actor=self.manager,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        commitment = form.save(commit=False)
        self.assertEqual(commitment.interval_count, 1)
        self.assertEqual(commitment.interval_unit, "")
        self.assertIsNone(commitment.start_date)
        self.assertIsNone(commitment.end_date)
        self.assertIsNone(commitment.next_occurrence)
        self.assertIsNone(commitment.usual_due_day)
        self.assertIsNone(commitment.fixed_amount)
        self.assertIsNone(commitment.service_account)

    def test_custom_commitment_reports_only_the_missing_dynamic_requirements(self):
        form = PaymentCommitmentForm(
            data={
                "context": self.company.payment_context.pk,
                "name": "Compromiso personalizado",
                "category": PaymentCommitment.Category.SUPPLIER,
                "creditor": self.creditor.pk,
                "payment_nature": PaymentCommitment.Nature.OWN,
                "frequency": PaymentCommitment.Frequency.CUSTOM,
                "amount_mode": PaymentCommitment.AmountMode.FIXED,
                "fixed_amount": "80.00",
                "currency": FundingSource.Currency.PEN,
            },
            actor=self.manager,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("interval_count", form.errors)
        self.assertIn("interval_unit", form.errors)
        self.assertIn("start_date", form.errors)

    def test_payable_uses_contextual_amount_and_discards_stale_service_account(self):
        card = PayableForm(
            data={
                "context": self.company.payment_context.pk,
                "concept": "Estado de tarjeta",
                "category": PaymentCommitment.Category.CREDIT_CARD,
                "creditor": self.creditor.pk,
                "payment_nature": PaymentCommitment.Nature.OWN,
                "currency": FundingSource.Currency.PEN,
                "due_date": "2026-10-28",
                "card_issuer": "Banco",
                "card_last_four": "1234",
                "card_statement_total": "900.00",
                "card_minimum_payment": "90.00",
            },
            actor=self.manager,
        )
        self.assertTrue(card.is_valid(), card.errors.as_json())
        self.assertEqual(card.save(commit=False).amount, Decimal("900.00"))

        supplier_data = {
            "context": self.company.payment_context.pk,
            "concept": "Compra eventual",
            "category": PaymentCommitment.Category.SUPPLIER,
            "creditor": self.creditor.pk,
            "service_account": self.service_account.pk,
            "payment_nature": PaymentCommitment.Nature.OWN,
            "currency": FundingSource.Currency.PEN,
            "due_date": "2026-10-29",
        }
        missing_amount = PayableForm(data=supplier_data, actor=self.manager)
        self.assertFalse(missing_amount.is_valid())
        self.assertIn("amount", missing_amount.errors)

        no_category = PayableForm(
            data={
                "context": self.company.payment_context.pk,
                "concept": "Sin categoría todavía",
                "creditor": self.creditor.pk,
                "currency": FundingSource.Currency.PEN,
                "due_date": "2026-10-29",
            },
            actor=self.manager,
        )
        self.assertFalse(no_category.is_valid())
        self.assertIn("category", no_category.errors)
        self.assertNotIn("amount", no_category.errors)

        incomplete = PayableForm(data={**supplier_data, "is_incomplete": "on"}, actor=self.manager)
        self.assertTrue(incomplete.is_valid(), incomplete.errors.as_json())
        self.assertIsNone(incomplete.save(commit=False).service_account)

    def test_review_status_only_requires_a_reason_for_dispute_or_cancellation(self):
        for status in (Payable.Status.DISPUTED, Payable.Status.CANCELLED):
            form = PayableReviewStatusForm(data={"status": status, "note": ""})
            self.assertFalse(form.is_valid())
            self.assertIn("note", form.errors)

        reactivation = PayableReviewStatusForm(data={"status": Payable.Status.PENDING, "note": ""})
        self.assertTrue(reactivation.is_valid(), reactivation.errors.as_json())

    def test_assistant_commitment_form_excludes_private_service_accounts(self):
        private_context = PaymentContext.objects.create(
            name="Ámbito privado",
            kind=PaymentContext.Kind.PERSONAL,
            assistant_access=False,
            created_by=self.manager,
            updated_by=self.manager,
        )
        private_account = ServiceAccount.objects.create(
            context=private_context,
            creditor=self.creditor,
            service_type=ServiceAccount.ServiceType.ELECTRICITY,
            identifier_type=ServiceAccount.IdentifierType.SUPPLY,
            primary_identifier="PRIVADO-001",
            created_by=self.manager,
            updated_by=self.manager,
        )

        form = PaymentCommitmentForm(actor=self.assistant)
        self.assertNotIn(private_account, form.fields["service_account"].queryset)


class DynamicFormRenderingTests(P0PaymentsBaseTestCase):
    def test_customer_forms_expose_progressive_regions_and_disabled_semantics(self):
        payable = self.make_payable()
        self.client.force_login(self.manager)

        payable_form = self.client.get(reverse("payment-payable-create"))
        self.assertContains(payable_form, 'id="payable-amount-field"')
        self.assertContains(payable_form, "ui.setRegionVisible(amountField")
        self.assertContains(payable_form, "ui.setRequired(")

        commitment_form = self.client.get(reverse("payment-commitment-create"))
        self.assertContains(commitment_form, 'id="commitment-fixed-amount-field"')
        self.assertContains(commitment_form, 'id="commitment-interval-unit-field"')
        self.assertContains(commitment_form, "updateAmountMode")

        service_form = self.client.get(reverse("payment-service-account-create"))
        self.assertContains(service_form, 'id="service-billing-day-field"')

        sources = self.client.get(reverse("payment-funding-sources"))
        self.assertContains(sources, "data-source-detail")

        detail = self.client.get(reverse("payment-payable-detail", args=[payable.pk]))
        self.assertContains(detail, 'id="review-note-field"')

        content = payable_form.content.decode()
        self.assertIn("region.hidden = !visible", content)
        self.assertIn("control.disabled = true", content)
