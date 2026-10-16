# INV-002 · Ámbitos personales, familiares y patrimoniales

## 1. Identificación y alcance

| Campo | Valor |
|---|---|
| ID de investigación | `INV-002` |
| Fecha de revisión | 15/10/2026 |
| Pregunta de producto | ¿PagoControl puede registrar correctamente obligaciones del gerente, su familia, otras personas, hogares y propiedades, además de empresas? |
| Origen | Observación del usuario y reauditoría de `INV-001` contra el código actual |
| Estado | Investigación terminada; ampliación funcional pendiente de decisión |

Esta ficha no declara una función como implementada ni modifica el Sprint original. Separa lo que existe, lo que solo puede improvisarse y lo que necesita un cambio de modelo, permisos y migración.

## 2. Resultado de la auditoría actual

PagoControl continúa centrado estructuralmente en empresas:

- `ServiceAccount.company`, `PaymentCommitment.company` y `Payable.company` son relaciones obligatorias.
- `Branch` solo puede pertenecer a una empresa.
- El acreedor representa a quien se paga, pero no al titular de la deuda, al beneficiario ni al dueño del dinero usado.
- Existe la categoría `Préstamo`, pero el préstamo todavía debe vincularse a una empresa.
- Un estado de tarjeta solo podría improvisarse como `Otro`; no hay ciclo, fecha de corte, pago mínimo ni saldo.
- Cada obligación acepta un único pago completo. No existen abonos, pago mínimo, saldo restante, devolución o anulación controlada.

Por tanto, crear empresas ficticias llamadas “Personal”, “Casa de mamá” o “Familia” no es una solución aceptable: contamina filtros, reportes y auditoría, y oculta quién tiene realmente la obligación.

| Caso consultado | Soporte actual | Conclusión |
|---|---|---|
| Luz de la casa de la madre | La cuenta admite otro titular, pero exige empresa | No está soportado de forma honesta |
| Préstamo bancario personal | Existe categoría préstamo y recurrencia mensual, pero exige empresa y pago total | Soporte parcial e insuficiente |
| Pago o ayuda a esposa/familiar | No existe beneficiario ni naturaleza de la ayuda | No soportado |
| Estado de tarjeta personal | Puede forzarse como `Otro`, sin ciclo, mínimo, saldo ni abonos | No soportado como tarjeta |

## 3. Qué confirman los referentes

### Gestión personal y familiar

