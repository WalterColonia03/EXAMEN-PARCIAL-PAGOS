# Feedback del profesor y control de cambios

## 1. Propósito

Este archivo mantiene trazabilidad entre lo planificado, lo construido y lo que el profesor solicite. Una sugerencia no modifica automáticamente el alcance: primero se analiza su valor, costo, riesgo y efecto sobre las historias existentes.

## 2. Registro de investigación externa

Una investigación es una fuente de aprendizaje; no demuestra por sí sola que una función exista, que una brecha se haya reproducido ni que una mejora entre automáticamente al Sprint. La cadena de trazabilidad es:

```text
INV (fuente) → MEJ-INV (propuesta y decisión) → CR (cambio aceptado) → HU/subtareas → evidencia real
```

| ID | Fecha | Fuente | Limitación registrada | Documentos relacionados | Estado |
|---|---|---|---|---|---|
| INV-001 | 15/10/2026 | Investigación de sistemas similares a PagoControl, entregada por el usuario | Benchmark funcional y de diseño; no es auditoría visual ni prueba de que las funciones estén implementadas localmente. | `08`, `09`, evidencia `INV-001` | Registrada |

### CR-001 · Incorporación del benchmark al roadmap de mejoras

**Origen:** INV-001  
**Clasificación:** Refinamiento de producto y priorización de backlog.  
**Estado de la línea base:** No modifica retroactivamente el Sprint original ni sus tiempos.  
**Resultado esperado:** Registrar las mejoras derivadas como `MEJ-INV-001` a `MEJ-INV-014`, con una decisión explícita, prioridad, relación con HUs y evidencia necesaria antes de declararlas implementadas.  
**Historias/documentos afectados:** `07_VISION_RECUPERADA_Y_HU_DE_PRODUCTO.md`, `08_INVESTIGACION_DE_REFERENTES_Y_BENCHMARK.md`, `09_MATRIZ_DE_MEJORAS_Y_TRAZABILIDAD.md`.  
**Decisión:** Aceptado para el roadmap por solicitud del usuario; cada mejora entra a implementación solo al actualizar su estado en la matriz y, si altera un Sprint comprometido, mediante un CR específico.  
**Aprobada por:** Responsable del producto / usuario, 15/10/2026.

### Hallazgos de coherencia de la auditoría técnica inicial · 15/10/2026

La auditoría ejecutada sobre el árbol de trabajo actual encontró los siguientes hechos. Este registro no cambia retrospectivamente el Sprint original ni declara historias como terminadas.

- La revisión histórica de `01_REVISION_ESTADO_Y_ALCANCE.md` describe Django 5.2 y 75 pruebas; el código local de ese corte fijaba Django 6.1.2 y su suite reproducible contenía 16 pruebas.
- `01_REVISION_ESTADO_Y_ALCANCE.md` conserva como brecha la inexistencia de `ServiceAccount`, mientras que el código, `07_VISION_RECUPERADA_Y_HU_DE_PRODUCTO.md` y la documentación de uso ya la refieren. Se clasifica como **documentación desactualizada / estado técnico pendiente de verificación**, no como modificación del pasado.
- Hay cambios técnicos sin consolidar en el árbol, incluida una migración de cuentas de servicio. Se preservan como estado de trabajo; ninguna mejora queda declarada implementada únicamente por su presencia.
- La línea base reproducible del 15/10/2026 fue: `manage.py check` sin incidencias, `makemigrations --check --dry-run` sin cambios y 16 pruebas aprobadas. La evidencia de esta ejecución se resume en la matriz; no se registran tiempos de trabajo.

### CR-002 · Preservación inmutable de la cuenta de destino en obligaciones y pagos

**Origen:** `MEJ-INV-003` derivada de `INV-001` y del roadmap `CR-001`.  
**Clasificación:** Corrección verificada de integridad e historial.  
**Estado de la línea base:** Cambio posterior al Sprint original; no modifica sus fechas, estimaciones ni estados históricos.  
**Fecha:** 15/10/2026.  
**Solicitante:** Responsable del producto / usuario, mediante la instrucción de aplicar el plan de mejoras.  
**Problema observado:** `Payable.destination_account` es una FK editable. Al actualizar banco, titular o número de una cuenta de destino, la obligación y el pago históricos pueden mostrar el valor nuevo en lugar del usado en ese momento.  
**Resultado esperado:** Cada obligación guarda una instantánea de banco, titular y número de cuenta al quedar asociada. Como el modelo actual tiene un único pago completo por obligación, `Payment` referencia esa misma instantánea y no duplica datos bancarios. Editar la cuenta maestra no cambia la instantánea. La interfaz muestra los números protegidos y la auditoría de cambios de la cuenta conserva anterior/nuevo sin exponer números completos.  
**Historias afectadas:** `HU-PROD-02`, `HU-PROD-05`, `HU-SEC-01`; corrección relacionada con la trazabilidad de `HU-CS-03`.  
**Criterios añadidos/eliminados/modificados:** Se añaden migración segura desde base vacía y existente, backfill solo desde el valor actual disponible, prueba de edición de cuenta sin alterar obligación/pago histórico, y auditoría de cambio con actor y fecha. No se afirma poder reconstruir valores que ya hubieran sido sobrescritos antes de la migración.  
**Impacto técnico:** Nuevos campos de snapshot en `Payable`, migración de datos, servicios de creación/generación/pago, vista de detalle/historial, auditoría y pruebas.  
**Impacto en seguridad y datos:** Los snapshots preservan historia y se muestran enmascarados. La auditoría registra banco/titular y número enmascarado; no escribe números completos en logs o mensajes.  
**Estimación anterior:** No aplica; no existía como trabajo comprometido en el Sprint original.  
**Estimación nueva:** Pendiente de estimación formal del equipo; no se inventan Story Points ni horas.  
**Trabajo que se retira o pospone:** Ninguno; no habilita validación previa de cuentas, banca, transferencias ni conciliación.  
**Decisión:** Aceptado para desarrollo y validación dentro del Bloque A de confiabilidad.  
**Aprobada por:** Responsable del producto / usuario, 15/10/2026.

