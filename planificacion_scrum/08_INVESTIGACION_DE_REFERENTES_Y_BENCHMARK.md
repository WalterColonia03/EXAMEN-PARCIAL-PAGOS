# Investigación de referentes y benchmarking funcional

## 1. Estado, propósito y límite de interpretación

**Fuentes:** `INV-001` — véase `evidencias/INV-001_investigacion_sistemas_similares.md`; e `INV-002` — véase `evidencias/INV-002_ambitos_personales_familiares_y_patrimoniales.md`.  
**Estado:** Registrada como fuente de mejora; no es evidencia de funcionalidades implementadas.  
**Decisión asociada:** `CR-001` en `06_FEEDBACK_Y_CONTROL_DE_CAMBIOS.md`.

El benchmarking sirve para contrastar el enfoque de PagoControl con productos de cuentas por pagar, recordatorios de vencimiento y supervisión financiera. Se utiliza para responder cuatro preguntas:

1. ¿Qué prácticas refuerzan el problema real de PagoControl?
2. ¿Cuáles encajan con la arquitectura y alcance actuales?
3. ¿Qué ideas deben esperar por costo, riesgo o dependencia externa?
4. ¿Qué evidencia permitirá decir que una adaptación funciona en nuestro proyecto?

No se copiará un producto ni se afirmará que una función comercial exista en PagoControl solo por aparecer en una referencia.

## 2. Posicionamiento de PagoControl

PagoControl no es un ERP ni una plataforma bancaria. Es un sistema web de gestión y seguimiento de obligaciones de pago que:

- centraliza compromisos recurrentes y extraordinarios;
- prioriza vencimientos y excepciones;
- conserva documentos de sustento y evidencias de pago;
- separa el trabajo operativo del asistente de la supervisión del gerente;
- registra pagos realizados fuera de la aplicación;
- conserva trazabilidad sin obligar a aprobar cada operación cotidiana.

## 3. Referentes documentados en la investigación

Los enlaces siguientes fueron citados por la fuente `INV-001`. Se guardan como inspiración y punto de consulta; no fueron revalidados para convertir sus funciones en requisitos propios.

