# Plan experimental del prototipo PagoControl

## 1. Naturaleza de esta etapa

PagoControl se encuentra en una etapa de **laboratorio de producto**. El objetivo actual no es ejecutar el Sprint académico ni alimentar Jira, sino construir, probar y corregir un prototipo hasta que el responsable del producto confirme que el sistema representa adecuadamente su trabajo real.

La documentación del laboratorio se utilizará después como evidencia para redactar una guía Scrum nueva y coherente con el producto aceptado. Por tanto:

- los identificadores `EXP-LAB-*` no son HUs comprometidas;
- no se asignan Story Points, horas, Developers, fechas de Sprint ni claves Jira;
- una capacidad documentada no se considera implementada hasta que existan código, migración cuando corresponda y pruebas reproducibles;
- los cambios y descartes del prototipo se conservan para poder explicar por qué la versión futura fue diseñada de esa manera;
- el Sprint histórico de los documentos `01` a `06` no se reescribe ni se presenta como ejecución de este laboratorio.

**Decisión de producto:** `CR-005` autoriza desarrollar experimentalmente todas las capacidades locales descritas en este documento. Las integraciones que dependan de proveedores externos permanecen documentadas, pero no se simularán como si fueran reales.

## 2. Objetivo experimental

Comprobar si una sola aplicación sencilla puede ayudar a un gerente y a su asistente a organizar obligaciones empresariales, personales, familiares y patrimoniales, registrar lo ocurrido fuera del sistema y conservar una historia verificable sin convertirse en un ERP ni en un banco.

El prototipo debe responder, como mínimo:

1. ¿A quién o a qué corresponde la obligación?
2. ¿Quién es el titular o deudor y quién recibe el beneficio?
3. ¿A quién se paga y con qué fuente de fondos?
4. ¿Qué se debe, en qué moneda, cuándo vence y cuánto falta pagar?
5. ¿Es recurrente, se omitió una ocurrencia o cambió solo a futuro?
6. ¿Qué documento sustenta la deuda y qué evidencias sustentan sus movimientos?
7. ¿Quién pudo ver o modificar la información y qué hizo?
8. ¿Existe un posible duplicado, una disputa, un reembolso o una excepción?
9. ¿Qué necesita atención hoy, esta semana o en el calendario?

## 3. Alcance que se construirá en el laboratorio

| ID | Capacidad | Resultado observable esperado | Estado al 16/10/2026 |
|---|---|---|---|
| EXP-LAB-01 | Ámbitos y partes | Registrar empresa, personal, hogar/propiedad, tercero o entidad patrimonial sin empresas ficticias | Verificada técnicamente |
| EXP-LAB-02 | Privacidad | Autorizar en servidor qué ámbitos ve y opera el asistente | Verificada técnicamente |
| EXP-LAB-03 | Categorías y moneda | Capturar datos especializados, incluyendo estados de tarjeta | Verificada técnicamente |
| EXP-LAB-04 | Recurrencias | Generar ocurrencias semanales, mensuales y por intervalos sin duplicarlas | Verificada técnicamente |
| EXP-LAB-05 | Movimientos | Registrar pagos parciales, devoluciones, reembolsos, anulaciones y ajustes sin borrar historia | Verificada técnicamente |
| EXP-LAB-06 | Duplicados | Advertir coincidencias y exigir una decisión explícita | Verificada técnicamente en la variante continuar/cancelar |
| EXP-LAB-07 | Calendario y recordatorios | Consultar agenda mensual y recordatorios internos derivados del vencimiento | Verificada técnicamente en la primera variante mensual |
| EXP-LAB-08 | Importación | Revisar CSV/XLSX antes de crear obligaciones definitivas | Verificada técnicamente para operación del gerente |
| EXP-LAB-09 | Actividad y análisis | Filtrar y resumir por ámbito, categoría, moneda y estado | Verificada técnicamente en la variante actual |
| EXP-LAB-10 | Formularios contextuales | Mostrar únicamente los campos aplicables según ámbito, categoría, frecuencia, tipo de monto, fuente y acción seleccionada | Verificada técnicamente — pendiente de revisión visual y validación de producto |
| EXP-LAB-11 | Acceso y recuperación segura | Ingresar sin depender de mayúsculas en el correo y recuperar correo/contraseña mediante códigos personales o una delegación temporal controlada | Implementado y verificado automáticamente; pendiente de validación visual |