- Quicken trata servicios y tarjetas como cuentas por pagar, distingue total y mínimo de una tarjeta, permite omitir una ocurrencia sin romper la recurrencia, conserva historial y ofrece vistas por vencimiento y calendario: [Bills & Income](https://info.quicken.com/win/using-the-bills-income-tab).
- La SBS señala que un estado de cuenta de tarjeta debe destacar fecha de pago, pago total del periodo y pago mínimo: [Reglamento de tarjetas](https://www.sbs.gob.pe/noticia/detallenoticia/idnoticia/1431?title=SBS+modifica+el+Reglamento+de+Tarjetas+de+Cr%C3%A9dito+y+D%C3%A9bito).
- Sunass distingue titular, dirección del predio, suministro, periodo, vencimiento, consumo y alertas por deuda o suspensión. Una cuenta de servicio no pertenece necesariamente a una empresa: [lectura del recibo](https://www.gob.pe/institucion/sunass/noticias/1388998-recibos-del-agua-potable-conoce-sus-conceptos-y-detalles-para-que-pagues-lo-justo).
- En seguros pueden ser personas distintas el contratante, el asegurado y el beneficiario; además, una prima puede pagarse completa o en cuotas y el atraso puede suspender la cobertura: [orientación de la SBS](https://www.sbs.gob.pe/usuarios/seguros/cobertura-e-indemnizacion).

### Gestión de patrimonio y family office

- J.P. Morgan describe administración financiera para familias que incluye pago de cuentas, flujo de caja, llamadas de capital, nómina, entidades familiares, personal doméstico, aviación privada y colecciones: [Lifestyle Services](https://privatebank.jpmorgan.com/latam/en/services/wealth-planning-and-advice/family-office-services/lifestyle-services).
- Asseta aplica cuentas por pagar a varias entidades y añade aprobación por entidad, proveedor o importe, detección de duplicados, programación y auditoría completa: [Family Office Bill Pay](https://www.asseta.ai/platform/products/bill-pay).
- La protección debe aplicarse por objeto y no solo por rol global porque salud, asuntos legales, personal doméstico y ayudas familiares contienen datos personales de terceros. La referencia normativa local es la [normativa de protección de datos personales de la ANPD](https://www.gob.pe/institucion/anpd/colecciones/3482-normativa-de-proteccion-de-datos-personales).

### Cuentas por pagar y control operativo

- Melio permite registrar pagos realizados fuera del sistema y también devolver a pendiente un pago marcado por error: [marcar pagado o no pagado](https://help.melio.com/hc/en-us/articles/6641702618012-How-to-mark-a-bill-as-paid-or-unpaid).
- Zoho Books reúne estado, pago, importación, filtros, calendario, adjuntos, recurrencia, anulación y créditos en torno a la obligación: [Bills](https://www.zoho.com/in/books/help/bills/).

La inferencia para PagoControl es que el eje no debe ser exclusivamente “empresa”, sino **a quién o a qué corresponde la obligación**. Empresa, persona, hogar o propiedad son ámbitos; el acreedor es una parte distinta.

## 4. Catálogo de situaciones que el sistema debería contemplar

| Grupo | Situación | Datos o excepción particular |
|---|---|---|
| Hogar | Luz, agua, gas, internet o seguridad de vivienda propia | Titular, predio, suministro, periodo, consumo y posible corte |
| Familia | Servicios de la casa de madre, padre u otro familiar | Titular y beneficiario distintos del pagador |
| Vivienda | Alquiler, hipoteca, mantenimiento, arbitrios y cuota de condominio | Propiedad, contrato, copropietario y calendario no siempre mensual |
| Crédito | Préstamo personal, hipotecario o vehicular | Cuota, capital, interés, seguro, prepago, refinanciación o gracia |
| Tarjeta | Estado de cuenta de tarjeta principal o adicional | Emisor, titular, últimos cuatro, ciclo, corte, total, mínimo, moneda y saldo |
| Pareja/familia | Apoyo a esposa, hijos o dependientes | Propio, compartido, ayuda, préstamo o reembolsable |
| Educación | Colegio, universidad, tutorías, matrícula y actividades | Alumno beneficiario, cuotas, descuentos y penalidades |
| Salud | Consulta, tratamiento, farmacia, emergencia y deducible | Datos sensibles, reembolso de seguro y acceso restringido |
| Seguros | Vida, salud, hogar, vehículo, viaje u obras de arte | Contratante, asegurado, beneficiario, póliza, vigencia y cobertura |
| Personal doméstico | Sueldo, adelanto, beneficio o reembolso de chofer, niñera, cuidador o administrador | Persona beneficiaria, periodo y privacidad laboral |
| Vehículos | Cuota, seguro, SOAT, mantenimiento, reparación, impuesto o multa | Vehículo, conductor, vencimiento y eventual disputa |
| Viajes | Vuelos, hotel, visa, seguro, depósitos, cancelación y gasto de emergencia | Viajero, itinerario, moneda, anticipo, saldo y reembolso |
| Eventos | Boda, funeral, celebración o evento benéfico | Hitos, depósitos, saldo final y múltiples beneficiarios |
| Patrimonio | Mantenimiento de varias propiedades, embarcación o aeronave | Activo, administrador, proveedor y fuente de fondos |
| Colecciones | Compra, subasta, transporte, restauración, almacenamiento, seguro o tasación de arte | Obra/activo, confidencialidad, hitos y moneda extranjera |
| Inversiones | Llamada de capital, comisión o aporte extraordinario | Entidad o vehículo, fecha estricta e instrucciones verificadas |
| Filantropía | Donación única o recurrente | Donante, beneficiario, finalidad y constancia |
| Legal/familiar | Pensión, manutención, abogado, sucesión, fideicomiso o acuerdo familiar | Alta privacidad, mandato, plazo y documentos restringidos |
| Suscripciones | Clubes, gimnasios, medios, software, membresías y renovaciones anuales | Renovación automática, cancelación y periodicidad variable |
| Impuestos personales | Predial, vehicular, renta u otra obligación personal | Contribuyente, periodo, código y monto por definir |
| Emergencia | Hospitalización, accidente, avería de vivienda, desastre o regreso urgente | Prioridad crítica, monto inicialmente desconocido y revisión posterior |

## 5. Casos inesperados y de corrección

El flujo normal no es suficiente. También deben diseñarse estos eventos:

1. documento duplicado o factura repetida;
2. importe desconocido que se completa después;
3. pago parcial, mínimo o en varias cuotas;
4. devolución, contracargo, nota de crédito o reembolso;
5. cargo de tarjeta disputado;
6. cuenta bancaria del acreedor cambiada a última hora;
7. operación rechazada o comprobante inválido;
8. saldo insuficiente o fuente de fondos bloqueada;
9. obligación en moneda extranjera y diferencia de cambio;
10. débito automático que debe cancelarse o ya se ejecutó;
11. anticipo pagado por el asistente y posterior reembolso;
12. gerente temporalmente ausente, incapacitado o sin acceso;
13. delegación temporal que debe vencer automáticamente;
14. obligación urgente creada después del horario habitual;
15. dato privado que el asistente puede ejecutar pero no consultar íntegramente.

Ninguna corrección debe borrar el hecho original. Pago, anulación, devolución y ajuste deben ser eventos separados con actor, fecha y motivo.

## 6. Modelo funcional propuesto

### 6.1 Ámbito administrado

Crear una entidad neutral, provisionalmente llamada `PaymentContext` o **Ámbito administrado**, con al menos estos tipos:

- empresa;
- personal del gerente;
- hogar o propiedad;
- familiar u otra persona;
- otra entidad patrimonial, para una futura fundación, fideicomiso o vehículo de inversión.

Ejemplos: `Empresa Central`, `Personal de Carlos`, `Casa de mamá`, `Departamento de playa`, `Educación de Lucía`.

### 6.2 Partes que no deben mezclarse

| Pregunta de negocio | Campo/concepto recomendado |
|---|---|
| ¿A quién corresponde? | Ámbito administrado |
| ¿Quién asumió legalmente la deuda? | Titular o deudor |
| ¿Quién recibe el beneficio? | Beneficiario, opcional |
| ¿A quién se paga? | Acreedor |
| ¿Con qué dinero se paga? | Fuente de fondos |
| ¿Se espera recuperar el dinero? | Naturaleza: propio, compartido, apoyo, reembolsable o préstamo |

Una madre, esposa u otro beneficiario no necesita convertirse en usuario del sistema.

### 6.3 Migración segura propuesta

1. Crear `PaymentContext` y una relación `context` inicialmente opcional en cuentas de servicio, compromisos y obligaciones.
2. Crear automáticamente un contexto empresarial por cada empresa existente y asociar todos los registros actuales sin cambiar sus identificadores ni documentos.
3. Validar conteos y relaciones mediante una migración probada.
4. Hacer `context` obligatorio y permitir que `company` sea nulo solo después del backfill.
5. Conservar temporalmente las relaciones empresariales heredadas; retirarlas únicamente en otra entrega.
6. Reemplazar restricciones de unicidad y filtros para que usen contexto, acreedor, referencia y periodo.

No se debe renombrar `Company` para fingir que representa personas o viviendas.

## 7. Flujo recomendado para el usuario

1. Elegir **“¿A quién corresponde este pago?”** y seleccionar el ámbito.
2. Elegir el tipo de obligación: servicio, tarjeta, préstamo, seguro, impuesto, proveedor u otro.
3. Indicar titular/deudor, beneficiario cuando corresponda y acreedor.
4. Registrar monto, moneda, periodo, vencimiento, recurrencia y documento.
5. Indicar fuente de fondos y, para terceros, si es apoyo, compartido, préstamo o reembolsable.
6. Advertir duplicados y cambios de cuenta antes de confirmar.
7. Enviar a revisión solo por regla de riesgo: importe alto, acreedor/cuenta nueva, contexto privado o dato incompleto.
8. Registrar el resultado del pago externo como total o parcial y adjuntar comprobante.
9. Corregir mediante anulación, devolución, disputa o reembolso sin borrar historia.

La interfaz debe usar revelado progresivo: Empresa y Local solo aparecen en ámbitos empresariales; los campos de tarjeta, préstamo o seguro aparecen únicamente al elegir ese tipo. Así se evita saturar al gerente y al asistente.

## 8. Tarjetas de crédito: regla específica

Para no contar dos veces el mismo gasto, el primer alcance debe registrar **una obligación por estado de cuenta**, no otra obligación por cada compra ya incluida en él. Debe conservar:

- titular y tarjeta enmascarada;
- emisor;
- periodo/ciclo y fecha de corte;
- fecha máxima de pago;
- pago total, pago mínimo y monto elegido;
- moneda y, si aplica, saldo pendiente;
- documento del estado de cuenta y comprobantes de pagos.

El desglose de compras puede ser informativo en una fase posterior. Un pago mínimo o abono exige cambiar la relación actual de un pago por obligación a varios movimientos por obligación.

## 9. Privacidad y permisos

- La visibilidad debe filtrarse en el servidor por ámbito, no solo ocultarse en botones.
- Deben protegerse también detalle, edición, descarga, vista previa, revelación de instrucciones, historial, filtros y exportaciones.
- El gerente administra ámbitos y decide cuáles puede ver el asistente.
- Salud, asuntos legales y ayudas familiares pueden requerir acceso restringido por registro.
- Un `POST` manipulado con un identificador de ámbito no autorizado debe responder `403` o `404` sin filtrar información.
- La auditoría debe guardar el identificador y tipo de ámbito, pero no copiar nombres sensibles, documentos médicos o números completos en mensajes y logs.

## 10. Aplicación de las recomendaciones recibidas

| Recomendación de `INV-001` | Estado verificado | Brecha para implementar |
|---|---|---|
| Registrar pago realizado fuera del sistema con comprobante | Implementada en lo esencial | Falta anulación controlada y no equivale a conciliación bancaria |
| Separar compromiso recurrente de obligación del periodo | Implementada | Solo pago único o mensual; faltan otras frecuencias |
| Adjuntar sustento y comprobante privado | Implementada | Mantener pruebas de acceso y revisión visual |
| Cola por urgencia y excepciones | Implementada | Falta añadir contexto personal/familiar y días/configuración avanzada |
| Ficha con documentos y actividad | Parcial | Actividad limitada; sin comentarios ni cronología completa |
| Roles y auditoría | Parcial | Roles globales; sin alcance por ámbito o privacidad por registro |
| Dashboard de pagado/pendiente/vencido | Parcial | Sin desglose por ámbito, moneda, beneficiario o antigüedad |
| Cuentas de servicio reutilizables | Implementada para empresas | No sirven aún para hogares/personas sin empresa |
| Importación CSV/XLSX | Parcial | Solo importa cuentas de servicio, no obligaciones |
| Prevención de duplicados | Parcial | Protege recurrencias; no detecta bien una obligación manual repetida |
| Recordatorios y calendario | No implementada | Solo hay cola al entrar al sistema |
| Pagos parciales, devoluciones y correcciones | No implementada | El pago actual es único y por el total exacto |
| OCR, correo, banca y conciliación | No implementada y fuera del MVP | Requiere proveedores, costos, seguridad y otro cambio aprobado |
| Ámbitos personales, familiares y patrimoniales | Autorizada para laboratorio; implementación en curso | `CR-005` aprobado; requiere migración, permisos por objeto y nuevas pruebas antes de declararse verificada |

**Actualización del 16/10/2026:** la tabla anterior conserva el diagnóstico previo a la construcción. El corte posterior implementó y verificó técnicamente ámbitos, permisos por objeto, categorías/moneda, recurrencias flexibles, movimientos, duplicados, calendario, recordatorios e importación revisable. La evidencia vigente y sus límites están en `EXP-LAB_IMPLEMENTACION_2026-10-16.md`; OCR, correo, banca y conciliación permanecen fuera.

## 11. Fases sugeridas, sin compromiso automático

| Fase candidata | Resultado | Incluye |
|---|---|---|
| Base de alcance | Registrar sin empresas ficticias | Ámbito, titular/beneficiario, tipo tarjeta, filtros y migración empresarial |
| Excepciones financieras | Representar la realidad del pago | Abonos, saldo, mínimo, anulación, devolución, disputa y reembolso |
| Automatización | Reducir trabajo repetitivo | Frecuencias flexibles, calendario, avisos e importación de obligaciones |
| Integraciones | Solo con necesidad confirmada | OCR, correo receptor, banco y conciliación |

El responsable del producto autorizó desarrollar estas fases en el laboratorio experimental el 15/10/2026. Esa autorización no las incorpora a la entrega Scrum histórica: no se asignan Story Points ni horas y, tras validar el prototipo, se decidirá qué capacidades pasan a una planificación Scrum nueva.
