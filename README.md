# CheckIA

CheckIA es una aplicación web para analizar siniestros de seguros con inteligencia artificial explicable. El sistema calcula un score de 0 a 100, clasifica cada caso con semáforo de riesgo y entrega al analista humano las señales que recomiendan revisión.

El prototipo responde al reto **Detector de Posibles Fraudes en Siniestros usando Inteligencia Artificial** de Aseguradora del Sur.

## Objetivo

Ayudar a priorizar casos con posible riesgo sin acusar fraude, sin rechazar automáticamente siniestros y sin tomar decisiones legales. CheckIA usa lenguaje de apoyo operativo: posible riesgo, alerta de revisión, revisión recomendada, caso prioritario y requiere análisis humano.

## Tecnologías

- Frontend: React, Vite, TailwindCSS, Recharts, lucide-react.
- Backend: FastAPI, pandas, numpy, scikit-learn.
- IA: RandomForestClassifier, IsolationForest, TF-IDF y similitud de coseno.
- Datos: CSV sintéticos dentro de `backend/data`.

## Instalación Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

API local: `http://127.0.0.1:8000`

## Instalación Frontend

```bash
cd frontend
npm install
npm run dev
```

Aplicación local: `http://localhost:5173`

## Comandos Útiles

```bash
pytest backend/tests
cd frontend && npm run build
```

## Score de Riesgo

El score final combina tres capas:

- Reglas de negocio explicables: 70%.
- Modelo IA y anomalías: 20%.
- NLP con TF-IDF y similitud de coseno: 10%.

Niveles:

- 0 a 40: Verde / Bajo.
- 41 a 75: Amarillo / Medio.
- 76 a 100: Rojo / Alto.

Cada regla activada devuelve código, nombre, puntos, explicación y severidad. El detalle del siniestro muestra factores, recomendación y mensaje ético.

## Agente IA

La página Agente IA permite consultar los datos cargados con preguntas rápidas. El agente responde únicamente con información derivada del dataset sintético y evita inventar hechos. Puede listar top de riesgo, proveedores con alertas, ciudades con casos rojos, documentos faltantes, montos atípicos, patrones recurrentes y resúmenes ejecutivos.

## Dataset

El proyecto incluye 160 siniestros sintéticos y tablas de pólizas, clientes, proveedores y documentos. No contiene datos reales, credenciales ni información personal identificable.

## Ética

CheckIA no acusa fraude. Una alerta no constituye prueba ni decisión. Todo caso marcado como medio o alto requiere revisión humana antes de cualquier acción operativa, contractual o legal.

## Demo Sugerida

1. Abrir Dashboard y revisar KPIs, gráficas y resumen inteligente.
2. Entrar a Casos, filtrar por riesgo alto y abrir un detalle.
3. Mostrar reglas activadas, explicación y mensaje ético.
4. Usar Agente IA con preguntas rápidas.
5. Generar Reporte Ejecutivo y exportar JSON.

## Estructura

```text
backend/      API FastAPI, datos, reglas, modelo, agente y servicios
frontend/     Aplicación React con dashboard, casos, agente y reportes
docs/         Documentación técnica y ética
presentation/ Guion de pitch de 10 minutos
```