### CR-003 · Importación de cuentas de servicio y formularios sin efectos parciales

**Origen:** `MEJ-INV-005` derivada de `INV-001` y del roadmap `CR-001`.  
**Clasificación:** Corrección verificada de confiabilidad y consistencia.  
**Estado de la línea base:** Cambio posterior al Sprint original; no modifica sus fechas, estimaciones ni estados históricos.  
**Fecha:** 15/10/2026.  
**Solicitante:** Responsable del producto / usuario, mediante la instrucción de aplicar el plan de mejoras.  
**Problema observado:** La política JavaScript global de adjuntos trata CSV/XLSX como documentos PDF/JPG/PNG y bloquea la importación. Además, formularios de obligaciones y compromisos escriben acreedores durante `clean()`, por lo que una validación posterior puede dejar datos huérfanos; un XLSX corrupto puede producir una respuesta 500.  
**Resultado esperado:** La política cliente distingue documentos de pago e importaciones; el servidor acepta únicamente CSV UTF-8 o XLSX de cuentas de servicio y responde con errores recuperables para archivos corruptos. `clean()` permanece libre de escrituras y la creación/actualización de acreedores, registros y auditoría se ejecuta dentro de una transacción atómica solo después de validar el formulario completo.  
**Historias afectadas:** `HU-PROD-03`, `HU-CS-01`, `HU-CS-03` y `HU-SEC-01`.  
**Criterios añadidos/eliminados/modificados:** Se añaden pruebas de UI/endpoint CSV y XLSX, archivo corrupto, rollback de una fila inválida y formulario inválido sin acreedores residuales. Los PDF/JPG/PNG siguen siendo la única política para sustento y comprobante; CSV/XLSX no se convierten en documentos de pago.  
**Impacto técnico:** Formularios, servicios transaccionales, parser de importación, vista de importación, plantilla/base JavaScript, pruebas y documentación de uso. No requiere migración de esquema.  
**Impacto en seguridad y datos:** Evita escrituras parciales, conserva la validación de servidor y no relaja las restricciones de archivos privados de pago.  
**Estimación anterior:** No aplica; no existía como trabajo comprometido en el Sprint original.  
**Estimación nueva:** Pendiente de estimación formal del equipo; no se inventan Story Points ni horas.  
**Trabajo que se retira o pospone:** Ninguno; OCR, importaciones externas adicionales y bandeja documental siguen fuera de este CR.  
**Decisión:** Aceptado para desarrollo y validación dentro del Bloque A de confiabilidad.  
**Aprobada por:** Responsable del producto / usuario, 15/10/2026.

### CR-004 · Permisos de mantenimiento y auditoría segura de datos sensibles

