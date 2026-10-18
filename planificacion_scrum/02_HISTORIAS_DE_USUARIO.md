# Product Backlog — Historias de Usuario

## 1. Resumen

| ID | Historia | MoSCoW | SP | Sprint único | Estado inicial |
|---|---|---:|---:|---|---|
| HU-CS-01 | Registrar una cuenta de servicio | 4 | 5 | Comprometida | Por hacer |
| HU-CS-02 | Consultar y mantener cuentas de servicio | 4 | 5 | Comprometida | Por hacer |
| HU-CS-03 | Vincular la cuenta con compromisos y obligaciones | 4 | 8 | Comprometida | Por hacer |
| HU-EXP-01 | Registrar un gasto irregular de forma express | 4 | 3 | Comprometida | Por hacer |
| HU-DOC-01 | Recibir y asociar documentos desde una bandeja | 3 | 8 | Comprometida | Por hacer |
| HU-ALT-01 | Atender alertas internas no duplicadas | 3 | 3 | Comprometida | Por hacer |
| HU-SEC-01 | Proteger identificadores y registrar su uso | 4 | 3 | Comprometida | Por hacer |
|  | **Total comprometido** |  | **35** |  |  |
| HU-PORT-01 | Administrar varios portafolios aislados | 3 | 8 | No | Backlog |
| HU-OCR-01 | Extraer datos de documentos mediante OCR | 3 | 8 | No | Backlog |
| HU-APR-01 | Aprobar pagos por excepción y por lote | 2 | 8 | No | Backlog |
| HU-ANL-01 | Consultar proyección y anomalías de gasto | 2 | 5 | No | Backlog |
| HU-NOT-01 | Recibir alertas externas | 1 | 8 | No | Backlog |
| HU-INT-01 | Consultar obligaciones en portales de proveedores | 1 | 13 | No; debe dividirse | Backlog |
| HU-REC-01 | Conciliar pagos y exportar información contable | 1 | 8 | No | Backlog |

Los 35 SP comprometidos constituyen un **pronóstico**, no una velocidad histórica. Los elementos fuera del Sprint no poseen fechas planificadas.

Las especificaciones `EXP-LAB-*` incluidas al final de este archivo pertenecen al laboratorio autorizado por `CR-005`. No forman parte de este resumen, no alteran los 35 SP, no son HUs comprometidas y no deben copiarse a Jira hasta que el prototipo sea aceptado y se realice un refinamiento formal posterior.

---

# Historias comprometidas

## HU-CS-01 · Registrar una cuenta de servicio — HU pivote

**Prioridad MoSCoW:** `4 — Must Have`  
**Story Points:** `5 SP`  
**Esfuerzo de referencia:** `30 horas-persona`  
**Dependencias:** línea base y contrato de datos del Sprint.

### Descripción

Como gerente quiero registrar la cuenta permanente de un servicio y relacionarla con una empresa y propiedad para identificar correctamente sus recibos futuros sin volver a digitar los mismos datos cada mes.

### Criterios de aceptación

1. Una cuenta nueva debe permitir seleccionar acreedor, tipo de servicio, tipo de identificador, código, empresa y local opcional.
2. El local seleccionado debe pertenecer a la empresa indicada; una combinación inconsistente debe rechazarse sin guardar información parcial.
3. El código debe normalizar espacios y mayúsculas para comparar duplicados, pero debe conservar un valor legible para el usuario.
4. No debe permitirse otra cuenta con el mismo acreedor, tipo de identificador y código normalizado.
5. No debe imponerse una longitud única a todos los proveedores; las validaciones específicas deben depender del tipo o regla configurada.
6. Una cuenta nueva debe quedar activa por defecto y registrar quién la creó y cuándo.
7. Una solicitud de creación no autorizada debe rechazarse en el servidor sin crear la cuenta ni exponer sus datos.

### Motivo de estimación

Es la referencia de `5 SP`: afecta modelo, migración, reglas, formulario, permisos, auditoría y pruebas, con complejidad media conocida para el equipo.

## HU-CS-02 · Consultar y mantener cuentas de servicio

**Prioridad MoSCoW:** `4 — Must Have`  
**Story Points:** `5 SP`  
**Comparación con pivote:** complejidad semejante; reutiliza el modelo, pero añade búsqueda, edición y ciclo de vida.  
**Dependencia:** HU-CS-01.

### Descripción

