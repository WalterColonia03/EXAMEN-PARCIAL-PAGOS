# Proyecto Parcial — Control de pagos

Esta carpeta es la raíz canónica y autosuficiente del proyecto. No depende de
ningún archivo ni ruta de otros proyectos.

El código se mantiene en
[`WalterColonia03/EXAMEN-PARCIAL-PAGOS`](https://github.com/WalterColonia03/EXAMEN-PARCIAL-PAGOS).
La publicación en Vercel y la conexión de producción con Supabase continúan
pendientes de validación. La planificación vigente se conserva en
`planificacion_scrum/` y solo se transformará en Scrum/Jira después de que el
responsable del producto acepte el comportamiento experimental.

## Desarrollo local

Requiere Python 3.12.

```powershell
.\iniciar_servidor_local.ps1
```

El servidor local queda disponible en `http://127.0.0.1:8010/`.

## Prototipo experimental disponible

- Ámbitos separados para empresa, vida personal, hogar/propiedad, familiar o
  tercero y entidad patrimonial, sin crear empresas ficticias.
- Titular, beneficiario, acreedor, naturaleza del gasto y fuente de fondos como
  datos independientes.
- Categorías cotidianas para servicios, tarjeta, préstamo, seguro, vivienda,
  educación, salud, apoyo familiar, personal doméstico, vehículo, viaje,
  inversión, donación, legal, suscripción, proveedor y emergencia.
- Los compromisos recurrentes especializados conservan contrato, póliza,
  tarjeta enmascarada, propiedad, viaje o inversión; cada período completa sus
  importes y demás datos variables.
- Decisión `CR-006`, verificada localmente: las operaciones nuevas usan PEN;
  los registros históricos en USD quedan en consulta de solo lectura y nunca se
  mezclan con los totales en PEN.
- Compromisos únicos o recurrentes, con pausa, omisión y generación idempotente.
- Pagos completos o parciales, devoluciones, contracargos, ajustes, reembolsos
  y anulaciones conservando el historial.
- Cola por excepciones: vencidas, próximas, sin cuenta de servicio, sin
  sustento, datos incompletos y listas para pagar.
- Calendario mensual, recordatorios internos, filtros y resumen gerencial por
  ámbito y moneda.
- Importación revisable de cuentas de servicio y obligaciones desde CSV/XLSX.
- Formularios que se adaptan al ámbito, categoría, recurrencia, tipo de monto,
  fuente y acción, ocultando y deshabilitando los campos que no corresponden.

La plantilla de cuentas de servicio admite ámbito o empresa, acreedor/proveedor,
tipo de servicio, tipo de identificador e identificador principal. Un local solo
se utiliza en ámbitos empresariales. La importación masiva queda reservada al
gerente; el asistente puede registrar y operar obligaciones de ámbitos que el
gerente haya compartido.

## Garantías P0 en validación

- Un pago externo solo puede registrarse cuando la obligación ya tiene un
  documento de sustento y se adjunta un comprobante válido. La regresión previa
  rechaza importes superiores al saldo y estados no operables. `CR-006` añade
  altas normalizadas a PEN y la consulta inmutable de los registros USD
  anteriores.
- Cada obligación conserva una instantánea inmutable de banco, titular y cuenta
  de destino. La migración `payments.0004_destination_account_snapshots` hace
  backfill con el valor disponible al migrar; no reconstruye valores que ya se
  hubieran modificado antes.
- El listado y el detalle normal muestran identificadores y cuentas enmascarados.
  La instrucción completa de pago requiere una acción `POST` autorizada y deja
  una auditoría sin almacenar el valor completo.
- Solo el gerente crea, edita o importa cuentas de servicio. El asistente puede
  consultarlas y asociar cuentas activas compatibles al trabajo de pagos.
- CSV/XLSX de cuentas de servicio usan una política propia de archivo. Un archivo
  corrupto o una fila inválida retorna un error recuperable y revierte toda la
  importación.
- Los ámbitos privados, obligaciones sensibles y fuentes ocultas se bloquean en
  servidor; ocultar un botón no se usa como sustituto del permiso.
- Al existir movimientos, la identidad financiera de la obligación queda
  protegida frente a cambios retroactivos de ámbito, acreedor, monto o moneda.

Para validar el bloque técnico:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

La validación automatizada cerró con **84 de 84 pruebas aprobadas** (incluye
`CR-006`), además de `check` limpio y `makemigrations --check --dry-run` sin
cambios. La revisión visual manual y el despliegue real permanecen pendientes;
por eso el estado sigue siendo `verificado técnicamente`, no `validado por
producto`.

## Carga y consulta de archivos

- Antes de adjuntar un comprobante o documento, la pantalla muestra una vista
  previa pequeña: imagen para JPG/PNG y primera página para PDF.
- Al cargar cuentas de servicio u obligaciones, CSV y Excel muestran sus primeras
  filas, además del nombre y tamaño, para confirmar la selección antes de importar.
- Los documentos guardados siguen siendo privados. Solo una persona con sesión
  autorizada puede abrir su vista previa o descargar el archivo.

## Decisión operativa vigente · CR-006

La implementación y pruebas automatizadas locales se registran en
[`EXP-LAB_CR-006_IMPLEMENTACION_2026-10-18.md`](planificacion_scrum/evidencias/EXP-LAB_CR-006_IMPLEMENTACION_2026-10-18.md).
La validación manual y el despliegue real aún no se declaran ejecutados:

- el asistente conserva acceso al calendario y consulta las cuentas de servicio
  compartidas; crear, editar e importar configuración corresponde al gerente;
- **Reportar falta de fondos** crea una excepción operativa auditada para el
  gerente y no suspende la obligación; suspender y reactivar siguen siendo
  decisiones exclusivas del gerente;
- un documento de sustento equivocado solo puede retirarse lógicamente antes de
  que exista cualquier movimiento, con motivo, actor y fecha; el archivo y su
  registro no se borran físicamente, y los comprobantes nunca se retiran por
  esta vía.

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

## Validación manual desde cero

El recorrido reproducible Gerente → Asistente → Gerente está en
[`planificacion_scrum/11_GUIA_VALIDACION_MANUAL_DESDE_CERO.md`](planificacion_scrum/11_GUIA_VALIDACION_MANUAL_DESDE_CERO.md).
La ficha de respaldo, conteos y controles del reinicio se mantiene separada en
[`planificacion_scrum/evidencias/EXP-LAB_REINICIO_CONTROLADO_2026-10-16.md`](planificacion_scrum/evidencias/EXP-LAB_REINICIO_CONTROLADO_2026-10-16.md).

No ejecutes `seed_demo_data.py` para ese recorrido: la validación comienza sin
datos operativos precargados. Las credenciales de las dos cuentas locales se
entregan por separado y no deben escribirse en archivos versionables ni capturas.
La guía está preparada, pero la validación manual todavía no se declara ejecutada.

## Recuperación de acceso

La pantalla de ingreso incluye **¿No recuerdas tu correo o contraseña?**. Cada
usuario puede guardar códigos personales de un solo uso desde **Mi acceso**. El
gerente también puede emitir al asistente un código temporal de 30 minutos tras
confirmar su propia contraseña; el asistente no puede restablecer al gerente.

La instalación local no simula envíos de correo. Si el gerente pierde también
sus códigos personales, la recuperación debe realizarla un operador autorizado
en el equipo local. La especificación y evidencia están en
[`planificacion_scrum/evidencias/EXP-LAB_RECUPERACION_ACCESO_2026-10-16.md`](planificacion_scrum/evidencias/EXP-LAB_RECUPERACION_ACCESO_2026-10-16.md).

## Producción en Vercel y Supabase

Producción utilizará PostgreSQL de Supabase y un bucket privado de Supabase
Storage. No se usará SQLite ni el sistema de archivos efímero de Vercel para
datos o adjuntos persistentes.

Configuración prevista en Vercel:

- Root Directory: `./`.
- Framework Preset: `Django`.
- Install Command: `pip install -r requirements.txt`.
- Build Command y Output Directory: valores predeterminados de Django.

Las variables requeridas están enumeradas, sin secretos reales, en
`.env.example`: `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS`, `DATABASE_URL` y las variables
`SUPABASE_STORAGE_*`. `DATABASE_URL` debe usar el *Transaction pooler* de
Supabase con TLS, y el bucket debe permanecer privado. Las migraciones se
ejecutan como una operación controlada contra PostgreSQL antes de habilitar la
versión; no se ejecutan de forma concurrente en cada Function de Vercel.

La configuración exacta de Supabase, las variables de Vercel, el primer
gerente y las comprobaciones posteriores están en
[`DESPLIEGUE_VERCEL_SUPABASE.md`](DESPLIEGUE_VERCEL_SUPABASE.md).

Con `DJANGO_DEBUG=0`, la aplicación activa HTTPS, cookies seguras y HSTS.
Define `DJANGO_HSTS_PRELOAD=1` únicamente si el dominio y todos sus
subdominios cumplen permanentemente los requisitos de la lista HSTS preload.

## Evidencia del laboratorio

La correspondencia entre `EXP-LAB-01` a `EXP-LAB-10`, el código, las pruebas y
los límites conscientes está en
`planificacion_scrum/evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md`.
`EXP-LAB-11` mantiene su evidencia de acceso por separado. `EXP-LAB-12` tiene
evidencia de implementación y pruebas locales, pero no se declara cerrado hasta
completar despliegue y validación manual.
