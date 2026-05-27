# Uso de IA

CheckIA usa IA como soporte de priorización, no como decisor automático.

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

El agente responde preguntas frecuentes usando agregaciones del dataset ya procesado. No llama modelos externos ni inventa datos.

## Métricas

El backend expone métricas simuladas del modelo: precision, recall, f1-score y matriz de confusión.
