# Uso de IA

CheckIA usa IA como soporte de priorización, no como decisor automático.

El enfoque es híbrido: ML + NLP + agente de IA para consultas en lenguaje natural.

## Modelo supervisado simulado

`RandomForestClassifier` aprende a estimar riesgo a partir de variables como:

- Monto reclamado.
- Relación monto / suma asegurada.
- Días desde inicio de póliza.
- Días hasta fin de póliza.
- Días para reportar.
- Faltantes documentales.
- Similitud narrativa.

Las etiquetas se generan de forma sintética para demo.

## Detección de anomalías

`IsolationForest` identifica patrones atípicos en variables numéricas y documentales.

## NLP

Se usa `TfidfVectorizer` y `cosine_similarity` para detectar narrativas parecidas:

- Más de 85%: alerta fuerte.
- 70% a 84%: alerta media.

## Agente IA

El agente responde consultas en lenguaje natural con Ollama local (`checkia-gemma`). Antes de enviar texto al agente, el backend interpreta la intención, calcula datos reales del dataset y prepara un preanálisis predictivo con score final, reglas, modelo, anomalía, NLP y factores explicables.

La integración está optimizada para reducir latencia:

- Las preguntas simples usan un prompt corto de Ollama.
- Las consultas de siniestros calculan primero datos con pandas, reglas, ML y NLP.
- Ollama recibe solo contexto compacto y datos permitidos para redactar sin inventar.
- Se usa `keep_alive` para mantener el modelo cargado.
- Se limita `num_ctx` y `num_predict` para evitar respuestas lentas.
- Si Ollama no responde a tiempo, el sistema entrega una respuesta segura basada en reglas.

Prompt base del agente: `backend/src/ai_agent/checkia_system_prompt.md`.

Perfil opcional para educar Ollama:

```powershell
ollama create checkia-gemma -f backend/src/ai_agent/Modelfile
```

Después se puede configurar `OLLAMA_MODEL=checkia-gemma`.

Endpoint de estado: `GET /api/agent/status`.

Endpoint de chat: `POST /api/agent/chat`.

Endpoint de verificación del enfoque híbrido: `GET /api/model/hybrid-status`.

Ejemplo PowerShell:

```powershell
Invoke-RestMethod -Uri "http://localhost:11434/api/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"model":"gemma2:2b","prompt":"Hola","stream":false}'
```

## Métricas

El backend expone métricas simuladas del modelo: precision, recall, f1-score y matriz de confusión.
