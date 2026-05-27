# Arquitectura

CheckIA usa una arquitectura simple para demo local:

- Frontend React/Vite consume endpoints REST.
- Backend FastAPI carga CSV sintéticos desde `backend/data`.
- La capa de features agrega contexto de póliza, proveedor, documentos y similitud textual.
- El motor de reglas produce señales explicables.
- El modelo IA calcula riesgo complementario con RandomForestClassifier e IsolationForest.
- El servicio consolida score, nivel de riesgo, explicación y recomendaciones.

Flujo:

1. Carga de datos CSV.
2. Enriquecimiento con conteos, documentos y fechas.
3. Cálculo TF-IDF y similitud de coseno.
4. Evaluación de reglas.
5. Predicción IA/anomalías.
6. Score final 70/20/10.
7. Exposición por API.
8. Visualización en dashboard, casos, agente y reportes.

La arquitectura prioriza trazabilidad, claridad para jurado de hackathon y ejecución local sin credenciales.