Como gerente quiero buscar, corregir, desactivar o reactivar las cuentas de servicio para mantener vigente el catálogo sin eliminar la historia de obligaciones anteriores.

### Criterios de aceptación

1. La lista debe poder filtrarse por empresa, local, acreedor, tipo de servicio y estado activo/inactivo.
2. El detalle debe diferenciar claramente código de servicio y número de factura o documento del periodo.
3. Editar una cuenta debe aplicar las mismas validaciones de pertenencia y duplicidad utilizadas al crearla.
4. Desactivar una cuenta debe impedir que se seleccione en nuevos compromisos u obligaciones.
5. Desactivar una cuenta no debe eliminar ni modificar sus compromisos, obligaciones, pagos, documentos o auditoría histórica.
6. Solo debe permitirse reactivar una cuenta si la empresa, el local y el acreedor relacionados continúan activos.
7. El asistente puede consultar y utilizar cuentas activas, pero no puede modificar su identidad o estado; un acceso directo no autorizado debe ser rechazado por el servidor.

## HU-CS-03 · Vincular cuentas de servicio con compromisos y obligaciones

**Prioridad MoSCoW:** `4 — Must Have`  
**Story Points:** `8 SP`  
**Comparación con pivote:** aproximadamente 1.6 veces el pivote por migración, retrocompatibilidad y cambios en varios flujos.  
**Dependencias:** HU-CS-01; integración con HU-CS-02.

### Descripción

Como asistente administrativo quiero vincular una cuenta de servicio con su compromiso y sus obligaciones para reconocer la propiedad y el proveedor correctos en cada periodo.

### Criterios de aceptación

1. Un compromiso puede seleccionar una cuenta activa compatible con su empresa, local, acreedor y categoría.
2. Una combinación incompatible debe rechazarse tanto desde la interfaz como mediante una solicitud directa al servidor.
3. Una obligación generada desde un compromiso debe heredar la cuenta de servicio sin volver a solicitarla.
4. Una obligación manual puede asociarse opcionalmente con una cuenta activa compatible.
5. Tablero, detalle e historial deben mostrar el tipo de identificador y su valor enmascarado sin confundirlo con el número del documento externo.
6. Desactivar la cuenta después de generar obligaciones no debe ocultar ni romper los registros históricos.
7. Los compromisos y obligaciones existentes deben continuar funcionando con cuenta de servicio vacía hasta que se clasifiquen.
8. La migración debe poder ejecutarse sobre una base existente y sobre una base vacía sin duplicar ni perder registros.

## HU-EXP-01 · Registrar un gasto irregular de forma express

**Prioridad MoSCoW:** `4 — Must Have`  
**Story Points:** `3 SP`  
**Comparación con pivote:** cerca de la mitad del pivote; reutiliza el flujo de obligaciones y reduce su captura inicial.  
**Dependencias:** línea base; integración con HU-CS-03 opcional.

### Descripción

Como asistente administrativo quiero registrar un gasto imprevisto con descripción, monto y vencimiento para ponerlo bajo control en menos de diez segundos y completar los datos secundarios después.

### Criterios de aceptación

1. Con empresa y local ya definidos en el contexto, el formulario debe mostrar como obligatorios únicamente descripción, monto y fecha de vencimiento.
2. Si no existe contexto, el sistema debe solicitar primero la empresa y el local opcional sin asignar una entidad silenciosamente.
3. El monto debe ser mayor que cero y aceptar moneda nacional con dos decimales.
4. La fecha puede ser anterior al día actual; en ese caso la obligación debe crearse como pendiente y visualizarse como vencida.
5. El gasto debe guardarse en categoría `Otro`, marcarse incompleto cuando falten acreedor o documento y aparecer inmediatamente en el tablero.
6. Después de guardarlo, el usuario debe poder abrir su detalle para añadir acreedor, cuenta de servicio, categoría, documento y cuenta de destino.
7. La creación debe registrar usuario, fecha, empresa, local y valores iniciales en la auditoría.

## HU-DOC-01 · Recibir y asociar documentos desde una bandeja

**Prioridad MoSCoW:** `3 — Should Have`  
**Story Points:** `8 SP`  
**Comparación con pivote:** mayor que el pivote por almacenamiento temporal, hash, estados, asociación y permisos.  
**Dependencias:** HU-CS-01 y HU-CS-03.

### Descripción

Como asistente administrativo quiero colocar recibos y facturas en una bandeja central para detectar cargas repetidas, previsualizarlas y asociarlas con la obligación correcta antes de pagar.

