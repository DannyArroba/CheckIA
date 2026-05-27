# Reglas de Negocio

Las reglas generan señales de posible riesgo. No prueban fraude ni reemplazan análisis humano.

Reglas implementadas:

- Reclamo cercano al inicio de póliza.
- Reclamo cercano al fin de vigencia.
- Reporte tardío.
- Alta frecuencia de reclamos por asegurado.
- Alta frecuencia de reclamos por vehículo.
- Proveedor recurrente.
- Proveedor en lista restrictiva simulada.
- Documentos incompletos.
- Documentos ilegibles.
- Documentos inconsistentes.
- Monto reclamado alto frente a suma asegurada.
- Narrativas similares.
- Cobertura pérdida total por robo.
- Accidente sin tercero identificado.
- Dinámica inusual declarada.
- Cambios recientes en datos del asegurado.

Cada regla devuelve:

- Código.
- Nombre.
- Puntos.
- Explicación.
- Severidad.

El score de reglas se limita a 100 y representa el 70% del score final.
