# Evidencia de reinicio controlado para validación manual

**Fecha de autorización:** 16/10/2026  
**Zona horaria:** America/Lima  
**Origen:** solicitud del responsable del producto para probar el sistema desde cero con los roles Gerente y Asistente  
**Guía relacionada:** `../11_GUIA_VALIDACION_MANUAL_DESDE_CERO.md`  
**Estado documental:** versión 0.8 lista para validación manual  
**Estado técnico del reinicio:** completado y verificado; línea base operativa vacía  
**Validación manual:** no ejecutada

## 1. Propósito y límites

Esta ficha debe demostrar qué se retiró de la instalación local, qué se conservó y cómo se puede recuperar el estado anterior. No demuestra que el recorrido visual haya sido ejecutado ni convierte el laboratorio en Sprint terminado.

El reinicio autorizado comprende datos operativos y archivos privados locales. No autoriza borrar código, migraciones, pruebas, documentación ni planificación. No se ejecuta `seed_demo_data.py` después de limpiar, porque repoblaría la base con información de muestra.

## 2. Estado previo observado

Los siguientes valores proceden de la inspección inmediatamente anterior a la limpieza y del respaldo copiado antes de modificar la base.

| Evidencia previa | Valor real |
|---|---|
| Ruta absoluta de la base | `C:\Users\walte\Downloads\PROYECTO PARCIAL\db.sqlite3` |
| Tamaño de `db.sqlite3` | 491.520 bytes |
| SHA-256 de `db.sqlite3` | `217A3E37FEE6D4FB70D7E88B820369CE7126E811E4F9248CCA4CC594D11ABC3C` |
| Archivos en `private_uploads/` | 5 archivos, 1.858.372 bytes; inventario y hashes en la sección 3 |
| Sesiones activas | 19 |
| Cuentas de usuario | 2: una con rol Gerente y una con rol Asistente |
| Registros operativos | 54 registros en los modelos detallados en la tabla de la sección 4 |
| Servidor local detenido antes de copiar | Sí; procesos del servidor local verificados en cero el 16/10/2026 a las 11:22, America/Lima |

Si algún dato previo no pudo obtenerse, se debe escribir `No disponible` y explicar el motivo; no se inventará un valor retrospectivo.

## 3. Respaldo recuperable

Antes de cualquier eliminación se debe conservar una copia consistente de la base y, si existían archivos, de `private_uploads/`. La ubicación debe estar fuera de las rutas activas de la aplicación para que el sistema limpio no los utilice.

| Elemento | Evidencia real |
|---|---|
| Ruta del respaldo de base | `C:\Users\walte\Downloads\PROYECTO PARCIAL_RESPALDOS\antes_limpieza_2026-10-16_111828\db.sqlite3` |
| SHA-256 del respaldo de base | `217A3E37FEE6D4FB70D7E88B820369CE7126E811E4F9248CCA4CC594D11ABC3C` |
| Coincide con el hash previo | Sí; la copia se hizo con el servidor detenido y antes de limpiar |
| Ruta del respaldo de archivos | `C:\Users\walte\Downloads\PROYECTO PARCIAL_RESPALDOS\antes_limpieza_2026-10-16_111828\private_uploads` |
| Formato del respaldo de archivos | Carpeta original movida íntegramente fuera de la ruta activa; sin compresión |
| SHA-256 del archivo comprimido | No aplica; se conservaron hashes SHA-256 individuales |
| Responsable y fecha/hora | Codex, bajo autorización explícita del responsable del producto; 16/10/2026, 11:22–11:31, America/Lima |

### Inventario verificable de archivos respaldados

