# Arquitectura

CheckIA usa una arquitectura simple para demo local:

- Frontend React/Vite consume endpoints REST.
- Backend FastAPI carga CSV sintéticos desde `backend/data`.
- La capa de features agrega contexto de póliza, proveedor, documentos y similitud textual.
- El motor de reglas produce señales explicables.
- El modelo IA calcula riesgo complementario con RandomForestClassifier e IsolationForest.
- El servicio consolida score, nivel de riesgo, explicación y recomendaciones.
- MySQL/MariaDB en XAMPP funciona como persistencia opcional para datos, resultados IA, reglas activadas e historial del agente.

Flujo:

1. Carga de datos CSV.
2. Enriquecimiento con conteos, documentos y fechas.
3. Cálculo TF-IDF y similitud de coseno.
4. Evaluación de reglas.
5. Predicción IA/anomalías.
6. Score final 70/20/10.
7. Exposición por API.
8. Sincronización opcional con MySQL.
9. Visualización en dashboard, casos, agente, datos y reportes.

La arquitectura prioriza trazabilidad, claridad para jurado de hackathon y ejecución local sin credenciales.

## Persistencia

La app usa CSV como fuente local principal para mantener la demo simple y reproducible. Cuando MySQL está activo, el botón **Sincronizar datos y resultados IA** copia el dataset y los resultados calculados a la base `checkia`.

Esto permite demostrar auditoría, historial, reportería y trazabilidad sin bloquear la app si XAMPP está apagado.

El generador de datos no modifica automáticamente el dataset activo. Produce un CSV descargable para que el usuario lo cargue manualmente desde su PC; recién en ese momento se recalculan features, reglas, NLP, modelo y dashboard.
