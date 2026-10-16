# Subtareas y cronograma nivelado

> **Documento histórico del Sprint original.** No se añadieron aquí subtareas ni horas del laboratorio `CR-005`; hacerlo después de la ejecución falsearía la planificación. El trabajo experimental se registra por capacidad y evidencia, sin tiempos inventados.

## 1. Reglas de lectura

- Las fechas son planificadas, no horas ya ejecutadas.
- Cada subtarea tiene un responsable y un revisor diferente.
- La duración indicada es esfuerzo estimado en horas-persona.
- `Inicio real`, `Fin real`, `Duración real` y `Tiempo trabajado` permanecen vacíos hasta la ejecución.
- `[H]` significa dependencia dura: no puede completarse el sucesor sin terminar el predecesor.
- `[I]` significa dependencia de integración: puede avanzarse contra un contrato acordado, pero la HU no se acepta hasta integrar ambos trabajos.
- Las subtareas con título autoexplicativo no reciben una descripción redundante.
- Los intervalos no ocupados se reservan para Daily, descansos, coordinación, revisiones, resolución de bloqueos y el margen del primer Sprint.

## 2. Resumen cuantitativo

| Grupo | Ítems | Horas |
|---|---:|---:|
| Trabajo técnico transversal | 5 | 30 |
| HU-CS-01 | 5 | 30 |
| HU-CS-02 | 5 | 26 |
| HU-CS-03 | 6 | 44 |
| HU-EXP-01 | 4 | 20 |
| HU-DOC-01 | 7 | 44 |
| HU-ALT-01 | 4 | 18 |
| HU-SEC-01 | 4 | 20 |
| **Total** | **40 ítems** | **232 h-persona** |

## 3. Trabajo técnico transversal — 30 h

| ID | Título | Descripción solo si es necesaria | Responsable | Revisor | Inicio | Fin | h | Dependencias |
|---|---|---|---|---|---|---|---:|---|
| ST-BASE-01 | Crear respaldo verificable y fijar la línea base | Preservar todos los cambios actuales, registrar commit o referencia recuperable y ejecutar las 75 pruebas sin descartar trabajo del usuario. | D1 | D6 | 15/10 16:00 | 15/10 22:00 | 6 | — |
| ST-ARQ-01 | Definir contrato de CuentaServicio y estados documentales | Acordar campos, nulabilidad, restricciones, nombres y límites antes de que las capas trabajen en paralelo. | D4 | D2 | 15/10 16:00 | 15/10 22:00 | 6 | — |
| ST-CI-01 | Preparar regresión reproducible del incremento | Ejecutar checks, migraciones y pruebas desde base limpia sin añadir dependencias externas no documentadas. | D6 | D5 | 15/10 16:00 | 15/10 22:00 | 6 | [I] ST-BASE-01 |
| ST-DEMO-01 | Actualizar datos ficticios para la demostración | Incluir cuentas de servicio y documentos ficticios sin números bancarios ni credenciales reales. | D1 | D3 | 20/10 09:00 | 20/10 15:00 | 6 | [I] HUs funcionales |
| ST-REL-01 | Preparar respaldo, guía de ejecución y evidencia final | La guía puede prepararse en paralelo; solo se cierra cuando regresión y criterios estén comprobados. | D5 | D6 | 20/10 09:00 | 20/10 15:00 | 6 | [I] ST-CI-01 y HUs funcionales |

## 4. HU-CS-01 · Registrar una cuenta de servicio — 30 h

| ID | Título | Descripción solo si es necesaria | Responsable | Revisor | Inicio | Fin | h | Dependencias |
|---|---|---|---|---|---|---|---:|---|
| ST-CS01-DB | Crear modelo CuentaServicio y migración | — | D1 | D2 | 16/10 09:00 | 16/10 16:00 | 7 | [H] ST-BASE-01; [I] ST-ARQ-01 |
| ST-CS01-SVC | Implementar normalización y duplicidad | La regla debe aceptar identificadores configurables sin imponer una longitud global. | D2 | D1 | 15/10 16:00 | 15/10 22:00 | 6 | [I] ST-ARQ-01, ST-CS01-DB |
| ST-CS01-UI | Construir formulario de alta | — | D3 | D4 | 15/10 16:00 | 15/10 22:00 | 6 | [I] ST-ARQ-01, ST-CS01-SVC |
| ST-CS01-AUTH | Aplicar autorización y auditoría de creación | — | D5 | D6 | 15/10 16:00 | 15/10 20:00 | 4 | [I] ST-CS01-SVC |
| ST-CS01-QA | Automatizar criterios y revisar alta completa | Incluye duplicidad, local ajeno, entidad inactiva y POST no autorizado. | D6 | D3 | 16/10 09:00 | 16/10 16:00 | 7 | [I] ST-CS01-DB, ST-CS01-SVC, ST-CS01-UI, ST-CS01-AUTH |

