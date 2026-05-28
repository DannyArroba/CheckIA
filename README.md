# CheckIA

CheckIA es una aplicación web para analizar siniestros de seguros con inteligencia artificial explicable. El sistema calcula un score de 0 a 100, clasifica cada caso con semáforo de riesgo y entrega al analista humano las señales que recomiendan revisión.

El prototipo responde al reto **Detector de Posibles Fraudes en Siniestros usando Inteligencia Artificial** de Aseguradora del Sur.

## Objetivo

Ayudar a priorizar casos con posible riesgo sin acusar fraude, sin rechazar automáticamente siniestros y sin tomar decisiones legales. CheckIA usa lenguaje de apoyo operativo: posible riesgo, alerta de revisión, revisión recomendada, caso prioritario y requiere análisis humano.

## Tecnologías

- Frontend: React, Vite, TailwindCSS, Recharts, lucide-react.
- Backend: FastAPI, pandas, numpy, scikit-learn.
- IA: RandomForestClassifier, IsolationForest, TF-IDF y similitud de coseno.
- LLM local opcional: Ollama con `gemma2:2b`.
- Datos: CSV sintéticos dentro de `backend/data`.
- Base de datos: MySQL/MariaDB con esquema en `database/checkia.sql`.

## Instalación Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

API local: `http://127.0.0.1:8000`

## Base de Datos

El archivo `database/checkia.sql` crea la base `checkia` con clientes, pólizas, proveedores, siniestros, documentos, resultados de riesgo, reglas activadas y mensajes del agente.

Para MySQL/MariaDB:

```bash
mysql -u root -p < database/checkia.sql
```

Con XAMPP normalmente funciona con:

```text
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=checkia
```

La página **Datos** permite verificar conexión, sincronizar CSV y resultados IA, generar nuevos CSV sintéticos descargables, cargar un CSV desde tu PC y comprobar que dashboard/casos/agente se actualizan. Los CSV generados usan `;` y `utf-8-sig` para abrirse correctamente por columnas en Excel.

## Ollama Local

CheckIA puede usar Ollama para responder preguntas abiertas del chat sin enviar datos a servicios externos.

```powershell
ollama pull gemma2:2b
ollama serve
```

Prueba rápida:

```powershell
Invoke-RestMethod -Uri "http://localhost:11434/api/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"model":"gemma2:2b","prompt":"Hola","stream":false}'
```

Variables disponibles:

```text
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:2b
OLLAMA_TIMEOUT_SECONDS=25
```

Modelo local educado para CheckIA:

```powershell
ollama create checkia-gemma -f backend/src/ai_agent/Modelfile
```

Luego cambia `OLLAMA_MODEL=checkia-gemma`.

## Instalación Frontend

```bash
cd frontend
npm install
npm run dev
```

Aplicación local: `http://localhost:5173`

## Comandos Útiles

```bash
python -m pytest backend/tests
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

## Agente IA

La página Agente IA permite consultar datos con preguntas rápidas y con Ollama local para preguntas abiertas. Las preguntas rápidas son inmediatas; las abiertas usan contexto compacto para responder en un rango razonable. Los IDs como `CLM-0131` son clickeables y abren el detalle del caso.

El historial del chat se guarda en MySQL por conversaciones, parecido a ChatGPT. Puedes crear un nuevo chat, volver a conversaciones anteriores y eliminar chats completos.

## Dataset

El proyecto incluye siniestros sintéticos iniciales y tablas de pólizas, clientes, proveedores y documentos. Desde la página **Datos** puedes crear un CSV adicional para descargarlo y luego cargarlo manualmente desde tus archivos. Solo al cargarlo se recalcula el modelo y cambian los indicadores.

## Ética

CheckIA no acusa fraude. Una alerta no constituye prueba ni decisión. Todo caso marcado como medio o alto requiere revisión humana antes de cualquier acción operativa, contractual o legal.

## Demo Sugerida

1. Abrir Dashboard y revisar KPIs, gráficas y resumen inteligente.
2. Entrar a Datos, verificar MySQL y sincronizar resultados IA.
3. Generar un CSV sintético descargable.
4. Cargar ese CSV manualmente desde tus archivos y comprobar cambios en KPIs.
5. Entrar a Casos, filtrar por riesgo alto, abrir un detalle y registrar seguimiento humano.
6. Usar Agente IA y mostrar historial por conversaciones.
7. Generar Reporte Ejecutivo y exportar JSON.

## Estructura

```text
backend/       API FastAPI, datos, reglas, modelo, agente y servicios
frontend/      Aplicación React con dashboard, casos, agente, datos y reportes
database/      SQL para crear la base checkia
docs/          Documentación técnica y ética
presentation/  Guion de pitch de 10 minutos
```
