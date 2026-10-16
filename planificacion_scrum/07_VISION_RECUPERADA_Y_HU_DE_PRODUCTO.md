# Visión recuperada y HUs de producto

## 1. Propósito y estado

Este anexo recupera la visión funcional redactada inicialmente para PagoControl y la adapta al sistema Django que existe actualmente. Su propósito es conservar el razonamiento de producto y facilitar la conversación con el profesor.

**No modifica por sí solo** el Sprint original, los Story Points, las horas, los estados ni la velocidad documentados en los archivos `01` a `06`. Cualquier ítem que se decida implementar debe pasar por el control de cambios.

Las referencias externas y la decisión operativa de cada mejora se registran en `08_INVESTIGACION_DE_REFERENTES_Y_BENCHMARK.md` y `09_MATRIZ_DE_MEJORAS_Y_TRAZABILIDAD.md`.

**Actualización experimental:** la visión organizacional de este anexo se conserva como antecedente. `CR-005` amplió el prototipo local para obligaciones empresariales, personales, familiares y patrimoniales; la especificación vigente está en `10_PLAN_EXPERIMENTAL_PROTOTIPO.md` y su evidencia en `evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md`.

## 2. Visión del producto

PagoControl es un sistema de **cuentas por pagar** para una organización donde:

- el asistente registra obligaciones, ejecuta pagos fuera de la aplicación y adjunta evidencia;
- el gerente supervisa el mes, completa excepciones y protege los datos sensibles de pago;
- el sistema reúne en una sola agenda qué se debe pagar, cuándo, a quién y qué información falta.

El criterio principal es: **si agrega pasos innecesarios al asistente, no sirve**. La trazabilidad debe proteger tanto al gerente como al asistente cuando una demora proviene de un monto pendiente o de una retención gerencial.

## 3. Equivalencia con el sistema actual

| Concepto de negocio | Implementación actual | Regla funcional |
| --- | --- | --- |
| Beneficiario | `Creditor` + `DestinationAccount` | El acreedor y sus datos de pago se reutilizan. |
| Contrato, suministro o cliente | `ServiceAccount` | Identifica un servicio por empresa y local. |
| Deuda concreta | `Payable` | Tiene monto, vencimiento, período, documento y estado. |
| Pago | `Payment` + `Attachment` | Un pago completo exige comprobante. |
| Repetición mensual | `PaymentCommitment` | Genera obligaciones sin duplicar el período. |
| Por definir monto | Pendiente sin monto / incompleta | Excepción dirigida al gerente; no es un cuarto estado administrativo. |
| Retenida / no pagar | `SUSPENDED` + motivo | No se presenta como atraso del asistente. |
| Vencida, hoy o próxima | Estado visual calculado | Se mantiene la regla aprobada de 5 días hasta nueva confirmación. |

## 4. Relación con el Product Backlog original

| HU de producto recuperada | Relación con la planificación original | Estado de la idea |
| --- | --- | --- |
| Acceder según rol | Regresión transversal; ya existe autenticación y permisos | Implementada; reforzar con pruebas negativas. |
| Guardar beneficiarios, cuentas y referencias | HU-CS-01, HU-CS-02, HU-CS-03 y HU-SEC-01 | Implementada en gran parte; quedan mejoras de historial y consulta del asistente. |
| Registrar deuda rápido | HU-EXP-01 | Parcial; requiere flujo guiado y menos repetición de datos. |
| Ver qué toca pagar | Tablero existente y HU-ALT-01 | Implementada en gran parte; falta mejorar filtros y días de atraso. |
| Pagar y registrar evidencia | Flujo base existente | Implementada en gran parte; quedan confirmación, historial inmutable y manejo de diferencias. |
| Ver el mes de un vistazo | Dashboard actual y HU-ANL-01 | Implementada en gran parte; faltan montos desconocidos y vencidos históricos claros. |
| Retener o definir monto | Suspensión existente y mejoras de excepción | Parcial; falta un flujo explícito para completar el monto. |
| Validar cuenta nueva o modificada | Extensión de HU-APR-01 | Propuesta futura; no es aprobación por cada pago. |
| Revisar eventos inusuales | Extensión de HU-ANL-01 | Propuesta futura. |

## 5. Historias de usuario funcionales

### HU-PROD-01 — Entrar según mi rol

Como gerente o asistente, quiero iniciar sesión y ver únicamente las acciones que me corresponden.

