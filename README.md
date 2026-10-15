# Proyecto Parcial — Control de pagos

Esta carpeta es la raíz canónica y autosuficiente del proyecto. No depende de
ningún archivo ni ruta de otros proyectos.

## Desarrollo local

Requiere Python 3.12.

```powershell
.\iniciar_servidor_local.ps1
```

El servidor local queda disponible en `http://127.0.0.1:8010/`.

## Cuentas de demostración

| Rol | Correo | Contraseña |
| --- | --- | --- |
| Gerente | `gerente.demo@pagos.invalid` | `DemoPagos2026!` |
| Asistente | `asistente.demo@pagos.invalid` | `DemoPagos2026!` |

El script `seed_demo_data.py` crea o actualiza estas cuentas conservando las
relaciones existentes de los datos demo.

Para reconstruir el entorno en una máquina nueva:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
```

## Datos locales

`db.sqlite3` y `private_uploads/` contienen datos locales y no se versionan.
Antes de eliminarlos o recrearlos, realiza un respaldo si necesitas conservar
usuarios, obligaciones o adjuntos.

## Configuración de producción

Para producción define, como mínimo, estas variables de entorno:

```text
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<clave-larga-y-aleatoria>
DJANGO_ALLOWED_HOSTS=<dominio-principal>
```

Con `DJANGO_DEBUG=0`, la aplicación activa HTTPS, cookies seguras y HSTS.
Define `DJANGO_HSTS_PRELOAD=1` únicamente si el dominio y todos sus
subdominios cumplen permanentemente los requisitos de la lista HSTS preload.
