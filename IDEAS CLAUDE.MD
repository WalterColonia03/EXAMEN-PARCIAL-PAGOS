# Visión y mejoras adaptadas — PagoControl

> Documento reconstruido a partir de las ideas originales recuperadas, los requisitos del curso y la implementación actual de PagoControl.
>
> Principio rector: el sistema debe reducir el trabajo administrativo del asistente y darle al gerente visibilidad, no convertirse en un ERP ni obligar a aprobar cada pago.

## 1. Problema que realmente resuelve el sistema

PagoControl es un sistema de **cuentas por pagar**: reúne en una sola agenda qué se debe pagar, cuándo, a quién, con qué referencia y si ya se realizó.

El asistente es el usuario operativo principal: registra obligaciones, adjunta documentos, ejecuta el pago fuera de la aplicación y sube su comprobante. El gerente supervisa el mes, atiende excepciones y administra los datos sensibles de pago.

La confianza no depende de perseguir aprobaciones por cada pago. Depende de datos de pago autorizados, evidencia, trazabilidad y una cola que deje claro cuándo una demora no es responsabilidad del asistente.

## 2. Alcance del MVP

### Incluye

- Servicios, proveedores, impuestos, préstamos y otros compromisos de pago.
- Empresas y locales.
- Compromisos recurrentes y obligaciones concretas por período.
- Beneficiarios, cuentas de destino y datos de pago reutilizables.
- Cuentas de servicio o contrato para luz, agua, internet, telefonía y casos similares.
- Documento de sustento y comprobante de pago privados.
- Tablero diario del asistente y panel mensual del gerente.
- Retención o suspensión excepcional por el gerente.
- Historial de quién hizo qué y cuándo.

### Queda fuera por ahora

- Transferencias bancarias ejecutadas por PagoControl.
- Flujos de aprobación para cada pago.
- Pagos parciales, conciliación bancaria y presupuesto contable.
- WhatsApp, correo, OCR, lectura de códigos de barras, API bancaria y Google Calendar.
- Reescritura del proyecto en otro framework.

Los ingresos no forman parte del sistema. Los compromisos mensuales sí pueden representar gastos recurrentes; no deben excluirse por ser “fijos”.

## 3. Traducción de las ideas al modelo que ya existe

| Idea funcional | Modelo actual de PagoControl | Regla adaptada |
| --- | --- | --- |
| Beneficiario | `Creditor` + `DestinationAccount` | El beneficiario se registra una vez; sus cuentas de destino solo las administra el gerente. |
| Contrato, suministro o cliente | `ServiceAccount` | Un proveedor puede tener varios suministros, por empresa y local. |
| Deuda concreta | `Payable` | Es una obligación con monto, vencimiento, período, documento y estado. |
| Pago | `Payment` + comprobante `Attachment` | Un pago completo por obligación; comprobante obligatorio. |
| Repetición mensual | `PaymentCommitment` | Genera obligaciones por período sin duplicarlas. |
| “Por definir monto” | Obligación pendiente sin monto, marcada como incompleta | Es una excepción calculada, no un cuarto estado administrativo. |
| “Retenida / no pagar” | `Payable.Status.SUSPENDED` + motivo | No aparece como atraso del asistente y el gerente puede reactivarla. |
| Vencida, hoy, próxima, pendiente | Estado visual calculado | Nunca se marca manualmente. Se conserva la regla actual de **5 días** de anticipación hasta que el profesor confirme otra. |

Esta equivalencia evita duplicar entidades o romper la arquitectura Django ya implementada.

## 4. Reglas de negocio que deben guiar la siguiente etapa

1. El asistente paga de manera autónoma obligaciones con datos de destino ya autorizados.
2. El gerente puede suspender o reactivar una obligación, completar un monto pendiente y administrar las cuentas de destino.
3. Una obligación sin monto, documento de sustento o cuenta de servicio debe indicar claramente qué falta y quién debe resolverlo.
4. Una demora causada por monto pendiente o retención del gerente no se presenta como incumplimiento del asistente.
5. “Pagado” exige un comprobante válido y no permite un segundo pago completo.
6. Nada financiero se elimina de forma silenciosa: se desactiva, suspende, anula o revierte con motivo y auditoría.
7. Los datos bancarios que se usaron en un pago deben conservarse como historia, aunque la cuenta actual cambie después.
8. Para un monto distinto al registrado, no se debe sobrescribir el importe sin explicación: se corrige la obligación o se registra una diferencia/mora con motivo y trazabilidad.