**Origen:** `MEJ-INV-002` derivada de `INV-001` y del roadmap `CR-001`.  
**Clasificación:** Corrección verificada de permisos y trazabilidad.  
**Estado de la línea base:** Cambio posterior al Sprint original; no modifica sus fechas, estimaciones ni estados históricos.  
**Fecha:** 15/10/2026.  
**Solicitante:** Responsable del producto / usuario, mediante la instrucción de aplicar el plan de mejoras.  
**Problema observado:** El asistente puede crear, editar e importar cuentas de servicio aunque las HUs reservan su mantenimiento al gerente. Además, identificadores y números completos aparecen por defecto en selectores, detalle y algunos resúmenes de auditoría; los cambios sensibles no guardan de forma consistente anterior/nuevo.  
**Resultado esperado:** Solo el gerente mantiene e importa cuentas de servicio; ambos roles conservan la consulta y el uso de cuentas activas compatibles. Las vistas normales muestran valores enmascarados y la revelación de un valor completo exige una acción explícita validada en el servidor y auditada sin guardar el valor completo. Los nuevos cambios sensibles registran actor, fecha y diferencias seguras de anterior/nuevo dentro de la misma transacción.  
**Historias afectadas:** `HU-PROD-01`, `HU-PROD-02`, `HU-PROD-05`, `HU-CS-01`, `HU-CS-02` y `HU-SEC-01`.  
**Criterios añadidos/eliminados/modificados:** Se añade matriz GET/POST por rol, pruebas negativas sin escrituras, enmascaramiento por defecto, revelación explícita y auditoría estructurada segura. No se modifica la política de generación mensual porque la planificación actual es ambigua respecto de su rol autorizado.  
**Impacto técnico:** Vistas, servicios, modelos/auditoría, formularios/selectores, plantillas, rutas y pruebas.  
**Impacto en seguridad y datos:** Los eventos nuevos no incluyen números o identificadores completos en `summary` ni mensajes. Las auditorías históricas que ya pudieran contener datos completos no se reescriben ni borran con este CR; su tratamiento requiere una decisión independiente.  
**Estimación anterior:** No aplica; no existía como trabajo comprometido en el Sprint original.  
**Estimación nueva:** Pendiente de estimación formal del equipo; no se inventan Story Points ni horas.  
**Trabajo que se retira o pospone:** No incorpora aprobación previa de cuentas (P2), transferencias, banca, conciliación, OCR ni la línea de tiempo unificada P1.  
**Decisión:** Aceptado para desarrollo y validación dentro del Bloque A de confiabilidad.  
**Aprobada por:** Responsable del producto / usuario, 15/10/2026.

## 2.1 Evidencia de ejecución del Bloque A P0 · 15/10/2026

Esta evidencia describe el estado técnico observado; no modifica el Sprint original ni registra horas, responsables humanos o aprobación de una revisión manual.

| Mejora | Código / migración | Evidencia automatizada | Resultado técnico | Límite pendiente |
|---|---|---|---|---|
| MEJ-INV-001 | Regla de sustento antes del pago, comprobante obligatorio y errores inline recuperables. | `PaymentFlowRegressionTests`: sustento, comprobante, monto distinto, segundo pago, historial, dashboard y descarga privada. | Aprobada en automatización. | Revisión visual manual de escritorio/móvil. |
| MEJ-INV-002 | Restricción de mantenimiento/importación al gerente; máscaras por defecto; `POST` de revelación explícita con auditoría segura. | Pruebas de GET/POST denegados, ausencia de mutaciones/auditoría, máscara y revelación autorizada. | Aprobada en automatización. | Revisión visual manual y matriz manual completa por rol. |
| MEJ-INV-003 | Migración `payments.0004_destination_account_snapshots`; snapshot inmutable solo en `Payable`; auditoría de cuenta con diff seguro. | Creación, edición posterior, actualización, dos períodos e idempotencia. La migración local se aplicó y marcó 12 obligaciones como `BACKFILLED`. | Aprobada en automatización y migración local. | Revisión visual manual. |
| MEJ-INV-004 | Generación mensual conserva servicio, monto, documentos e instrucción por período. | Prueba de dos períodos e idempotencia. | Aprobada en automatización. | Revisión visual manual. |
| MEJ-INV-005 | Parser robusto CSV/XLSX, políticas separadas de archivo, formularios sin escritura en `clean()` y transacciones. | XLSX corrupto, fila inválida con rollback y formulario inválido sin acreedor residual. | Aprobada en automatización. | Revisión visual manual. |

Validación de cierre ejecutada: `python -m py_compile` sobre los módulos modificados, `manage.py check`, `manage.py makemigrations --check --dry-run`, `manage.py test` (**32 pruebas aprobadas**) y `git diff --check`. No se marca ninguna mejora como **Implementada** hasta completar la validación manual reproducible. El entorno de ejecución no expuso un navegador controlable, por lo que esa validación queda explícitamente pendiente y no se sustituye por una afirmación visual.

## 2.2 Ajuste de experiencia operativa · 15/10/2026

**Solicitud observada:** al adjuntar archivos, gerente y asistente deben poder confirmar visualmente el documento elegido. La aplicación no debe presentar mensajes de demostración, planificación o implementación interna a sus usuarios operativos.

**Alcance aplicado:** se añadió vista previa local para JPG/PNG/PDF y primeras filas para CSV/XLSX; los documentos ya guardados pueden abrirse mediante una ruta privada de vista previa. Se simplificó el texto de la interfaz, se retiraron referencias visibles de demostración y se ordenó el menú lateral desde configuración hasta la cola operativa.

**Seguridad y datos:** no se expuso el almacenamiento privado ni se modificaron registros históricos. La vista previa reutiliza los mismos roles autorizados de descarga y solo sirve PDF, JPG, JPEG o PNG en línea. La revisión previa de Excel está limitada al gerente, no importa ni persiste el archivo y devuelve únicamente las primeras filas validadas.

**Evidencia:** `FilePreviewAndClientCopyTests` verifica la ruta privada, la vista previa Excel sin importación, el copy orientado al cliente y el orden del menú. La revisión visual manual de escritorio y móvil continúa pendiente.

