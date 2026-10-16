from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook

from .models import ServiceAccount
from .services import attach_source_document
from .test_p0_regressions import P0PaymentsBaseTestCase


class FilePreviewAndClientCopyTests(P0PaymentsBaseTestCase):
    @staticmethod
    def xlsx_upload():
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(
            [
                "empresa",
                "local",
                "acreedor",
                "tipo de servicio",
                "tipo de identificador",
                "identificador principal",
                "titular",
                "frecuencia",
                "día habitual",
                "canal",
                "estado",
                "identificadores adicionales",
            ]
        )
        worksheet.append(
            [
                "Empresa Central",
                "Sede Principal",
                "Proveedor de ejemplo",
                "Electricidad",
                "Suministro",
                "12345678",
                "Titular de la cuenta",
                "Mensual",
                15,
                "Manual",
                "Activa",
                "Número de medidor: 98765",
            ]
        )
        content = BytesIO()
        workbook.save(content)
        workbook.close()
        return SimpleUploadedFile(
            "cuentas.xlsx",
            content.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_saved_document_preview_is_private_and_served_inline(self):
        payable = self.make_payable()
        attachment = attach_source_document(
            actor=self.assistant,
            payable=payable,
            upload=self.pdf_upload("recibo-octubre.pdf"),
        )

        self.client.force_login(self.assistant)
        preview = self.client.get(reverse("payment-attachment-preview", args=[attachment.pk]))

        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview["Content-Type"], "application/pdf")
        self.assertIn("inline", preview["Content-Disposition"])
        self.assertIn("no-store", preview["Cache-Control"])
        self.assertEqual(preview["X-Frame-Options"], "SAMEORIGIN")
        preview.close()

        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("payment-attachment-preview", args=[attachment.pk])).status_code,
            302,
        )

    def test_upload_interfaces_offer_preview_and_use_customer_copy(self):
        payable = self.make_payable()
        self.client.force_login(self.manager)

        detail = self.client.get(reverse("payment-payable-detail", args=[payable.pk]))
        self.assertContains(detail, 'data-file-policy="payment-document"')
        self.assertContains(detail, "Vista previa del archivo seleccionado")
        self.assertNotContains(detail, "Congelada durante la migración")
        self.assertNotContains(detail, "trazabilidad")

        accounts = self.client.get(reverse("payment-service-accounts"))
        self.assertContains(accounts, "data-file-input-group")
        self.assertContains(accounts, "Cargar cuentas desde un archivo")
        self.assertContains(accounts, "Encuentra cada servicio por su suministro o contrato")
        self.assertNotContains(accounts, "Cada servicio, una sola cuenta trazable")
        self.assertNotContains(accounts, "Etapa 1")
        self.assertNotContains(accounts, "demostración")

        payable_create = self.client.get(reverse("payment-payable-create"))
        self.assertContains(
            payable_create,
            "Registra una obligación puntual, identifica a quién corresponde, a quién se paga y cuándo debe atenderse.",
        )
        self.assertNotContains(payable_create, "empresa, local y proveedor")
        self.assertNotContains(payable_create, "Registra un gasto puntual sin perder la trazabilidad")

        destinations = self.client.get(reverse("payment-destination-accounts"))
        self.assertNotContains(destinations, "demostración")
        self.assertNotContains(destinations, "DEMO-")

        template = self.client.get(reverse("payment-service-account-import-template"))
        self.assertEqual(template.status_code, 200)
        self.assertNotIn("Demo", template.content.decode("utf-8-sig"))

        self.client.force_login(self.assistant)
        assistant_board = self.client.get(reverse("payments-board"))
        assistant_detail = self.client.get(reverse("payment-payable-detail", args=[payable.pk]))
        for response in (assistant_board, assistant_detail):
            self.assertNotContains(response, "planificación")
            self.assertNotContains(response, "demostración")
            self.assertNotContains(response, "trazabilidad")

    def test_xlsx_preview_shows_rows_without_importing_them(self):
        self.client.force_login(self.manager)
        original_count = ServiceAccount.objects.count()

        response = self.client.post(
            reverse("payment-service-account-import-preview"),
            {"workbook": self.xlsx_upload()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["rows"][0][0], "Empresa Central")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(ServiceAccount.objects.count(), original_count)

        self.client.force_login(self.assistant)
        forbidden = self.client.post(
            reverse("payment-service-account-import-preview"),
            {"workbook": self.xlsx_upload()},
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_sidebar_places_queue_before_follow_up_and_configuration(self):
        self.client.force_login(self.manager)
        content = self.client.get(reverse("payments-board")).content.decode()

        positions = [
            content.index('id="nav-board"'),
            content.index('id="nav-history"'),
            content.index('id="nav-manager"'),
            content.index('id="nav-payable-create"'),
            content.index('id="nav-commitment-create"'),
            content.index('id="nav-service-accounts"'),
            content.index('id="nav-accounts"'),
            content.index('id="nav-funding-sources"'),
            content.index('id="nav-contexts"'),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_progressive_configuration_uses_customer_labels(self):
        self.client.force_login(self.manager)

        contexts = self.client.get(reverse("payment-contexts"))
        self.assertContains(contexts, "Nombre del ámbito")
        self.assertContains(contexts, "Tipo de ámbito")
        self.assertContains(contexts, 'id="context-company-field"')
        self.assertContains(contexts, "kind.value === 'BUSINESS'")

        sources = self.client.get(reverse("payment-funding-sources"))
        self.assertContains(sources, "Nombre de la fuente")
        self.assertContains(sources, "Banco o institución")
        self.assertContains(sources, "Visible para el asistente")
        self.assertContains(sources, "data-source-detail")

    def test_assistant_only_sees_actions_available_to_the_role(self):
        self.client.force_login(self.assistant)
        accounts = self.client.get(reverse("payment-service-accounts"))

        self.assertNotContains(accounts, "Descargar plantilla")
        self.assertNotContains(accounts, "Cargar cuentas desde un archivo")
        self.assertNotContains(accounts, "Crear primera cuenta")
        self.assertContains(accounts, "Solo lectura")
