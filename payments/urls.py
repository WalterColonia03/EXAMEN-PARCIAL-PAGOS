from django.urls import path

from . import views

urlpatterns = [
    path("", views.board, name="payments-board"),
    path("obligaciones/nueva/", views.payable_create, name="payment-payable-create"),
    path("obligaciones/<int:payable_id>/", views.payable_detail, name="payment-payable-detail"),
    path("obligaciones/<int:payable_id>/documento/", views.source_document_upload, name="payment-source-document"),
    path("obligaciones/<int:payable_id>/pago/", views.payment_record, name="payment-record"),
    path("obligaciones/<int:payable_id>/suspension/", views.payable_suspension, name="payment-suspension"),
    path("compromisos/nuevo/", views.commitment_create, name="payment-commitment-create"),
    path("compromisos/<int:commitment_id>/estado/", views.commitment_toggle, name="payment-commitment-toggle"),
    path("compromisos/generar/", views.monthly_generation, name="payment-monthly-generation"),
    path("historial/", views.payment_history, name="payment-history"),
    path("gerencia/", views.manager_dashboard, name="payment-manager-dashboard"),
    path("cuentas-destino/", views.destination_accounts, name="payment-destination-accounts"),
    path("cuentas-destino/<int:account_id>/", views.destination_account_edit, name="payment-destination-account-edit"),
    path("documentos/<int:attachment_id>/descargar/", views.attachment_download, name="payment-attachment-download"),
]