## 2.3 Investigación de obligaciones personales, familiares y patrimoniales · 15/10/2026

La observación del usuario evidenció que el copy anterior y, principalmente, el modelo obligatorio de Empresa no contemplan la vida financiera completa del gerente. Se registró `INV-002`, se auditó el código y se identificaron casos de hogar, familia, tarjetas, préstamos, seguros, propiedades, personal doméstico, viajes, inversiones, donaciones, asuntos legales y emergencias.

El texto visible se neutralizó inicialmente para no presentar el registro como exclusivamente empresarial. Esa observación se conserva como antecedente: después de aprobar `CR-005`, el laboratorio incorporó `PaymentContext` y Empresa dejó de ser obligatoria para ámbitos personales, familiares y patrimoniales. La evidencia posterior se registra en la sección 2.4.

### CR-005 · Ámbitos personales, familiares y patrimoniales

**Origen:** `FB-002`, `INV-002` y `MEJ-INV-015`.  
**Clasificación:** Capacidad nueva aprobada para laboratorio experimental.  
**Estado de la línea base:** No modifica el Sprint original; propuesta posterior a la línea base académica.  
**Fecha:** 15/10/2026.  
**Solicitante:** Responsable del producto / usuario, mediante la consulta sobre pagos personales, familiares, tarjetas y préstamos.  
**Problema observado:** Empresa es obligatoria en cuentas de servicio, compromisos y obligaciones. El sistema no puede representar honestamente la luz de la casa de un familiar, un préstamo personal, un gasto de la pareja o un estado de tarjeta sin crear empresas ficticias o clasificar mal los datos.  
**Resultado esperado:** Crear un ámbito administrado neutral —empresa, personal, hogar/propiedad, familiar/tercero u otra entidad patrimonial— y separar titular/deudor, beneficiario, acreedor, fuente de fondos y naturaleza del pago.  
**Historias afectadas:** Si se aprueba, deben refinarse o dividirse `HU-PROD-02` a `HU-PROD-07`, `HU-PORT-01`, `HU-CS-01` a `HU-CS-03` y `HU-SEC-01`; no se crean puntos ni compromiso antes de esa decisión.  
**Criterios propuestos:** Migración empresarial sin pérdida; registro sin empresa ficticia; tarjetas por estado de cuenta; filtros y totales por ámbito; visibilidad autorizada en servidor; generación recurrente por contexto; prevención de duplicados y pruebas de acceso directo. Pagos parciales, devoluciones y reembolsos se incorporan únicamente como experimento de `EXP-LAB-05`, sin estimación ni modificación del Sprint histórico.  
**Impacto técnico:** Nuevo modelo de contexto, claves foráneas y restricciones; backfill; formularios con revelado progresivo; filtros, dashboard, importación, generación mensual y pruebas. Las claves empresariales se conservarían durante una transición.  
**Impacto en seguridad y datos:** Introduce datos personales de terceros y potencialmente sensibles. Exige permisos por ámbito en listados, detalle, edición, archivos, revelación bancaria, historial y exportaciones, además de validación contra acceso directo no autorizado.  
**Estimación anterior:** No aplica; no estaba incluido en el Sprint original.  
**Estimación nueva:** No se estima durante el laboratorio. Los Story Points y horas se definirán al reconstruir la planificación Scrum después de aceptar el prototipo.  
**Trabajo que se retira o pospone:** OCR, transferencias, conciliación bancaria, scraping, correo receptor, WhatsApp y consultas externas no se simularán; requieren una decisión y evidencia externa posterior.  
**Decisión:** Aceptado para prototipado experimental integral. Primero se mantiene la especificación en `10_PLAN_EXPERIMENTAL_PROTOTIPO.md`; luego se implementa y se actualiza su evidencia. No modifica ni reabre el Sprint histórico.  
**Aprobada por:** Responsable del producto / usuario, 15/10/2026.

## 2.4 Ejecución experimental de CR-005 · 16/10/2026

Se implementó la variante local descrita en `10_PLAN_EXPERIMENTAL_PROTOTIPO.md` y se contrastó con `evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md`. El cambio no altera SP, horas, responsables, fechas ni estados del Sprint original.

| Grupo | Resultado observado | Estado |
|---|---|---|
| Ámbitos y privacidad | Cinco tipos de ámbito, empresa/local opcionales, visibilidad del asistente y registro sensible protegido en servidor. | Verificado técnicamente |
| Registro expresivo | Categorías cotidianas, PEN/USD, partes, naturaleza, fuentes y campos progresivos especializados. | Verificado técnicamente |
| Dinero e historia | Abonos, saldo, devolución/contracargo, reembolso, ajuste, disputa y anulación sin borrado. | Verificado técnicamente |
| Tiempo | Recurrencias flexibles, pausa, omisión, límite de generación, calendario mensual y recordatorios sincronizados. | Verificado; variantes diaria/semanal pendientes de decisión |
| Volumen y supervisión | Importación previa CSV/XLSX, duplicados, filtros, dashboard por moneda y actividad reciente. | Verificado parcialmente con límites documentados |
| Experiencia | Vista previa pequeña de adjuntos/importaciones, textos orientados al cliente, acciones por rol y cola como entrada superior del flujo inverso del menú. | HTML y pruebas verificados; revisión visual manual pendiente |