### Criterios de aceptación

1. La bandeja debe aceptar PDF, JPG y PNG de hasta 10 MB aplicando las validaciones de firma y tamaño existentes.
2. Cada archivo debe registrar nombre original, tipo, tamaño, usuario, fecha y hash SHA-256 calculado por el servidor.
3. Una segunda carga del mismo contenido debe advertir que el archivo ya existe y no debe almacenar otra copia física.
4. Un documento debe recorrer los estados `Recibido`, `Por asociar`, `Asociado` o `Descartado` sin presentarse como validado por el proveedor o banco.
5. El usuario debe poder ver una previsualización compatible antes de asociar el documento.
6. El usuario debe poder asociar manualmente el documento con una obligación existente y consultar la empresa, local, acreedor y cuenta de servicio antes de confirmar.
7. Si se introduce un código que coincide exactamente con una sola cuenta activa, el sistema debe sugerirla; si existen cero o varias coincidencias, debe solicitar revisión humana.
8. Al confirmar la asociación, el archivo debe convertirse en documento de sustento de la obligación sin perder sus metadatos ni auditoría.
9. Los documentos deben permanecer privados y su descarga debe requerir sesión y permisos válidos.

## HU-ALT-01 · Atender alertas internas no duplicadas

**Prioridad MoSCoW:** `3 — Should Have`  
**Story Points:** `3 SP`  
**Comparación con pivote:** menor que el pivote porque reutiliza el cálculo de urgencia actual.  
**Dependencia:** obligaciones existentes; integración con HU-CS-03.

### Descripción

Como asistente administrativo quiero recibir alertas internas en momentos relevantes para atender vencimientos sin revisar manualmente cada tarjeta durante el día.

### Criterios de aceptación

1. Una obligación pendiente debe poder generar alertas internas al entrar en D-5, D-2, D-0 y estado vencido.
2. La misma obligación no debe generar dos alertas del mismo tipo para la misma fecha de referencia.
3. La alerta debe mostrar empresa, local, concepto, fecha, monto cuando exista y una acción para abrir la obligación.
4. Registrar el pago o suspender la obligación debe cerrar sus alertas accionables sin borrar la historia.
5. Marcar una alerta como leída no debe cambiar el estado de la obligación.
6. El gerente debe poder consultar las alertas vencidas y el asistente debe consultar las correspondientes a su trabajo operativo.
7. Ejecutar dos veces el generador para la misma fecha debe producir el mismo resultado sin duplicados.

## HU-SEC-01 · Proteger identificadores y registrar su uso

**Prioridad MoSCoW:** `4 — Must Have`  
**Story Points:** `3 SP`  
**Comparación con pivote:** menor en volumen, pero con riesgo elevado de seguridad.  
**Dependencias:** HU-CS-01 y HU-CS-03.

### Descripción

Como gerente quiero que los códigos de servicio y documentos privados se muestren únicamente a usuarios autorizados para reducir la exposición de información sin impedir el trabajo del asistente.

### Criterios de aceptación

1. Los listados deben mostrar los identificadores enmascarados y conservar solo los últimos cuatro caracteres visibles cuando la longitud lo permita.
2. La visualización o copia del valor completo debe requerir una acción explícita y un permiso validado en el servidor.
3. Los cambios de código, empresa, local, acreedor o estado deben registrar valor anterior, valor nuevo, actor y fecha en la auditoría.
4. Los logs de aplicación y mensajes de error no deben incluir códigos completos, números de cuenta completos ni contenido de documentos.
5. Un usuario sin permiso no debe descargar documentos ni consultar el valor completo mediante URL o solicitud construida manualmente.
6. Las pruebas negativas deben confirmar que una denegación no modifica datos ni crea registros parciales.

---

# Historias fuera del Sprint

Estas historias permanecen refinadas para discutirlas con el profesor. No tienen fechas, subtareas ni compromiso de entrega en el Sprint único.

## HU-PORT-01 · Administrar varios portafolios aislados

**Prioridad MoSCoW:** `3 — Should Have`  
**Story Points:** `8 SP`

### Descripción

Como administrador del sistema quiero separar empresas y propiedades por cliente o dueño principal para impedir que la información de un portafolio sea visible desde otro.

### Criterios de aceptación

