# PagoControl

Sistema Django para controlar obligaciones y pagos, con acceso por roles de Gerente y Asistente.

## Estado actual

- Supabase está protegido con RLS en las 27 tablas públicas y sin acceso directo para `anon` ni `authenticated`.
- Las migraciones `payments.0011_lock_down_supabase_data_api`, `identity.0003_email_password_recovery` e `identity.0004_assistant_account_onboarding` están aplicadas en Supabase. Antes de publicar este cambio se debe aplicar `identity.0006_revoke_external_recovery_codes`.
- La aplicación tiene recuperación de contraseña por código de correo, cambio de contraseña y panel **Equipo de asistentes** para el Gerente.
- TurboSMTP API v2 está integrado como proveedor transaccional y una prueba real de entrega fue aceptada por el proveedor.
- La revisión permanece local hasta confirmarla, subirla a GitHub y dejar configuradas las mismas variables en Vercel.

## Acceso y cuentas

- El correo es el identificador de inicio de sesión y se normaliza sin distinguir mayúsculas/minúsculas.
- Las altas de asistentes rechazan direcciones locales, reservadas y de prueba. La cuenta no queda operativa hasta demostrar control del buzón con un código de ocho dígitos que vence en 15 minutos.
- El Gerente crea al Asistente, le comunica la contraseña temporal por un canal privado y puede reenviar la verificación, desactivar o reactivar la cuenta. Desactivar revoca códigos pendientes y cierra sus sesiones.
- La recuperación de contraseña nunca revela si el correo existe. Solo acepta códigos numéricos enviados al correo registrado; los códigos de respaldo o temporales entregados fuera del sistema no están disponibles y los existentes se revocan con la migración.
- Los códigos enviados por correo se guardan únicamente como resúmenes criptográficos, vencen en 15 minutos y se consumen una sola vez.

Las cuatro cuentas históricas con direcciones de prueba/no entregables (dos Gerentes y dos Asistentes) están desactivadas, con sus sesiones revocadas y registro de auditoría. El nuevo gerente fue aprovisionado y queda pendiente de canjear su código para marcar su correo como verificado. No hay asistentes activos hasta que el gerente activado cree y verifique los nuevos desde su panel.

## Publicación

1. Configure en Vercel las variables TurboSMTP de `.env.example`, con un remitente autorizado por el proveedor.
2. Ejecute las pruebas, revise el diff, confirme los cambios y haga `push` a la rama conectada con Vercel.
3. Confirme el despliegue, active el gerente y pruebe recuperación de contraseña, activación de un asistente y desactivación/reactivación.

Un gerente inicial se aprovisiona sin pasar contraseñas en la terminal:

```powershell
python manage.py provision_initial_manager --email gerente@dominio.com --display-name "Nombre del gerente"
```

El comando envía un código de activación al correo del gerente. Este lo canjea en **Recuperar acceso** para definir personalmente su contraseña; el Gerente ya activado crea luego los asistentes desde el panel.

Nunca añada a Git, documentos, capturas o el navegador contraseñas, claves de TurboSMTP, cadenas de conexión, claves S3 ni `DJANGO_SECRET_KEY`.

## Desarrollo local

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

La guía de producción está en [DESPLIEGUE_VERCEL_SUPABASE.md](DESPLIEGUE_VERCEL_SUPABASE.md). La planificación vigente está en [planificacion_scrum](planificacion_scrum/00_ESTADO_VIGENTE.md).