## 5. Historias de usuario adaptadas

### HU1 — Entrar según mi rol

Como gerente o asistente, quiero iniciar sesión y ver mi área de trabajo sin exponer funciones que no me corresponden.

**Criterios de aceptación:**

- Sin sesión no se accede a pagos ni documentos.
- El asistente llega a su cola de trabajo; el gerente al control gerencial.
- Las validaciones de permisos viven en el servidor, no solo en botones ocultos.
- `ADMIN`, si se conserva, se considera rol técnico y no un tercer rol de negocio.

### HU2 — Guardar beneficiarios y referencias una sola vez

Como asistente, quiero elegir datos ya conocidos para no volver a escribir banco, cuenta, suministro o contrato.

**Criterios de aceptación:**

- Un acreedor puede tener varias cuentas de destino y varias cuentas de servicio.
- Servicio, empresa, local, acreedor e identificador deben ser coherentes entre sí.
- Se puede desactivar una cuenta o compromiso sin destruir su historial.
- Todo cambio de cuenta destino registra actor, fecha y valores anterior/nuevo.
- El asistente puede consultar cuentas autorizadas, pero no crearlas ni editarlas.

### HU3 — Registrar una obligación rápido

Como asistente, quiero registrar una factura, recibo o impuesto en menos de 30 segundos cuando ya existe el acreedor o compromiso.

**Criterios de aceptación:**

- Desde un compromiso, empresa, local, categoría, acreedor y cuentas asociadas se completan automáticamente.
- Solo se pide la información propia del período: monto, vencimiento, documento externo y sustento si está disponible.
- Para SUNAT u obligaciones equivalentes puede existir el vencimiento sin monto; se envía a “Por definir monto”.
- El sistema advierte posibles duplicados por acreedor, número de documento, período o suministro; no bloquea ciegamente casos legítimos.
- Un formulario inválido no crea acreedores ni otros datos huérfanos.

### HU4 — Abrir y saber qué toca pagar

Como asistente, quiero que la pantalla inicial me muestre qué resolver primero, sin tener que configurar filtros.

**Criterios de aceptación:**

- La cola se ordena: vencidas, vence hoy, próximas dentro de 5 días y más adelante.
- Las vencidas muestran días de atraso.
- Pagadas y suspendidas salen de la cola principal.
- Se ven claramente las excepciones: sin monto, sin sustento, sin cuenta de servicio y lista para pagar.
- Filtros por empresa/local se muestran antes del listado, se conservan al abrir accesos rápidos y muestran chips activos.

### HU5 — Ejecutar el pago y registrarlo

Como asistente, quiero ver el monto y los datos de pago, copiar la referencia y dejar constancia al terminar.

**Criterios de aceptación:**

- La ficha muestra banco, cuenta o instrucción externa, titular, suministro/contrato y monto.
- El botón de copiar confirma accesiblemente si copió o falló.
- Registrar pago pide comprobante PDF/JPG/PNG y, si se decide con el profesor, referencia de operación única.
- Antes de confirmar, se muestra un resumen de monto, fecha y archivo; el envío bloquea doble clics mientras procesa.
- La obligación desaparece de la cola y aparece en historial y dashboard al instante.
- No se permite un segundo pago completo sobre la misma obligación.

> La regla actual de un pago por obligación es correcta para el MVP. Si se necesitan moras o diferencias, debe ampliarse el modelo de forma explícita; no se debe reutilizar “monto pagado” para ocultar la diferencia.

### HU6 — Ver el mes de un vistazo

Como gerente, quiero conocer pagado, pendiente, vencido, suspendido y datos pendientes del período.

**Criterios de aceptación:**

- Muestra cantidad e importe de pagado, pendiente, vencido y suspendido sin doble conteo.
- Distingue “importe conocido” de “N obligaciones sin monto”; nunca presenta los montos desconocidos como S/ 0.00 sin aviso.
- El resultado del mes seleccionado se distingue de la liquidez próxima desde hoy.
- También muestra vencidos de períodos anteriores para que ninguna obligación desaparezca por cambiar de mes.
- Cada métrica enlaza a un detalle realmente filtrado, o se presenta como tarjeta informativa sin enlace engañoso.

