from django.db import migrations


def backfill_business_contexts(apps, schema_editor):
    Company = apps.get_model("payments", "Company")
    PaymentContext = apps.get_model("payments", "PaymentContext")
    ServiceAccount = apps.get_model("payments", "ServiceAccount")
    PaymentCommitment = apps.get_model("payments", "PaymentCommitment")
    Payable = apps.get_model("payments", "Payable")

    for company in Company.objects.all().iterator():
        context, _ = PaymentContext.objects.get_or_create(
            company_id=company.pk,
            defaults={
                "name": company.name,
                "kind": "BUSINESS",
                "assistant_access": True,
                "is_active": company.is_active,
            },
        )
        ServiceAccount.objects.filter(company_id=company.pk, context__isnull=True).update(context_id=context.pk)
        PaymentCommitment.objects.filter(company_id=company.pk, context__isnull=True).update(context_id=context.pk)
        Payable.objects.filter(company_id=company.pk, context__isnull=True).update(context_id=context.pk)


class Migration(migrations.Migration):
    dependencies = [("payments", "0005_fundingsource_internalreminder_payableimportbatch_and_more")]

    operations = [
        migrations.RunPython(backfill_business_contexts, reverse_code=migrations.RunPython.noop),
    ]
