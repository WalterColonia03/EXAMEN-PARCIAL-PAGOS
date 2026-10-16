# Guía de validación manual desde cero — PagoControl

## 1. Propósito y estado

Esta guía permite que el responsable del producto recorra PagoControl como si acabara de recibirlo: primero como **gerente**, después como **asistente** y finalmente otra vez como **gerente**. El recorrido comienza con una base operativa vacía y construye un caso completo sin depender de datos precargados.

**Estado:** preparada para ejecución manual.  
**Ejecución manual:** pendiente.  
**Ámbito:** laboratorio experimental `CR-005`; no modifica el Sprint histórico, no crea Story Points, horas o incidencias Jira y no constituye aceptación del producto.  
**Evidencia del reinicio:** `evidencias/EXP-LAB_REINICIO_CONTROLADO_2026-10-16.md`.
**Evidencia de acceso y recuperación:** `evidencias/EXP-LAB_RECUPERACION_ACCESO_2026-10-16.md`.

Los resultados se completarán durante la prueba. Una expectativa escrita en esta guía no equivale a evidencia de que la pantalla ya fue revisada.

## 2. Qué significa “desde cero”

La línea base funcional debe conservar únicamente lo necesario para ingresar y operar:

- código, migraciones y documentación del proyecto;
- roles técnicos necesarios;
- una cuenta activa de gerente y una cuenta activa de asistente;
- permisos y catálogos internos definidos por el código.

Debe comenzar sin empresas, locales, ámbitos, acreedores, cuentas de destino, fuentes de fondos, cuentas de servicio, compromisos, obligaciones, adjuntos, movimientos, recordatorios, importaciones ni auditorías operativas. Las sesiones anteriores deben estar cerradas y `private_uploads/` no debe contener archivos de pruebas anteriores.

La limpieza no significa borrar el código, las migraciones ni la planificación. Tampoco se debe ejecutar `seed_demo_data.py`, porque ese archivo crea datos de muestra y dejaría de ser una prueba desde una base operativa vacía.

### Limitación conocida del punto de partida

La variante actual no tiene registro público de usuarios ni pantallas para crear empresas o locales. Por eso se conservaron exactamente las dos cuentas necesarias para entrar y este primer recorrido utiliza un ámbito personal o de hogar, que sí puede configurarse íntegramente desde la interfaz. Si se desea repetir la validación con una empresa nueva y sus locales, antes habrá que implementar su alta administrativa o preaprovisionarlos de forma técnica y documentada; esta guía no simula que esa capacidad ya existe.

## 3. Precondiciones

Antes de iniciar el recorrido:

1. consultar la ficha `EXP-LAB_REINICIO_CONTROLADO_2026-10-16.md` y confirmar que la columna **Resultado real** ya no contiene marcadores pendientes para la línea base;
2. iniciar el servidor local con `.\iniciar_servidor_local.ps1` y abrir `http://127.0.0.1:8010/`;
3. disponer de las credenciales locales de las dos cuentas por un canal separado de los archivos versionables;
4. guardar fuera del equipo o imprimir los códigos personales entregados a cada titular; no colocarlos en esta guía, capturas, incidencias ni documentos de evidencia;
5. no escribir contraseñas en archivos versionables y no compartir un código entre gerente y asistente;
6. preparar dos archivos totalmente ficticios y sin información real:
   - `sustento_recibo_prueba.pdf` o una imagen JPG/PNG equivalente;
   - `comprobante_pago_prueba.pdf` o una imagen JPG/PNG equivalente;
7. registrar la fecha de ejecución como `F0` y calcular:
   - `F1 = F0 + 5 días`, vencimiento del primer recibo;
   - `F2 = primer día del mes siguiente a F0`, inicio de la recurrencia;
   - `F3 = F0 + 10 días`, vencimiento de la obligación privada;
8. usar una ventana normal para un rol y, si se desea conservar ambas sesiones, una ventana privada para el otro; nunca cambiar de usuario dejando un formulario sin guardar.

Todos los nombres, identificadores y archivos de esta guía son ficticios. No se deben usar personas, cuentas, recibos, documentos, números bancarios o comprobantes reales.

## 4. Datos ficticios sugeridos

