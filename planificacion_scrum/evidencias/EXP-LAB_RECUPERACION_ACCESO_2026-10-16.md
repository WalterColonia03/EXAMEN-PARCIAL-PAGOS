# Evidencia técnica de acceso y recuperación segura

**Fecha:** 16/10/2026  
**Zona horaria:** America/Lima  
**Origen:** primer intento del recorrido manual desde cero  
**Feedback:** `FB-005`  
**Capacidad:** `EXP-LAB-11`  
**Estado:** verificada automáticamente; revisión visual y aceptación del responsable del producto pendientes

Esta ficha no contiene correos completos de personas reales, contraseñas, códigos de recuperación ni huellas de códigos. Los datos utilizados pertenecen únicamente a las dos cuentas locales ficticias del laboratorio.

## 1. Problema observado

La pantalla inicial respondió **Credenciales inválidas**. Antes de modificar el sistema se comprobó:

- las dos cuentas locales existían, estaban activas y tenían contraseña utilizable;
- `check_password()` y `authenticate()` aceptaban las credenciales exactas;
- un POST real con CSRF y cookies redirigía correctamente al panel gerencial y a la cola del asistente;
- escribir el mismo correo con mayúsculas distintas era rechazado;
- no existían rutas, enlaces, pantallas, correo saliente útil, códigos ni administración visual para recuperar una cuenta.

No había telemetría previa para reconstruir qué texto exacto envió el navegador en el intento del usuario. Por ello no se atribuye ese intento a una causa no demostrada. Sí se corrigió el defecto reproducible de sensibilidad a mayúsculas y la ausencia total de recuperación.

## 2. Decisión funcional

Como las cuentas de laboratorio terminan en `.local` y no existe un canal de correo configurado, no se simula el envío de mensajes. La variante implementada usa:

1. códigos personales de emergencia para cada titular;
2. código temporal de 30 minutos que solo el gerente reautenticado puede emitir al asistente;
3. recuperación pública mediante código opaco, contraseña nueva y confirmación;
4. presentación del correo canónico únicamente después de validar y consumir el código;
5. intervención técnica local como último recurso si el gerente pierde también sus códigos.

El asistente no puede emitir códigos para el gerente ni administrar otra cuenta.

## 3. Controles implementados

| Control | Resultado técnico |
|---|---|
| Normalización del correo | Se recortan espacios externos y se compara mediante `email_normalized`, sin distinguir mayúsculas |
| Contraseña | Conserva sensibilidad a mayúsculas; nunca se repuebla después de un error |
| Ayuda en el ingreso | El correo escrito se conserva; existe Mostrar/Ocultar y enlace de recuperación |
| Código | 128 bits aleatorios, representación hexadecimal con guiones y almacenamiento mediante HMAC-SHA-256 |
| Consumo | Un solo uso; se rechaza si fue usado, revocado o venció |
| Código temporal | Solo Gerente → Asistente, reautenticación obligatoria y vigencia de 30 minutos |
| Código personal | Lo renueva únicamente el titular; emitir un juego nuevo revoca el anterior |
| Nueva contraseña | Validadores de similitud, mínimo 10 caracteres, contraseña común y solo numérica |
| Sesiones | Se eliminan las sesiones activas de la cuenta recuperada |
| Enumeración | Código inválido, usado o vencido recibe un mensaje neutro sin revelar cuenta ni rol |
| Límite de intentos | Ingreso: 8 intentos; recuperación: 6 intentos; pausa local de 15 minutos |
| Auditoría | Eventos de emisión, uso, rechazo y revocación separados de pagos y obligaciones; sin secretos |
| Navegación | Módulo **Mi acceso** para ambos roles y recuperación pública desde el login |

## 4. Cambios técnicos trazables

