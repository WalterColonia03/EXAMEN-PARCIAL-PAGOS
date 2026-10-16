# Revisión del estado y alcance

## 1. Resultado de la auditoría

La carpeta local contenía un monolito Django 5.2 con un módulo funcional `payments`. La revisión histórica ejecutada el 15/10/2026 produjo:

- `manage.py check`: sin errores.
- Suite completa: **75 pruebas aprobadas**.
- Persistencia local SQLite y compatibilidad configurada con PostgreSQL.
- Sesiones de servidor, Argon2 y roles `GERENTE` y `ASISTENTE`.
- Archivos privados y validación de PDF, JPG y PNG hasta 10 MB.

### Actualización de coherencia técnica · 15/10/2026

La descripción anterior se conserva como registro de la revisión previa. La auditoría reproducible del árbol actual no la sustituye retroactivamente y obtuvo esta evidencia:

- `requirements.txt` fija Django 6.1.2; por ello la referencia histórica a Django 5.2 está desactualizada.
- `manage.py check` y `manage.py makemigrations --check --dry-run` finalizaron sin incidencias.
- La suite actual descubrió 16 pruebas y las 16 aprobaron. Esta cifra no convierte la afirmación histórica de 75 pruebas en falsa: ambas corresponden a estados de trabajo distintos que deben aclararse antes de la presentación.
- El código actual contiene `ServiceAccount` y una migración de etapa inicial pendiente de consolidación. La brecha histórica sobre su inexistencia queda marcada para verificación documental, no eliminada.

### Evidencia posterior del Bloque A P0 · 15/10/2026

Sin reescribir la línea base anterior, la ejecución posterior incorporó 12 regresiones P0 y, después, 4 pruebas de experiencia operativa; la suite reproducible actual tiene **32 pruebas aprobadas**. `payments.0004_destination_account_snapshots` se aplicó sobre la base local existente y congeló 12 obligaciones como `BACKFILLED`. `manage.py check` y `manage.py makemigrations --check --dry-run` permanecen limpios. La revisión visual manual de escritorio y móvil no se ejecutó porque el entorno no expuso navegador controlable; por ello el Bloque A está **en validación**, no declarado implementado.

### Corte experimental posterior · 16/10/2026

La información anterior se conserva como historia del diagnóstico, pero ya no describe por sí sola el producto actual. `CR-005` añadió ámbitos empresariales, personales, familiares y patrimoniales; fuentes de fondos; categorías y monedas; recurrencias flexibles; varios movimientos; duplicados; calendario; recordatorios; importación revisable; filtros y supervisión.

- las migraciones `payments.0001` a `payments.0009` están aplicadas en la base local;
- `manage.py check` no reporta incidencias;
- `manage.py makemigrations --check --dry-run` no detecta cambios pendientes;
- la suite completa del corte aprobó **53 de 53 pruebas** y se registra también en `06_FEEDBACK_Y_CONTROL_DE_CAMBIOS.md` y en la evidencia EXP-LAB;
- la revisión visual automatizada se detuvo al no poder verificar con seguridad la URL de la ventana del navegador; por ello sigue pendiente la comprobación manual de escritorio/móvil;
- no existe publicación en GitHub ni conexión con Jira.

La correspondencia detallada se encuentra en `evidencias/EXP-LAB_IMPLEMENTACION_2026-10-16.md`. El estado es **verificado técnicamente**, no aceptado todavía por el responsable del producto.

### Actualización EXP-LAB-10 · 16/10/2026

Se incorporaron formularios contextuales que ocultan y deshabilitan campos no aplicables según ámbito, categoría, recurrencia, tipo de monto, fuente de fondos y cambio de estado. El servidor también normaliza valores residuales para que una petición directa no conserve datos incompatibles. La suite completa posterior a este refinamiento aprobó **62 de 62 pruebas**; la revisión visual manual en escritorio y móvil y la aceptación del responsable del producto continúan pendientes.

### Capacidades ya presentes

| Capacidad | Estado |
|---|---|
| Empresas y locales | Implementada. |
| Acreedores con RUC | Implementada. |
| Cuentas de destino administradas por el gerente | Implementada. |
| Compromisos únicos o mensuales, de monto fijo o variable | Implementada. |
| Generación mensual idempotente | Implementada. |
| Obligaciones con importe, vencimiento y estados | Implementada. |
| Urgencia: vencido, hoy, próximos cinco días y posterior | Implementada. |
| Tablero operativo del asistente | Implementada. |
| Resumen mensual del gerente | Implementada. |
| Adjuntos privados y previsualización local | Implementada. |
| Pago con comprobante obligatorio y prevención de duplicados | Implementada. |
| Historial y auditoría de acciones críticas | Implementada. |

Estas funciones no deben planificarse como si no existieran. Sí forman parte de la regresión obligatoria del Sprint.

## 2. Brechas encontradas

1. No existe una entidad `Cuenta de servicio` para el código permanente del suministro, contrato, cliente, predio o contribuyente.
2. El número externo de una obligación representa el documento del periodo y no debe reutilizarse como código permanente.
3. No existe una bandeja central de documentos ni hash para detectar el mismo archivo más de una vez.
4. El alta manual de una obligación todavía requiere demasiados campos para un gasto irregular urgente.
5. Las alertas se calculan visualmente, pero no se conservan como eventos atendibles ni evitan repeticiones.
6. Los códigos futuros y los números de cuenta requieren una estrategia uniforme de enmascaramiento y acceso.
7. No existen OCR, API de proveedores, scraping, WhatsApp, pagos bancarios, lotes de aprobación ni conciliación.
8. El árbol actual comienza en empresa; no existe aislamiento multiportafolio o multicliente.
9. El directorio `payments/` y varios cambios relacionados aparecían sin consolidar en el control de versiones local. Esto no implicaba publicación o conexión con GitHub.

