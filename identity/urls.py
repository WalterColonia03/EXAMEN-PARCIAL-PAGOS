from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("recuperar-acceso/", views.recover_access, name="access-recovery"),
    path(
        "recuperar-acceso/completado/",
        views.recovery_complete,
        name="access-recovery-complete",
    ),
    path("mi-acceso/", views.access_security, name="access-security"),
    path(
        "mi-acceso/codigos/",
        views.generate_emergency_codes,
        name="access-generate-emergency-codes",
    ),
    path(
        "mi-acceso/asistente/codigo/",
        views.generate_assistant_temporary_code,
        name="access-generate-assistant-code",
    ),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("cambiar-rol/<str:role_code>/", views.switch_role, name="switch-role"),
]
