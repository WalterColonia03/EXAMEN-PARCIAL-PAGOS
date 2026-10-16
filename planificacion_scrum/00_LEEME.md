# Planificación Scrum — Sistema de Control de Pagos y Vencimientos

## Estado del documento

**Borrador vivo de planificación y especificación experimental. No cargado en Jira.**

Esta carpeta pertenece exclusivamente al sistema de control de pagos de la carpeta local `PROYECTO PARCIAL`. No reemplaza, reutiliza ni modifica la planificación existente del proyecto de minimarket.

**Aclaración de conectividad:** este trabajo permanece local. No se publicó en GitHub, no se configuró un repositorio remoto y no se conectó una cuenta de Jira. El uso local de comandos de control de versiones sirve únicamente para revisar diferencias antes de entregar.

La documentación se actualizará mientras se construye y valida el sistema. Cuando el profesor revise la versión funcional:

1. se registrará su feedback;
2. se aceptarán, rechazarán o reformularán las sugerencias;
3. se actualizarán las historias, criterios, puntos y subtareas;
4. se congelará una versión final de la planificación;
5. recién entonces se preparará la carga a un proyecto Jira separado.

Desde el 15/10/2026 existe además un **laboratorio experimental de producto** autorizado mediante `CR-005`. Su objetivo es probar, cambiar y descartar ideas hasta que el responsable del producto considere que PagoControl representa correctamente obligaciones empresariales, personales, familiares y patrimoniales. Este laboratorio:

- se documenta en `10_PLAN_EXPERIMENTAL_PROTOTIPO.md`;
- no modifica el Sprint único ni sus historias, puntos, fechas, horas o estados;
- no crea incidencias ni worklogs en Jira;
- no convierte una especificación en funcionalidad implementada;
- será refinado como Scrum y preparado para Jira solo después de que el responsable del producto apruebe el resultado funcional del prototipo.

No se deben inventar fechas, estados `Done`, worklogs ni evidencias retroactivas. Las fechas de este documento son **planificadas**. Los campos de ejecución real se completarán cuando el equipo haga el trabajo.

## Archivos

| Archivo | Propósito |
|---|---|
| `01_REVISION_ESTADO_Y_ALCANCE.md` | Auditoría del sistema actual, brechas, objetivo y límites. |
| `02_HISTORIAS_DE_USUARIO.md` | Product Backlog con descripción, criterios de aceptación, MoSCoW y Story Points. |
| `03_SPRINT_PLANNING_Y_VELOCIDAD.md` | Capacidad, HU pivote, pronóstico de velocidad, Sprint Goal, DoR y DoD. |
| `04_SUBTAREAS_Y_CRONOGRAMA.md` | Subtareas, responsables, dependencias y fechas/horas planificadas. |
| `05_REGISTRO_DE_TIEMPOS_REALES.md` | Plantilla para registrar inicio, fin, duración transcurrida y esfuerzo real. |
| `06_FEEDBACK_Y_CONTROL_DE_CAMBIOS.md` | Registro de feedback del profesor y decisiones de alcance. |
| `07_VISION_RECUPERADA_Y_HU_DE_PRODUCTO.md` | Visión recuperada del producto, HUs funcionales adaptadas y relación con el backlog original. No altera compromisos del Sprint por sí sola. |
| `08_INVESTIGACION_DE_REFERENTES_Y_BENCHMARK.md` | Fuente `INV-001`: referentes investigados, aprendizajes y límites de interpretación. |
| `09_MATRIZ_DE_MEJORAS_Y_TRAZABILIDAD.md` | Registro `MEJ-INV`: decisión, prioridad, relación con HUs, evidencia requerida y estado de cada mejora derivada de la investigación. |
| `10_PLAN_EXPERIMENTAL_PROTOTIPO.md` | Especificación trazable del laboratorio `CR-005`: dominio ampliado, reglas, flujos, pantallas, experimentos y puertas de validación, sin SP, horas ni Jira. |
| `11_GUIA_VALIDACION_MANUAL_DESDE_CERO.md` | Recorrido reproducible Gerente → Asistente → Gerente desde una base operativa vacía; define datos ficticios, resultados esperados y checklist, sin afirmar su ejecución. |
| `evidencias/INV-001_investigacion_sistemas_similares.md` | Ficha de integridad y procedencia de la investigación entregada por el usuario. |
| `evidencias/INV-002_ambitos_personales_familiares_y_patrimoniales.md` | Investigación de casos personales, familiares, patrimoniales y excepciones financieras que fundamenta `CR-005`. |
| `evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md` | Evidencia técnica del prototipo: correspondencia EXP-LAB, pruebas, decisiones conscientes y validaciones pendientes. |
| `evidencias/EXP-LAB_REINICIO_CONTROLADO_2026-10-16.md` | Ficha separada con el respaldo, los conteos anteriores y posteriores y los controles reales del reinicio previo a la validación manual. |
| `evidencias/EXP-LAB_RECUPERACION_ACCESO_2026-10-16.md` | Evidencia técnica de `EXP-LAB-11`: diagnóstico del primer ingreso, normalización del correo, códigos de recuperación, permisos, pruebas y límites pendientes. |

## Convenciones

- Zona horaria: `America/Lima` (`UTC-5`).
- Sprint único: jueves 15/10/2026 14:00 a martes 20/10/2026 19:00.
- Equipo: seis Developers.
- Jornada declarada: diez horas por día durante jueves, viernes, sábado, domingo, lunes y martes.
- Story Points: únicamente en Historias de Usuario.
- Horas: únicamente en subtareas y trabajo técnico.
- Prioridad MoSCoW:
  - `4 — Must Have`.
  - `3 — Should Have`.
  - `2 — Could Have`.
  - `1 — Won't Have Now`.
- Una HU incompleta al cierre aporta `0 SP` a la velocidad real, aunque tenga subtareas terminadas.
- Los identificadores `EXP-LAB-*` son especificaciones experimentales, no HUs del Sprint: no llevan MoSCoW, Story Points, horas, responsable ni clave Jira.

## Equipo propuesto

La siguiente correspondencia procede de la documentación existente del equipo y debe ratificarse antes de iniciar el Sprint. Los códigos se usan para mantener legibles los cronogramas.

| Código | Developer |
|---|---|
| D1 | Favio Adriano Velasquez Revilla |
| D2 | Juan David Nolasco Castillo |
| D3 | Jordan Castillo Aranda |
| D4 | Sebastian Alcalde |
| D5 | Walter Luis Colonia Infantas |
| D6 | Jhonny Angeles |

Si cambia una persona o su disponibilidad, debe recalcularse el cronograma antes de comprometer el Sprint.

## Regla de honestidad temporal

Se conservarán por separado cuatro valores:

1. **Inicio y fin planificados:** ventana prevista en este documento.
2. **Inicio y fin reales:** marcas obtenidas cuando la incidencia cambia de estado durante la ejecución.
3. **Duración transcurrida:** `fin real − inicio real`.
4. **Esfuerzo real:** suma de periodos efectivamente trabajados; no incluye pausas ni tiempo bloqueado.

Ejemplo:

```text
Inicio real:             16/10/2026 12:00
Fin real:                16/10/2026 14:00
Duración transcurrida:   2 h
Esfuerzo real:           2 h
```

Si la incidencia estuvo bloqueada una hora, podría tener tres horas transcurridas y solo dos horas de esfuerzo. Ambas métricas son válidas, pero responden preguntas diferentes.