## 5. HU-CS-02 · Consultar y mantener cuentas de servicio — 26 h

| ID | Título | Descripción solo si es necesaria | Responsable | Revisor | Inicio | Fin | h | Dependencias |
|---|---|---|---|---|---|---|---:|---|
| ST-CS02-LIST | Implementar consulta y filtros | — | D2 | D3 | 16/10 09:00 | 16/10 14:00 | 5 | [I] HU-CS-01 |
| ST-CS02-UI | Construir lista, detalle y edición | — | D3 | D4 | 16/10 09:00 | 16/10 16:00 | 7 | [I] ST-CS02-LIST |
| ST-CS02-STATE | Implementar desactivación y reactivación | Conservar historia e impedir nuevas asociaciones con cuentas inactivas. | D4 | D1 | 16/10 09:00 | 16/10 13:00 | 4 | [I] HU-CS-01 |
| ST-CS02-COPY | Implementar visualización enmascarada y copia explícita | La interfaz no debe mantener el código completo visible de forma permanente. | D4 | D5 | 16/10 13:00 | 16/10 17:00 | 4 | [I] HU-SEC-01 |
| ST-CS02-QA | Probar filtros, edición, estados y permisos | — | D3 | D6 | 19/10 09:00 | 19/10 15:00 | 6 | [H] ST-CS02-LIST, ST-CS02-UI, ST-CS02-STATE; [I] ST-CS02-COPY |

## 6. HU-CS-03 · Vincular cuentas con compromisos y obligaciones — 44 h

| ID | Título | Descripción solo si es necesaria | Responsable | Revisor | Inicio | Fin | h | Dependencias |
|---|---|---|---|---|---|---|---:|---|
| ST-CS03-MIG | Añadir relaciones nullable y migrar sin pérdida | Mantener compatibles todos los compromisos y obligaciones existentes que aún no tengan cuenta. | D1 | D2 | 17/10 09:00 | 17/10 17:00 | 8 | [H] ST-CS01-DB |
| ST-CS03-SVC | Validar coherencia y heredar la cuenta | — | D2 | D5 | 17/10 09:00 | 17/10 17:00 | 8 | [I] ST-CS03-MIG |
| ST-CS03-FORM | Adaptar formularios y selectores dependientes | — | D3 | D4 | 17/10 09:00 | 17/10 16:00 | 7 | [I] ST-CS03-SVC |
| ST-CS03-UI | Mostrar cuenta en tablero, detalle e historial | — | D4 | D3 | 17/10 09:00 | 17/10 16:00 | 7 | [I] ST-CS03-MIG, HU-SEC-01 |
| ST-CS03-AUTO | Probar migración, herencia e incompatibilidades | Ejecutar pruebas con base vacía y datos existentes, incluidas cuentas desactivadas. | D5 | D6 | 18/10 09:00 | 18/10 17:00 | 8 | [I] ST-CS03-MIG, ST-CS03-SVC, ST-CS03-FORM, ST-CS03-UI |
| ST-CS03-E2E | Ejecutar recorrido completo de cuenta a pago | Crear cuenta, compromiso y periodo; adjuntar documento, pagar y comprobar historial. | D6 | D1 | 19/10 09:00 | 19/10 15:00 | 6 | [H] ST-CS03-AUTO; [I] ST-CI-01 |

## 7. HU-EXP-01 · Registrar un gasto irregular express — 20 h