### Fuera de esta implementación local

No se fingirán OCR, transferencias, conciliación bancaria, scraping, correo receptor, WhatsApp ni consulta automática a proveedores. Son experimentos posteriores que requieren credenciales, contratos, costos, tratamiento de datos y evidencia de un tercero. El prototipo sí dejará preparado un flujo manual honesto: cargar, revisar, registrar el movimiento externo y adjuntar evidencia.

## 4. Modelo de dominio experimental

### 4.1 Ámbito administrado

`PaymentContext` será el contenedor operativo al que pertenece una obligación.

| Tipo | Ejemplo | Regla |
|---|---|---|
| `BUSINESS` | Grupo Gastronómico | Requiere una empresa; puede usar local |
| `PERSONAL` | Personal de Carlos | No admite empresa ni local |
| `HOUSEHOLD` | Casa de mamá / departamento de playa | Puede identificar titular o beneficiario; no exige usuario |
| `THIRD_PARTY` | Educación de Lucía / apoyo a esposa | Requiere identificar beneficiario |
| `PATRIMONIAL` | Fundación / fideicomiso / vehículo de inversión | Identifica la entidad administrada sin convertirla en empresa operativa |

Campos mínimos: nombre, tipo, empresa opcional, titular predeterminado, beneficiario predeterminado, visibilidad para asistente, estado activo, creador y fechas.

Los registros empresariales existentes se migrarán automáticamente a un ámbito empresarial por cada empresa, conservando claves, documentos y relaciones históricas.

### 4.2 Partes y naturaleza

No se utilizará una sola etiqueta para conceptos diferentes:

- **Ámbito:** a quién o a qué corresponde.
- **Titular/deudor:** quién asumió la obligación.
- **Beneficiario:** quién recibe el bien, servicio o apoyo.
- **Acreedor:** a quién se paga.
- **Fuente de fondos:** cuenta, tarjeta, efectivo u otro origen usado para pagar.
- **Naturaleza:** propio, compartido, apoyo, reembolsable o préstamo.

Los nombres de titular y beneficiario son datos operativos; no crean usuarios ni otorgan acceso.

### 4.3 Fuente de fondos

`FundingSource` tendrá ámbito, nombre visible, tipo —cuenta, tarjeta, efectivo u otro—, institución, titular, identificador enmascarable, moneda predeterminada, estado y visibilidad. La fuente utilizada se copiará como instantánea en el movimiento para que una edición posterior no cambie el pasado.

### 4.4 Categorías

El catálogo experimental admitirá:

- servicio;
- vivienda/propiedad;
- tarjeta de crédito;
- préstamo;
- impuesto;
- seguro;
- educación;
- salud;
- apoyo familiar;
- personal doméstico;
- vehículo;
- viaje/evento;
- inversión;
- donación;
- legal;
- suscripción;
- proveedor;
- emergencia;
- otro.

La interfaz mostrará campos especializados mediante revelado progresivo, sin obligar a todos los usuarios a completar todos los datos.

### 4.5 Datos especializados

Para evitar una proliferación prematura de tablas, el laboratorio conservará en la obligación un bloque estructurado `details` validado por categoría. Debe mostrarse mediante campos con etiqueta, nunca como JSON al usuario.

| Categoría | Datos mínimos específicos |
|---|---|
| Tarjeta | Emisor, titular, últimos cuatro, inicio/fin de ciclo, corte, pago total y mínimo |
| Préstamo | Contrato, número de cuota, total de cuotas, capital, interés y seguro cuando se conozcan |
| Seguro | Póliza, contratante, asegurado, beneficiario, vigencia y riesgo de suspensión |
| Propiedad/servicio | Predio, suministro/contrato, titular y periodo de consumo |
| Viaje/evento | Viajero o evento, fecha/hito, anticipo y saldo |
| Inversión | Vehículo, llamada de capital y fecha límite |

Una tarjeta se representa inicialmente como **una obligación por estado de cuenta**. Sus compras no se vuelven obligaciones independientes si ya forman parte del total, evitando doble conteo.