| Elemento | Valor de prueba |
|---|---|
| Ámbito compartido | `Casa familiar de prueba` |
| Tipo de ámbito | `Hogar o propiedad` |
| Titular predeterminado | `Carlos Prueba` |
| Beneficiario predeterminado | `Familiar Prueba` |
| Acceso del asistente | Sí |
| Fuente de fondos | `Cuenta familiar de prueba` |
| Tipo / moneda | Cuenta / PEN |
| Institución e identificador | `Banco Ficticio` / `CTA-PRUEBA-9001` |
| Acreedor | `Proveedor Eléctrico Ficticio` |
| Cuenta de destino | `Banco Ficticio` / `0000-PRUEBA-1111` |
| Primera obligación | `Electricidad casa familiar - primer recibo` |
| Categoría / naturaleza | Servicio / Apoyo no reembolsable |
| Importe | S/ 180,50 |
| Cuenta de servicio | Electricidad / Suministro `SUM-PRUEBA-0001` |
| Compromiso | `Electricidad mensual casa familiar` |
| Frecuencia | Mensual desde `F2`, vencimiento habitual día 20 |
| Modalidad del importe | Monto fijo de S/ 180,50 |
| Ámbito privado | `Asunto personal privado de prueba` |
| Tipo / acceso | Personal / sin acceso para asistente |
| Obligación privada | `Documento privado de prueba`, S/ 35,00, vencimiento `F3` |

Si una fecha o etiqueta no coincide literalmente con la interfaz del corte probado, se utilizará su equivalente visible y se anotará la diferencia como observación; no se alterará el resultado esperado para ocultarla.

## 5. Responsabilidades que debe demostrar el recorrido

| Capacidad | Gerente | Asistente |
|---|---:|---:|
| Crear y modificar ámbitos | Sí | No |
| Decidir acceso del asistente y privacidad | Sí | No |
| Crear fuentes de fondos y cuentas de destino | Sí | Solo consultar las autorizadas durante la operación |
| Crear, editar o importar cuentas de servicio | Sí | Solo consultar y usar las compartidas |
| Crear obligaciones manuales en ámbitos accesibles | Sí | Sí |
| Adjuntar sustento y comprobante | Sí | Sí, en ámbitos compartidos y no sensibles |
| Registrar un pago realizado fuera de PagoControl | Sí | Sí |
| Suspender, reactivar, anular o corregir movimientos | Sí | No |
| Consultar información privada o sensible | Sí | No |
| Importar obligaciones en lote | Sí | No en la variante actual |

PagoControl no transfiere dinero. “Registrar el pago” significa dejar constancia de una operación que el usuario ejecutó previamente en un banco, portal, agente u otro medio externo.

## 6. Cómo registrar la evidencia

Para cada paso se debe completar una fila en una ficha de validación manual con estas columnas:

| ID | Fecha/hora | Actor | Pantalla o URL | Acción y dato ficticio | Resultado esperado | Resultado observado | Estado | Evidencia | Referencia |
|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | `OK`, `Falla`, `Bloqueado` o `No aplica` | Captura o nombre de archivo | `EXP-LAB-*` / caso de aceptación |

Una captura debe evitar contraseña, identificadores completos o información personal. Un paso solo queda `OK` después de observar su resultado; no se completa por anticipado.

## 7. Recorrido completo

### Fase 0 — Comprobar ingreso y salida de recuperación

#### V-01 · Repetir el ingreso que originó FB-005

1. abrir `http://127.0.0.1:8010/login/`;
2. escribir el correo del gerente alternando alguna mayúscula y minúscula, sin cambiar sus caracteres;
3. escribir la contraseña exactamente, usando **Mostrar** si necesita verificarla;
4. enviar el formulario.

**Resultado esperado:** el correo no distingue mayúsculas y minúsculas, la contraseña sí, y el gerente entra a Control gerencial. Si la contraseña fuera incorrecta, el correo permanece escrito, la contraseña se borra y aparece un enlace claro para recuperar el acceso.

#### V-02 · Confirmar la preparación del gerente

1. abrir **Mi acceso** en la barra superior;
2. confirmar que se ve el correo de la cuenta y el número de códigos personales disponibles;
3. no regenerarlos si los códigos iniciales ya fueron guardados; generar otro juego únicamente si se desea revocar los anteriores;
4. comprobar que la actividad no muestra el valor de ningún código.