### HU7 — Resolver excepciones sin culpar al asistente

Como gerente, quiero retener un pago, reactivarlo o definir un importe pendiente sin que la cola pierda contexto.

**Criterios de aceptación:**

- Suspender exige motivo; reactivar conserva el historial de la suspensión.
- Definir monto deja una auditoría y vuelve la obligación a la cola operativa.
- Una retención o monto por definir se destaca como tarea del gerente, no como atraso del asistente.

## 6. Control preventivo: lo recomendable sin romper la autonomía

El MVP actual ya protege que el asistente no modifique cuentas destino. Si el profesor prioriza prevención de fraude, la extensión adecuada no es aprobar cada pago: es una **validación del gerente solo para beneficiarios nuevos o cambios de cuenta destino**.

| Caso | Control recomendado | Prioridad |
| --- | --- | --- |
| Pago a cuenta ya autorizada | El asistente paga y registra evidencia sin aprobación | MVP actual |
| Nueva cuenta o cambio de cuenta | Propuesta pendiente de validación del gerente, con antes/después y motivo | Siguiente fase |
| Pago diferente al importe registrado | Corrección con motivo y alerta de diferencia | Siguiente fase |
| Comprobante repetido | Rechazar por referencia de operación repetida y advertir sobre archivo reutilizado | Siguiente fase |
| Pago ya registrado | Bloqueo total de segundo pago completo | MVP actual |
| Pago externo al sistema | No puede detectarse desde PagoControl; se cubre con controles y alertas del banco | Fuera del sistema |

No se debe prometer que el sistema “impide todo fraude”. Sí debe hacer los cambios sensibles difíciles, trazables y visibles.

## 7. Pago real para la demo

La interpretación viable es: el asistente realiza el pago en su banco, portal o agente, y luego registra la evidencia en PagoControl. Esta es la modalidad que el sistema actual ya soporta y es coherente con los requisitos.

No se deben usar transferencias reales ni cuentas personales en una demostración académica sin autorización explícita. Usar beneficiarios y cuentas claramente ficticios, por ejemplo con prefijo `DEMO-`, más comprobantes de ejemplo. Nunca subir números reales a un repositorio.

Para servicios e impuestos, la ficha debe admitir una **referencia de pago**: suministro, contrato, NPS, código de contribuyente o número de cuota. No se asume que toda entidad usa una cuenta bancaria fija.

## 8. Mejoras técnicas y de producto priorizadas

### P0 — bloquear riesgos y cerrar la demo

1. **Reparar importación CSV/XLSX.** La validación JavaScript global de archivos trata el importador como si fuera un comprobante PDF/JPG/PNG y bloquea archivos válidos. Separar validación de importación y documentos.
2. **Conservar la instantánea bancaria histórica.** Una `DestinationAccount` editable no puede cambiar lo que muestra un pago antiguo. Versionar la cuenta o copiar sus datos al usarla.
3. **Eliminar efectos de base de datos durante `form.clean()`.** Crear acreedores y auditoría dentro de servicios transaccionales, después de validar todo.
4. **Completar pruebas de negocio.** Cubrir urgencia, permisos, pago sin comprobante, doble pago, suspensión, filtros, totales, descarga privada, importación y conservación histórica.
5. **Completar datos demo y README.** Dos empresas, dos locales, gasto sin local, proveedor en dos locales, servicio, suscripción, agua, tributo, préstamo, pagada, pendiente, vencida y suspendida; el seed debe ser idempotente.
6. **Corregir errores y móvil.** Los errores de pago/adjunto deben volver al formulario con su campo y foco; el detalle debe pasar a una columna en móvil; no ocultar acciones esenciales de la navegación móvil.

### P1 — reducir pasos y mejorar control diario

1. Registro guiado desde compromiso, con campos derivados y selectores dependientes.
2. Estado de preparación calculado a partir de monto, sustento y cuenta de servicio; no depender solo de una casilla manual.
3. CRUD mínimo y con desactivación para empresas, locales, acreedores y compromisos; editar un compromiso afecta únicamente obligaciones futuras.
4. Catálogo de cuentas de destino de solo lectura para asistente y edición exclusiva del gerente.
5. Vista previa de generación mensual: se crearán, ya existen y requieren corrección.
6. Importación con prevalidación, reporte por fila, normalización de identificadores y conciliación opcional con compromisos/obligaciones existentes.
7. Filtros visibles, búsqueda y paginación cuando el volumen lo requiera.