| ID | Título | Descripción solo si es necesaria | Responsable | Revisor | Inicio | Fin | h | Dependencias |
|---|---|---|---|---|---|---|---:|---|
| ST-EXP01-SVC | Crear gasto incompleto desde contexto | Permitir los tres campos visibles sin fabricar un acreedor; conservar el indicador de información incompleta. | D2 | D5 | 16/10 14:00 | 16/10 19:00 | 5 | [I] ST-ARQ-01 |
| ST-EXP01-UI | Construir captura express y continuación al detalle | — | D3 | D4 | 18/10 09:00 | 18/10 15:00 | 6 | [I] ST-EXP01-SVC |
| ST-EXP01-AUD | Aplicar validaciones, permisos y auditoría | — | D5 | D2 | 16/10 14:00 | 16/10 18:00 | 4 | [I] ST-EXP01-SVC |
| ST-EXP01-QA | Medir captura y probar casos límite | Incluye contexto ausente, monto inválido, fecha vencida y posterior completado. | D6 | D3 | 18/10 14:00 | 18/10 19:00 | 5 | [I] ST-EXP01-UI, ST-EXP01-AUD |

## 8. HU-DOC-01 · Recibir y asociar documentos — 44 h

| ID | Título | Descripción solo si es necesaria | Responsable | Revisor | Inicio | Fin | h | Dependencias |
|---|---|---|---|---|---|---|---:|---|
| ST-DOC01-DB | Crear modelo de bandeja, estados y hash | — | D1 | D2 | 18/10 09:00 | 18/10 17:00 | 8 | [H] ST-CS01-DB; [I] ST-ARQ-01 |
| ST-DOC01-SVC | Implementar carga, deduplicación y asociación atómica | Reutilizar validaciones privadas y evitar una segunda copia física del mismo contenido. | D2 | D5 | 19/10 09:00 | 19/10 17:00 | 8 | [I] ST-DOC01-DB |
| ST-DOC01-LIST | Construir lista, detalle y previsualización | — | D3 | D4 | 19/10 15:00 | 19/10 19:00 | 4 | [I] ST-DOC01-DB |
| ST-DOC01-LINK | Construir confirmación de asociación | — | D3 | D6 | 20/10 09:00 | 20/10 13:00 | 4 | [I] ST-DOC01-SVC, ST-DOC01-LIST |
| ST-DOC01-MATCH | Sugerir cuenta mediante coincidencia exacta | No incluye OCR: usa un código introducido por el usuario y solo sugiere cuando existe una única coincidencia activa. | D4 | D2 | 18/10 09:00 | 18/10 17:00 | 8 | [I] ST-DOC01-DB, HU-CS-03 |
| ST-DOC01-ACCESS | Proteger descarga, descarte y transición de estados | — | D5 | D6 | 17/10 09:00 | 17/10 15:00 | 6 | [I] ST-DOC01-DB, HU-SEC-01 |
| ST-DOC01-QA | Probar duplicados, privacidad y asociación | Incluye mismo contenido con nombre distinto, archivo inválido, cero/varias coincidencias y URL no autorizada. | D6 | D1 | 20/10 09:00 | 20/10 15:00 | 6 | [I] ST-DOC01-SVC, ST-DOC01-LINK, ST-DOC01-MATCH, ST-DOC01-ACCESS |

## 9. HU-ALT-01 · Atender alertas internas — 18 h

| ID | Título | Descripción solo si es necesaria | Responsable | Revisor | Inicio | Fin | h | Dependencias |
|---|---|---|---|---|---|---|---:|---|
| ST-ALT01-DB | Crear evento de alerta e idempotencia | — | D1 | D2 | 19/10 09:00 | 19/10 14:00 | 5 | [I] HU-CS-03 |
| ST-ALT01-SVC | Generar D-5, D-2, D-0 y vencida | El generador debe ser repetible para una misma fecha sin crear duplicados. | D4 | D1 | 19/10 09:00 | 19/10 14:00 | 5 | [I] ST-ALT01-DB |
| ST-ALT01-UI | Construir centro de alertas y acción de lectura | — | D4 | D3 | 19/10 14:00 | 19/10 18:00 | 4 | [I] ST-ALT01-SVC |
| ST-ALT01-QA | Probar escalamiento, cierre e idempotencia | — | D6 | D5 | 19/10 15:00 | 19/10 19:00 | 4 | [I] ST-ALT01-SVC, ST-ALT01-UI |