- `identity/models.py`: códigos y eventos de acceso; autenticación por clave natural normalizada.
- `identity/services.py`: emisión, huella, consumo, expiración, revocación y cierre de sesiones.
- `identity/forms.py`: recuperación, confirmación de contraseña y selección controlada del asistente.
- `identity/views.py` e `identity/urls.py`: ingreso normalizado, límites de intentos, recuperación y gestión autenticada.
- `identity/templates/identity/`: ingreso mejorado, recuperación, confirmación y módulo **Mi acceso**.
- `identity/migrations/0002_access_recovery.py`: persistencia de códigos y auditoría de identidad.
- `identity/test_access_recovery.py`: regresiones y controles de seguridad.
- `config/settings.py`: validadores de contraseña.
- `payments/templates/payments/base.html`: acceso visible a **Mi acceso** para el usuario autenticado.

## 5. Protección del estado previo

Antes de migrar se detuvo el servidor y se creó una copia de la base local:

| Evidencia | Valor |
|---|---|
| Ruta | `C:\Users\walte\Downloads\PROYECTO PARCIAL_RESPALDOS\antes_recuperacion_acceso_2026-10-16_121326\db.sqlite3` |
| Tamaño | 475.136 bytes |
| SHA-256 | `749921040E2168074F2ECFA143421D1DD0589FEEBB27A46D867FE7AD3239DED8` |

La migración `identity.0002_access_recovery` se aplicó después del respaldo. No se ejecutó `seed_demo_data.py` ni se recrearon datos operativos.

## 6. Comprobaciones automatizadas

| Comprobación | Resultado |
|---|---|
| `manage.py check` | 0 incidencias |
| `makemigrations --check --dry-run` | Sin cambios pendientes |
| Pruebas de `identity` | 23 de 23 aprobadas |
| Suite completa | 78 de 78 pruebas aprobadas en 157,066 s |
| Ingreso HTTP Gerente con mayúsculas mixtas | Redirección correcta a Control gerencial; sin mensaje inválido |
| Ingreso HTTP Asistente en mayúsculas | Redirección correcta a Cola operativa; sin mensaje inválido |
| Recuperación pública | HTTP 200 y formulario de código disponible |
| Navegación autenticada | Enlace **Mi acceso** presente para ambos roles |

Las pruebas de identidad cubren los destinos por rol, correo con mayúsculas y espacios externos, preservación del correo tras error, ocultamiento de contraseña, códigos personales, expiración y uso único, revocación de sesiones, contraseña débil, reautenticación del gerente, prohibición al asistente, revocación de juegos anteriores, ausencia de secretos persistidos y límites de intentos. La suite completa confirmó además que obligaciones, pagos, permisos, archivos y formularios anteriores no sufrieron regresiones.

Después de las comprobaciones HTTP se eliminaron sus sesiones y se restituyó `last_login` a vacío. La línea base conserva cero empresas, ámbitos, fuentes, locales, acreedores, cuentas operativas, compromisos, obligaciones, adjuntos, pagos, recordatorios, importaciones y auditorías de pagos; también conserva cero sesiones y cero archivos activos. Solo existen seis códigos técnicos activos —tres por titular— y su auditoría de identidad, necesarios para el nuevo mecanismo.

## 7. Validaciones manuales pendientes

- revisar el ingreso, Mostrar/Ocultar y recuperación con teclado;
- comprobar el diseño en escritorio y a 375 px;
- confirmar que el responsable entiende dónde guardar los códigos;
- ejecutar una recuperación temporal real del asistente y verificar el relevo Gerente → Asistente;
- decidir si, antes de un despliegue real, se incorpora correo secundario verificado, passkey o MFA;
- sustituir el límite en memoria por un mecanismo compartido/persistente si se ejecutan varios procesos o servidores.

## 8. Conclusión

El bloqueo inicial ya tiene una salida funcional y segura para el laboratorio. La corrección no demuestra todavía aceptación visual ni sustituye un servicio real de recuperación para producción. La siguiente acción es reiniciar la guía manual desde su **Fase 0** y registrar el resultado observado sin incluir secretos.