En una recurrencia, el compromiso conserva solo los identificadores que no deberían cambiar en cada período —por ejemplo, emisor y últimos cuatro dígitos, contrato, póliza, predio, viaje o vehículo de inversión—. El ciclo, total, mínimo, número de cuota, desglose y demás valores variables se completan en la obligación concreta. Una obligación periódica variable permanece señalada como incompleta hasta recibirlos.

### 4.6 Moneda

Toda obligación, compromiso y movimiento guardará un código de moneda ISO de tres letras. El laboratorio ofrecerá al menos PEN y USD, con PEN como valor inicial para los registros existentes.

- No se suman monedas diferentes.
- Una conversión solo puede mostrarse si existe tipo de cambio y fecha explícitos.
- Pago y obligación deben usar la misma moneda en esta etapa; un caso distinto queda bloqueado para revisión.

## 5. Recurrencias

Un compromiso conserva la regla; cada obligación conserva la ocurrencia concreta.

Campos: frecuencia, intervalo, día habitual, fecha inicial, próxima ocurrencia, fecha final opcional, estado y zona horaria. Frecuencias visibles:

- única;
- semanal;
- quincenal;
- mensual;
- bimestral;
- trimestral;
- semestral;
- anual;
- personalizada por número de días, semanas o meses.

Reglas:

1. `compromiso + fecha de ocurrencia` es único.
2. Ejecutar el generador nuevamente no duplica.
3. Omitir una ocurrencia crea un evento de omisión y avanza la siguiente fecha.
4. Pausar no modifica obligaciones ya creadas.
5. Cambiar la regla solo afecta el futuro.
6. El último día del mes se ajusta al último día válido del siguiente periodo.

## 6. Obligaciones y movimientos

### 6.1 Estado calculado de la obligación

Los estados administrativos y financieros se mantienen separados. El resultado visible se deriva de ambos:

- pendiente;
- parcialmente pagada;
- pagada;
- suspendida;
- en disputa;
- anulada;
- reembolsada.

Vencida, vence hoy y próxima a vencer son estados visuales calculados desde la fecha cuando todavía existe saldo abierto.

### 6.2 Movimientos financieros

`Payment` pasa de uno-a-uno a varios movimientos por obligación. Cada movimiento contiene:

- tipo: pago, devolución, reembolso, contracargo o ajuste;
- importe positivo;
- moneda;
- fecha;
- fuente de fondos opcional e instantánea;
- referencia;
- motivo obligatorio para correcciones;
- comprobante cuando corresponda;
- movimiento original al que revierte o corrige;
- actor y fecha de registro;
- estado activo o anulado, sin eliminación física.

El saldo será `importe de obligación − pagos netos`. Una devolución o contracargo aumenta nuevamente el saldo; un reembolso esperado se controla aparte de lo pagado al acreedor.

Reglas:

1. un pago no puede superar el saldo abierto;
2. un pago positivo requiere sustento de la obligación y comprobante;
3. una corrección nunca borra el movimiento original;
4. anular exige gerente y motivo;
5. cuando el saldo llega a cero la obligación se marca pagada;
6. si el saldo queda entre cero y el total se marca parcialmente pagada;
7. “pagado” no significa “conciliado por el banco”.

## 7. Privacidad y autorización

### 7.1 Regla de ámbito

- El gerente accede a todos los ámbitos.
- Un ámbito define si el asistente tiene acceso operativo.
- Una obligación puede marcarse sensible y quedar visible solo al gerente aunque el ámbito sea compartido.
- Salud, legal y datos familiares se consideran candidatos a sensibilidad por defecto, pero el gerente puede decidirlo explícitamente.

### 7.2 Superficies que deben filtrar en servidor

Tablero, calendario, historial, dashboard, formularios, selectores, detalle, edición, movimientos, cuentas de servicio, fuentes, importación, adjuntos, vista previa, descarga, revelación de instrucciones y actividad.

Ocultar un botón no constituye autorización. Un identificador directo no autorizado debe devolver `404` o `403` sin contenido del registro y sin escrituras laterales.

## 8. Duplicados

Antes de crear manualmente o confirmar una importación se comparará:

