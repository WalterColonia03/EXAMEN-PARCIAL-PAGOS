from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path(
        "recuperar-acceso/correo/",
        views.request_email_recovery,
        name="access-recovery-email",
    ),
    path(
        "recuperar-acceso/correo-enviado/",
        views.recovery_email_sent,
        name="access-recovery-email-sent",
    ),
    path("recuperar-acceso/", views.recover_access, name="access-recovery"),
    path(
        "recuperar-acceso/completado/",
        views.recovery_complete,
        name="access-recovery-complete",
    ),
    path("mi-acceso/", views.access_security, name="access-security"),
    path(
        "activar-cuenta/",
        views.account_onboarding,
        name="account-onboarding",
    ),
    path("mi-acceso/contrasena/", views.change_password, name="access-change-password"),
    path(
        "gestion-asistentes/",
        views.manager_assistant_accounts,
        name="manager-assistant-accounts",
    ),
    path(
        "gestion-asistentes/<uuid:account_id>/verificacion/",
        views.resend_assistant_account_verification,
        name="manager-assistant-verification-resend",
    ),
    path(
        "gestion-asistentes/<uuid:account_id>/desactivar/",
        views.set_managed_assistant_active,
        {"active": False},
        name="manager-assistant-deactivate",
    ),
    path(
        "gestion-asistentes/<uuid:account_id>/reactivar/",
        views.set_managed_assistant_active,
        {"active": True},
        name="manager-assistant-reactivate",
    ),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("cambiar-rol/<str:role_code>/", views.switch_role, name="switch-role"),
]