**Resultado esperado:** solo el titular autenticado puede gestionar sus códigos y los valores originales no reaparecen después de abandonar la pantalla.

#### V-03 · Probar la recuperación delegada del asistente

Esta variante cambia la contraseña del asistente. Debe ejecutarse solo si se registrará la nueva contraseña por un canal privado.

1. como gerente, en **Mi acceso**, elegir al asistente y confirmar la contraseña actual del gerente;
2. emitir el código temporal y copiarlo por un canal privado;
3. cerrar la sesión del gerente y abrir **¿No recuerdas tu correo o contraseña?**;
4. introducir el código, una contraseña nueva fuerte y su confirmación;
5. confirmar que el sistema muestra el correo del asistente únicamente después de aceptar el código;
6. ingresar como asistente con ese correo y la contraseña nueva.

**Resultado esperado:** el código vence a los 30 minutos, funciona una sola vez, no cambia el rol y deja inválidas la contraseña y las sesiones anteriores. Si se omite esta variante, debe anotarse como pendiente y continuar con la contraseña inicial entregada por separado.

#### V-04 · Confirmar límites por rol

Ya dentro de la cuenta del asistente, abrir **Mi acceso**.

**Resultado esperado:** el asistente puede renovar sus propios códigos personales, pero no puede emitir códigos para el gerente ni administrar otra cuenta. Si pierde todos sus datos, debe pedir al gerente un código temporal tras verificar su identidad. Si el gerente pierde también sus códigos personales, la recuperación requiere al operador local autorizado.

### Fase A — Gerente: construir la configuración inicial

#### G-01 · Ingresar como gerente

1. Abrir la pantalla de acceso.
2. Introducir las credenciales recibidas fuera del repositorio.
3. Confirmar que se abre **Control gerencial** y que el encabezado identifica el rol Gerente.

**Resultado esperado:** el panel no presenta totales, obligaciones ni actividad heredada. Los módulos de configuración y operación están disponibles según el rol.

#### G-02 · Confirmar la línea base vacía en la interfaz

Revisar **Cola operativa**, **Pagos realizados**, **Control gerencial**, **Ámbitos**, **Fuentes de fondos**, **Cuentas autorizadas** y **Cuentas de servicio**.

**Resultado esperado:** las pantallas muestran estados vacíos comprensibles, no tarjetas antiguas, datos empresariales precargados ni mensajes técnicos de planificación.

#### G-03 · Crear el ámbito compartido no empresarial

1. Entrar en **Ámbitos** y elegir **Añadir ámbito**.
2. Registrar `Casa familiar de prueba` como `Hogar o propiedad`.
3. Usar `Carlos Prueba` como titular y `Familiar Prueba` como beneficiario predeterminados.
4. activar **Permitir acceso al asistente** y guardar.

**Resultado esperado:** empresa y local no aparecen o quedan deshabilitados; el ámbito queda activo, identificado como no empresarial y compartido con el asistente.

#### G-04 · Crear una fuente de fondos autorizada

1. Abrir **Fuentes de fondos**.
2. Añadir `Cuenta familiar de prueba` dentro de `Casa familiar de prueba`.
3. Seleccionar tipo Cuenta, moneda PEN, `Banco Ficticio`, titular `Carlos Prueba` e identificador `CTA-PRUEBA-9001`.
4. dejarla activa y visible para el asistente.

**Resultado esperado:** la lista presenta únicamente un identificador enmascarado. Los campos bancarios aparecen porque se eligió Cuenta; al seleccionar Efectivo deberían ocultarse, pero no se cambia el tipo en este recorrido.

#### G-05 · Registrar el primer recibo y crear el acreedor

1. Elegir **Registrar obligación**.
2. Seleccionar `Casa familiar de prueba` y categoría Servicio.
3. Comprobar que empresa y local permanecen ocultos.
4. escribir `Electricidad casa familiar - primer recibo`.
5. elegir **Registrar nuevo acreedor** y usar `Proveedor Eléctrico Ficticio`; el identificador fiscal puede quedar vacío.
6. indicar titular `Carlos Prueba`, beneficiario `Familiar Prueba`, naturaleza Apoyo no reembolsable, PEN, importe `180,50`, vencimiento `F1` y el período correspondiente a `F0`.
7. seleccionar `Cuenta familiar de prueba` como fuente prevista.
8. dejar vacía la cuenta de servicio, no marcar la obligación como sensible y guardar.