- ámbito;
- acreedor;
- número externo;
- periodo;
- monto y moneda;
- cuenta de servicio;
- concepto normalizado.

Una coincidencia exacta de ámbito, acreedor y número externo activo bloquea el guardado. Una coincidencia aproximada devuelve candidatos y permite continuar únicamente con confirmación y motivo. La decisión queda en auditoría.

## 9. Importación experimental de obligaciones

La importación acepta CSV UTF-8 y XLSX hasta 2 MB.

Flujo:

1. seleccionar archivo y ver una previsualización pequeña;
2. analizar sin persistir obligaciones;
3. mostrar filas válidas, errores y posibles duplicados;
4. mapear ámbitos y acreedores existentes;
5. confirmar el lote;
6. crear todas las filas válidas dentro de una transacción o devolver el lote completo a corrección;
7. registrar actor, fecha, nombre de archivo y resultado, sin hacer público el archivo.

Columnas iniciales: ámbito, categoría, concepto, acreedor, documento, periodo, monto, moneda, vencimiento, titular, beneficiario, naturaleza y sensible.

## 10. Interfaz experimental

La experiencia seguirá estas reglas de `ui-ux-pro-max`:

- etiquetas visibles asociadas a todos los campos;
- campos obligatorios claramente identificados;
- errores junto al campo y resumen enfocable;
- confirmación de éxito o error después de cada envío;
- revelado progresivo por tipo de ámbito y categoría;
- botones y controles táctiles de al menos 44 × 44 px en pantallas pequeñas;
- ninguna acción disponible únicamente al pasar el mouse;
- estados expresados con texto además de color;
- calendario navegable mediante controles nativos con nombre accesible;
- foco visible y navegación por teclado.

### 10.1 Registro de obligación

Orden de decisión:

1. `¿A quién corresponde?` — ámbito.
2. `¿Qué tipo de obligación es?` — categoría.
3. `Titular` y `Beneficia a`, solo cuando aporten información.
4. `¿A quién se paga?` — acreedor.
5. importe, moneda, vencimiento y periodo.
6. campos particulares de tarjeta, préstamo o seguro.
7. naturaleza, fuente prevista, privacidad y documento.

Empresa/Local solo aparecen para un ámbito empresarial. Los campos especializados deben conservarse tras un error.

### 10.2 Navegación

Orden funcional de configuración a operación, conservando la cola como módulo superior:

1. Ámbitos.
2. Fuentes de fondos y cuentas de pago.
3. Cuentas de servicio.
4. Compromisos.
5. Registrar obligación / importar.
6. Calendario.
7. Historial y resumen.
8. Cola operativa, visible como entrada principal.

### 10.3 Calendario y recordatorios internos

La primera versión ofrece navegación por mes y lista por día. Cada evento muestra ámbito, concepto, saldo, moneda, estado y acceso al detalle. Los recordatorios se calculan dentro de la aplicación; pueden marcarse atendidos u omitidos sin cambiar la obligación.

### 10.4 Formularios contextuales

Los formularios aplicarán revelado progresivo para reducir carga visual y prevenir datos contradictorios. La decisión de ocultar un campo dependerá de una selección explícita y comprensible.

Reglas de esta variante:

1. un ámbito no empresarial oculta y deshabilita empresa y local;
2. cada categoría muestra solo su cuenta de servicio o bloque especializado;
3. una tarjeta usa el total del estado de cuenta como monto y no repite ambos campos;
4. una recurrencia muestra fechas, intervalo, día habitual y monto fijo únicamente cuando su frecuencia o modalidad los necesita;
5. una fuente en efectivo no solicita banco, titular ni identificador;
6. una frecuencia de servicio eventual no solicita día habitual;
7. una reactivación no solicita el motivo requerido para disputar o anular;
8. un campo oculto queda deshabilitado y no se envía con valores residuales;
9. si el servidor devuelve un error, el bloque correspondiente vuelve visible y conserva el mensaje junto al campo;
10. etiquetas, indicadores obligatorios, navegación por teclado y validación del servidor se mantienen aunque JavaScript no esté disponible.