## 3. Problema que resolverá el incremento

El asistente puede registrar obligaciones y pagos, pero todavía debe reconocer manualmente a qué servicio corresponde cada documento y completar formularios extensos. El gerente recibe visibilidad del mes, aunque aún no existe una referencia permanente que conecte propiedad, proveedor, compromiso, recibo y pago.

## 4. Objetivo del producto

Centralizar las obligaciones de varias empresas y propiedades mediante cuentas de servicio identificables, reducir la digitación del asistente y conservar una trazabilidad verificable desde el documento recibido hasta el comprobante de pago.

## 5. Objetivo del Sprint

> Incorporar cuentas de servicio al MVP existente y utilizarlas para reconocer, registrar y atender obligaciones con menos digitación, manteniendo permisos, documentos privados y trazabilidad.

## 6. Alcance comprometido

- Registrar cuentas de servicio con identificadores configurables.
- Consultarlas, editarlas y desactivarlas sin perder historia.
- Vincularlas con compromisos y obligaciones.
- Mostrar el identificador de forma segura en tablero, detalle e historial.
- Registrar un gasto irregular mediante un flujo express contextual.
- Recibir documentos en una bandeja, detectar duplicados y asociarlos manualmente o por coincidencia exacta.
- Crear alertas internas no duplicadas.
- Reforzar permisos, enmascaramiento y auditoría.
- Conservar y volver a ejecutar toda la regresión del MVP existente.

## 7. Fuera del compromiso del Sprint

Aunque pertenecen a la visión del producto, no se prometen en este Sprint:

- OCR o extracción mediante IA.
- Consulta automática a portales.
- Scraping y resolución de CAPTCHA o MFA.
- API de proveedores.
- WhatsApp, correo o notificaciones push.
- Transferencias o integraciones bancarias.
- Aprobación obligatoria de cada pago.
- Lotes de pago.
- Conciliación automática.
- Pagos parciales.
- Analítica predictiva avanzada.
- Multiportafolio con aislamiento entre distintos clientes.

Estas funciones permanecen en el Product Backlog para ser evaluadas con el profesor. Añadir una de ellas exige retirar trabajo equivalente o recalcular el Sprint; no se incorporará silenciosamente.

## 8. Decisiones de dominio

```text
Empresa
└── Local o propiedad
    └── Cuenta de servicio
        └── Compromiso
            └── Obligación del periodo
                ├── Documento por pagar
                ├── Pago
                └── Comprobante
```

- `Cuenta de servicio` es la relación relativamente estable con un proveedor.
- `Compromiso` define frecuencia, tipo de monto y vencimiento habitual.
- `Obligación` representa una deuda concreta de un periodo.
- `Documento` sustenta la deuda; `comprobante` sustenta el pago.
- Los gastos irregulares pueden existir sin cuenta de servicio.
- No se impondrá una longitud global al código. La validación depende del tipo de identificador o proveedor.
- Desactivar una cuenta impide nuevas asociaciones, pero conserva compromisos, obligaciones y pagos históricos.

## 9. Riesgos principales

| Riesgo | Respuesta planificada |
|---|---|
| Perder cambios actuales no consolidados | Crear respaldo verificable y una línea base antes del trabajo paralelo. |
| Romper datos al añadir claves foráneas | Migración nullable, backfill controlado y pruebas desde base limpia y base existente. |
| Confundir código fijo con número de factura | Campos, etiquetas y criterios separados. |
| Duplicar cuentas o documentos | Normalización, restricciones y hash SHA-256. |
| Exponer identificadores | Enmascaramiento por defecto, permiso de copia y auditoría. |
| Sobreprometer automatización | Bandeja y coincidencia exacta en el Sprint; OCR/API quedan fuera. |
| Trabajo paralelo sobre el mismo archivo | Contratos tempranos, ramas pequeñas y revisión cruzada. |
| Alcance mayor a seis días | WIP máximo de tres HUs y congelamiento funcional el lunes. |

## 10. Supuestos pendientes de ratificación

- La jornada de diez horas incluye pausas; se usa una capacidad conservadora.
- El producto académico administra un solo portafolio con múltiples empresas en este Sprint.
- Ambos roles consultan cuentas de servicio; las modificaciones sensibles requieren permiso de gerente.
- La coincidencia documental automática se limita a valores exactos introducidos o detectables sin OCR.
- Los seis nombres y disponibilidades del equipo deben confirmarse antes del inicio real.

## 11. Hallazgo posterior · ámbitos no empresariales

La investigación `INV-002` confirmó una brecha que no se había explicitado en la línea base: las cuentas de servicio, compromisos y obligaciones exigen una empresa. Por tanto, el sistema no representa correctamente pagos personales, familiares, patrimoniales o de terceros sin crear empresas ficticias.

Este hallazgo **no cambia retroactivamente el Sprint**. La solución aprobada para el laboratorio experimental es introducir un ámbito administrado neutral y separar titular/deudor, beneficiario, acreedor y fuente de fondos. `CR-005` fue autorizado por el responsable del producto el 15/10/2026 exclusivamente para prototipado: no modifica los 35 SP, no crea trabajo Jira y cada capacidad se mantendrá como experimental hasta contar con evidencia técnica y validación del producto.
