# Evidencia técnica del laboratorio EXP-LAB

**Fecha de corte:** 16/10/2026  
**Ámbito:** prototipo local PagoControl  
**Decisión relacionada:** `CR-005`  
**Estado:** verificado técnicamente; pendiente de validación visual manual y aceptación del responsable del producto.

## 1. Qué significa este documento

Esta ficha relaciona la especificación escrita antes de construir con el comportamiento que ahora existe en la carpeta local. No convierte los experimentos en Historias de Usuario terminadas, no registra horas ni Story Points y no crea trabajo en Jira.

No se publicó código, no se configuró un remoto de GitHub y no se conectó ninguna cuenta de Jira. Las comprobaciones de diferencias realizadas con Git fueron únicamente locales y no enviaron información fuera del equipo.

## 2. Evidencia por capacidad

| ID | Comportamiento disponible en el prototipo | Evidencia principal | Estado técnico |
|---|---|---|---|
| EXP-LAB-01 | Ámbitos `Empresa`, `Personal`, `Hogar o propiedad`, `Familiar o tercero` y `Entidad patrimonial`; empresa/local opcionales; titular, beneficiario, naturaleza y fuente de fondos separados. | Modelos `PaymentContext` y `FundingSource`; migraciones `0005` a `0007`; `ContextAndPrivacyTests`. | Verificada |
| EXP-LAB-02 | Acceso del asistente filtrado en servidor por ámbito; obligación sensible solo para gerente; adjuntos, instrucciones y fuentes privadas protegidos. | `visible_contexts_for`, `payable_queryset_for`, `ensure_context_access`; pruebas de URL directa, descarga, vista previa y fuente oculta. | Verificada |
| EXP-LAB-03 | Diecinueve categorías, PEN/USD y campos progresivos para tarjeta, préstamo, seguro, vivienda, viaje e inversión. Los compromisos conservan sus identificadores estables y cada obligación sus datos del período; si estos últimos aún no existen, queda marcada como incompleta. | `PaymentCommitment.Category`, `PaymentCommitmentForm`, `PayableForm`, validadores de `details` y `ScopeAndHistoryIntegrityTests`. | Verificada |
| EXP-LAB-04 | Pago único y recurrencias semanal, quincenal, mensual, bimestral, trimestral, semestral, anual o personalizada; pausa, omisión, fecha final e idempotencia. | `next_recurrence_date`, `generate_scheduled_payables`, límite de 5 000 ocurrencias por ejecución y pruebas de mes corto/idempotencia. | Verificada |
| EXP-LAB-05 | Varios pagos, abonos parciales, saldo, devolución, contracargo, ajuste, reembolso recibido y anulación sin borrar movimientos. | Modelo `Payment` uno-a-muchos; servicios de movimiento/anulación; `ReminderAndMovementIntegrityTests` y `MovementAndRecurrenceTests`. | Verificada |
| EXP-LAB-06 | Bloqueo de documento exacto; advertencia de coincidencia aproximada; continuación solo con confirmación y motivo auditado, tanto manual como por importación. | `possible_duplicate_payables`, acción `DUPLICATE_OVERRIDE` y pruebas de creación/importación. | Verificada para la variante continuar/cancelar |
| EXP-LAB-07 | Calendario mensual, agenda adaptable para pantallas pequeñas y recordatorios internos que se reprograman o cierran con el estado real de la obligación. | `payment_calendar`, `InternalReminder`, `_sync_default_reminder` y pruebas de vencimiento/pago/devolución. | Verificada para la primera variante mensual |
| EXP-LAB-08 | Vista previa pequeña CSV/XLSX, errores por fila, coincidencias y confirmación transaccional; una fila inválida no crea obligaciones. | `payable_importing.py`, `PayableImportBatch`, rutas de previsualización/confirmación y `ExperimentalUiAndImportTests`. | Verificada para importación controlada por gerente |
| EXP-LAB-09 | Filtros por ámbito, empresa/local, acreedor, categoría, moneda, fechas, privacidad y estado; resumen por moneda, saldos, excepciones y reembolsos; actividad del registro. | `PayableFilterForm`, `manager_month_summary`, dashboard y detalle con auditoría/movimientos. | Verificada para la variante actual |
| EXP-LAB-10 | Formularios adaptados por ámbito, categoría, recurrencia, modo de monto, fuente y cambio de estado; los campos ocultos quedan deshabilitados y la tarjeta usa el total del estado como único monto. | `PagoControlForms`, formularios de obligación/compromiso/ámbito/fuente/cuenta de servicio, `DynamicFormNormalizationTests` y `DynamicFormRenderingTests`. | Verificada técnicamente; revisión visual manual pendiente |