La pantalla conservará temporalmente lo escrito si el usuario cambia una opción y luego regresa a ella durante la misma edición, pero solo enviará los controles visibles al guardar.

## 11. Dashboard y filtros

Filtros comunes:

- tipo de ámbito y ámbito;
- empresa/local cuando aplica;
- acreedor;
- categoría;
- moneda;
- estado;
- titular/beneficiario;
- rango de vencimiento;
- sensible, si el usuario tiene permiso.

El dashboard separa por moneda:

- pendiente conocido;
- sin monto;
- parcialmente pagado y saldo;
- vencido;
- suspendido;
- en disputa;
- pagado;
- reembolsable pendiente;
- reembolsado.

También separa flujo próximo, resultado del mes y antigüedad de saldo. No suma PEN y USD.

## 12. Actividad y correcciones

La ficha presenta una línea de tiempo paginada con creación, edición, documentos, movimientos, suspensión, disputa, importación y accesos sensibles. Las notas operativas futuras no reemplazan la auditoría.

El resumen de auditoría usa lenguaje cliente, mientras sus metadatos conservan identificadores técnicos enmascarados. No se copian documentos médicos, descripciones legales, nombres sensibles ni cuentas completas a logs.

## 13. Migración y compatibilidad

Orden obligatorio:

1. crear ámbitos, fuentes y nuevos campos opcionales;
2. crear un ámbito empresarial por empresa existente;
3. rellenar contexto y PEN en cuentas, compromisos, obligaciones y pagos existentes;
4. convertir pago uno-a-uno a uno-a-muchos conservando claves y comprobantes;
5. volver opcional `company` donde el ámbito no sea empresarial;
6. activar nuevas restricciones después del backfill;
7. adaptar consultas, permisos, formularios y plantillas;
8. retirar dependencias heredadas solo en una entrega posterior.

Controles de migración:

- mismos conteos de empresas, obligaciones, documentos y movimientos;
- mismos identificadores primarios y archivos;
- ningún registro sin ámbito;
- todas las monedas heredadas en PEN;
- todo pago heredado continúa relacionado con su comprobante;
- reversión de migración probada cuando sea técnicamente segura.

## 14. Casos de aceptación obligatorios

1. Registrar la luz de la casa de la madre sin empresa ni local y generar el mes siguiente sin duplicar.
2. Registrar préstamo personal mensual con cuota, capital/interés opcional y un abono parcial.
3. Registrar apoyo a esposa como no reembolsable y otro gasto como reembolsable, sin confundir sus totales.
4. Registrar estado de tarjeta con ciclo, corte, total, mínimo y pago parcial, sin duplicar compras.
5. Registrar seguro con contratante, asegurado y beneficiario distintos.
6. Registrar vivienda, educación, salud, personal doméstico, viaje, inversión, donación y emergencia usando su ámbito correcto.
7. Rechazar pago superior al saldo y moneda incompatible.
8. Anular un movimiento con motivo sin eliminarlo; registrar devolución o contracargo y reabrir saldo.
9. Bloquear al asistente en un ámbito privado mediante lista, URL directa, descarga y vista previa.
10. Advertir un posible duplicado manual y durante importación.
11. Mostrar calendario mensual y recordatorio sin enviar correo ni WhatsApp.
12. Importar un lote válido y revertir completamente un lote con error.
13. Filtrar panel por ámbito/categoría/moneda sin mezclar monedas.
14. Conservar el flujo empresarial anterior y sus documentos después de la migración.
15. Cambiar ámbito, categoría, frecuencia, tipo de monto, tipo de fuente y estado de revisión, y comprobar que solo aparezcan y se envíen los campos aplicables.
16. Ingresar con el correo correcto aunque contenga espacios externos o cambie su combinación de mayúsculas y minúsculas, conservándolo en el formulario cuando la contraseña sea incorrecta.
17. Recuperar el correo de acceso y establecer una contraseña fuerte mediante un código personal opaco, de un solo uso y almacenado únicamente como hash.
18. Permitir que el gerente, después de reautenticarse, emita para el asistente un código temporal de 30 minutos; impedir que el asistente emita o use una recuperación privilegiada para el gerente.
19. Rechazar códigos vencidos, reutilizados o sometidos a demasiados intentos; revocar las sesiones anteriores después de cambiar la contraseña y registrar los eventos en una auditoría de seguridad separada de los pagos.

