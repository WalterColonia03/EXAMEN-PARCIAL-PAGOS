# Matriz de mejoras y trazabilidad

## 1. Uso de la matriz

Esta matriz transforma el benchmark `INV-001` en decisiones visibles. El estado **Aceptada para roadmap** significa que el usuario desea aplicarla en el proyecto, pero no que ya esté desarrollada ni comprometida en el Sprint original.

Una mejora solo podrá declararse implementada cuando tenga:

1. cambio aprobado si altera alcance o datos;
2. código y migración, cuando correspondan;
3. pruebas automatizadas y prueba manual reproducible;
4. evidencia de interfaz y permisos;
5. actualización de HU, subtareas y tiempos reales si entra a un Sprint.

## 2. Matriz `MEJ-INV`

| ID | Hallazgo / referente | Mejora propuesta | Estado real verificado | Decisión | Prioridad | HUs/documentos relacionados | CR | Evidencia requerida | Estado |
|---|---|---|---|---|---|---|---|---|---|
| MEJ-INV-001 | Melio / Zoho: ciclo completo con pago externo | Validar como flujo obligatorio: crear obligación → adjuntar sustento → registrar pago con comprobante → historial → dashboard | El servicio exige sustento y comprobante; la regresión recorre el flujo hasta historial y dashboard. Falta revisión visual manual reproducible. | Aceptada para reforzar | P0 | HU-PROD-03, 05, 06; HU-DOC-01, HU-SEC-01 | CR-001 | E2E automatizado, prueba de permisos y revisión visual de escritorio/móvil pendiente | En validación — 15/10/2026 |
| MEJ-INV-002 | BILL / Stampli: roles y auditoría | Reforzar permisos de gerente/asistente, accesos directos y trazabilidad de acciones sensibles | Mantenimiento/importación de cuentas de servicio restringidos al gerente; páginas normales enmascaran y la revelación de instrucciones se audita en servidor. Falta revisión visual manual. | Aceptada para reforzar | P0 | HU-PROD-01, 02, 05; HU-SEC-01 | CR-001; CR-004 | Matriz GET/POST automatizada, pruebas negativas sin escrituras, revelación explícita y auditoría segura; revisión visual pendiente | En validación — 15/10/2026 |
| MEJ-INV-003 | Trazabilidad de cuentas de pago | Mantener una instantánea histórica de banco, titular y número usados en cada obligación/pago | `0004_destination_account_snapshots` congela la instrucción en `Payable`; el pago único la referencia sin duplicar PII. Backfill local aplicado a 12 obligaciones como `BACKFILLED`. | Aceptada como corrección de integridad | P0 | HU-PROD-02, 05; HU-SEC-01 | CR-001; CR-002 | Migración aplicada, edición sin alterar histórico, auditoría anterior/nuevo enmascarada y pruebas automatizadas; revisión visual pendiente | En validación — 15/10/2026 |
| MEJ-INV-004 | Akaunting: recurrencia separada de factura concreta | Conservar y probar la relación Cuenta de servicio → Compromiso → Obligación mensual | La regresión prueba dos períodos: ejecución idempotente, montos propios, documentos separados e instantánea propia por período. Falta revisión visual manual. | Aceptada como regresión | P0 | HU-PROD-02; HU-CS-01 a 03 | CR-001 | Prueba automatizada de dos períodos e idempotencia; revisión visual pendiente | En validación — 15/10/2026 |
| MEJ-INV-005 | Holded / Melio: importación y formularios confiables | Corregir importación CSV/XLSX, conservar errores específicos y evitar escrituras parciales | Las políticas de archivo se separaron; corruptos devuelven error controlado y el rollback/formulario inválido se prueban sin datos huérfanos. Falta revisión visual manual. | Aceptada como corrección | P0 | HU-PROD-03; HU-CS-01; documentación técnica | CR-001; CR-003 | CSV/XLSX, corrupto sin 500, rollback e inválido sin residuos automatizados; revisión visual pendiente | En validación — 15/10/2026 |
| MEJ-INV-006 | TimelyBills / Holded: cola visual de acción | Mostrar días de atraso, responsable de excepción, filtros persistentes y próximo paso por tarjeta | Tablero y excepciones existen; detalles de decisión pendientes | Aceptada para adaptar | P1 | HU-PROD-04; HU-ALT-01 | CR-001 | Pruebas de orden y filtros; prueba móvil con estados textuales | Backlog priorizado |
| MEJ-INV-007 | Stampli: actividad centrada en obligación | Unificar datos, documentos y auditoría en línea de tiempo clara dentro del detalle | Detalle y auditoría existen por separado; no hay timeline unificado | Aceptada para adaptar | P1 | HU-PROD-05; HU-DOC-01; HU-SEC-01 | CR-001 | Evento por creación, edición, adjunto, suspensión y pago con actor/fecha | Backlog priorizado |
| MEJ-INV-008 | Zoho / Alegra: dashboard de cuentas por pagar | Separar importe conocido, obligaciones sin monto, vencidos históricos y liquidez próxima | Dashboard existe; los montos sin definir se suman como cero y el período puede confundir el horizonte de liquidez | Aceptada para adaptar | P1 | HU-PROD-06, 07; HU-ANL-01 | CR-001 | Pruebas de totales, registros sin monto y vencidos previos | Backlog priorizado |
| MEJ-INV-009 | ERPNext: prevención de duplicados | Advertir obligaciones manuales similares por acreedor, documento, período o suministro sin bloquear falsos positivos | Unicidad de recurrencia existe; alerta manual no existe | Aceptada para adaptar | P1 | HU-PROD-03; HU-CS-03 | CR-001 | Escenario de advertencia, confirmación explícita y prueba de no duplicar recurrencias | Backlog priorizado |
| MEJ-INV-010 | BILL / control preventivo | Validar cuenta nueva o cambio de cuenta antes de usarla, sin aprobar pagos de cuentas ya autorizadas | Capacidad no existe; amplía estados, permisos y migraciones | Aceptada como propuesta futura | P2 | HU-PROD-08; HU-APR-01 | CR futuro | Flujo proponer/aprobar/rechazar, auditoría antes/después y permiso negativo | Postergada |
| MEJ-INV-011 | Organizadores de facturas | Calendario, búsqueda avanzada, paginación e importación de obligaciones por correo/hoja | No son necesarios para validar el núcleo actual | Postergada | P2 | HU-PROD-04; backlog posterior | — | Decisión de volumen, prototipo y pruebas de navegación | Fuera del Sprint |
| MEJ-INV-012 | Stampli: comentarios por factura | Comentarios/mensajería dentro de cada obligación | Aumenta alcance; la auditoría cubre la necesidad actual de trazabilidad | Postergada | P2 | HU-DOC-01 / backlog posterior | — | Caso de uso confirmado por profesor y diseño de permisos | Fuera del Sprint |
| MEJ-INV-013 | Ramp / Odoo: OCR, banca, conciliación y avisos externos | Integraciones avanzadas: OCR, transferencia bancaria, conciliación, correo/WhatsApp | Requieren proveedores, seguridad, costos y pruebas externas | Pospuesta fuera del MVP | P3 | HU-OCR-01, HU-NOT-01, HU-REC-01, HU-INT-01 | — | Contrato/API, análisis de seguridad y Sprint independiente | Fuera del MVP |
| MEJ-INV-014 | Sistemas contables generales | Convertir PagoControl en ERP o contabilidad completa | Contradice el propósito de simplicidad y cuentas por pagar | Descartada | Fuera de alcance | Visión y alcance | — | No aplica | No implementar |
| MEJ-INV-015 | Quicken / SBS / Sunass / family office: obligaciones no empresariales | Introducir ámbitos administrados y separar titular, beneficiario, acreedor y fuente de fondos sin crear empresas ficticias | `PaymentContext` admite cinco tipos; empresa/local son opcionales fuera del ámbito empresarial; el backfill conserva los registros existentes. | Aceptada para laboratorio | Experimental | EXP-LAB-01 | CR-005 | Migraciones `0005` a `0007`; casos personal/hogar/tercero y regresión empresarial | Verificada técnicamente — 16/10/2026 |
| MEJ-INV-016 | Gestión personal y familiar | Incorporar fuentes de fondos, naturaleza propia/compartida/apoyo/reembolsable/préstamo y beneficiarios sin crear usuarios | Fuentes, titular, beneficiario y naturaleza son independientes; el reembolso recibido se controla sin alterar el pago al acreedor. | Aceptada para laboratorio | Experimental | EXP-LAB-01, 03 y 05 | CR-005 | Casos de apoyo, fuente y reembolso sin doble conteo | Verificada técnicamente — 16/10/2026 |
| MEJ-INV-017 | ANPD / controles de family office | Aplicar visibilidad y autorización por ámbito y registro en todas las rutas y archivos | Listas, objetos, documentos, instrucciones y fuentes se filtran en servidor; un registro sensible restringe más que su ámbito. | Aceptada para laboratorio | Experimental | EXP-LAB-02 | CR-005 | Pruebas GET/POST, URL directa, descarga, vista previa, fuente oculta e instrucciones | Verificada técnicamente — 16/10/2026 |
| MEJ-INV-018 | Quicken / SBS: tarjetas y varias monedas | Añadir categorías especializadas, estado de tarjeta y moneda sin sumar divisas | En el corte del 16/10 existían PEN/USD y resúmenes separados; `CR-006` conserva USD solo como historia y restringe las altas nuevas a PEN. | Aceptada para laboratorio | Experimental | EXP-LAB-03 | CR-005; ajustada por CR-006 | Formularios progresivos, detalle obligatorio/incompleto y pruebas de moneda | Ajuste CR-006 verificado localmente — despliegue pendiente |
| MEJ-INV-019 | Akaunting / Holded: reglas recurrentes | Ampliar la generación más allá de mensual y permitir omitir/pausar futuras ocurrencias | Se implementaron ocho frecuencias más intervalo personalizado, pausa, omisión, fin, idempotencia y protección contra rangos excesivos. | Aceptada para laboratorio | Experimental | EXP-LAB-04 | CR-005 | Pruebas de frecuencias, idempotencia, omisión y meses cortos | Verificada técnicamente — 16/10/2026 |
| MEJ-INV-020 | Melio / Zoho: correcciones y pagos parciales | Convertir el pago único en movimientos, saldo, anulación, devolución, reembolso y disputa | Una obligación admite múltiples movimientos; una devolución/contracargo reabre saldo y un reembolso completo cierra el gasto recuperable. | Aceptada para laboratorio | Experimental | EXP-LAB-05 | CR-005 | Parciales, saldo, corrección/anulación sin borrado, reembolso y comprobantes | Verificada técnicamente — 16/10/2026 |
| MEJ-INV-021 | ERPNext / Asseta: control de duplicados | Usar coincidencias exactas y advertencias con decisión humana | Referencia exacta bloquea; coincidencia aproximada exige confirmación y motivo auditado en creación e importación. No hay fusión automática. | Aceptada para laboratorio | Experimental | EXP-LAB-06 | CR-005 | Candidatos, motivo, auditoría e idempotencia de recurrencias | Verificada parcialmente — 16/10/2026 |
| MEJ-INV-022 | TimelyBills / Zoho: calendario y avisos internos | Añadir agenda mensual y recordatorios internos idempotentes | Existe calendario mensual, agenda adaptable y recordatorios que se reprograman o cierran con vencimiento/estado. No hay vista semanal/diaria independiente. | Aceptada para laboratorio | Experimental | EXP-LAB-07 | CR-005 | Calendario, acceso por rol, omisión, reprogramación y no duplicación | Verificada parcialmente — 16/10/2026 |
| MEJ-INV-023 | Ramp / Zoho / Stampli: volumen y supervisión | Importar obligaciones con vista previa y ampliar filtros, actividad y dashboard por ámbito/moneda | El gerente revisa y confirma lotes transaccionales; filtros y dashboard separan ámbito/moneda/estado. El original es transitorio y la actividad visible está acotada. | Aceptada para laboratorio | Experimental | EXP-LAB-08 y 09 | CR-005 | Previsualización, rollback, permisos, filtros, totales y movimientos/auditoría | Verificada parcialmente — 16/10/2026 |
| MEJ-INV-024 | Formularios contextuales y revelado progresivo | Mostrar solo datos aplicables y evitar valores residuales al cambiar ámbito, categoría, recurrencia, fuente o acción | Los bloques no aplicables se ocultan y deshabilitan; el servidor normaliza peticiones directas y mantiene errores inline. | Aceptada para laboratorio | Experimental | EXP-LAB-10 | CR-005 / FB-003 | Visibilidad, estado `disabled`, normalización del POST, errores inline, teclado y revisión manual | Verificada técnicamente — 16/10/2026 |
| MEJ-INV-025 | Revisión del PR #1 y preparación Vercel/Supabase | Restringir altas a PEN, conservar USD histórico, separar reporte de falta de fondos de suspensión, retirar sustento sin borrarlo, mantener consultas del asistente y usar persistencia externa | Implementado localmente con migración, controles de servidor/UI y configuración de PostgreSQL/Storage; no se afirma un despliegue real. | Aceptada para implementar y verificar | P0 experimental | EXP-LAB-12; HU-PROD-01, 04, 05 y 07; HU-DOC-01; HU-SEC-01 | CR-006 / FB-006 | Pruebas de moneda y legado USD, permisos, excepción, retiro lógico, auditoría, PostgreSQL, Storage privado y recorrido manual | Verificada técnicamente local — 84 pruebas; despliegue/manual pendientes |