1. Cada empresa debe pertenecer a un único portafolio activo.
2. Todas las consultas y operaciones deben filtrar el portafolio autorizado en el servidor.
3. Un usuario no debe acceder a identificadores, obligaciones o documentos de otro portafolio mediante una URL directa.
4. La migración inicial debe asociar los datos existentes con un portafolio predeterminado sin perder historia.
5. La auditoría debe conservar el portafolio afectado.

## HU-OCR-01 · Extraer datos de documentos mediante OCR

**Prioridad MoSCoW:** `3 — Should Have`  
**Story Points:** `8 SP`

### Descripción

Como asistente administrativo quiero que el sistema proponga los datos de un recibo o factura para revisar y confirmar la obligación con menos digitación.

### Criterios de aceptación

1. Debe proponer emisor, RUC, código de servicio, número de documento, periodo, monto, moneda y vencimiento cuando pueda reconocerlos.
2. Cada campo debe mostrar su confianza y origen.
3. Ningún resultado de baja confianza debe confirmarse sin revisión humana.
4. La confirmación debe detectar duplicados antes de crear o modificar una obligación.
5. Debe conservarse el documento original y la corrección realizada por el usuario.

## HU-APR-01 · Aprobar pagos por excepción y por lote

**Prioridad MoSCoW:** `2 — Could Have`  
**Story Points:** `8 SP`

### Descripción

Como gerente quiero aprobar únicamente pagos que superen reglas de riesgo y revisar varios de ellos en un lote para mantener control sin bloquear todo el trabajo del asistente.

### Criterios de aceptación

1. Debe existir un modo directo y un modo de aprobación por reglas configurables.
2. Un lote debe conservar una instantánea de obligaciones, importes y cuentas al momento de aprobar.
3. Modificar un dato material después de la aprobación debe invalidarla.
4. Aprobar o rechazar debe registrar actor, fecha y observación.
5. El resultado de pago debe conservarse individualmente por obligación.

## HU-ANL-01 · Consultar proyección y anomalías de gasto

**Prioridad MoSCoW:** `2 — Could Have`  
**Story Points:** `5 SP`

### Descripción

Como gerente quiero conocer el efectivo requerido y las variaciones inusuales para anticipar decisiones antes del vencimiento.

### Criterios de aceptación

1. Debe mostrar importes pendientes para los próximos 7 y 30 días.
2. Debe separar empresa, local, categoría y moneda.
3. Una variación debe compararse con periodos históricos equivalentes y explicar su regla.
4. Los registros sin monto deben mostrarse aparte y no sumarse como cero.

## HU-NOT-01 · Recibir alertas externas

**Prioridad MoSCoW:** `1 — Won't Have Now`  
**Story Points:** `8 SP`

### Descripción

Como usuario autorizado quiero recibir alertas por correo o WhatsApp para conocer una urgencia aunque no tenga abierta la aplicación.

### Criterios de aceptación

1. El usuario debe elegir canal, categorías y horarios permitidos.
2. WhatsApp debe requerir consentimiento explícito y plantillas permitidas.
3. Los reintentos no deben duplicar el mismo aviso.
4. La baja de un canal debe respetarse inmediatamente.

## HU-INT-01 · Consultar obligaciones en portales de proveedores

**Prioridad MoSCoW:** `1 — Won't Have Now`  
**Story Points:** `13 SP`; debe dividirse por proveedor antes de entrar en un Sprint.

### Descripción

Como asistente administrativo quiero consultar importes y vencimientos desde fuentes autorizadas para reducir la revisión manual de portales.

### Criterios de aceptación

1. Cada proveedor debe implementarse mediante un adaptador independiente y observable.
2. Deben priorizarse APIs oficiales sobre automatización de navegador.
3. No deben guardarse credenciales en texto plano.
4. CAPTCHA, MFA o cambios de contrato deben enviar el caso a revisión manual sin bloquear otras cuentas.
5. La consulta debe ser idempotente y no duplicar obligaciones existentes.

## HU-REC-01 · Conciliar pagos y exportar información contable

**Prioridad MoSCoW:** `1 — Won't Have Now`  
**Story Points:** `8 SP`

### Descripción

Como gerente quiero confirmar que los pagos fueron aplicados y exportar sus datos para cerrar el ciclo con contabilidad.

### Criterios de aceptación

1. `Pagado` y `Conciliado` deben ser estados diferentes.
2. Una conciliación debe registrar fuente, referencia, actor y fecha.
3. Las diferencias deben quedar como excepción sin sobrescribir el pago original.
4. La exportación debe conservar empresa, local, proveedor, periodo, monto y referencias sin exponer documentos privados.

