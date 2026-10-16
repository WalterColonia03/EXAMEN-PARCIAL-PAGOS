# Sprint Planning y estimación inicial

> **Documento histórico del Sprint original.** El laboratorio `CR-005` y sus cambios `EXP-LAB-*` no alteran este compromiso, sus 35 SP, capacidad, fechas ni velocidad. Su estado actual se consulta en los documentos `09`, `10` y la evidencia EXP-LAB.

## 1. Identidad del Sprint

| Campo | Valor |
|---|---|
| Nombre | Sprint único — Cuentas de servicio y captura asistida |
| Zona horaria | America/Lima |
| Inicio | Jueves 15/10/2026 14:00 |
| Fin | Martes 20/10/2026 19:00 |
| Días trabajados | Jueves, viernes, sábado, domingo, lunes y martes |
| Equipo | 6 Developers |
| Jornada declarada | 10 horas por persona y día |
| Sprint Goal | Incorporar cuentas de servicio y reducir la digitación sin perder seguridad ni trazabilidad |
| Alcance comprometido | 7 HUs / 35 SP |

La duración cronológica del contenedor es de 125 horas, pero la capacidad se calcula únicamente con las jornadas declaradas del equipo.

## 2. Capacidad del equipo

### 2.1 Capacidad bruta

```text
6 Developers × 6 días × 10 h = 360 horas-persona
```

### 2.2 Descuentos planificados

Se adopta la interpretación conservadora de que las diez horas declaradas incluyen pausas.

| Concepto | Cálculo | Horas-persona |
|---|---:|---:|
| Comida y descansos | 1.5 h × 6 días × 6 personas | 54.0 |
| Sprint Planning | 2 h × 6 personas | 12.0 |
| Daily Scrum | 0.25 h × 5 días × 6 personas | 7.5 |
| Revisión de riesgo de mitad de Sprint | 0.5 h × 6 personas | 3.0 |
| Sprint Review | 1 h × 6 personas | 6.0 |
| Retrospectiva | 0.75 h × 6 personas | 4.5 |
| **Total no disponible para entrega** |  | **87.0** |

```text
Capacidad operativa = 360 − 87 = 273 horas-persona
```

Por ser el primer Sprint del equipo en este producto, se reserva un 15 % para integración, defectos, bloqueos y desconocimiento:

```text
Capacidad comprometible = 273 × 0.85 = 232.05 horas-persona
```

Se redondea a **232 horas-persona**. La reserva no autoriza alcance nuevo; protege el Sprint Goal.

## 3. La velocidad del primer Sprint

No existe una velocidad histórica antes de completar el primer Sprint. Se diferencian dos valores:

### Pronóstico inicial

Sirve para seleccionar el alcance y puede cambiar durante la sesión de Planning.

```text
Pronóstico de SP = capacidad comprometible ÷ esfuerzo por SP de la HU pivote
```

### Velocidad observada

Solo se conoce al cierre:

```text
Velocidad real V1 = Σ SP de las HUs completamente Done
```

Una HU parcialmente terminada aporta `0 SP`, aunque posea subtareas finalizadas. Los Story Points representan esfuerzo, complejidad e incertidumbre relativos; no son horas. La equivalencia temporal siguiente se usa una sola vez para arrancar sin datos históricos.

## 4. HU pivote y cálculo

Se adopta `HU-CS-01 · Registrar una cuenta de servicio` como pivote:

- valor: `5 SP`;
- esfuerzo técnico de referencia: `30 horas-persona`;
- contiene datos, reglas, interfaz, autorización, auditoría y pruebas;
- el equipo puede comprenderla y compararla con el resto.

```text
Relación inicial de arranque = 30 h ÷ 5 SP = 6 h/SP
Pronóstico = 232.05 h ÷ 6 h/SP = 38.675 SP
```

Resultado:

- pronóstico matemático: aproximadamente `38 SP`;
- compromiso conservador: `35 SP`;
- margen respecto del pronóstico: aproximadamente `3 SP`;
- velocidad máxima posible si todo lo comprometido cumple DoD: `35 SP`.

Esta relación no debe reutilizarse como tarifa permanente. Si al cierre se completan, por ejemplo, 27 SP, la velocidad real del Sprint será 27 SP, no 35 ni 38.

## 5. Escala relativa

| SP | Comparación con HU-CS-01 de 5 SP |
|---:|---|
| 1 | Cambio muy pequeño, conocido y localizado. |
| 2 | Menos de la mitad del pivote. |
| 3 | Aproximadamente entre la mitad y dos tercios. |
| 5 | Complejidad equivalente al pivote. |
| 8 | Entre 1.5 y 2 veces el pivote; varias capas o riesgo de integración. |
| 13 | Demasiado grande para este Sprint; debe dividirse. |

Cada estimación considera reglas de negocio, capas afectadas, incertidumbre, dependencias, pruebas y riesgo de datos o seguridad. No aumenta porque una persona específica trabaje más lento.

## 6. Composición del compromiso

| HU | MoSCoW | SP | Horas de subtareas |
|---|---:|---:|---:|
| HU-CS-01 | 4 | 5 | 30 |
| HU-CS-02 | 4 | 5 | 26 |
| HU-CS-03 | 4 | 8 | 44 |
| HU-EXP-01 | 4 | 3 | 20 |
| HU-DOC-01 | 3 | 8 | 44 |
| HU-ALT-01 | 3 | 3 | 18 |
| HU-SEC-01 | 4 | 3 | 20 |
| **Subtotal funcional** |  | **35** | **202** |
| Trabajo técnico transversal | — | Sin SP | 30 |
| **Total** |  | **35** | **232** |