## 15. Secuencia de construcción experimental

### E1 — Fundamento seguro

Ámbitos, backfill, moneda, partes, visibilidad y autorización por objeto.

### E2 — Registro expresivo

Categorías, detalles de tarjeta/préstamo/seguro, fuente de fondos, formularios progresivos y duplicados.

### E3 — Dinero real

Movimientos parciales, saldo, anulación, devolución, reembolso, disputa e historial.

### E4 — Tiempo y volumen

Recurrencias flexibles, calendario, recordatorios internos e importación revisable.

### E5 — Supervisión

Filtros comunes, dashboard por moneda/contexto, actividad completa, pruebas de permisos y revisión visual.

El estado de cada `EXP-LAB-*` se actualizará en `02_HISTORIAS_DE_USUARIO.md` y `09_MATRIZ_DE_MEJORAS_Y_TRAZABILIDAD.md` solo con evidencia verificable.

## 16. Puerta para salir del laboratorio

El producto podrá pasar a planificación Scrum definitiva cuando:

- el responsable del producto pruebe los recorridos principales y acepte el modelo;
- los nombres y pantallas ya no requieran cambios estructurales frecuentes;
- se decida qué experimentos se conservan, simplifican o descartan;
- la migración y los permisos tengan pruebas reproducibles;
- no se presenten integraciones simuladas como reales;
- se redacten nuevas HUs a partir del comportamiento aceptado;
- el equipo estime esas HUs y recién entonces defina Sprint, capacidad, horas y Jira.

## 17. Evidencia y desviaciones conscientes · 16/10/2026

La implementación, las pruebas reproducibles y los límites de cada variante están registrados en `evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md`. El estado **verificada técnicamente** significa que existe código y prueba local; no significa aceptación del producto, `Done` del Sprint ni publicación en Jira.

Durante la construcción se tomaron cuatro decisiones que deberán ser aceptadas o cambiadas por el responsable del producto:

1. la importación masiva de obligaciones queda reservada al gerente;
2. el archivo importado se procesa transitoriamente y se conserva el lote normalizado, no el original;
3. los duplicados permiten continuar con motivo o cancelar, pero no fusionar automáticamente;
4. la primera agenda es mensual y adaptable; las vistas semanal y diaria no se afirman como implementadas.

La revisión visual manual de escritorio y móvil permanece pendiente porque la herramienta disponible no pudo verificar de forma segura la URL de la ventana del navegador. La validación automatizada de HTML, permisos, reglas, migraciones y accesibilidad estructural sí fue ejecutada.

**Cierre reproducible del 16/10/2026:** `manage.py check` limpio, ninguna migración pendiente y **62 de 62 pruebas aprobadas**.

## 18. Protocolo de validación manual desde base operativa vacía

La versión documental 0.8 incorpora `11_GUIA_VALIDACION_MANUAL_DESDE_CERO.md` para recorrer el producto en el orden Gerente → Asistente → Gerente sin depender de los datos sembrados usados durante el desarrollo.

La línea base conserva esquema, migraciones, roles y dos cuentas activas, pero no contiene empresas, ámbitos, acreedores, cuentas, compromisos, obligaciones, documentos, movimientos, recordatorios, importaciones, auditorías operativas ni sesiones anteriores. El reinicio y su respaldo se documentan por separado en `evidencias/EXP-LAB_REINICIO_CONTROLADO_2026-10-16.md` para no alterar la evidencia técnica de implementación.

El recorrido principal utiliza datos ficticios y un ámbito de hogar compartido. Comprueba creación inicial, campos contextuales, permisos de catálogos, sustento, pago externo, comprobante, historial, un ámbito privado mediante acceso directo rechazado, generación mensual e idempotencia. Las credenciales no se escriben en documentos versionables.

**Estado:** reinicio técnico demostrado y versión lista para validación manual. La ficha ya contiene rutas, hashes, conteos y resultados reales; el producto solo se considerará validado cuando el responsable complete el recorrido y registre su decisión. Esta sección no convierte los 62 resultados automatizados en aceptación visual.