**Criterios de aceptación**

1. Sin sesión no se accede a obligaciones, pagos ni documentos.
2. El asistente llega a su cola operativa y el gerente al control gerencial.
3. El asistente registra obligaciones, adjunta documentos y registra pagos.
4. El gerente administra cuentas de destino, suspende/reactiva y completa excepciones.
5. Los permisos se validan en el servidor, incluso ante una URL o petición directa.

### HU-PROD-02 — Reutilizar beneficiarios y referencias de pago

Como asistente, quiero seleccionar datos ya conocidos para no volver a escribir banco, cuenta, suministro o contrato en cada período.

**Criterios de aceptación**

1. Un acreedor puede tener varias cuentas de destino y varios contratos o suministros.
2. Cada cuenta de servicio coincide con empresa, local opcional y acreedor.
3. La pantalla diferencia el suministro/contrato del número de factura o recibo del período.
4. El asistente puede consultar datos autorizados, pero no cambiar cuentas de destino.
5. Cambiar una cuenta de destino registra actor, fecha y valores anterior/nuevo, sin alterar pagos históricos.

### HU-PROD-03 — Registrar una obligación rápida

Como asistente, quiero registrar una factura, recibo, impuesto o préstamo con la menor digitación posible.

**Criterios de aceptación**

1. Desde un compromiso, se completan automáticamente empresa, local, categoría, acreedor y cuentas asociadas.
2. Solo se solicitan los datos del período: monto, vencimiento, documento externo y sustento disponible.
3. Una obligación tributaria puede nacer sin monto y mostrarse como “Por definir monto”.
4. Se advierte un posible duplicado por acreedor, documento, período o suministro, sin bloquear casos legítimos automáticamente.
5. Un formulario inválido no crea acreedores ni otros datos parciales.
6. Con datos conocidos, el registro debe poder realizarse en 30 segundos o menos durante una prueba de usabilidad.

### HU-PROD-04 — Ver qué toca pagar sin configurar filtros

Como asistente, quiero abrir el sistema y saber de inmediato qué resolver primero.

**Criterios de aceptación**

1. La pantalla inicial muestra primero vencidas, luego vence hoy, próximas dentro de 5 días y finalmente las demás pendientes.
2. Las vencidas muestran los días de atraso.
3. Las pagadas y suspendidas no aparecen en la cola principal.
4. La cola muestra excepciones de monto, sustento, cuenta de servicio y preparación de pago.
5. Los filtros por empresa/local se conservan al abrir atajos de excepciones.

### HU-PROD-05 — Pagar externamente y registrar evidencia

Como asistente, quiero consultar los datos de pago y registrar el resultado cuando lo ejecute en banco, portal o agente.

**Criterios de aceptación**

1. La ficha muestra cuenta o instrucción externa, titular, referencia de pago y monto.
2. El sistema permite copiar la referencia y confirma de manera accesible el resultado.
3. Registrar un pago exige comprobante PDF/JPG/PNG válido y guarda fecha, usuario y referencia de operación si se solicita.
4. Antes de confirmar, muestra un resumen del pago y evita doble envío.
5. No permite un segundo pago completo sobre la misma obligación.
6. Tras pagar, la obligación sale de la cola y aparece en historial y dashboard.

### HU-PROD-06 — Supervisar el mes con cifras honestas

Como gerente, quiero ver pagado, pendiente, vencido, suspendido y obligaciones sin monto para decidir rápidamente.

**Criterios de aceptación**

1. El mes seleccionado muestra cantidades e importes de pagado, pendiente, vencido y suspendido, sin doble conteo.
2. Las obligaciones sin monto se muestran por separado y no se presentan como S/ 0.00 sin aviso.
3. Los vencidos de períodos previos permanecen visibles hasta resolverse.
4. El dashboard diferencia “liquidez próxima desde hoy” de “resultado del mes seleccionado”.
5. Cada métrica abre un detalle realmente filtrado o no se presenta como enlace.

### HU-PROD-07 — Resolver excepciones sin atribuir retrasos injustos

Como gerente, quiero retener un pago o completar un monto pendiente sin que el asistente quede marcado como responsable de esa demora.

**Criterios de aceptación**

1. Suspender exige un motivo y reactivar conserva el historial de la suspensión.
2. Definir el monto registra actor, fecha y valor antes/después.
3. Una obligación retenida o sin monto se destaca como tarea del gerente.
4. Al resolver la excepción, la obligación vuelve a la cola operativa sin perder documentos ni auditoría.

