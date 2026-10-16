# Registro de tiempos reales

> **Documento histórico del Sprint original.** El laboratorio `CR-005` no incorpora tiempos retroactivos en esta plantilla. Solo deberán registrarse tiempos que procedan de una ejecución humana medida y revisada.

## 1. Regla principal

Este documento comienza vacío de resultados porque todavía no acredita ejecución. Se completa durante el desarrollo, nunca con tiempos inventados después.

Para cada subtarea se registran:

- inicio real: primera transición efectiva a `En curso`;
- fin real: transición a `Finalizada` después de revisión;
- duración transcurrida: diferencia entre ambas marcas;
- esfuerzo real: suma de sesiones de trabajo;
- tiempo bloqueado: intervalos en los que no se pudo avanzar;
- responsable y revisor;
- evidencia verificable.

```text
Duración transcurrida = Fin real − Inicio real
Esfuerzo real = Σ duración de sesiones activas
Tiempo bloqueado = Σ duración de sesiones bloqueadas
```

Ejemplo solicitado:

```text
Inicio real:           16/10/2026 12:00
Fin real:              16/10/2026 14:00
Duración transcurrida: 2 h
Esfuerzo real:         2 h
```

Si se pausa una incidencia, se registra cada sesión:

| Sesión | Inicio | Fin | Tipo | Duración |
|---|---|---|---|---:|
| 1 | 12:00 | 13:00 | Trabajo | 1 h |
| 2 | 13:00 | 14:00 | Bloqueo | 1 h |
| 3 | 14:00 | 15:00 | Trabajo | 1 h |

Resultado: tres horas transcurridas, dos horas trabajadas y una hora bloqueada.

## 2. Registro real por subtarea

Usar formato `dd/mm/aaaa hh:mm`. No completar `Fin real` hasta que la subtarea satisfaga su resultado y revisión.

| ID | Responsable | Inicio real | Fin real | Duración transcurrida | Esfuerzo real | Bloqueo | Evidencia/observación |
|---|---|---|---|---:|---:|---:|---|
| ST-BASE-01 | D1 | — | — | — | — | — | — |
| ST-ARQ-01 | D4 | — | — | — | — | — | — |
| ST-CI-01 | D6 | — | — | — | — | — | — |
| ST-DEMO-01 | D1 | — | — | — | — | — | — |
| ST-REL-01 | D5 | — | — | — | — | — | — |
| ST-CS01-DB | D1 | — | — | — | — | — | — |
| ST-CS01-SVC | D2 | — | — | — | — | — | — |
| ST-CS01-UI | D3 | — | — | — | — | — | — |
| ST-CS01-AUTH | D5 | — | — | — | — | — | — |
| ST-CS01-QA | D6 | — | — | — | — | — | — |
| ST-CS02-LIST | D2 | — | — | — | — | — | — |
| ST-CS02-UI | D3 | — | — | — | — | — | — |
| ST-CS02-STATE | D4 | — | — | — | — | — | — |
| ST-CS02-COPY | D4 | — | — | — | — | — | — |
| ST-CS02-QA | D3 | — | — | — | — | — | — |
| ST-CS03-MIG | D1 | — | — | — | — | — | — |
| ST-CS03-SVC | D2 | — | — | — | — | — | — |
| ST-CS03-FORM | D3 | — | — | — | — | — | — |
| ST-CS03-UI | D4 | — | — | — | — | — | — |
| ST-CS03-AUTO | D5 | — | — | — | — | — | — |
| ST-CS03-E2E | D6 | — | — | — | — | — | — |
| ST-EXP01-SVC | D2 | — | — | — | — | — | — |
| ST-EXP01-UI | D3 | — | — | — | — | — | — |
| ST-EXP01-AUD | D5 | — | — | — | — | — | — |
| ST-EXP01-QA | D6 | — | — | — | — | — | — |
| ST-DOC01-DB | D1 | — | — | — | — | — | — |
| ST-DOC01-SVC | D2 | — | — | — | — | — | — |
| ST-DOC01-LIST | D3 | — | — | — | — | — | — |
| ST-DOC01-LINK | D3 | — | — | — | — | — | — |
| ST-DOC01-MATCH | D4 | — | — | — | — | — | — |
| ST-DOC01-ACCESS | D5 | — | — | — | — | — | — |
| ST-DOC01-QA | D6 | — | — | — | — | — | — |
| ST-ALT01-DB | D1 | — | — | — | — | — | — |
| ST-ALT01-SVC | D4 | — | — | — | — | — | — |
| ST-ALT01-UI | D4 | — | — | — | — | — | — |
| ST-ALT01-QA | D6 | — | — | — | — | — | — |
| ST-SEC01-MASK | D5 | — | — | — | — | — | — |
| ST-SEC01-AUDIT | D2 | — | — | — | — | — | — |
| ST-SEC01-NEG | D6 | — | — | — | — | — | — |
| ST-SEC01-REV | D5 | — | — | — | — | — | — |

## 3. Línea temporal real por HU

No se suman intervalos paralelos para calcular duración cronológica.

```text
Inicio real HU = menor Inicio real de sus subtareas
Fin real HU = mayor Fin real de sus subtareas, después de aceptar los CA
Duración transcurrida HU = Fin real HU − Inicio real HU
Esfuerzo real HU = suma del esfuerzo real de sus subtareas
```

| HU | Inicio real | Fin real | Duración transcurrida | Esfuerzo real | SP aceptados | Evidencia de CA |
|---|---|---|---:|---:|---:|---|
| HU-CS-01 | — | — | — | — | 0/5 | — |
| HU-CS-02 | — | — | — | — | 0/5 | — |
| HU-CS-03 | — | — | — | — | 0/8 | — |
| HU-EXP-01 | — | — | — | — | 0/3 | — |
| HU-DOC-01 | — | — | — | — | 0/8 | — |
| HU-ALT-01 | — | — | — | — | 0/3 | — |
| HU-SEC-01 | — | — | — | — | 0/3 | — |

`SP aceptados` solo cambia de `0/x` a `x/x` cuando toda la HU cumple la Definition of Done. No existe crédito parcial de puntos.

## 4. Registro de sesiones cuando una subtarea se pausa

Duplicar filas según sea necesario.

| Subtarea | Sesión | Inicio | Fin | Tipo: trabajo/bloqueo/revisión | Duración | Nota |
|---|---:|---|---|---|---:|---|
| — | 1 | — | — | — | — | — |

## 5. Registro diario del Sprint

| Fecha | SP Done acumulados | Horas trabajadas acumuladas | Horas restantes estimadas | Bloqueos | Decisión de replanificación |
|---|---:|---:|---:|---|---|
| 15/10/2026 | 0 | — | 232 | — | — |
| 16/10/2026 | — | — | — | — | — |
| 17/10/2026 | — | — | — | — | — |
| 18/10/2026 | — | — | — | — | — |
| 19/10/2026 | — | — | — | — | Congelamiento funcional 19:00 |
| 20/10/2026 | — | — | — | — | — |

## 6. Cierre y velocidad

Completar únicamente después de la Sprint Review:

```text
SP comprometidos:                  35
SP que cumplen completamente DoD:  __
Velocidad real V1:                 __ SP
Horas-persona reales:              __ h
Horas bloqueadas:                  __ h
HUs trasladadas o retiradas:       __
```

No sustituir la velocidad real con porcentaje de avance, cantidad de subtareas ni horas consumidas.
