# Despliegue de PagoControl en Vercel + Supabase

Esta guía prepara una primera publicación segura. El repositorio ya está listo
para PostgreSQL y un bucket privado de Supabase; todavía **no** se ha creado ni
modificado ningún proyecto real de Supabase o Vercel desde este repositorio.

## 1. Crear y preparar Supabase

1. Crea un proyecto nuevo en Supabase y guarda sus credenciales fuera del
   repositorio.
2. En **Storage**, crea el bucket privado `pagocontrol-private`. No lo marques
   público. Limita los archivos a PDF, JPG, JPEG y PNG con un máximo de 4 MB.
3. En **Storage > S3 Access Keys**, crea una clave de servidor y conserva su
   `access key` y `secret key` únicamente para las variables de Vercel. No uses
   la clave anónima ni expongas estas claves en el navegador.
4. En **Connect**, copia dos URI distintos:

   - La conexión directa (o *Session pooler* si la conexión directa no es
     accesible desde tu red) solo se usa desde una máquina controlada para las
     migraciones.
   - El URI del **Transaction pooler**, puerto `6543`, se usa en Vercel. Debe
     conservar TLS (`sslmode=require`).

5. Copia de la configuración S3 el endpoint y la región. El endpoint tiene la
   forma `https://<project-ref>.storage.supabase.co/storage/v1/s3`; no adivines
   ni cambies el `project-ref` o la región.

La aplicación se conecta directamente a PostgreSQL y S3; no requiere activar
la Data API para funcionar. Mantenerla desactivada reduce la superficie que no
usa esta aplicación.

## 2. Aplicar el esquema antes del primer deploy

No ejecutes migraciones durante el build de Vercel: varias Functions podrían
intentar hacerlo a la vez. Desde una terminal controlada, con una conexión
directa o Session pooler de Supabase, exporta temporalmente `DATABASE_URL` y
ejecuta:

```powershell
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py create_initial_manager --email gerente@tu-dominio.pe --display-name "Gerente principal"
```

El segundo comando pide la contraseña de forma interactiva y crea el rol
`Gerente`. No uses `createsuperuser` como sustituto: crea un usuario `Admin`,
que no es un rol operativo de PagoControl.

Para una base local con datos existentes, primero conserva una copia de
`db.sqlite3` y `private_uploads/`. `migrate` solo crea el esquema de PostgreSQL;
no migra automáticamente las filas ni los archivos locales. No despliegues ni
ejecutes `seed_demo_data.py` en producción. Planifica una migración de datos
separada y verificable si necesitas conservar información local.

## 3. Valores en la pantalla “New Project” de Vercel

Usa estos valores en la pantalla mostrada al importar el repositorio:

| Campo | Valor |
| --- | --- |
| Project Name | `examen-parcial-pagos` |
| Root Directory | `./` |
| Application Preset | `Django` |
| Build Command | Déjalo sin personalizar (`None`/valor predeterminado) |
| Output Directory | Déjalo sin personalizar (`N/A`) |
| Install Command | `pip install -r requirements.txt` |

No agregues un `vercel.json` ni un comando que ejecute `migrate` en el build.

## 4. Variables de entorno de Vercel

Añade las siguientes variables antes de pulsar **Deploy**. Inicialmente elige
solo el entorno **Production**. Para *Preview* usa otro proyecto/bucket de
Supabase; no reutilices las credenciales productivas en ramas de prueba.

| Key | Valor de Production |
| --- | --- |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | Una clave aleatoria larga, por ejemplo generada con `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS` | `examen-parcial-pagos.vercel.app` (y el dominio propio, separado por comas, si existe) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://examen-parcial-pagos.vercel.app` (y cada dominio propio con `https://`) |
| `DATABASE_URL` | URI del **Transaction pooler** de Supabase, puerto `6543`, con TLS |
| `SUPABASE_STORAGE_BUCKET` | `pagocontrol-private` |
| `SUPABASE_S3_ENDPOINT_URL` | Endpoint S3 copiado de Supabase, por ejemplo `https://<project-ref>.storage.supabase.co/storage/v1/s3` |
| `SUPABASE_S3_REGION` | Región exacta copiada de la configuración S3 de Supabase |
| `SUPABASE_S3_ACCESS_KEY_ID` | Access key S3 de servidor |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | Secret key S3 de servidor |
| `SUPABASE_SIGNED_URL_TTL` | `60` |

Si Vercel asigna otro dominio al proyecto, sustituye los dos valores con
`examen-parcial-pagos.vercel.app` por el dominio que Vercel indique. No incluyas
comillas, `<>`, la URL del panel de Supabase ni secretos reales en `.env.example`
o en Git.

## 5. Verificación posterior al deploy

1. Revisa el log de Vercel: no debe aparecer un error por variables faltantes,
   migraciones pendientes ni configuración incompleta de Storage.
2. Inicia sesión con el gerente inicial creado en el paso 2.
3. Crea una obligación nueva y confirma que muestra PEN como moneda fija.
4. Adjunta un PDF de prueba menor a 4 MB y confirma que puede verse y
   descargarse solo con una sesión autorizada.
5. Registra el aviso de falta de fondos con un asistente y confirma que el
   estado de la obligación no cambia a suspendido.
6. Haz un redeploy sin modificar la base: la obligación y el documento deben
   seguir disponibles. Esto prueba que no dependen de SQLite ni del disco
   efímero de Vercel.

Vercel limita el cuerpo de solicitud/respuesta de una Function a 4.5 MB. Por
eso esta versión valida documentos de hasta 4 MB. Para archivos mayores habría
que diseñar una carga directa firmada al bucket, no subir el límite a ciegas.

## 6. Reversión

Si una versión falla, usa **Rollback** de Vercel para volver al deployment
anterior. El rollback no revierte cambios de PostgreSQL ni archivos en Storage:
antes de una migración de datos toma un respaldo de la base y del bucket y
prueba la restauración en un entorno separado.

## Referencias oficiales

- [Supabase: conectar a Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase: autenticación S3](https://supabase.com/docs/guides/storage/s3/authentication)
- [Supabase: proteger la Data API](https://supabase.com/docs/guides/api/securing-your-api)
- [Vercel: soporte Django sin configuración](https://vercel.com/changelog/zero-configuration-django-support)
- [Vercel: límites de Functions](https://vercel.com/docs/functions/limitations)