**Resultado esperado:** se crea una obligación abierta en el ámbito compartido. La ficha explica que falta asociar una cuenta de servicio; el nuevo acreedor ya queda disponible para configuraciones posteriores.

#### G-06 · Crear y asociar la cuenta de servicio

1. Desde el detalle anterior elegir **Crear y asociar cuenta**.
2. registrar Electricidad, identificador tipo Suministro y `SUM-PRUEBA-0001`.
3. seleccionar `Casa familiar de prueba`, `Proveedor Eléctrico Ficticio`, titular `Carlos Prueba`, frecuencia Mensual, día habitual 20, canal Registro manual y estado Activa.
4. guardar.

**Resultado esperado:** empresa y local no se solicitan; la cuenta queda asociada automáticamente al primer recibo y su identificador se muestra enmascarado en los listados.

#### G-07 · Autorizar la cuenta de destino del acreedor

1. Entrar en **Cuentas autorizadas**.
2. seleccionar `Proveedor Eléctrico Ficticio`.
3. registrar `Banco Ficticio`, titular `Proveedor Eléctrico Ficticio` y número ficticio `0000-PRUEBA-1111`.
4. mantenerla activa y guardar.

**Resultado esperado:** el número aparece enmascarado y la cuenta queda disponible para compromisos futuros. El primer recibo conserva la información con la que fue creado; no se debe fingir que el dato nuevo se aplicó retroactivamente.

#### G-08 · Crear el compromiso recurrente

1. Elegir **Crear compromiso**.
2. seleccionar `Casa familiar de prueba`, nombre `Electricidad mensual casa familiar`, categoría Servicio y acreedor `Proveedor Eléctrico Ficticio`.
3. asociar la cuenta `SUM-PRUEBA-0001`.
4. seleccionar frecuencia Mensual, inicio `F2`, día habitual 20, monto fijo `180,50`, moneda PEN, fuente `Cuenta familiar de prueba` y la cuenta de destino autorizada.
5. usar titular `Carlos Prueba`, beneficiario `Familiar Prueba` y naturaleza Apoyo no reembolsable.
6. guardar sin generar todavía la siguiente obligación.

**Resultado esperado:** el compromiso queda activo y muestra `F2` como próxima ocurrencia. Los controles de intervalo personalizado permanecen ocultos y el monto fijo está visible por corresponder a la modalidad elegida.

#### G-09 · Crear el caso privado para la prueba negativa

1. Crear el ámbito `Asunto personal privado de prueba`, tipo Personal, sin acceso para el asistente.
2. registrar dentro de él una obligación `Documento privado de prueba`, categoría Otro, acreedor existente, PEN `35,00` y vencimiento `F3`.
3. copiar de forma segura la URL del detalle o anotar solo su identificador técnico en la ficha de prueba.
4. cerrar la sesión del gerente.

**Resultado esperado:** el gerente puede ver el registro privado. Empresa y local no se solicitan. La URL se utiliza únicamente para la prueba de autorización y no se incluye en capturas públicas.

### Fase B — Asistente: operar únicamente lo autorizado

#### A-01 · Ingresar como asistente

Iniciar sesión con las credenciales del asistente recibidas por separado.

**Resultado esperado:** la página inicial es la cola de trabajo; el rol visible es Asistente y no aparecen acciones exclusivas del gerente.

#### A-02 · Verificar el alcance compartido

1. localizar `Electricidad casa familiar - primer recibo` en la cola;
2. revisar Ámbitos, Fuentes de fondos y Cuentas de servicio;
3. confirmar que `Casa familiar de prueba`, la fuente visible y `SUM-PRUEBA-0001` pueden consultarse;
4. confirmar que no existen botones para crear, editar o importar cuentas de servicio ni para modificar cuentas autorizadas.

**Resultado esperado:** el asistente ve y opera el ámbito compartido, pero los catálogos protegidos permanecen en solo lectura.

#### A-03 · Ejecutar la prueba negativa de privacidad