## 3. Orden de aplicación aceptado para el roadmap

### Bloque A — confiabilidad demostrable

`MEJ-INV-001` a `MEJ-INV-005`: cerrar flujo principal, permisos, historia bancaria, recurrencia e importación antes de añadir capacidades nuevas.

### Bloque B — claridad operativa y gerencial

`MEJ-INV-006` a `MEJ-INV-009`: mejorar cola, detalle, dashboard y prevención de errores sin alterar la autonomía del asistente.

### Bloque C — controles e integraciones posteriores

`MEJ-INV-010` a `MEJ-INV-013`: introducir solo cuando el núcleo esté estable, exista una necesidad confirmada y se apruebe el cambio correspondiente.

## 4. Criterio de actualización de estado

| Cambio de estado | Condición mínima |
|---|---|
| `Pendiente de implementación/verificación` → `En desarrollo` | CR específico si afecta datos/alcance; HU/subtareas creadas; responsable definido. |
| `En desarrollo` → `En validación` | Código integrado, migración aplicable y pruebas automatizadas ejecutadas. |
| `En validación` → `Implementada` | Criterios de aceptación aprobados, prueba de permisos y evidencia reproducible. |
| `Backlog priorizado` / `Postergada` | No se registra tiempo real ni se presenta como función existente. |
| `Descartada` | Se conserva la justificación; no se elimina de la matriz. |

## 5. Próximo paso documentado

El Bloque A y el corte de `CR-005` cuentan con validación automatizada local. `MEJ-INV-025`/`CR-006` también cuenta con migración y pruebas locales documentadas, pero no se le atribuyen todavía despliegue real ni validación manual. Los CR no reescriben el compromiso original ni registran tiempos reales.

## 6. Laboratorio posterior a la línea base

La regla anterior se conserva para el roadmap histórico. `CR-005` abrió el laboratorio que integra `MEJ-INV-015` a `MEJ-INV-024`; `CR-006` añade `MEJ-INV-025` sin reabrir el Sprint. Su ejecución se controla con los estados `Especificada`, `En desarrollo experimental`, `Verificada técnicamente`, `Validada por producto` o `Descartada`. Ninguno equivale a `Done` del Sprint ni crea tiempos o incidencias Jira.

El corte del 16/10/2026 está respaldado por `evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md`. `MEJ-INV-021` a `023` se mantienen como verificación parcial. `MEJ-INV-025` se respalda en `evidencias/EXP-LAB_CR-006_IMPLEMENTACION_2026-10-18.md`; aún requiere la evidencia de despliegue y validación manual.
