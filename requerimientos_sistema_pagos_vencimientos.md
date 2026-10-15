# Proyecto: Sistema de Control de Pagos y Vencimientos

## 1. Contexto

Desarrollaremos un Producto Mínimo Viable (MVP) para el examen parcial del curso Agile Development, aplicando Scrum con un único sprint.

El cliente es el gerente de uno o varios negocios y cuenta con un asistente encargado de controlar y registrar el pago de sus obligaciones.

Actualmente el negocio tiene dificultades para controlar gastos variables, pagos a proveedores, servicios, impuestos, préstamos y otras deudas. Algunos pagos se realizan fuera de plazo, ocasionando moras.

La solución debe facilitar el trabajo del asistente y ofrecer al gerente visibilidad de los pagos del mes.

**Principio fundamental: la aplicación debe reducir el trabajo administrativo, no incrementarlo.**

## 2. Objetivo del MVP

Crear una aplicación web funcional que permita:

1. Registrar compromisos de pago.
2. Administrar cuentas por pagar de cada período.
3. Visualizar obligaciones mediante tarjetas tipo Post-it, ordenadas por urgencia.
4. Alertar visualmente sobre vencimientos.
5. Adjuntar el documento que se debe pagar.
6. Registrar pagos realizados con comprobante obligatorio.
7. Consultar el historial.
8. Desactivar compromisos sin eliminar su historial.
9. Administrar varias empresas y locales.
10. Mostrar al gerente el estado mensual de sus obligaciones.

NO implementar transferencias bancarias reales en esta versión. Los pagos se realizan externamente y el asistente registra la evidencia correspondiente.

## 3. Tecnologías

Primero inspecciona el repositorio existente. Si ya hay un proyecto, conserva su arquitectura y tecnologías cuando sean apropiadas.

Si el repositorio está vacío, propón una implementación full-stack sencilla mediante:

- Next.js con TypeScript.
- Tailwind CSS.
- Prisma con SQLite para la demostración local.
- Autenticación por sesiones y contraseñas cifradas mediante hash.
- Almacenamiento local protegido para los documentos.

Prioriza simplicidad, mantenibilidad y ejecución local.

## 4. Usuarios y permisos

Solo existen dos roles:

**GERENTE**
- Consultar las obligaciones e historial.
- Visualizar los resúmenes mensuales.
- Registrar y modificar números de cuenta de destino.
- Suspender o reactivar obligaciones excepcionalmente.
- Activar o desactivar compromisos de pago.
- Registrar obligaciones y pagos si lo necesita.

**ASISTENTE**
- Consultar y registrar compromisos y cuentas por pagar.
- Adjuntar recibos y documentos.
- Registrar pagos efectuados.
- Adjuntar obligatoriamente sus comprobantes.
- Consultar el historial.
- Consultar los números de cuenta autorizados, sin modificarlos.

El asistente realiza los pagos de manera autónoma. No debe existir un flujo obligatorio de aprobación gerencial para cada pago.

Validar los permisos en el backend además de la interfaz.

## 5. Estructura del negocio

La aplicación manejará:

- Empresas.
- Locales asociados a empresas.
- Acreedores (proveedores, bancos, entidades, etc.).
- Compromisos de pago.
- Cuentas por pagar.
- Pagos realizados.
- Documentos adjuntos.
- Historial de cambios importantes.

Una empresa puede tener múltiples locales.

Un gasto puede pertenecer a una empresa sin asociarse a un local.

Un mismo proveedor puede tener contratos diferentes con varias empresas o locales.

No mezclar los pagos de diferentes empresas y locales.

## 6. Compromisos de pago

Crear compromisos con estos campos:

- Identificador automático.
- Nombre del compromiso.
- Categoría: servicio, impuesto, proveedor, préstamo u otro.
- Empresa.
- Local opcional.
- Acreedor.
- Frecuencia: pago único o mensual.
- Día habitual de vencimiento para pagos mensuales.
- Monto fijo o variable.
- Número de cuenta de destino opcional.
- Estado activo/inactivo.

Solo el gerente puede registrar o modificar cuentas bancarias de destino.

Permitir desactivar un compromiso. Desactivarlo evita generar nuevas obligaciones, pero conserva las anteriores y todos sus comprobantes.

Para compromisos mensuales, reutilizar la configuración y generar las cuentas de cada período evitando duplicados. No asumir que el monto variable del mes anterior es el monto definitivo del siguiente.

## 7. Cuentas por pagar

Cada obligación concreta incluirá:

- ID automático.
- Número de documento externo, si existe.
- Compromiso asociado.
- Nombre o concepto.
- Empresa y local.
- Categoría y acreedor.
- Período correspondiente.
- Monto.
- Fecha de vencimiento.
- Estado.
- Documento por pagar.
- Fecha de pago si corresponde.
- Comprobante del pago si corresponde.
- Referencia de operación opcional.

Estados administrativos:

- Pendiente.
- Pagado.
- Suspendido.

Estados visuales calculados según la fecha:

- Vencido.
- Vence hoy.
- Próximo a vencer.
- Pendiente sin urgencia.

También contemplar una indicación de información incompleta cuando una cuenta periódica aún no tenga monto o documento definitivo.

## 8. Reglas de vencimiento

Utilizar inicialmente 5 días de anticipación.

Orden de visualización:

1. Obligaciones vencidas.
2. Obligaciones que vencen hoy.
3. Obligaciones próximas a vencer.
4. Las demás obligaciones pendientes, por fecha ascendente.