1. confirmar que `Asunto personal privado de prueba` y `Documento privado de prueba` no aparecen en cola, búsquedas, calendario, historial ni selectores;
2. pegar directamente la URL del detalle anotada en G-09.

**Resultado esperado:** el servidor rechaza el acceso con `403` o `404`, no revela nombre, importe, documentos ni otra información del registro y no crea una escritura lateral. Una simple ausencia visual sin probar la URL directa no completa este caso.

#### A-04 · Adjuntar el documento de sustento

1. abrir el primer recibo compartido;
2. seleccionar `sustento_recibo_prueba.pdf` o su imagen equivalente;
3. comprobar la vista previa pequeña, el nombre y el tamaño antes de enviar;
4. adjuntar el archivo.

**Resultado esperado:** el sustento queda disponible mediante vista previa y descarga privadas. Todavía no existe un pago.

#### A-05 · Comprobar el rechazo de un pago inválido

Intentar registrar S/ `181,00`, un importe superior al saldo, usando un comprobante ficticio.

**Resultado esperado:** aparece un error comprensible junto al flujo de pago; no se crea movimiento, no cambia el saldo y el comprobante del intento fallido no queda como evidencia válida.

#### A-06 · Registrar el pago externo correcto

1. simular que la operación se realizó fuera de PagoControl;
2. registrar fecha `F0`, importe S/ `180,50`, referencia `OP-PRUEBA-0001`, fuente `Cuenta familiar de prueba` y `comprobante_pago_prueba.pdf`;
3. comprobar la vista previa antes de confirmar;
4. guardar una sola vez.

**Resultado esperado:** se crea un movimiento de pago, el saldo llega a cero, la obligación queda Pagada y el comprobante permanece accesible dentro de la ficha. Un segundo intento de pago completo debe rechazarse.

#### A-07 · Verificar historia y cerrar sesión

Revisar **Pagos realizados**, el detalle del recibo y el calendario del período; después cerrar sesión.

**Resultado esperado:** el pago muestra actor, fecha, importe, moneda y referencia sin exponer identificadores completos. El registro privado continúa ausente.

### Fase C — Gerente: supervisar, generar y cerrar

#### G-10 · Confirmar el resultado financiero

Volver a ingresar como gerente y abrir **Control gerencial**.

**Resultado esperado:** el panel refleja el recibo pagado en PEN, sin mezclar monedas; la ficha conserva sustento, comprobante y actor. La obligación privada sigue disponible únicamente para el gerente.

#### G-11 · Revisar la trazabilidad

Abrir el primer recibo y revisar su actividad.

**Resultado esperado:** se distinguen creación, asociación de cuenta de servicio, carga del sustento y pago. El intento inválido no aparece como movimiento financiero exitoso ni modifica la historia.

#### G-12 · Generar la siguiente ocurrencia

1. ir a **Cola operativa**, sección Compromisos recurrentes;
2. en **Generar recurrencias hasta**, seleccionar `F2`;
3. pulsar **Generar programadas** una sola vez;
4. localizar `Electricidad mensual casa familiar` para el nuevo período.

**Resultado esperado:** se crea exactamente una obligación nueva vinculada al compromiso, con vencimiento el día 20, S/ 180,50, la cuenta de servicio, la fuente y una instantánea de la cuenta de destino.

#### G-13 · Probar la idempotencia

1. anotar cuántas obligaciones pertenecen al compromiso;
2. volver a ejecutar **Generar programadas** con la misma fecha `F2`;
3. volver a contar y revisar el mensaje de resultado.

**Resultado esperado:** no aparece una segunda obligación para el mismo período; el conteo permanece igual. El mensaje puede indicar cero ocurrencias nuevas o que la ocurrencia ya existía.

#### G-14 · Probar una excepción gerencial reversible

1. abrir la obligación recién generada;
2. suspenderla con el motivo `Validación de retención temporal`;
3. confirmar que queda Suspendida y no se presenta como atraso del asistente;
4. reactivarla.

**Resultado esperado:** ambas decisiones quedan en la actividad con actor y fecha; la reactivación no exige un motivo que solo corresponde a disputar o anular; la obligación vuelve a estado abierto sin perder sus datos.

#### G-15 · Cerrar el recorrido