La automatización del navegador no continuó porque la herramienta no pudo determinar de forma segura la URL de la ventana existente. No se sustituyó esa comprobación por una afirmación visual. Se mantuvo la validación reproducible de servidor, HTML, permisos y reglas.

El cierre automatizado ejecutó `manage.py check`, `makemigrations --check --dry-run`, `git diff --check` y la suite completa: **53 de 53 pruebas aprobadas**.

En el corte histórico de esta sección todavía no se había publicado el proyecto ni conectado GitHub o Jira. El estado de conectividad posterior se registra sin reescribir esa evidencia.

## 2.5 Refinamiento de formularios contextuales · 16/10/2026

`FB-003` detectó que los formularios todavía presentaban datos innecesarios para la selección realizada. El refinamiento se incorporó como `EXP-LAB-10` dentro de `CR-005`, después de especificarlo en el plan experimental y sin alterar el Sprint histórico.

La variante verificada cubre obligaciones, compromisos, ámbitos, fuentes de fondos, cuentas de servicio y cambios de estado. Los controles no aplicables quedan ocultos y deshabilitados; al alternar una decisión conservan temporalmente lo escrito en la pantalla, pero no se envían. El servidor descarta además empresa/local fuera del ámbito empresarial, datos bancarios para efectivo, día habitual para servicio eventual, recurrencia de pago único, monto fijo en modo variable y cuenta de servicio fuera de esa categoría.

Se añadieron pruebas de normalización, privacidad del selector de cuentas, errores inline y estructura de revelado progresivo. El cierre completo fue **62 de 62 pruebas aprobadas**. La revisión visual manual de todas las transiciones en escritorio y móvil sigue pendiente, por lo que el estado es verificado técnicamente y no validado por producto.

## 2.6 Preparación de la validación manual sobre base limpia · 16/10/2026

`FB-004` solicita iniciar el producto como una instalación nueva, retirar los datos operativos anteriores y recorrer el ciclo completo alternando los roles Gerente → Asistente → Gerente. Esta actividad valida el prototipo; no añade capacidad funcional, no reabre el Sprint y no modifica sus SP, fechas, horas o estados.

Se definieron dos artefactos independientes:

- `11_GUIA_VALIDACION_MANUAL_DESDE_CERO.md`, que establece precondiciones, datos ficticios, permisos, pasos, resultados esperados, privacidad, recurrencia, idempotencia y checklist;
- `evidencias/EXP-LAB_REINICIO_CONTROLADO_2026-10-16.md`, que debe conservar los conteos anterior/posterior, el respaldo recuperable, sus hashes y las comprobaciones reales de la limpieza.

La línea base prevista conserva únicamente el esquema, migraciones, roles técnicos y dos cuentas activas —una de gerente y una de asistente—. Debe iniciar sin datos operativos, sesiones anteriores ni archivos privados heredados. Las credenciales se entregan fuera de archivos versionables y los documentos usados durante la prueba deben ser ficticios.

La guía utiliza un ámbito no empresarial compartido, una obligación privada para la prueba negativa de acceso, un pago externo con sustento y comprobante, y un compromiso mensual generado dos veces para comprobar que no se duplica. `seed_demo_data.py` no forma parte del procedimiento porque volvería a poblar la instalación.

**Estado:** reinicio técnico completado, documentación consolidada y versión 0.8 lista para validación manual. La ficha contiene el respaldo, los hashes, los conteos y los controles reales. El recorrido visual todavía no se declara ejecutado ni el producto aceptado.

## 2.7 Corrección del ingreso y recuperación de acceso · 16/10/2026

`FB-005` se originó en el primer paso de la validación manual: la pantalla informó credenciales inválidas y el responsable del producto preguntó qué ocurriría si el gerente o el asistente olvidaban tanto su correo como su contraseña.

El diagnóstico comprobó que las credenciales exactas conservadas eran válidas, pero encontró dos brechas reales:

- el correo se comparaba de forma sensible a mayúsculas, aunque el modelo ya mantenía una versión normalizada;
- no existían enlace, pantalla, canal secundario ni código para recuperar el acceso desde la interfaz.

La variante `EXP-LAB-11` corrige la comparación del correo, conserva el correo escrito después de un error, incorpora un control accesible para mostrar u ocultar la contraseña y añade recuperación mediante códigos opacos de un solo uso. Cada titular puede mantener códigos personales fuera del sistema; además, el gerente reautenticado puede emitir al asistente un código temporal de 30 minutos. El asistente no puede administrar el acceso del gerente. Cambiar la contraseña revoca sesiones anteriores y genera trazabilidad separada de pagos y obligaciones.