No incluir pagos realizados ni suspendidos en el listado de obligaciones que deben pagarse ahora.

Calcular las fechas según la zona horaria America/Lima.

Las alertas del MVP son visuales dentro de la aplicación. No implementar correo, WhatsApp ni notificaciones push.

## 9. Documentos y comprobantes

Permitir adjuntar PDF, JPG y PNG, con límite de tamaño razonable.

Distinguir:

- Documento que sustenta la obligación por pagar.
- Comprobante del pago efectuado.

Regla obligatoria:

**No permitir marcar una obligación como Pagada sin adjuntar un comprobante del pago.**

Al registrar un pago, guardar monto, fecha, usuario responsable y comprobante.

Impedir que se registre nuevamente un pago completo sobre una obligación ya pagada.

Conservar los documentos históricos y restringir su acceso a usuarios autorizados.

La aplicación no debe afirmar que un archivo subido fue validado por el banco. Solo registra la evidencia presentada.

## 10. Interfaz de usuario

Diseñar una interfaz moderna, intuitiva, en español y adaptable a computadoras y celulares.

Usar como inspiración un tablero visual de notas adhesivas o Post-it.

Las tarjetas deben mostrar:

- Nombre del gasto o acreedor.
- Empresa y local.
- Monto.
- Fecha de vencimiento.
- Estado.
- Identificador del recibo.
- Indicador de documento adjunto.

Aplicar colores suaves según la urgencia, con texto e iconos para que el estado no dependa exclusivamente del color.

Las tarjetas deben ordenarse automáticamente. No implementar arrastrar y soltar durante el MVP.

Pantallas esenciales:

1. Inicio de sesión.
2. Tablero del asistente con filtros por empresa, local y estado.
3. Formulario sencillo para crear compromisos y cuentas por pagar.
4. Detalle de obligación para adjuntar documentos y registrar pagos.
5. Historial de pagos.
6. Panel del gerente con resumen mensual y control de excepciones.

La gestión básica de empresas, locales y acreedores puede resolverse mediante formularios o ventanas sencillas, sin construir grandes módulos administrativos.

Evitar menús excesivos y campos repetitivos. Cuando sea posible, rellenar automáticamente los datos conocidos del compromiso.

## 11. Dashboard del gerente

Mostrar, para el mes seleccionado:

- Cantidad e importe de obligaciones pagadas.
- Cantidad e importe de obligaciones pendientes.
- Cantidad e importe de obligaciones vencidas.
- Cantidad de obligaciones suspendidas.
- Detalle consultable de las obligaciones.

Permitir filtrar por empresa y local.

Evitar contabilizar dos veces la misma obligación al calcular los totales.

## 12. Seguridad y trazabilidad

- Almacenar contraseñas mediante hash seguro.
- Usar sesiones seguras.
- Validar los permisos en el servidor.
- Impedir modificar cuentas de destino mediante solicitudes no autorizadas.
- Registrar quién cambió una cuenta de destino y cuándo.
- Registrar quién marcó una obligación como pagada.
- Evitar borrar silenciosamente pagos y comprobantes históricos.
- No exponer los documentos privados mediante URLs públicas sin autorización.
- Validar tipos y tamaños de archivo.

## 13. Datos iniciales para la demostración

Crear datos ficticios:

- Un usuario gerente.
- Un usuario asistente.
- Dos empresas.
- Dos locales de una empresa.
- Un gasto empresarial sin local.
- Un proveedor contratado por dos locales.
- Una suscripción mensual.
- Un servicio de internet.
- Un servicio de agua.
- Una obligación tributaria.
- Un préstamo.
- Obligaciones pagadas, pendientes, vencidas y suspendidas.

Las cuentas bancarias deben ser ficticias y claramente identificadas como datos de demostración.

Usar fechas relativas a la fecha actual para que existan tarjetas próximas a vencer y vencidas durante la demostración.

## 14. Condiciones para considerar terminado el MVP

Verificar que:

1. El asistente pueda crear y consultar una obligación.
2. Los pagos estén ordenados por urgencia.
3. Las alertas cambien correctamente según la fecha.
4. Se pueda adjuntar el recibo.
5. No se pueda confirmar un pago sin comprobante.
6. Al pagar, la obligación deje de figurar como pendiente.
7. El gerente pueda visualizar inmediatamente ese pago.
8. El asistente no pueda cambiar una cuenta bancaria de destino.
9. Un compromiso desactivado conserve el historial anterior.
10. Se puedan filtrar obligaciones por empresa y local.
11. Los datos persistan después de cerrar y volver a abrir la aplicación.
12. Los documentos puedan descargarse de forma autorizada.

## 15. Forma de trabajo

Antes de escribir código:

1. Inspecciona el proyecto.
2. Propón la arquitectura mínima.
3. Define el modelo de datos.
4. Identifica dependencias y riesgos.
5. Organiza el trabajo en tareas pequeñas.
6. Implementa las funcionalidades prioritarias.
7. Ejecuta pruebas de los flujos críticos.
8. Proporciona instrucciones para ejecutar el proyecto localmente.

No construyas solamente pantallas estáticas. El resultado debe tener persistencia real, operaciones CRUD funcionales, control de roles, carga de documentos y cálculo correcto de vencimientos.

Si alguna decisión resulta ambigua, explícala antes de adoptar una solución que incremente innecesariamente el alcance.

**El objetivo es entregar un sistema sencillo, utilizable y demostrable en un solo sprint, no un ERP completo.**