---

# Refinamientos P0 posteriores a la línea base

Los siguientes refinamientos son trazables a mejoras aceptadas del roadmap. No modifican la historia, los Story Points, las fechas ni el estado inicial de las HUs comprometidas; tampoco se les asignan Story Points sin una estimación formal del equipo.

## REF-P0-001 · Evidencia del flujo completo de pago

**Origen:** `MEJ-INV-001`, `CR-001`.  
**HUs que refina:** `HU-PROD-03`, `HU-PROD-05`, `HU-PROD-06`, `HU-DOC-01`, `HU-SEC-01`.  
**Estado:** En validación automatizada; no equivale a una HU original terminada ni sustituye la revisión manual pendiente.

El pago externo solo se podrá registrar cuando la obligación tenga un sustento y se adjunte un comprobante válido. La evidencia automática debe recorrer obligación → sustento → pago con comprobante → historial → dashboard, incluyendo el rechazo de pago sin sustento, sin comprobante, con monto distinto o repetido.

## REF-P0-002 · Permisos y trazabilidad de acciones sensibles

**Origen:** `MEJ-INV-002`, `CR-004`.  
**HUs que refina:** `HU-PROD-01`, `HU-PROD-02`, `HU-PROD-05`, `HU-CS-01`, `HU-CS-02`, `HU-SEC-01`.  
**Estado:** En validación automatizada; no equivale a una HU original terminada ni sustituye la revisión manual pendiente.

El mantenimiento e importación de cuentas de servicio corresponde al gerente. El asistente puede consultar y usar solo cuentas activas compatibles. Las páginas normales no exponen identificadores o números completos; su revelación requiere acción explícita, autorización de servidor y un evento seguro. Todo cambio sensible nuevo conserva actor, fecha y anterior/nuevo enmascarado.

## REF-P0-003 · Instantánea histórica de cuenta de destino

**Origen:** `MEJ-INV-003`, `CR-002`.  
**HUs que refina:** `HU-PROD-02`, `HU-PROD-05`, `HU-SEC-01`, `HU-CS-03`.  
**Estado:** En validación automatizada; no equivale a una HU original terminada ni sustituye la revisión manual pendiente.

Cada obligación conservará una instantánea del banco, titular y número de cuenta usado. Como el pago completo es uno a uno con la obligación, referencia esa instantánea sin duplicar datos bancarios. Editar la cuenta maestra no alterará la instantánea; los valores de cuenta se mostrarán enmascarados y el cambio dejará auditoría de anterior/nuevo sin exponer el número completo.

## REF-P0-005 · Importación y formularios sin datos parciales

**Origen:** `MEJ-INV-005`, `CR-003`.  
**HUs que refina:** `HU-PROD-03`, `HU-CS-01`, `HU-CS-03`, `HU-SEC-01`.  
**Estado:** En validación automatizada; no equivale a una HU original terminada ni sustituye la revisión manual pendiente.

La importación de cuentas de servicio acepta solo CSV UTF-8 y XLSX dentro de su límite propio, sin relajar las reglas de documentos de pago. Un archivo corrupto devuelve un error recuperable y una fila inválida revierte toda la operación. La validación de formularios no crea ni modifica acreedores hasta que el envío completo sea válido y se guarde dentro de su transacción.

---

# Especificaciones experimentales posteriores a la línea base

## Regla de uso

Los siguientes elementos describen comportamientos que el responsable del producto autorizó **solo para prototipado experimental** mediante `CR-005` y `CR-006`. Fueron especificados antes de programarse. No tienen MoSCoW, Story Points, horas, responsable, Sprint ni clave Jira. Si el prototipo es aprobado, deberán convertirse después en HUs refinadas y estimadas sin reescribir el Sprint original.

