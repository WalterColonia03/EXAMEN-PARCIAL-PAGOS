# Evidencia técnica local · CR-006

**Fecha:** 18/10/2026  
**Alcance:** `EXP-LAB-12` / `MEJ-INV-025` / `CR-006`  
**Entorno:** copia local del repositorio, Python 3.12 y Django 6.1.2.

## Decisión sobre el PR de interfaz

El PR #1 fue revisado como insumo, pero no se integra. Sus intenciones útiles se
implementan de manera distinta: el asistente informa una falta de fondos sin
suspender, los documentos se retiran lógicamente con auditoría y no se elimina
el acceso de consulta a Calendario ni Cuentas de servicio. No se modifica el
estado remoto del PR desde esta evidencia.

## Cambios implementados

- Altas de compromisos, obligaciones y fuentes se normalizan a PEN. Las filas
  USD históricas son consultables, aparecen separadas y los servicios/rutas
  bloquean edición, generación, pagos, cambios de estado, documentos y
  recordatorios nuevos.
- El asistente puede crear un aviso de falta de fondos con actor, fecha y
  observación; no cambia el estado financiero. El gerente puede resolver el
  aviso o tomar por separado una decisión de suspensión/reactivación.
- Un sustento se retira antes del primer movimiento con motivo, actor, fecha y
  auditoría. Su fila y objeto permanecen; ya no habilita pagos. Los comprobantes
  no usan este flujo.
- La migración `payments.0010_attachment_withdrawal_reason_attachment_withdrawn_at_and_more`
  agrega el aviso de fondos, retiro lógico y restricciones de consistencia.
- `config/settings.py` admite PostgreSQL mediante `DATABASE_URL` y Storage S3
  privado de Supabase. En producción rechaza configuración incompleta y limita
  adjuntos a 4 MB por el límite de Functions de Vercel.
- El comando interactivo `create_initial_manager` crea el primer usuario con
  rol Gerente sin pasar contraseñas como argumento de shell.

## Validaciones ejecutadas

```text
manage.py check                                  -> sin incidencias
manage.py makemigrations --check --dry-run       -> No changes detected
manage.py test --parallel 4                      -> 84 pruebas aprobadas
```

Las pruebas nuevas cubren: separación de falta de fondos/suspensión, permisos
del asistente, retiro lógico antes y después de movimientos, auditoría,
normalización PEN, bloqueo de USD histórico y creación del gerente inicial.

## Límites que siguen pendientes

- No se creó ni se alteró un proyecto real de Supabase o Vercel.
- No se ejecutó una migración contra PostgreSQL real ni se migraron datos de
  `db.sqlite3` o `private_uploads/`.
- Falta la validación visual/manual por roles y la prueba de persistencia real
  tras una nueva invocación o redeploy de Vercel.

La guía operativa para completar esos pasos está en
`DESPLIEGUE_VERCEL_SUPABASE.md`.