## 10. HU-SEC-01 · Proteger identificadores — 20 h

| ID | Título | Descripción solo si es necesaria | Responsable | Revisor | Inicio | Fin | h | Dependencias |
|---|---|---|---|---|---|---|---:|---|
| ST-SEC01-MASK | Implementar enmascaramiento y copia autorizada | — | D5 | D3 | 16/10 09:00 | 16/10 14:00 | 5 | [I] ST-ARQ-01, HU-CS-01 |
| ST-SEC01-AUDIT | Registrar cambios sin filtrar secretos a logs | — | D2 | D5 | 18/10 09:00 | 18/10 14:00 | 5 | [I] ST-SEC01-MASK |
| ST-SEC01-NEG | Automatizar accesos negativos | Probar URL, POST y descarga manual con ambos roles y una sesión sin autorización. | D6 | D5 | 17/10 09:00 | 17/10 14:00 | 5 | [I] ST-SEC01-MASK |
| ST-SEC01-REV | Ejecutar revisión independiente de seguridad | — | D5 | D1 | 19/10 09:00 | 19/10 14:00 | 5 | [H] ST-SEC01-AUDIT, ST-SEC01-NEG; [I] HU-DOC-01 |

## 11. Carga planificada por Developer

| Developer | Horas asignadas | Capacidad comprometible media | Diferencia |
|---|---:|---:|---:|
| D1 | 40 | 38.7 | +1.3 |
| D2 | 37 | 38.7 | -1.7 |
| D3 | 40 | 38.7 | +1.3 |
| D4 | 38 | 38.7 | -0.7 |
| D5 | 38 | 38.7 | -0.7 |
| D6 | 39 | 38.7 | +0.3 |
| **Equipo** | **232** | **232** | **0** |

La diferencia individual no representa horas extra. Existe holgura dentro de las seis jornadas y la responsabilidad colectiva permite redistribuir una subtarea antes de iniciarla.

## 12. Línea temporal individual

### D1 — 40 h

```text
15/10 16:00–22:00  ST-BASE-01       6 h
16/10 09:00–16:00  ST-CS01-DB       7 h
17/10 09:00–17:00  ST-CS03-MIG      8 h
18/10 09:00–17:00  ST-DOC01-DB      8 h
19/10 09:00–14:00  ST-ALT01-DB      5 h
20/10 09:00–15:00  ST-DEMO-01       6 h
```

### D2 — 37 h

```text
15/10 16:00–22:00  ST-CS01-SVC      6 h
16/10 09:00–14:00  ST-CS02-LIST     5 h
16/10 14:00–19:00  ST-EXP01-SVC     5 h
17/10 09:00–17:00  ST-CS03-SVC      8 h
18/10 09:00–14:00  ST-SEC01-AUDIT   5 h
19/10 09:00–17:00  ST-DOC01-SVC     8 h
```

### D3 — 40 h

```text
15/10 16:00–22:00  ST-CS01-UI       6 h
16/10 09:00–16:00  ST-CS02-UI       7 h
17/10 09:00–16:00  ST-CS03-FORM     7 h
18/10 09:00–15:00  ST-EXP01-UI      6 h
19/10 09:00–15:00  ST-CS02-QA       6 h
19/10 15:00–19:00  ST-DOC01-LIST    4 h
20/10 09:00–13:00  ST-DOC01-LINK    4 h
```

### D4 — 38 h

```text
15/10 16:00–22:00  ST-ARQ-01        6 h
16/10 09:00–13:00  ST-CS02-STATE    4 h
16/10 13:00–17:00  ST-CS02-COPY     4 h
17/10 09:00–16:00  ST-CS03-UI       7 h
18/10 09:00–17:00  ST-DOC01-MATCH   8 h
19/10 09:00–14:00  ST-ALT01-SVC     5 h
19/10 14:00–18:00  ST-ALT01-UI      4 h
```

### D5 — 38 h

```text
15/10 16:00–20:00  ST-CS01-AUTH     4 h
16/10 09:00–14:00  ST-SEC01-MASK    5 h
16/10 14:00–18:00  ST-EXP01-AUD     4 h
17/10 09:00–15:00  ST-DOC01-ACCESS  6 h
18/10 09:00–17:00  ST-CS03-AUTO     8 h
19/10 09:00–14:00  ST-SEC01-REV     5 h
20/10 09:00–15:00  ST-REL-01        6 h
```