| ID | Capacidad experimental | Origen | Estado |
|---|---|---|---|
| EXP-LAB-01 | Administrar ámbitos y partes de una obligación | INV-002; MEJ-INV-015/016 | Verificada técnicamente — pendiente de validación de producto |
| EXP-LAB-02 | Proteger la privacidad por ámbito y registro | INV-002; MEJ-INV-017 | Verificada técnicamente — pendiente de validación de producto |
| EXP-LAB-03 | Registrar categorías especializadas, tarjetas y moneda | INV-001/002; MEJ-INV-018 | Verificada técnicamente — pendiente de validación de producto |
| EXP-LAB-04 | Configurar recurrencias flexibles | Akaunting/TimelyBills; MEJ-INV-019 | Verificada técnicamente — pendiente de validación de producto |
| EXP-LAB-05 | Registrar movimientos parciales y correcciones financieras | Melio/Zoho; MEJ-INV-020 | Verificada técnicamente — pendiente de validación de producto |
| EXP-LAB-06 | Detectar y resolver posibles duplicados | ERPNext/Asseta; MEJ-INV-009 | Verificada parcialmente — sin fusión automática |
| EXP-LAB-07 | Consultar calendario y recordatorios internos | TimelyBills/Zoho; MEJ-INV-011 | Verificada parcialmente — mes y agenda adaptable |
| EXP-LAB-08 | Importar obligaciones a una bandeja de revisión | Ramp/Zoho; MEJ-INV-011 | Verificada parcialmente — gerente y archivo transitorio |
| EXP-LAB-09 | Consultar actividad, filtros y dashboard multidimensional | Stampli/Alegra/Odoo; MEJ-INV-007/008/012 | Verificada parcialmente — actividad reciente no paginada |
| EXP-LAB-10 | Completar formularios contextuales sin campos innecesarios | FB-003; MEJ-INV-024; CR-005 | Verificada técnicamente — pendiente de validación de producto |
| EXP-LAB-12 | Ajustar operación PEN, excepciones, documentos, navegación y persistencia productiva | FB-006; MEJ-INV-025; CR-006 | Verificada técnicamente en local — despliegue y validación de producto pendientes |

La evidencia del corte anterior se encuentra en `evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md`. La evidencia local de `EXP-LAB-12` está en `evidencias/EXP-LAB_CR-006_IMPLEMENTACION_2026-10-18.md`; despliegue real y recorrido manual siguen pendientes.

## EXP-LAB-01 · Ámbitos y partes de una obligación

**Descripción experimental:** como gerente quiero indicar a quién o a qué corresponde cada obligación y distinguir a las personas y entidades relacionadas, para registrar pagos empresariales, propios, de hogares, familiares, terceros y entidades patrimoniales sin crear empresas ficticias.

### Criterios de experimento

1. El ámbito debe admitir al menos `Empresa`, `Personal`, `Hogar/propiedad`, `Familiar/tercero` y `Entidad patrimonial`.
2. Empresa y local solo deben solicitarse cuando el ámbito empresarial los necesite.
3. Deben registrarse por separado titular/deudor, beneficiario opcional y acreedor.
4. Debe registrarse una fuente de fondos y una naturaleza: propia, compartida, apoyo, reembolsable o préstamo.
5. Una persona beneficiaria no debe convertirse obligatoriamente en usuario.
6. Los registros empresariales existentes deberán poder migrarse a un ámbito empresarial sin perder documentos, historial ni identificadores.

## EXP-LAB-02 · Privacidad por ámbito y registro

**Descripción experimental:** como gerente quiero decidir qué ámbitos y obligaciones puede consultar o gestionar el asistente para proteger datos personales de familia, salud, asuntos legales y patrimonio.

### Criterios de experimento

1. La autorización debe aplicarse en servidor a listas, detalle, edición, archivos, vista previa, instrucciones de pago, historial, importación y reportes.
2. Cada ámbito debe permitir al menos acceso completo, acceso operativo con datos sensibles enmascarados y sin acceso.
3. Un registro especialmente sensible debe poder restringirse más que su ámbito.
4. Un identificador manipulado de un ámbito no autorizado debe responder sin revelar existencia ni contenido.
5. La actividad debe registrar actor, fecha, acción e identificadores técnicos, sin copiar datos médicos, legales o bancarios completos.

## EXP-LAB-03 · Categorías especializadas, tarjetas y moneda

**Descripción experimental:** como usuario autorizado quiero que el formulario se adapte al tipo real de obligación para registrar solo la información pertinente y evitar clasificaciones ambiguas.

### Criterios de experimento

1. El catálogo debe contemplar servicios, vivienda/propiedad, tarjeta, préstamo, impuesto, seguro, educación, salud, apoyo familiar, personal doméstico, vehículo, viaje/evento, inversión, donación, legal, suscripción, proveedor, emergencia y otro.
2. El formulario debe usar revelado progresivo y mostrar campos especializados solo cuando correspondan.
3. Una tarjeta debe guardar emisor, titular, últimos cuatro dígitos, ciclo, fecha de corte, vencimiento, total, mínimo y monto elegido.
4. El prototipo inicial debe representar una obligación por estado de cuenta y evitar contar nuevamente cada compra incluida.
5. Cada obligación y cada movimiento deben guardar moneda. Desde `CR-006`, las altas nuevas usan PEN; los registros USD anteriores se conservan en solo lectura y sus importes nunca se mezclan con PEN.