### P2 — preparación para uso real y extensiones opcionales

1. Línea de tiempo unificada con valores anterior/nuevo para cambios sensibles.
2. Reversión o anulación controlada de pagos: nunca borrar, siempre con motivo y permiso de gerente.
3. Panel “Para revisar”: cambios de cuenta, primer pago a beneficiario nuevo, importe fuera de rango, pagos revertidos y comprobantes pendientes de verificación.
4. Respaldo/restauración de base y `private_uploads`, cabeceras seguras en descargas, límite de intentos de inicio de sesión y mejor política de contraseñas.
5. Moneda por obligación solo si el profesor confirma USD u otras monedas; los totales nunca mezclan monedas.
6. Correo diario, exportación CSV, alertas por variación, OCR y API bancaria únicamente después de estabilizar el núcleo.

## 9. Criterios UX y accesibilidad para toda mejora

- Formularios con etiquetas visibles, ayuda clara y errores junto al campo.
- Tras un envío inválido, resumen de errores enfocable, con enlaces a los campos y `role="alert"`.
- Confirmación visible antes de acciones irreversibles; éxito confirmado después de guardar.
- Objetivos táctiles de al menos 44 × 44 px; navegación completa por rol en celular.
- Texto y estados con contraste de al menos 4.5:1; el color nunca es el único indicador.
- Tablas usables con teclado y vista adaptada o desplazamiento controlado en teléfonos.
- Errores importantes permanecen visibles; los avisos de éxito pueden cerrarse automáticamente.

## 10. Preguntas que deben confirmarse con el profesor

| Pregunta | Supuesto actual hasta recibir respuesta |
| --- | --- |
| ¿“Pagar con el sistema” significa transferir o registrar el pago externo? | Registrar evidencia de un pago externo. |
| ¿SUNAT, SAT u otro impuesto? ¿Quién define el monto? | SUNAT puede nacer sin monto y el gerente lo completa tras declarar. |
| ¿Se mantienen 5 días de alerta o se requieren 7? | 5 días, porque es la regla ya aprobada en el documento actual. |
| ¿Hay pagos en USD? | Solo soles. Moneda múltiple queda fuera. |
| ¿Debe aprobarse una cuenta nueva o solo alertarse? | El gerente administra cuentas; la solicitud de validación es una mejora opcional. |
| ¿Cuántas obligaciones hay por mes y cómo llegan los recibos? | Menos de 50 y carga manual; validar con casos reales anonimizados. |
| ¿Necesita exportar para contador? | CSV como mejora posterior. |

## 11. Guion de demo de 10 minutos

1. El gerente abre el panel y detecta una vencida y una obligación sin monto.
2. El asistente abre su cola sin configurar filtros.
3. Registra una obligación desde un compromiso o cuenta de servicio existente.
4. Adjunta el documento y abre la ficha con datos de pago y referencia para copiar.
5. Registra el pago con comprobante de demostración.
6. El gerente actualiza su panel y ve el cambio inmediato en totales e historial.
7. El gerente suspende una obligación con motivo; el asistente la ve como retenida, no como atraso suyo.
8. Se muestra una cuenta de servicio mensual y la generación idempotente del siguiente período.

La demostración debe tener criterios de aceptación impresos o visibles para que el profesor pueda verificarlos. Si se muestran datos reales, deben estar anonimizados; para una demo académica es preferible usar datos ficticios.

## 12. Definición de terminado para la siguiente entrega

1. La importación CSV/XLSX funciona desde el navegador.
2. Un formulario inválido no deja datos huérfanos.
3. Cambiar una cuenta bancaria no altera pagos históricos.
4. El asistente consulta cuentas autorizadas, pero no las modifica.
5. Crear obligación → adjuntar → pagar → historial → dashboard está probado de extremo a extremo.
6. La generación mensual no duplica obligaciones.
7. La demo se siembra desde cero con todos los escenarios requeridos.
8. Los errores son específicos, accesibles y conservan datos ingresados.
9. El sistema funciona correctamente desde un teléfono.
10. `manage.py check`, migraciones y la suite completa de pruebas terminan sin errores.