La instalación local no dispone de correo saliente verificado y sus direcciones terminan en `.local`; por ello no se simula un envío de correo inexistente. Si el gerente pierde contraseña, correo y códigos personales, el último recurso continúa siendo una recuperación técnica local por un operador autorizado, con verificación de identidad. Esta limitación debe seguir visible hasta incorporar un canal secundario real.

**Estado:** implementado y verificado automáticamente; revisión visual y ejecución manual del flujo pendientes. La evidencia se conserva en `evidencias/EXP-LAB_RECUPERACION_ACCESO_2026-10-16.md` y no incluye credenciales ni códigos.

## 2.8 Ajuste operativo, integridad documental y producción · 18/10/2026

### CR-006 · Operación PEN, excepciones auditables y persistencia en Supabase

**Origen:** `FB-006`, revisión del PR de ajustes de interfaz y decisión del responsable del producto.

**Clasificación:** Refinamiento funcional, corrección de permisos e integridad y preparación de producción.

**Estado de la línea base:** No modifica ni reabre el Sprint original; cambio posterior del laboratorio.

**Fecha:** 18/10/2026.

**Solicitante:** Responsable del producto / usuario.

**Problema observado:** Ocultar módulos eliminaba consultas necesarias del asistente; convertir «Sin fondos» en suspensión le otorgaba una decisión gerencial; borrar adjuntos destruía trazabilidad; retirar la moneda solo de la interfaz no establecía una regla consistente; SQLite y archivos locales no ofrecen persistencia adecuada en Vercel.

**Resultado esperado:** Las operaciones nuevas usan PEN y el USD anterior queda en consulta de solo lectura; el asistente reporta falta de fondos como excepción auditada sin suspender; solo el gerente suspende/reactiva; un sustento puede retirarse lógicamente y con auditoría antes del primer movimiento, nunca borrarse físicamente; calendario y cuentas de servicio siguen consultables por el asistente; producción usa PostgreSQL y Storage privado de Supabase desde Vercel.

**Historias afectadas:** `HU-PROD-01`, `HU-PROD-04`, `HU-PROD-05`, `HU-PROD-07`, `HU-DOC-01`, `HU-SEC-01`, `EXP-LAB-02`, `EXP-LAB-03`, `EXP-LAB-05`, `EXP-LAB-07`, `EXP-LAB-09`, `EXP-LAB-10` y el nuevo `EXP-LAB-12`.

**Criterios añadidos/eliminados/modificados:** PEN es la única moneda de alta para compromisos, obligaciones, fuentes y movimientos nuevos; USD histórico no se convierte ni edita. Reportar falta de fondos no cambia el estado a `SUSPENDED`. Retirar sustento exige ausencia total de movimientos, motivo y evento de auditoría, conserva archivo/registro y no reactiva automáticamente. Los comprobantes se corrigen mediante el flujo financiero autorizado. La navegación conserva calendario y consulta de cuentas compartidas.

**Impacto técnico:** Reglas de modelo/servicio/formulario, estado de excepción, retiro lógico de adjuntos, auditoría, permisos, migraciones, pruebas de regresión, configuración PostgreSQL y almacenamiento S3 compatible de Supabase.

**Impacto en seguridad y datos:** Impide escalamiento de permisos, destrucción de evidencia y persistencia en disco efímero. Secretos de base y Storage permanecen solo en variables de entorno del servidor; el bucket no es público.

**Estimación anterior:** No aplica; el ajuste no estaba estimado en el Sprint histórico.

**Estimación nueva:** Pendiente de estimación formal; no se inventan Story Points ni horas.

**Trabajo que se retira o pospone:** Altas nuevas en USD, conversión de moneda, borrado físico desde la interfaz y suspensión por parte del asistente.

**Decisión:** Implementado y verificado localmente con evidencia reproducible. No se declara validado por producto ni desplegado hasta completar la prueba manual y la persistencia real en Vercel/Supabase.

**Aprobada por:** Responsable del producto / usuario, 18/10/2026.

## 3. Versiones de la planificación