### D6 — 39 h

```text
15/10 16:00–22:00  ST-CI-01         6 h
16/10 09:00–16:00  ST-CS01-QA       7 h
17/10 09:00–14:00  ST-SEC01-NEG     5 h
18/10 14:00–19:00  ST-EXP01-QA      5 h
19/10 09:00–15:00  ST-CS03-E2E      6 h
19/10 15:00–19:00  ST-ALT01-QA      4 h
20/10 09:00–15:00  ST-DOC01-QA      6 h
```

## 13. Camino crítico provisional

```text
ST-BASE-01 / ST-ARQ-01
  → ST-CS01-DB
  → ST-CS03-MIG
  → ST-CS03-AUTO
  → ST-CS03-E2E
  → integración de ST-DOC01-*
  → ST-DOC01-QA
  → control final de DoD
```

No se interpreta esta cadena como una suma simple de horas calendario: varias actividades de servicio, interfaz y pruebas avanzan en paralelo mediante contratos. Si un contrato cambia, se detiene la integración afectada y se actualiza el plan antes de continuar.

## 14. Control diario

En cada Daily se actualizará por subtarea:

- estado: Por hacer / En curso / Bloqueada / En revisión / Finalizada;
- inicio real, si comenzó;
- tiempo trabajado acumulado;
- tiempo restante;
- bloqueo y responsable de resolverlo;
- impacto sobre el criterio de aceptación;
- necesidad de replanificar sin aumentar alcance.

## 15. Adenda de ejecución P0 posterior a la línea base

Esta adenda corresponde a los CR aprobados el 15/10/2026. No altera las tareas, responsables, fechas ni horas del Sprint original. No registra tiempo real; los responsables humanos y la estimación formal permanecen pendientes.

| ID | Mejora / CR | Subtarea verificable | Estado | Evidencia de cierre |
|---|---|---|---|---|
| AD-P0-001-A | MEJ-INV-001 / CR-001 | Exigir sustento antes de registrar un pago y conservar el comprobante obligatorio. | En validación | Pruebas negativas y E2E automatizadas aprobadas; revisión manual pendiente. |
| AD-P0-001-B | MEJ-INV-001 / CR-001 | Verificar historial y dashboard después del pago sin doble conteo. | En validación | E2E automatizada aprobada; revisión manual reproducible pendiente. |
| AD-P0-002-A | MEJ-INV-002 / CR-004 | Restringir mantenimiento e importación de cuentas de servicio al gerente y verificar accesos directos. | En validación | GET/POST negativo automatizado sin escrituras; revisión manual pendiente. |
| AD-P0-002-B | MEJ-INV-002 / CR-004 | Enmascarar valores por defecto y registrar cambios/revelaciones sin secretos en auditoría. | En validación | Pruebas de HTML, auditoría y permisos aprobadas; revisión manual pendiente. |
| AD-P0-003-A | MEJ-INV-003 / CR-002 | Añadir snapshots inmutables y backfill seguro de la cuenta destino. | En validación | Migración aplicada desde base existente y pruebas desde base limpia; revisión manual pendiente. |
| AD-P0-003-B | MEJ-INV-003 / CR-002 | Registrar auditoría de cambio con anterior/nuevo enmascarado y probar permisos. | En validación | Prueba de edición segura y denegación de mantenimiento aprobadas; revisión manual pendiente. |
| AD-P0-005-A | MEJ-INV-005 / CR-003 | Separar la política cliente de archivos de pago e importación. | En validación | CSV/XLSX y documentos de pago conservan políticas separadas; revisión manual pendiente. |
| AD-P0-005-B | MEJ-INV-005 / CR-003 | Eliminar escrituras desde `clean()` y encapsular la persistencia en servicios atómicos. | En validación | Formulario inválido sin acreedor residual y rollback de archivo auditado. |
| AD-P0-005-C | MEJ-INV-005 / CR-003 | Traducir archivos corruptos y validar rollback completo de importación. | En validación | Pruebas de corrupto y fila inválida aprobadas; revisión manual pendiente. |