## 3. Casos cotidianos representables

El modelo ya permite registrar sin empresa ficticia, entre otros:

- luz, agua, internet, mantenimiento o impuesto predial de una vivienda propia o de un familiar;
- préstamo personal, hipotecario o cuota pactada con un tercero;
- apoyo no reembolsable o gasto recuperable de pareja, familiar, empleado o invitado;
- estado de cuenta de tarjeta, con total, mínimo, ciclo y abonos parciales;
- préstamo, tarjeta, seguro, propiedad, viaje o inversión recurrente conservando en cada obligación el contrato, tarjeta enmascarada, póliza o referencia configurada;
- seguro, educación, salud, personal doméstico, vehículo, viaje, evento, donación, asunto legal, suscripción, inversión y emergencia;
- gasto adelantado y posterior reembolso, sin confundirlo con el pago al acreedor;
- devolución o contracargo que vuelve a abrir el saldo, conservando el movimiento anterior.

## 4. Integridad y seguridad comprobadas

- Los pagos requieren documento de sustento y comprobante.
- Un pago no puede superar el saldo y debe usar la moneda de la obligación.
- Una fuente oculta al asistente no puede utilizarse mediante una petición directa.
- Después del primer movimiento se bloquean ámbito, acreedor, categoría, monto, moneda y naturaleza financiera.
- Los compromisos especializados no se guardan sin el identificador estable que corresponde a su categoría; los datos variables de cada período se validan en la obligación.
- Una corrección no elimina el movimiento original; una anulación exige gerente y motivo.
- Los documentos continúan en almacenamiento privado; sus rutas verifican sesión, rol y ámbito.
- La importación confirma todo el lote dentro de una transacción y resiste una segunda confirmación sin degradar un lote ya confirmado.
- Los recordatorios se conservan como historial: al reprogramar o cerrar se marcan, no se eliminan.
- Los controles ocultos se deshabilitan y no se envían; además, el servidor elimina valores residuales de combinaciones incompatibles aun cuando se construye una petición directa.
- Las cuentas de servicio ofrecidas en compromisos se limitan a los ámbitos visibles para el usuario y no exponen etiquetas de ámbitos privados al asistente.

## 5. Validación reproducible

Comandos ejecutados desde la carpeta local:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
git diff --check
```

Resultado de cierre: controles Django limpios, ninguna migración pendiente, migraciones `payments.0001` a `payments.0009` aplicadas en la base local y **62 de 62 pruebas aprobadas**. La suite incluye permisos, privacidad, archivos, importaciones, recurrencias, movimientos, recordatorios, formularios especializados y nueve casos específicos de formularios contextuales.

## 6. Decisiones y límites conscientes

- La importación de obligaciones queda reservada al gerente en esta variante porque puede crear registros masivos y sensibles. El asistente conserva registro manual y operación sobre ámbitos compartidos.
- El archivo de importación se procesa de forma transitoria y no se archiva; se conserva nombre, actor, fecha, filas normalizadas y resultado. Esto reduce retención de datos. Si el producto exige conservar el original, deberá aprobarse una política de retención y descarga privada.
- La resolución de duplicados permite cancelar o continuar con motivo. La fusión automática se pospone para no alterar historia ni documentos sin una regla de consolidación aprobada.
- El calendario inicial ofrece mes en escritorio y agenda del mes en pantallas pequeñas. Las vistas semanal y diaria siguen como opción de producto, no como capacidad afirmada.
- La actividad visible está acotada a los eventos recientes; una bitácora paginada y exportable puede añadirse después si el volumen real lo exige.
- La zona horaria es global (`America/Lima`); no se configuró una zona diferente por compromiso.
- OCR, banca, conciliación, scraping, correo receptor, WhatsApp y consultas a proveedores siguen fuera del prototipo local.

## 7. Validación pendiente

La automatización visual de una ventana de navegador se detuvo porque la herramienta no pudo verificar de forma segura la URL de la pestaña ya abierta. No se interactuó con esa ventana después del bloqueo. Por honestidad, quedan pendientes:

1. recorrido manual del gerente en escritorio;
2. recorrido manual del asistente en escritorio;
3. comprobación a 375 px y en orientación horizontal;
4. aceptación o descarte de cada variante por el responsable del producto.

Hasta completar esas revisiones, el estado correcto es **verificada técnicamente**, no `Done`, no validada por producto y no lista para Jira.