## EXP-LAB-04 · Recurrencias flexibles

**Descripción experimental:** como asistente quiero configurar la periodicidad real de un compromiso para no recrear manualmente cuotas, primas, renovaciones o pagos que no son mensuales.

### Criterios de experimento

1. Debe admitir pago único, semanal, quincenal, mensual, bimestral, trimestral, semestral, anual y una regla personalizada acotada.
2. Debe conservar fecha inicial, próxima ocurrencia, eventual fecha final y zona horaria.
3. Generar dos veces el mismo período no debe duplicar una obligación.
4. Debe poder omitirse una ocurrencia, pausarse o finalizarse el compromiso sin borrar períodos anteriores.
5. Cambiar una regla solo afecta ocurrencias futuras; cada obligación conserva su propio monto, fecha, estado y documentos.

## EXP-LAB-05 · Movimientos parciales y correcciones

**Descripción experimental:** como usuario autorizado quiero registrar lo que realmente ocurrió con el dinero para representar abonos, pago mínimo, devoluciones, disputas y reembolsos sin borrar la historia original.

### Criterios de experimento

1. Una obligación debe admitir varios movimientos y calcular total pagado y saldo abierto.
2. Debe distinguir pendiente, parcialmente pagada, pagada, suspendida, en disputa, anulada y reembolsada, sin confundir pago con conciliación bancaria.
3. Pago, devolución, anulación, contracargo, reembolso y ajuste deben ser eventos separados con monto, moneda, fecha, actor, motivo y evidencia cuando corresponda.
4. Una corrección no puede eliminar o sobrescribir el movimiento original.
5. Un pago superior al saldo, una moneda incompatible o una anulación sin motivo deben bloquearse o pasar a revisión explícita.
6. Debe poder registrarse un gasto adelantado por el gerente o asistente y su posterior reembolso sin doble conteo.

## EXP-LAB-06 · Duplicados con decisión humana

**Descripción experimental:** como asistente quiero recibir una advertencia cuando una obligación se parezca a otra para evitar pagar dos veces sin bloquear casos legítimos.

### Criterios de experimento

1. La comparación debe considerar ámbito, acreedor, número de documento, período, importe, moneda, suministro y huella del archivo cuando existan.
2. Una coincidencia exacta de referencia debe impedir el guardado salvo un flujo explícito de excepción autorizado.
3. Una coincidencia aproximada debe advertir y mostrar candidatos, sin decidir automáticamente que son duplicados.
4. Continuar, fusionar o cancelar debe quedar registrado con actor, fecha y motivo.
5. La importación y la creación manual deben usar la misma regla.

## EXP-LAB-07 · Calendario y recordatorios internos

**Descripción experimental:** como usuario autorizado quiero ver vencimientos y recordatorios dentro de PagoControl para anticipar obligaciones sin depender de mensajes externos.

### Criterios de experimento

1. Debe existir vista de agenda y calendario por día, semana o mes.
2. Los recordatorios deben calcularse desde vencimiento, prioridad, estado y configuración del ámbito.
3. Un mismo evento no debe crear avisos duplicados para la misma persona y canal interno.
4. Posponer u omitir un aviso no modifica el vencimiento ni borra el evento.
5. Correo, WhatsApp y notificaciones de terceros quedan fuera de este experimento mientras no exista otro cambio aprobado.

## EXP-LAB-08 · Importación de obligaciones con revisión

**Descripción experimental:** como asistente quiero cargar obligaciones desde CSV/XLSX para reducir digitación, revisarlas y corregirlas antes de que afecten la cola operativa.

### Criterios de experimento

1. La carga debe entrar a una bandeja temporal y no crear obligaciones definitivas en el primer paso.
2. Debe presentar vista previa, filas válidas, errores por fila, candidatos duplicados y totales por moneda.
3. Ámbitos, acreedores y categorías desconocidos no se crean silenciosamente; requieren mapeo o decisión explícita.
4. Confirmar debe ser transaccional: una regla de error definida no puede dejar importación parcial inadvertida.
5. Debe conservar lote, archivo original protegido, actor, fecha y resultado de cada fila.
6. La importación por correo y el OCR no forman parte de esta primera variante experimental.

