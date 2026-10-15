from __future__ import annotations

import os
import sys
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.core.files.base import ContentFile
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
)


DEMO_PASSWORD = "DemoPagos2026!"
MANAGER_EMAIL = "gerente.demo@pagos.invalid"
ASSISTANT_EMAIL = "asistente.demo@pagos.invalid"


def ensure_demo_account(*, email, legacy_email, password, display_name, role, is_staff=False):
    """Create or upgrade a demo account without breaking existing relations."""
    account = Account.objects.filter(email=email).first()
    if account is None:
        account = Account.objects.filter(email=legacy_email).first()

    if account is None:
        account = Account.objects.create_user(
            email=email,
            password=password,
            display_name=display_name,
            role=role,
            is_staff=is_staff,
        )
        created = True
    else:
        account.email = email
        account.display_name = display_name
        account.role = role
        account.is_staff = is_staff
        account.is_active = True
        account.set_password(password)
        account.save()
        created = False

    return account, created


def run():
    print("Iniciando sembrado de datos de prueba...")

    # 1. Roles
    role_admin, _ = Role.objects.get_or_create(code=Role.Code.ADMIN, defaults={"name": "Administrador"})
    role_manager, _ = Role.objects.get_or_create(code=Role.Code.MANAGER, defaults={"name": "Gerente"})
    role_assistant, _ = Role.objects.get_or_create(code=Role.Code.ASSISTANT, defaults={"name": "Asistente"})

    # 2. Cuentas de usuario
    gerente, gerente_created = ensure_demo_account(
        email=MANAGER_EMAIL,
        legacy_email="gerente@empresa.com",
        password=DEMO_PASSWORD,
        display_name="Carlos Mendoza (Gerente)",
        role=role_manager,
        is_staff=True,
    )
    asistente, asistente_created = ensure_demo_account(
        email=ASSISTANT_EMAIL,
        legacy_email="asistente@empresa.com",
        password=DEMO_PASSWORD,
        display_name="Ana Valenzuela (Asistente)",
        role=role_assistant,
    )
    gerente_status = "creado" if gerente_created else "actualizado"
    asistente_status = "creado" if asistente_created else "actualizado"
    print(f"[OK] Usuario Gerente {gerente_status}: {MANAGER_EMAIL} / {DEMO_PASSWORD}")
    print(f"[OK] Usuario Asistente {asistente_status}: {ASSISTANT_EMAIL} / {DEMO_PASSWORD}")

    # 3. Empresa y Locales
    empresa, _ = Company.objects.get_or_create(name="Grupo Gastronómico & Retail S.A.C.")
    local_central, _ = Branch.objects.get_or_create(company=empresa, name="Sede Principal - San Isidro")
    local_miraflores, _ = Branch.objects.get_or_create(company=empresa, name="Sucursal Miraflores")

    # 4. Acreedores y Cuentas Bancarias
    c_luz, _ = Creditor.objects.get_or_create(name="Luz del Sur S.A.A.", defaults={"tax_id": "20345678901"})
    cta_luz, _ = DestinationAccount.objects.get_or_create(
        creditor=c_luz,
        account_number="193-45678901-0-22",
        defaults={
            "bank_name": "Banco de Crédito BCP",
            "account_holder": "Luz del Sur S.A.A.",
            "created_by": gerente,
        }
    )

    c_agua, _ = Creditor.objects.get_or_create(name="SEDAPAL", defaults={"tax_id": "20100152356"})
    cta_agua, _ = DestinationAccount.objects.get_or_create(
        creditor=c_agua,
        account_number="0011-0175-0100034567",
        defaults={
            "bank_name": "BBVA Continental",
            "account_holder": "Servicio de Agua Potable y Alcantarillado de Lima",
            "created_by": gerente,
        }
    )

    c_tel, _ = Creditor.objects.get_or_create(name="Telefónica del Perú S.A.A.", defaults={"tax_id": "20100017491"})
    cta_tel, _ = DestinationAccount.objects.get_or_create(
        creditor=c_tel,
        account_number="200-3001245678",
        defaults={
            "bank_name": "Interbank",
            "account_holder": "Telefónica del Perú S.A.A.",
            "created_by": gerente,
        }
    )

    c_prov, _ = Creditor.objects.get_or_create(name="Distribuidora Mayorista Alimentos S.A.C.", defaults={"tax_id": "20512345678"})
    cta_prov, _ = DestinationAccount.objects.get_or_create(
        creditor=c_prov,
        account_number="194-98765432-0-11",
        defaults={
            "bank_name": "Banco de Crédito BCP",
            "account_holder": "Distribuidora Mayorista Alimentos S.A.C.",
            "created_by": gerente,
        }
    )

    c_sunat, _ = Creditor.objects.get_or_create(name="SUNAT - Tributos Nacionales", defaults={"tax_id": "20131312955"})
    cta_sunat, _ = DestinationAccount.objects.get_or_create(
        creditor=c_sunat,
        account_number="00-000-876543",
        defaults={
            "bank_name": "Banco de la Nación",
            "account_holder": "Superintendencia Nacional de Aduanas y Administración Tributaria",
            "created_by": gerente,
        }
    )

    # 5. Compromisos de pago
    compr_luz, _ = PaymentCommitment.objects.get_or_create(
        name="Servicio Eléctrico Mensual",
        company=empresa,
        creditor=c_luz,
        defaults={
            "branch": local_central,
            "category": PaymentCommitment.Category.SERVICE,
            "frequency": PaymentCommitment.Frequency.MONTHLY,
            "amount_mode": PaymentCommitment.AmountMode.VARIABLE,
            "usual_due_day": 18,
            "destination_account": cta_luz,
            "created_by": gerente,
        }
    )

    compr_agua, _ = PaymentCommitment.objects.get_or_create(
        name="Servicio Agua Potable",
        company=empresa,
        creditor=c_agua,
        defaults={
            "branch": local_miraflores,
            "category": PaymentCommitment.Category.SERVICE,
            "frequency": PaymentCommitment.Frequency.MONTHLY,
            "amount_mode": PaymentCommitment.AmountMode.VARIABLE,
            "usual_due_day": 22,
            "destination_account": cta_agua,
            "created_by": gerente,
        }
    )

    compr_tel, _ = PaymentCommitment.objects.get_or_create(
        name="Internet Fibra Óptica 1Gbps",
        company=empresa,
        creditor=c_tel,
        defaults={
            "branch": local_central,
            "category": PaymentCommitment.Category.SERVICE,
            "frequency": PaymentCommitment.Frequency.MONTHLY,
            "amount_mode": PaymentCommitment.AmountMode.FIXED,
            "fixed_amount": Decimal("450.00"),
            "usual_due_day": 12,
            "destination_account": cta_tel,
            "created_by": gerente,
        }
    )

    today = timezone.localdate()

    # 6. Tickers / Obligaciones concretas
    # A) VENCIDO (Overdue) - Venció hace 3 días
    p_vencido, _ = Payable.objects.get_or_create(
        company=empresa,
        branch=local_central,
        creditor=c_luz,
        due_date=today - timedelta(days=3),
        defaults={
            "concept": "Luz Eléctrica San Isidro - Periodo Setiembre",
            "category": PaymentCommitment.Category.SERVICE,
            "amount": Decimal("1840.50"),
            "commitment": compr_luz,
            "destination_account": cta_luz,
            "created_by": asistente,
            "status": Payable.Status.PENDING,
        }
    )

    # B) VENCE HOY (Due Today)
    p_hoy, _ = Payable.objects.get_or_create(
        company=empresa,
        branch=local_central,
        creditor=c_prov,
        due_date=today,
        defaults={
            "concept": "Factura F001-4820 Insumos y Harinas Lote A",
            "category": PaymentCommitment.Category.SUPPLIER,
            "amount": Decimal("3450.00"),
            "destination_account": cta_prov,
            "created_by": asistente,
            "status": Payable.Status.PENDING,
        }
    )

    # C) PRÓXIMO (Due Soon) - Vence en 2 días
    p_proximo1, _ = Payable.objects.get_or_create(
        company=empresa,
        branch=local_miraflores,
        creditor=c_agua,
        due_date=today + timedelta(days=2),
        defaults={
            "concept": "Recibo SEDAPAL - Sucursal Miraflores",
            "category": PaymentCommitment.Category.SERVICE,
            "amount": Decimal("685.20"),
            "commitment": compr_agua,
            "destination_account": cta_agua,
            "created_by": asistente,
            "status": Payable.Status.PENDING,
        }
    )

    # D) PRÓXIMO (Due Soon) - Vence en 4 días
    p_proximo2, _ = Payable.objects.get_or_create(
        company=empresa,
        branch=local_central,
        creditor=c_prov,
        due_date=today + timedelta(days=4),
        defaults={
            "concept": "Factura F002-1109 Lácteos y Refrigerados",
            "category": PaymentCommitment.Category.SUPPLIER,
            "amount": Decimal("1290.00"),
            "destination_account": cta_prov,
            "created_by": asistente,
            "status": Payable.Status.PENDING,
        }
    )

    # E) FUTURO (Pending) - Vence en 14 días
    p_futuro, _ = Payable.objects.get_or_create(
        company=empresa,
        branch=local_central,
        creditor=c_sunat,
        due_date=today + timedelta(days=14),
        defaults={
            "concept": "Declaración Jurada Mensual IGV-Renta",
            "category": PaymentCommitment.Category.TAX,
            "amount": Decimal("5820.00"),
            "destination_account": cta_sunat,
            "created_by": asistente,
            "status": Payable.Status.PENDING,
        }
    )

    # F) PAGADO (Paid) con comprobante
    p_pagado = Payable.objects.filter(
        company=empresa,
        branch=local_central,
        creditor=c_tel,
        due_date=today - timedelta(days=2),
    ).first()
    if not p_pagado:
        p_pagado = Payable.objects.create(
            company=empresa,
            branch=local_central,
            creditor=c_tel,
            due_date=today - timedelta(days=2),
            concept="Internet Fibra Optica 1Gbps - Setiembre",
            category=PaymentCommitment.Category.SERVICE,
            amount=Decimal("450.00"),
            commitment=compr_tel,
            destination_account=cta_tel,
            created_by=asistente,
            status=Payable.Status.PAID,
        )

    if not hasattr(p_pagado, "payment"):
        dummy_content = b"%PDF-1.4\nConstancia de Transferencia Bancaria BCP\nOperacion 9845124\n%%EOF"
        dummy_file = ContentFile(dummy_content, name="constancia_bcp_pago_450.pdf")

        att = Attachment.objects.create(
            payable=p_pagado,
            kind=Attachment.Kind.RECEIPT,
            file=dummy_file,
            original_name="constancia_bcp_pago_450.pdf",
            content_type="application/pdf",
            size_bytes=len(dummy_content),
            uploaded_by=asistente,
        )

        Payment.objects.create(
            payable=p_pagado,
            amount=Decimal("450.00"),
            paid_on=today - timedelta(days=1),
            operation_reference="BCP-OP-9845124",
            receipt=att,
            registered_by=asistente,
        )

    print("[OK] Datos de prueba sembrados exitosamente:")
    print(f"  - 1 Gerente: {MANAGER_EMAIL} / {DEMO_PASSWORD}")
    print(f"  - 1 Asistente: {ASSISTANT_EMAIL} / {DEMO_PASSWORD}")
    print("  - Obligaciones creadas: Vencido, Vence Hoy, Proximos, Futuro y Pagado con comprobante.")

if __name__ == "__main__":
    run()
