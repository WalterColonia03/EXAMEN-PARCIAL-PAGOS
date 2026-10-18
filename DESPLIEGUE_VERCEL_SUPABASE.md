# Despliegue y operación: Vercel + Supabase

## Estado confirmado

- PostgreSQL usa el Transaction Pooler de Supabase mediante TLS.
- RLS está activo en las 27 tablas de `public`; `anon` y `authenticated` no tienen permisos directos.
- El bucket `pagocontrol-private` es privado y se accede mediante autorización de Django y URL firmada.
- Están aplicadas `payments.0011_lock_down_supabase_data_api`, `identity.0003_email_password_recovery` e `identity.0004_assistant_account_onboarding`. La liberación de este cambio debe aplicar además `identity.0006_revoke_external_recovery_codes`.
- La entrega real de TurboSMTP se comprobó desde el entorno controlado. El sitio publicado no usará esta integración hasta recibir el código por GitHub/Vercel y sus variables de entorno.

No use Supabase Auth ni Data API desde el navegador: esta aplicación usa Django para autenticar y autorizar.

## Variables de Vercel

Registre valores reales exclusivamente en Vercel; `.env.example` no contiene secretos y `.env` no se versiona.

| Variable | Requisito |
| --- | --- |
| `DJANGO_DEBUG` | `0` en Production. |
| `DJANGO_SECRET_KEY` | Valor aleatorio y exclusivo de Production. |
| `DJANGO_ALLOWED_HOSTS` | Dominio de producción y dominio Vercel si corresponde. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS completos separados por coma. |
| `DATABASE_URL` | URI TLS del Transaction Pooler de Supabase. |
| `SUPABASE_STORAGE_BUCKET` | `pagocontrol-private`. |
| `SUPABASE_S3_ENDPOINT_URL` | Endpoint S3 del proyecto. |
| `SUPABASE_S3_REGION` | Región S3 del proyecto. |
| `SUPABASE_S3_ACCESS_KEY_ID` | Credencial S3 exclusiva del servidor. |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | Secreto S3 exclusivo del servidor. |
| `SUPABASE_SIGNED_URL_TTL` | `60` salvo necesidad justificada. |
| `DJANGO_EMAIL_BACKEND` | `identity.email_backends.TurboSMTPEmailBackend`. |
| `TURBOSMTP_API_URL` | `https://api.turbo-smtp.com/api/v2/mail/send` o el endpoint EU asignado por el proveedor. |
| `TURBOSMTP_CONSUMER_KEY` | Consumer Key de TurboSMTP. |
| `TURBOSMTP_CONSUMER_SECRET` | Consumer Secret de TurboSMTP. |
| `TURBOSMTP_TIMEOUT` | `10` segundos salvo necesidad justificada. |
| `DJANGO_DEFAULT_FROM_EMAIL` | Dirección remitente autorizada por TurboSMTP. |

El remitente debe ser una dirección autorizada por TurboSMTP. La contraseña personal del buzón no se utiliza ni se almacena en PagoControl.

## Liberación

1. Configure las variables anteriores en Vercel Production.
2. Ejecute, en una base de pruebas aislada:

   ```powershell
   python manage.py test identity payments.test_ui_experience
   python manage.py check --deploy
   python manage.py migrate --plan
   ```

3. Confirme que `migrate --plan` no propone cambios inesperados. Las migraciones no se ejecutan durante el build de Vercel.
4. Revise el diff, cree el commit y haga `push` a la rama conectada con Vercel.
5. Compruebe el despliegue y los logs, sin registrar códigos, contraseñas ni secretos.

## Activación inicial y asistentes

Con una base sin gerentes activos o después de retirar las cuentas de prueba, ejecute una sola vez:

```powershell
python manage.py provision_initial_manager --email gerente@dominio.com --display-name "Nombre del gerente"
```

El gerente recibe un código de recuperación de un solo uso en su correo. En **Recuperar acceso** define su propia contraseña y queda con el correo verificado. Después inicia sesión, abre **Equipo de asistentes**, crea la cuenta del asistente y entrega su contraseña temporal solo por un canal privado.

El asistente debe recibir el código en su correo, iniciar sesión con la contraseña temporal, verificar su buzón y definir una contraseña personal. Una cuenta no verificada no puede acceder a pagos. Verifique también que desactivar cierre sus sesiones, revoque sus códigos y que reactivar una cuenta pendiente envíe un código nuevo. La recuperación de contraseña solo admite códigos recibidos por correo; no distribuya códigos de respaldo ni temporales.

## Reversión

Si debe revertirse la aplicación, revierta solamente código a una revisión comprobada. No elimine ni revierta a ciegas migraciones, RLS, cuentas o archivos del bucket: evalúe antes el impacto y mantenga una copia recuperable.