Revisar panel, cola, calendario, pagos realizados e historial; registrar incidencias y cerrar sesión.

**Resultado esperado al final:** existen dos ámbitos ficticios —uno compartido y uno privado—, un pago completo trazable, una obligación privada no expuesta, un compromiso mensual y una única ocurrencia futura. No existe información real ni se ejecutó una transferencia desde PagoControl.

## 8. Casos complementarios posteriores

El recorrido principal cubre el inicio operativo, permisos, sustento, pago, supervisión, privacidad, recurrencia e idempotencia. Los demás casos de `10_PLAN_EXPERIMENTAL_PROTOTIPO.md` deben probarse después como recorridos separados para no confundir sus evidencias:

- tarjeta con total, mínimo, ciclo y abono parcial;
- préstamo personal con capital e interés;
- gasto reembolsable y posterior reembolso;
- devolución o contracargo que reabre saldo;
- seguro con contratante, asegurado y beneficiario diferentes;
- advertencia de duplicado manual;
- importación válida y reversión completa de un lote inválido;
- separación PEN/USD y filtros gerenciales;
- transiciones de todos los formularios contextuales en escritorio y a 375 px.

## 9. Registro de incidencias y decisiones

Por cada diferencia se registrará:

- ID correlativo `VM-INC-___`;
- paso afectado;
- actor y fecha/hora;
- resultado esperado y observado;
- evidencia sin datos sensibles;
- severidad: bloqueante, alta, media o baja;
- decisión: aceptar, reformular, corregir, posponer o descartar;
- capacidad `EXP-LAB-*` relacionada.

Una incidencia no debe corregirse silenciosamente ni utilizarse para reescribir el Sprint histórico. Si origina un cambio, se registrará después en el control de cambios del laboratorio.

## 10. Checklist final

### Línea base y seguridad

- [ ] La evidencia del reinicio tiene fecha, responsable, conteos, respaldo y hashes reales.
- [ ] Solo existen las dos cuentas activas previstas para esta prueba.
- [ ] No quedan datos operativos ni archivos de pruebas anteriores al iniciar.
- [ ] Las credenciales no aparecen en archivos versionables, capturas o incidencias.
- [ ] Todos los datos y documentos usados son ficticios.
- [ ] El correo permite mayúsculas/minúsculas, pero la contraseña conserva su sensibilidad.
- [ ] Cada titular guardó sus códigos fuera del sistema y no los incluyó en evidencias.
- [ ] La recuperación temporal del asistente se probó o quedó explícitamente pendiente.

### Gerente

- [ ] Inició en un panel realmente vacío.
- [ ] Creó un ámbito no empresarial compartido sin empresa ni local.
- [ ] Creó fuente, acreedor, cuenta de servicio, cuenta de destino y compromiso.
- [ ] Creó un ámbito privado y conservó su URL para la prueba negativa.
- [ ] Vio el pago del asistente en panel, detalle e historial.
- [ ] Generó una sola ocurrencia futura y la segunda ejecución no duplicó.
- [ ] Suspendió y reactivó sin borrar historia.

### Asistente

- [ ] Vio el ámbito compartido y no el privado.
- [ ] El acceso directo al registro privado fue rechazado sin filtrar datos.
- [ ] No pudo mantener o importar catálogos exclusivos del gerente.
- [ ] Vio la vista previa pequeña del sustento y del comprobante.
- [ ] El pago superior al saldo fue rechazado sin crear movimiento.
- [ ] Registró el pago correcto y observó saldo cero.

### Experiencia y cierre

- [ ] Los formularios mostraron solo campos pertinentes y conservaron errores junto al campo.
- [ ] No aparecieron textos sobre demo, Scrum, Jira, implementación o revisión del profesor en la interfaz operativa.
- [ ] Los estados se entendieron sin depender únicamente del color.
- [ ] El recorrido se comprobó con teclado y luego a 375 px, o esas revisiones quedaron explícitamente pendientes.
- [ ] Cada paso tiene resultado observado y evidencia, no solo resultado esperado.
- [ ] El responsable del producto marcó cada variante como aceptada, reformulada, pospuesta o descartada.

Hasta completar este checklist, el estado correcto es **lista para validación manual**, no `Validada por producto`, no `Done` y no lista para Jira.