## 19. EXP-LAB-11 — Acceso y recuperación segura

### 19.1 Problema que debe resolver

Durante el primer intento de entrada se mostró el mensaje de credenciales inválidas. La comprobación técnica confirmó que las credenciales exactas de las dos cuentas conservadas eran válidas, pero también que el ingreso distinguía mayúsculas y minúsculas en el correo. Además, no existía un flujo para una persona que hubiera olvidado tanto su correo de acceso como su contraseña.

El experimento no debe resolver ese problema revelando cuentas, enviando contraseñas, compartiendo un código entre roles ni creando un acceso permanente de emergencia.

### 19.2 Reglas del ingreso normal

1. El correo se normaliza en el servidor: se eliminan espacios externos y se compara sin distinguir mayúsculas o minúsculas.
2. Después de un error se conserva el correo escrito, pero nunca la contraseña.
3. La contraseña puede mostrarse u ocultarse mediante un control accesible que no modifica su valor ni la envía a un tercero.
4. La respuesta a una combinación inválida permanece genérica y no confirma si el correo, la cuenta o la contraseña existen.
5. Los intentos fallidos quedan sujetos a un límite configurable por cuenta y origen; alcanzar el límite no revela cuál de los datos fue correcto.

### 19.3 Códigos personales de recuperación

1. Cada cuenta dispone de sus propios códigos; un código no se comparte entre gerente y asistente ni sirve para otra cuenta.
2. El material aleatorio de cada código tiene al menos 128 bits de entropía, es opaco y se muestra únicamente cuando debe entregarse al titular.
3. La base conserva solo un hash del código. El valor original no se escribe en auditorías, capturas, mensajes persistentes ni documentación.
4. Un código es de un solo uso. Se rechaza después de utilizarlo, revocarlo o vencer.
5. Un código personal válido permite identificar de forma privada el correo de acceso y establecer una contraseña nueva sin exponer ese correo ante una solicitud inválida.
6. La contraseña nueva debe satisfacer los validadores de fortaleza configurados y no se almacena ni se comunica en texto claro.

### 19.4 Recuperación delegada del asistente

1. Solo el gerente puede emitir un código temporal para el asistente.
2. Antes de emitirlo, el gerente debe reautenticarse con su propia contraseña dentro de la operación sensible.
3. El código temporal vence a los 30 minutos, es opaco, se almacena como hash y se consume una sola vez.
4. Emitir un código nuevo revoca los códigos temporales anteriores aún vigentes para esa cuenta.
5. El asistente puede recuperar únicamente su propia cuenta. No puede emitir, consultar ni utilizar un flujo delegado para recuperar al gerente.
6. La delegación no cambia el rol, los permisos ni la propiedad de datos de ninguna cuenta.

### 19.5 Sesiones, auditoría y último recurso

1. Cambiar una contraseña por recuperación revoca las sesiones anteriores de esa cuenta; la persona debe iniciar sesión de nuevo.
2. Emisión, uso, rechazo, vencimiento, revocación y bloqueo por límite de intentos se registran en una auditoría de seguridad separada de la auditoría de obligaciones y pagos.
3. La auditoría identifica actor cuando existe, cuenta afectada, tipo de evento, fecha y resultado, pero no guarda contraseña, código original ni hash reutilizable.
4. El flujo aplica límites de solicitud y verificación. Las respuestas visibles no permiten enumerar cuentas ni comparar resultados válidos e inválidos.
5. Si el gerente perdió contraseña, correo y códigos personales, queda un canal local de último recurso reservado al operador autorizado del equipo donde se ejecuta PagoControl. Debe verificar identidad, emitir una credencial temporal de un solo uso y dejar auditoría; no está disponible como atajo público en la web.

### 19.6 Evidencia exigida

La evidencia separada se mantiene en `evidencias/EXP-LAB_RECUPERACION_ACCESO_2026-10-16.md`. Registra pruebas automatizadas, comprobaciones HTTP, límites pendientes y el respaldo previo sin incluir correos completos, contraseñas, códigos ni hashes reutilizables. `EXP-LAB-11` está verificado técnicamente, pero no se declara aceptado visualmente ni validado por producto hasta que el responsable ejecute el recorrido.