| Ruta relativa dentro de `private_uploads` | Bytes | SHA-256 |
|---|---:|---|
| `payments\2026\10\1f8673afe9764c51aeb333e70fae4f8e.pdf` | 73 | `119E7E781ADBA8A80FE364AADEF78E3EB1D0E28D973F12C9F93F87C69E89F590` |
| `payments\2026\10\241999a8c2304143b034adf86ca4a8eb.jpg` | 110.749 | `50186D65BCA4BC6E8CF39363163B8988D5772038A55D6E57F4587690E6665838` |
| `payments\2026\10\4e39ab4a67ff429b80bc96284aad324c.pdf` | 1.636.728 | `71F5FF08F0533326FBAB0AC90B5EACABA5DFB109333B1332B03FC65AFAA28E4E` |
| `payments\2026\10\8bfabde4b6c146d6b94164f9417e18b4.jpg` | 110.749 | `50186D65BCA4BC6E8CF39363163B8988D5772038A55D6E57F4587690E6665838` |
| `payments\2026\10\ce9258402dbd4e2fa5f9040ccdfb81a0.pdf` | 73 | `119E7E781ADBA8A80FE364AADEF78E3EB1D0E28D973F12C9F93F87C69E89F590` |

### Prueba de recuperación documentada

Procedimiento previsto, que debe ajustarse a las rutas reales anteriores:

1. detener el servidor de PagoControl;
2. apartar la base y `private_uploads/` actuales sin sobrescribirlos;
3. copiar el respaldo verificado a la ruta activa de `db.sqlite3`;
4. restaurar `private_uploads/` manteniendo nombres y estructura;
5. ejecutar `manage.py check` y confirmar que la base abre;
6. registrar si se realizó una restauración de ensayo o solo se documentó el procedimiento.

**Resultado real de la prueba de recuperación:** no se sobrescribió la línea base nueva con una restauración completa. El 16/10/2026 se abrió la copia de `db.sqlite3` en modo de solo lectura: `PRAGMA integrity_check` devolvió `ok`, `PRAGMA foreign_key_check` no devolvió incidencias y se comprobaron 28 migraciones, 2 cuentas y 5 registros de adjuntos. Los cinco archivos respaldados pudieron leerse y calcularse sus hashes. Queda visible la limitación de que no se realizó una restauración integral de ensayo.

No se debe afirmar “respaldo recuperable” hasta confirmar las rutas, hashes y al menos la legibilidad de la copia. Si no se realizó una restauración de ensayo, esa limitación permanecerá visible.

## 4. Alcance de la limpieza y conteos

La columna **Objetivo posterior** define la línea base acordada. La columna **Resultado real** debe completarse después de ejecutar la limpieza.

| Modelo o almacenamiento | Estado previo | Objetivo posterior | Resultado real |
|---|---:|---:|---:|
| `Company` | 1 | 0 | 0 |
| `PaymentContext` | 1 | 0 | 0 |
| `FundingSource` | 0 | 0 | 0 |
| `Branch` | 2 | 0 | 0 |
| `Creditor` | 5 | 0 | 0 |
| `DestinationAccount` | 5 | 0 | 0 |
| `ServiceAccount` | 3 | 0 | 0 |
| `PaymentCommitment` | 3 | 0 | 0 |
| `Payable` | 12 | 0 | 0 |
| `Attachment` | 5 | 0 | 0 |
| `Payment` | 2 | 0 | 0 |
| `InternalReminder` | 10 | 0 | 0 |
| `PayableImportBatch` | 0 | 0 | 0 |
| `AuditLog` | 5 | 0 | 0 |
| Sesiones Django | 19 | 0 | 0 |
| Archivos activos en `private_uploads/` | 5 | 0 | 0 |
| Cuentas activas Gerente | 1 | 1 | 1 |
| Cuentas activas Asistente | 1 | 1 | 1 |
| Otras cuentas activas | 0 | 0 | 0 |

Los roles, permisos, tipos de contenido y registros de migración son datos técnicos y deben conservarse o reconstruirse de manera controlada. La contraseña de las dos cuentas no se registra aquí.

## 5. Acciones ejecutadas

Completar con el método real, en orden, sin incluir secretos:

| Orden | Fecha/hora | Acción real | Resultado |
|---:|---|---|---|
| 1 | 16/10/2026 11:22 | Detener y verificar el proceso del servidor | Servidor del puerto 8010 detenido; cero procesos coincidentes después de la operación |
| 2 | 16/10/2026 11:22 | Crear y verificar respaldo de base | Copia de 491.520 bytes creada fuera del proyecto y hash SHA-256 confirmado |
| 3 | 16/10/2026 11:22 | Respaldar archivos privados, si existían | 5 archivos movidos íntegramente al respaldo; carpeta activa recreada vacía |
| 4 | 16/10/2026 11:23 | Retirar datos operativos y sesiones | Eliminación por ORM dentro de una sola transacción, respetando el orden de relaciones protegidas |
| 5 | 16/10/2026 11:23 | Conservar o recrear solo Gerente y Asistente | Se conservaron sus UUID y roles; se retiró “demo” de los correos y nombres, se renovaron claves y se reinició `last_login` |
| 6 | 16/10/2026 11:24 | Verificar conteos posteriores | Todos los modelos operativos, sesiones y archivos activos quedaron en cero; cuentas previstas en 1 + 1 |
| 7 | 16/10/2026 11:25–11:35 | Ejecutar controles técnicos y reiniciar el servidor | Integridad, migraciones y 62 pruebas aprobadas; servidor local iniciado y `http://127.0.0.1:8010/login/` respondió HTTP 200 |

**Comando o mecanismo exacto utilizado:** respaldo nativo de `db.sqlite3`, traslado íntegro de `private_uploads`, eliminación mediante Django ORM dentro de `transaction.atomic()`, desvinculación previa de autorreferencias de movimientos, borrado de sesiones, reinicio de secuencias exclusivas de `payments` y `VACUUM` posterior. Las credenciales no se incluyen en esta evidencia.

## 6. Comprobaciones posteriores

| Comprobación | Resultado esperado | Resultado real |
|---|---|---|
| `manage.py check` | Sin incidencias | Aprobado: 0 incidencias |
| `manage.py makemigrations --check --dry-run` | Sin cambios | Aprobado: `No changes detected` |
| Migraciones aplicadas | Esquema vigente completo | 28 registros de migración conservados; sin migraciones pendientes |
| Suite automatizada | Todas las pruebas aprobadas | Aprobada el 16/10/2026: 62 de 62 pruebas en 118,836 s sobre base aislada |
| Inicio de sesión Gerente | Acceso a Control gerencial vacío | Credencial verificada por el backend; recorrido visual reservado para G-01 |
| Inicio de sesión Asistente | Acceso a Cola operativa vacía | Credencial verificada por el backend; recorrido visual reservado para A-01 |
| Revisión de archivos activos | Cero archivos heredados | Aprobado: 0 archivos activos |
| Integridad SQLite activa | Base consistente | `integrity_check = ok`; 0 incidencias de claves foráneas |
| Base activa compactada | Línea base técnica estable | 475.136 bytes; SHA-256 `719186C2B1832A6262EFE9DBF0C21A1F23B9B845327F869966AA5FE039A2E1FF` |
| Disponibilidad local | Pantalla de acceso accesible | Aprobado: HTTP 200 en `http://127.0.0.1:8010/login/` y marca PagoControl presente |

La suite automatizada utiliza una base aislada y no sustituye la comprobación de los conteos de la base local activa.

## 7. Estado posterior y siguiente paso

La versión documental `0.8` queda **lista para validación manual**. Esto significa que existen una guía y una línea base técnica verificada; no significa que el recorrido funcional ya haya sido ejecutado por el responsable del producto.

Una vez consolidados respaldo, hashes, conteos y controles técnicos, el responsable del producto debe ejecutar `11_GUIA_VALIDACION_MANUAL_DESDE_CERO.md`. Sus observaciones se registrarán en una evidencia nueva `EXP-LAB_VALIDACION_MANUAL_<FECHA>.md`; no se sobrescribirá esta ficha de reinicio ni la evidencia técnica anterior.

**Conclusión técnica del reinicio:** completado. La instalación conserva código, documentación, 28 migraciones, 3 roles técnicos y exactamente dos cuentas activas; no conserva datos operativos, sesiones ni archivos activos anteriores. El estado previo permanece respaldado fuera del proyecto y la siguiente actividad autorizada es la validación manual descrita en la guía relacionada.