| Versión | Fecha | Estado | Descripción | Responsable de aprobación |
|---|---|---|---|---|
| 0.1 | 15/10/2026 | Borrador vivo | Auditoría, Product Backlog y Sprint iniciales. | Equipo pendiente de ratificación |
| 0.2 | 15/10/2026 | Borrador vivo | Se registró INV-001 y su matriz de mejoras, sin declarar nuevas funciones como terminadas ni alterar la línea base. | Responsable del producto / usuario |
| 0.3 | 15/10/2026 | En desarrollo | Se registraron hallazgos de coherencia y los CR-002/CR-003 para correcciones P0, sin alterar la línea base. | Responsable del producto / usuario |
| 0.4 | 15/10/2026 | En validación | Se ejecutó el Bloque A P0 con CR-002, CR-003 y CR-004, migración aplicada localmente, checks limpios y 32 pruebas aprobadas. La revisión visual manual continúa pendiente. | Responsable del producto / usuario |
| 0.5 | 15/10/2026 | En laboratorio | Se registró INV-002 y se aprobó CR-005 para construir el prototipo experimental descrito en el documento 10, sin alterar Sprint, SP, horas ni Jira. | Responsable del producto / usuario |
| 0.6 | 16/10/2026 | Verificada técnicamente | Se ejecutó CR-005 en el prototipo local, con migraciones aplicadas, controles limpios y 53 de 53 pruebas aprobadas. La revisión visual manual y aceptación de producto continúan pendientes. | Responsable del producto / usuario pendiente |
| 0.7 | 16/10/2026 | Verificada técnicamente | Se completó EXP-LAB-10 con formularios contextuales, normalización defensiva y 62 de 62 pruebas aprobadas. La revisión visual manual y aceptación de producto continúan pendientes. | Responsable del producto / usuario pendiente |
| 0.8 | 16/10/2026 | Lista para validación manual | Se completó el reinicio controlado con respaldo, hashes, conteos, integridad y 62 pruebas aprobadas; se preparó el recorrido Gerente → Asistente → Gerente desde una base operativa vacía. El recorrido manual todavía no fue ejecutado. | Responsable del producto / usuario pendiente |
| 0.9 | 16/10/2026 | Lista para validación manual | Se corrigió el acceso sin distinción de mayúsculas y se incorporó recuperación local segura con códigos personales y delegación temporal Gerente → Asistente; 78 de 78 pruebas aprobadas. La validación visual permanece pendiente. | Responsable del producto / usuario pendiente |
| 0.10 | 18/10/2026 | Especificada; verificación pendiente | `CR-006` define operación nueva solo PEN, USD histórico de solo lectura, reporte de falta de fondos separado de suspensión, retiro lógico de sustento, navegación por rol y producción Vercel/Supabase. No se registran pruebas aún. | Responsable del producto / usuario |
| 0.11 | 18/10/2026 | Verificada técnicamente | `CR-006` se implementó localmente: migración `payments.0010`, reglas PEN/USD, excepción de fondos, retiro lógico, configuración PostgreSQL/Storage y 84 de 84 pruebas aprobadas. Despliegue real y recorrido manual permanecen pendientes. | Responsable del producto / usuario pendiente |
| 1.0 | — | Pendiente | Versión funcional presentada al profesor. | — |
| 1.1 | — | Pendiente | Feedback del profesor incorporado y validado. | — |
| Final-Jira | — | Pendiente | Línea base congelada para preparar un Jira separado. | — |

## 4. Registro de feedback

| ID | Fecha/hora | Fuente | Observación o sugerencia | Tipo | HUs afectadas | Decisión | Justificación | Reestimación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| FB-001 | — | Profesor | — | Corrección / mejora / nueva función / eliminación | — | Pendiente | — | — | Pendiente |
| FB-002 | 15/10/2026 | Responsable del producto / usuario | El sistema debe contemplar pagos propios, de familiares, terceros, tarjetas y préstamos sin exigir que pertenezcan a una empresa. | Nueva capacidad / ampliación de dominio | EXP-LAB-01 a 09; futuras HU por refinar | Aceptar como laboratorio CR-005 | La empresa obligatoria no representa correctamente estos casos y crear empresas ficticias contaminaría reportes | Sin estimación durante laboratorio | Verificado técnicamente; pendiente de aceptación del prototipo |
| FB-003 | 16/10/2026 | Responsable del producto / usuario | Los formularios deben mostrar únicamente los campos necesarios para la información elegida y evitar controles que no se usarán. | Refinamiento de experiencia e integridad | EXP-LAB-10; futura HU por refinar | Incorporar dentro de CR-005 | Reduce carga visual y evita valores contradictorios sin debilitar la validación del servidor | Sin estimación durante laboratorio | Verificado técnicamente; pendiente de revisión visual y aceptación |
| FB-004 | 16/10/2026 | Responsable del producto / usuario | Limpiar los datos operativos y probar el sistema desde el inicio simulando primero al gerente, luego al asistente y finalmente al gerente. | Preparación de validación del laboratorio | EXP-LAB-01 a 10; casos de aceptación del documento 10 | Preparar reinicio controlado y guion reproducible | Una base vacía permite comprobar descubribilidad, dependencias, permisos y cierre del ciclo sin apoyarse en datos sembrados | No aplica; no añade alcance funcional | Lista para validación manual; ejecución y aceptación pendientes |
| FB-005 | 16/10/2026 | Responsable del producto / usuario | El primer ingreso mostró credenciales inválidas y no existía una salida si gerente o asistente olvidaban correo y contraseña. | Corrección y nueva capacidad de seguridad | EXP-LAB-11; futura HU de identidad por refinar | Corregir normalización e implementar recuperación local por códigos de un solo uso | Un error de acceso sin camino de recuperación bloquea todo el producto; el flujo debe evitar enumerar cuentas o crear puertas traseras | Sin estimación durante laboratorio | Verificado automáticamente; pendiente de revisión visual y aceptación |
| FB-006 | 18/10/2026 | Responsable del producto / usuario | Rehacer de forma coherente los ajustes del PR: simplificar sin ocultar consultas, operar en PEN, reportar falta de fondos sin suspender, corregir sustento sin borrarlo y desplegar con persistencia real. | Refinamiento funcional, permisos, integridad y arquitectura | EXP-LAB-12 y HUs relacionadas | Aceptar como `CR-006` | Separa responsabilidades, conserva evidencia y evita depender de SQLite o archivos efímeros en producción | Pendiente de estimación | Implementado y verificado localmente; despliegue/manual pendientes |