### HU-PROD-08 — Validar cambios sensibles de datos de pago

Como gerente, quiero validar cuentas nuevas o cambios de cuenta para reducir el riesgo sin aprobar cada pago cotidiano.

**Estado:** propuesta posterior al Sprint original; requiere cambio aprobado.

**Criterios de aceptación**

1. Una cuenta nueva o modificada queda pendiente de validación antes de usarse para pagar.
2. El gerente ve cuenta anterior/nueva, solicitante, fecha, motivo y sustento disponible.
3. Aprobar o rechazar deja una auditoría inmutable con motivo.
4. Las cuentas ya autorizadas permiten al asistente seguir pagando sin una aprobación por operación.

## 6. Reglas de alcance

### Entra en la conversación de mejora

- Flujo guiado de obligaciones y datos dependientes.
- Conservación histórica de cuentas de destino.
- Manejo explícito de monto pendiente y suspensión.
- Pruebas de reglas financieras y permisos.
- Demo reproducible con datos ficticios y criterios observables.

### Se mantiene fuera hasta una nueva decisión

- Transferencias ejecutadas desde la aplicación.
- Pagos parciales, conciliación bancaria y presupuesto completo.
- Correo, WhatsApp, OCR, API bancaria, scraping y consulta en tiempo real de proveedores.
- Aprobación de todos los pagos o lotes de aprobación generalizados.
- Moneda múltiple, salvo que el profesor confirme pagos distintos a soles.

## 7. Preguntas para validar con el profesor

| Pregunta | Supuesto de planificación actual |
| --- | --- |
| ¿“Pagar con el sistema” es transferir o registrar pago externo? | El asistente paga fuera y registra comprobante. |
| ¿Qué impuestos se controlan y quién define el monto? | SUNAT puede generarse sin monto hasta la declaración del gerente. |
| ¿La alerta debe ser de 5 o 7 días? | 5 días, según requisito actual. |
| ¿Hay pagos en USD u otra moneda? | Solo soles. |
| ¿Quiere aprobar cuentas nuevas o solo ver alertas? | El gerente administra cuentas; validación previa es mejora opcional. |
| ¿Cuántas obligaciones existen por mes y cómo llegan documentos? | Menos de 50; carga manual mientras no se acuerde otra fuente. |
| ¿La entrega debe cubrir pagos personales, familiares y patrimoniales además de empresas? | Sí para el laboratorio experimental autorizado mediante `CR-005`; la versión que pase a la guía Scrum definitiva se decidirá después de validar el prototipo y recién entonces se estimará. |

## 8. Criterios transversales de experiencia y seguridad

- Los formularios tienen etiquetas visibles, ayuda clara y errores junto al campo.
- Tras un error, se conserva lo ingresado, aparece un resumen enfocable y el mensaje se anuncia de forma accesible.
- Las acciones irreversibles muestran una confirmación y bloquean doble clic mientras se procesan.
- En celular, navegación y botones esenciales siguen disponibles y tienen objetivos táctiles de al menos 44 × 44 px.
- Los estados usan texto e iconos además de color, con contraste suficiente.
- Los pagos y comprobantes no se borran; una reversión futura debe dejar motivo, actor y fecha.
- Los datos de demostración son ficticios; no se exponen cuentas ni credenciales reales.

## 9. Guion de demostración sugerido

1. El gerente detecta una obligación vencida y otra sin monto.
2. El asistente abre su cola y registra una obligación desde un compromiso existente.
3. Revisa la referencia de pago, adjunta evidencia de demostración y registra el pago.
4. El gerente actualiza el panel y comprueba el cambio en historial y totales.
5. El gerente suspende una obligación con motivo; el asistente la ve como retenida, no como atraso suyo.
6. Se muestra la cuenta de servicio y la generación idempotente del siguiente período.

## 10. Uso de este anexo

Antes de incorporar una HU de este archivo al Sprint o modificar una HU existente:

1. registrarla en `06_FEEDBACK_Y_CONTROL_DE_CAMBIOS.md`;
2. identificar las historias, criterios, modelos y pruebas afectadas;
3. estimarla de nuevo con el equipo;
4. retirar alcance equivalente si el Sprint ya está comprometido;
5. actualizar el cronograma y las subtareas sin inventar tiempos reales.