| Referente | Patrón observado en la investigación | Adaptación posible para PagoControl | Referencia citada |
|---|---|---|---|
| Melio | Marcar y separar pagos realizados externamente | Pago externo + comprobante + historial, sin integración bancaria | [Guía de pagos externos](https://help.melio.com/hc/en-us/articles/6641702618012-Mark-bills-as-paid-unpaid) |
| Zoho Books | Obligaciones, documentos, filtros y estados | Ficha completa de una obligación y dashboard sin contabilidad general | [Cuentas por pagar](https://www.zoho.com/us/books/accounting-software/bills/) |
| Akaunting | Plantilla recurrente distinta de factura concreta | `PaymentCommitment` genera `Payable` por período sin cambiar históricos | [Documentación de bills](https://akaunting.com/hc/docs/bills/) |
| TimelyBills | Jerarquía visual de vencimientos y recurrencias | Tarjetas del asistente con urgencia, bloqueo y próximo paso | [Bill organizer](https://www.timelybills.app/bill-organizer) |
| Stampli | Documento, actividad y auditoría centrados en la factura | Línea de tiempo de datos, documentos y acciones dentro de la obligación | [Invoice audit trails](https://www.stampli.com/invoice-audit-trails/) |
| BILL / ERPNext / Holded | Roles, excepciones, prevención de duplicados y tareas pendientes | Permisos en servidor, trazabilidad y advertencias de calidad de datos | Referentes secundarios de INV-001 |
| Alegra | Resúmenes simples de cuentas por pagar | Panel gerencial adaptado a empresas/locales peruanos | Referente secundario de INV-001 |

## 4. Hallazgos que se conservan

### 4.1 Pago externo con evidencia, no banca integrada

La investigación confirma la decisión de alcance actual: el asistente paga en banco, portal o agente y luego registra la evidencia. PagoControl no debe afirmar que el banco validó el archivo ni prometer conciliación sin una integración real.

### 4.2 Compromiso recurrente y obligación del período son entidades distintas

Un servicio mensual conserva proveedor, suministro y recurrencia; cada mes genera una obligación con su propio importe, vencimiento, documento, comprobante y estado. Es exactamente la separación que ya representan `PaymentCommitment`, `ServiceAccount` y `Payable`.

### 4.3 La cola debe enseñar qué hacer, no solo qué existe

La prioridad no depende de que el usuario marque “vencida”. Debe calcularse desde la fecha y comunicar también bloqueos: monto pendiente, sustento faltante, cuenta de servicio pendiente y retención del gerente.

### 4.4 La ficha de obligación es el centro de trazabilidad

La ficha debe dejar visibles, sin saturar:

1. datos de obligación y referencia de pago;
2. documento de sustento y comprobante;
3. actividad: creación, ediciones, suspensión, pago y descargas relevantes.

### 4.5 La supervisión necesita cifras honestas

El panel gerencial debe separar importe conocido de obligaciones sin monto. También debe distinguir liquidez futura desde hoy del resultado del mes que se está consultando.

## 5. Decisiones de alcance derivadas

| Tipo de idea | Tratamiento en PagoControl |
|---|---|
| Flujo principal, permisos, recurrencia, documentos y evidencia | Adoptar o reforzar; son el núcleo demostrable. |
| Tarjetas, filtros, línea de tiempo, dashboard honesto y advertencia de duplicados | Adaptar gradualmente como mejoras de producto. |
| Validar cuentas nuevas o modificadas sin aprobar cada pago | Diseñar como capacidad futura, no como cambio silencioso del Sprint. |
| Calendario, comentarios, búsqueda avanzada e importación de obligaciones | Posponer hasta que el volumen o el profesor lo justifiquen. |
| OCR, transferencias bancarias, conciliación y notificaciones externas | Fuera del MVP; requieren integraciones y controles adicionales. |
| Contabilidad general o ERP completo | Descartar; contradice el objetivo de simplicidad. |

## 6. Relación con documentación del proyecto

| Documento | Cómo se relaciona con este benchmark |
|---|---|
| `01_REVISION_ESTADO_Y_ALCANCE.md` | Conserva el alcance formal y las brechas verificadas. |
| `02_HISTORIAS_DE_USUARIO.md` | Solo se modifica si una mejora acepta convertirse en HU refinada. |
| `06_FEEDBACK_Y_CONTROL_DE_CAMBIOS.md` | Registra INV-001, CR-001 y futuros cambios aprobados. |
| `07_VISION_RECUPERADA_Y_HU_DE_PRODUCTO.md` | Contiene la visión funcional y las HUs de producto relacionadas. |
| `09_MATRIZ_DE_MEJORAS_Y_TRAZABILIDAD.md` | Convierte los hallazgos en decisiones operativas y evidencia requerida. |

## 7. Regla para futuras investigaciones

Toda nueva referencia externa debe registrar: fuente, fecha, alcance, limitaciones, hallazgo, decisión, HU afectada, prioridad y evidencia requerida. Si una idea implica datos, permisos, migraciones o trabajo de Sprint, también necesita un `CR` antes de entrar en ejecución.

## 8. Extensión investigada: vida personal, familia y patrimonio

`INV-002` amplía el benchmark desde cuentas por pagar empresariales hacia gestión doméstica y family office. La revisión cruzó el código actual con documentación oficial de Quicken, SBS, Sunass, ANPD, J.P. Morgan, Asseta, Melio y Zoho Books.

### Hallazgo principal

La obligación no debe depender conceptualmente de una empresa. El concepto raíz recomendado es un **ámbito administrado** —empresa, persona, hogar/propiedad, familiar/tercero u otra entidad patrimonial— y debe separarse de estas partes:

- titular o deudor;
- beneficiario;
- acreedor;
- fuente de fondos;
- naturaleza del pago a un tercero: propio, compartido, apoyo, reembolsable o préstamo.

Esto cubre, sin datos ficticios, servicios de la casa de un familiar, préstamos personales, pagos de pareja o dependientes, tarjetas, seguros, propiedades, personal doméstico, educación, salud, viajes, capital calls, donaciones y emergencias.

### Consecuencia de alcance

No es un cambio de texto ni una categoría adicional: afecta esquema, migración, filtros, reportes, importación, permisos por objeto y pruebas de acceso. Se registró como `MEJ-INV-015` y fue autorizado mediante `CR-005` el 15/10/2026 para construcción experimental. Esto no lo convierte automáticamente en alcance del Sprint histórico ni en funcionalidad terminada: cada parte debe implementarse, probarse y validarse según el documento `10_PLAN_EXPERIMENTAL_PROTOTIPO.md`.
