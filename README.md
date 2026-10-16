# Proyecto Parcial — Control de pagos

Esta carpeta es la raíz canónica y autosuficiente del proyecto. No depende de
ningún archivo ni ruta de otros proyectos.

El prototipo se trabaja de forma local: no está publicado en GitHub y no está
conectado con Jira. La planificación vigente se conserva en
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
- PEN y USD separados; una fuente incompatible con la moneda queda bloqueada.
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
  documento de sustento y se adjunta un comprobante válido. El servidor rechaza
  importes superiores al saldo, monedas incompatibles y estados no operables.
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

La validación automatizada cerró con **62 de 62 pruebas aprobadas**. La revisión visual manual de escritorio
y móvil sigue pendiente porque la herramienta disponible no pudo verificar de
forma segura la URL de la ventana del navegador; por eso el estado documental es
`verificado técnicamente`, no `validado por producto`.

## Carga y consulta de archivos

- Antes de adjuntar un comprobante o documento, la pantalla muestra una vista
  previa pequeña: imagen para JPG/PNG y primera página para PDF.
- Al cargar cuentas de servicio u obligaciones, CSV y Excel muestran sus primeras
  filas, además del nombre y tamaño, para confirmar la selección antes de importar.
- Los documentos guardados siguen siendo privados. Solo una persona con sesión
  autorizada puede abrir su vista previa o descargar el archivo.

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

## Evidencia del laboratorio

La correspondencia entre `EXP-LAB-01` a `EXP-LAB-10`, el código, las pruebas y
los límites conscientes está en
`planificacion_scrum/evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md`.