### Regla especial del laboratorio aprobada con FB-002

Durante esta etapa, cada experimento se documenta antes de modificarse en código. Los documentos Scrum históricos permanecen como antecedente, no como orden de ejecución vigente. Cuando el responsable del producto acepte el sistema, los comportamientos conservados se transformarán en nuevas HUs, criterios, estimaciones y, solo después, elementos de Jira.

Decisiones permitidas:

- `Aceptar`.
- `Aceptar parcialmente`.
- `Reformular`.
- `Posponer`.
- `Rechazar con justificación`.

## 5. Análisis obligatorio de un cambio

Antes de modificar una HU se responde:

1. ¿Qué problema de usuario resuelve?
2. ¿Modifica un criterio existente o crea una capacidad diferente?
3. ¿Afecta datos, permisos, documentos, auditoría o migraciones?
4. ¿Qué HU y subtareas quedan obsoletas?
5. ¿Debe dividirse la HU?
6. ¿Cambia MoSCoW o Story Points?
7. ¿Aumenta el camino crítico?
8. ¿Qué prueba demuestra que funciona?
9. ¿Qué función equivalente debe salir si no cabe?
10. ¿El profesor aprobó la interpretación final?

## 6. Solicitud de cambio

Copiar esta plantilla por cada cambio aceptado:

```markdown
### CR-___ · Título

**Origen:** FB-___  
**Clasificación:** Corrección verificada / refinamiento de HU / capacidad nueva / propuesta descartada  
**Estado de la línea base:** No modifica Sprint original / cambio aceptado antes de iniciar / posterior al Sprint  
**Fecha:**  
**Solicitante:**  
**Problema observado:**  
**Resultado esperado:**  
**Historias afectadas:**  
**Criterios añadidos/eliminados/modificados:**  
**Impacto técnico:**  
**Impacto en seguridad y datos:**  
**Estimación anterior:**  
**Estimación nueva:**  
**Trabajo que se retira o pospone:**  
**Decisión:**  
**Aprobada por:**  
```

## 7. Momento del cambio

### Antes de iniciar el Sprint

Se pueden refinar historias, volver a estimar y nivelar el cronograma. La planificación cambia de versión antes de ratificar el Sprint.

### Durante el Sprint

No se añade alcance silenciosamente. Si el cambio es imprescindible para el Sprint Goal:

1. se registra como cambio;
2. se calcula su impacto;
3. se negocia retirar alcance equivalente;
4. se actualizan dependencias y horas planificadas;
5. los tiempos ya ejecutados permanecen intactos.

### Después de la Sprint Review o del feedback del profesor

El cambio entra al Product Backlog. Como el curso utiliza un único Sprint, debe indicarse si se trata de:

- corrección necesaria para aceptar una HU del Sprint;
- mejora posterior a la línea base académica;
- función futura no realizada;
- sustitución de una función existente.

No se reescribe el pasado para simular que la mejora estaba incluida originalmente.

## 8. Checklist previo a presentar al profesor

- [ ] Las siete HUs comprometidas reflejan el sistema construido.
- [ ] Cada criterio tiene evidencia reproducible.
- [ ] Los estados reales coinciden con el código y la base local del corte.
- [ ] Los tiempos reales proceden del registro de ejecución.
- [ ] La velocidad usa únicamente HUs completamente Done.
- [ ] Las funciones retiradas aparecen como retiradas, no como terminadas.
- [ ] OCR, WhatsApp, scraping y banca no se presentan como implementados si solo están diseñados.
- [x] La suite reproducible actual y todas las pruebas nuevas pasan en el corte técnico: 62 de 62 el 16/10/2026.
- [ ] No existen datos bancarios o credenciales reales en la demostración.
- [ ] El equipo puede explicar la HU pivote y la comparación de puntos.

## 9. Puerta para preparar Jira en el futuro

No se prepara ni importa Jira hasta cumplir todo lo siguiente:

- [ ] El profesor revisó la versión funcional.
- [ ] Todo feedback aceptado fue implementado o quedó explícitamente pospuesto.
- [ ] La versión documental final coincide con el producto.
- [ ] Las HUs, criterios, puntos y subtareas están congelados.
- [ ] Los tiempos reales fueron revisados por cada responsable.
- [ ] Se decidió un proyecto Jira independiente del minimarket.
- [ ] Se confirmó que ningún elemento se cargará en el proyecto Jira equivocado.
- [ ] El equipo autorizó la transformación de estos `.md` al formato de importación.

Hasta entonces, el estado correcto es: **planificación local en Markdown; Jira sin cambios**.