Los puntos se asignan solo a HUs. Las 30 horas transversales no producen Story Points y no se duplican dentro de las historias.

## 7. Cronograma del Sprint

| Fecha y hora | Evento o hito |
|---|---|
| Jue. 15, 14:00–16:00 | Planning: objetivo, capacidad, criterios, estimación y ratificación del equipo. |
| Jue. 15, 16:00–00:00 | Línea base, contratos, seguridad y primeras verticales. |
| Vie. 16, 09:00–09:15 | Daily Scrum. |
| Vie. 16, 09:15–19:00 | Cuenta de servicio, mantenimiento y gasto express. |
| Sáb. 17, 09:00–09:15 | Daily Scrum. |
| Sáb. 17, 09:15–19:00 | Integración con compromisos, seguridad y bandeja. |
| Dom. 18, 09:00–09:15 | Daily Scrum. |
| Dom. 18, 13:00–13:30 | Revisión de riesgo y replanificación sin aumentar alcance. |
| Dom. 18, resto de jornada | Integración, pruebas y cierre del registro express. |
| Lun. 19, 09:00–09:15 | Daily Scrum. |
| Lun. 19, 09:15–19:00 | Pruebas integradas, alertas y bandeja documental. |
| Lun. 19, 19:00 | Congelamiento funcional: desde aquí no entran funciones nuevas. |
| Mar. 20, 09:00–09:15 | Daily Scrum. |
| Mar. 20, 09:15–15:00 | Regresión, correcciones, evidencia y preparación de demo. |
| Mar. 20, 15:00–16:00 | Control final de DoD y demostración interna. |
| Mar. 20, 16:00–17:00 | Sprint Review. |
| Mar. 20, 17:00–17:45 | Retrospectiva. |
| Mar. 20, 17:45–19:00 | Cierre documental y registro de trabajo pendiente real. |

## 8. Línea temporal planificada por HU

Esta tabla es independiente del contenedor del Sprint. La ventana de una HU va desde el inicio de su primera subtarea hasta el fin de la última. La duración cronológica incluye noches y tiempos sin trabajo; el esfuerzo suma únicamente horas de subtareas.

| HU | Inicio planificado | Fin planificado | Ventana cronológica | Esfuerzo |
|---|---|---|---:|---:|
| HU-CS-01 | 15/10 16:00 | 16/10 16:00 | 24 h | 30 h-persona |
| HU-CS-02 | 16/10 09:00 | 19/10 15:00 | 78 h | 26 h-persona |
| HU-CS-03 | 17/10 09:00 | 19/10 15:00 | 54 h | 44 h-persona |
| HU-EXP-01 | 16/10 14:00 | 18/10 19:00 | 53 h | 20 h-persona |
| HU-DOC-01 | 17/10 09:00 | 20/10 15:00 | 78 h | 44 h-persona |
| HU-ALT-01 | 19/10 09:00 | 19/10 19:00 | 10 h | 18 h-persona |
| HU-SEC-01 | 16/10 09:00 | 19/10 14:00 | 77 h | 20 h-persona |

El esfuerzo puede superar la ventana de una HU porque varias personas trabajan en paralelo. La línea real se completará con el archivo `05_REGISTRO_DE_TIEMPOS_REALES.md`.

## 9. Estrategia de ejecución

- WIP máximo: tres HUs en curso simultáneamente a nivel de equipo.
- Una subtarea tiene un único responsable y un revisor diferente.
- Se permite comenzar trabajo de interfaz o servicio contra un contrato acordado aunque una migración todavía no esté integrada; esa relación se marca como de integración, no como bloqueo duro.
- Ninguna persona debe tener dos subtareas activas al mismo tiempo.
- Los defectos encontrados antes de aceptar una HU se corrigen dentro de esa HU.
- Un defecto nuevo después de aceptar la HU se registra por separado y consume reserva.
- No se inicia alcance `Could` o `Won't` durante este Sprint.

## 10. Definition of Ready

Una HU puede iniciarse cuando:

- tiene descripción y beneficio claros;
- posee criterios verificables y sin contradicciones;
- tiene prioridad y Story Points ratificados por los seis Developers;
- sus dependencias y datos de prueba están identificados;
- el equipo entiende qué queda fuera;
- cabe en el Sprint sin superar el WIP;
- no existe una decisión funcional imprescindible pendiente.

## 11. Definition of Done

Una HU está `Done` únicamente cuando:

1. todos sus criterios de aceptación fueron comprobados;
2. sus subtareas están finalizadas y sus tiempos reales registrados;
3. el código fue revisado por alguien distinto del implementador;
4. las migraciones funcionan desde una base vacía y desde la línea base aplicable;
5. las pruebas automáticas nuevas y las 75 pruebas de regresión pasan;
6. se probaron permisos negativos mediante solicitudes directas;
7. no quedan defectos críticos o altos abiertos asociados;
8. la interfaz funciona en escritorio y móvil sin depender solo del color;
9. se actualizó la documentación necesaria;
10. existe evidencia real y reproducible; no una afirmación simulada.

## 12. Resultado posible al cierre

| Condición | Velocidad real |
|---|---:|
| Todas las HUs cumplen DoD | 35 SP |
| Una HU de 8 SP queda incompleta | 27 SP |
| Solo terminan las HUs Must | 24 SP |
| Una HU está al 90 %, pero no cumple DoD | 0 SP por esa HU |

El profesor puede recomendar cambios después de la demostración. Esos cambios no alterarán retroactivamente la velocidad ni los tiempos reales; se registrarán en el control de cambios y se reestimarán.