## EXP-LAB-09 · Actividad, filtros y dashboard multidimensional

**Descripción experimental:** como gerente quiero entender qué pasó, qué requiere atención y cuánto dinero se necesita por ámbito y moneda para decidir sin mezclar datos incompatibles.

### Criterios de experimento

1. La ficha debe reunir datos, documentos, notas operativas y una actividad paginada de creación, edición, importación, suspensión, movimientos y accesos sensibles.
2. Debe poder filtrarse por ámbito, tipo de ámbito, empresa/local cuando aplique, titular, beneficiario, acreedor, categoría, moneda, estado, vencimiento y responsable.
3. El dashboard debe separar pendiente conocido, monto por definir, parcialmente pagado, vencido, suspendido, disputado, reembolsable y reembolsado.
4. Los totales deben presentarse por moneda o usar una conversión explícita; nunca sumar monedas silenciosamente.
5. Deben distinguirse flujo próximo, resultado del período y antigüedad de saldos.
6. Las notas no sustituyen la auditoría y no pueden editar eventos históricos.

## EXP-LAB-10 · Formularios contextuales

**Descripción experimental:** como gerente o asistente quiero ver únicamente los campos que corresponden a la decisión que estoy tomando, para completar cada registro con menos carga visual y sin enviar datos incompatibles.

### Criterios de experimento

1. Todo bloque que no aplique debe ocultarse, quedar deshabilitado y no enviarse al servidor.
2. Empresa y local aparecen únicamente en ámbitos empresariales; el servidor elimina esos valores en ámbitos personales, familiares o patrimoniales incluso ante una petición directa.
3. La categoría controla la cuenta de servicio y los datos especializados. En tarjeta, el total del estado de cuenta es el único monto y no se solicita un segundo importe genérico.
4. Pago único, recurrencia personalizada, día habitual y monto fijo o variable muestran solo las fechas y reglas que necesitan.
5. Efectivo no solicita banco, titular ni identificador; un servicio eventual no solicita día habitual; reactivar no exige el motivo usado para disputar o anular.
6. Cambiar temporalmente una selección conserva en la pantalla lo escrito por el usuario, pero solo envía los controles que vuelven a ser aplicables.
7. Si existe un error del servidor, la selección ligada debe mantener visible el bloque que contiene el campo y presentar el mensaje junto a este.
8. Los campos aplicables conservan etiqueta visible, obligatoriedad coherente, navegación por teclado y devolución segura del foco al alternar bloques.
9. La validación del servidor y las reglas de autorización siguen siendo obligatorias; el comportamiento visual no las reemplaza.

La especificación completa, las reglas transversales y la secuencia de experimentos se mantienen en `10_PLAN_EXPERIMENTAL_PROTOTIPO.md`.

## EXP-LAB-12 · Ajuste operativo y persistencia productiva

**Descripción experimental:** como gerente y asistente quiero operar con reglas simples y trazables en producción, para atender excepciones y corregir documentos sin perder historia ni asumir permisos que no corresponden.

### Criterios de experimento

1. Compromisos, obligaciones, fuentes y movimientos nuevos se registran solo en PEN; los datos USD existentes permanecen consultables, separados y sin edición financiera.
2. El asistente puede reportar falta de fondos con actor, fecha y observación, pero esa acción no suspende ni reactiva la obligación. Solo el gerente decide esas transiciones.
3. Un documento fuente puede retirarse lógicamente solo antes de cualquier movimiento, con motivo y auditoría. Se conserva el archivo y el registro; los comprobantes no se retiran por este flujo.
4. El asistente conserva Calendario y Cuentas de servicio en consulta y uso de registros compartidos. Crear, editar, importar o administrar configuración corresponde al gerente.
5. Producción usa PostgreSQL de Supabase y un bucket privado de Supabase Storage; Vercel no conserva datos ni adjuntos en su disco efímero.
6. Deben existir pruebas negativas de permisos, inmutabilidad USD, retiro posterior a movimientos, acceso privado a archivos y persistencia sobre PostgreSQL/Storage antes de declarar la capacidad verificada.

**Estado:** implementada y verificada localmente mediante `CR-006`, migración `payments.0010` y 84 pruebas automatizadas aprobadas. Despliegue con PostgreSQL/Storage reales y validación manual por roles pendientes.
