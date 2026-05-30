# CheckIA

CheckIA es una aplicación web para apoyar la revisión de siniestros de seguros con inteligencia artificial explicable. El sistema importa datos sintéticos desde Excel, procesa documentos PDF, detecta posibles señales de riesgo, calcula un score por siniestro y entrega explicaciones claras para que un analista humano priorice la revisión.

El prototipo responde al reto **Detector de Posibles Fraudes en Siniestros usando Inteligencia Artificial** de Aseguradora del Sur.

## Objetivo

CheckIA ayuda a identificar patrones anómalos o inconsistencias en siniestros, pólizas, asegurados, proveedores y documentos. La aplicación no acusa fraude, no rechaza automáticamente siniestros, no sustituye el análisis humano y no toma decisiones legales.

El lenguaje de la aplicación está orientado a apoyo operativo:

- posible riesgo
- alerta de revisión
- revisión recomendada
- caso prioritario
- requiere análisis humano

## Funcionalidades

- Importación de Excel con varias hojas: `1_Siniestros`, `2_Polizas`, `3_Asegurados`, `4_Proveedores` y `5_Documentos`.
- Carga de lotes de PDFs: declaraciones de accidente, facturas, partes policiales y otros documentos relacionados.
- Extracción de texto PDF directa y OCR cuando el PDF viene escaneado.
- Relación automática por `SIN-0001`, `DOC-0001`, nombre de archivo y campos internos del documento.
- Validación de documentos faltantes, documentos no listados, PDFs duplicados e inconsistencias.
- Cálculo de alertas explicables y score de riesgo.
- Dashboard con KPIs, gráficos interactivos, filtros acumulables y ranking de casos.
- Bandeja de casos con búsqueda, ordenamiento, filtros y detalle completo.
- Agente IA con Ollama para consultar siniestros, documentos, alertas, proveedores y patrones.
- Reporte ejecutivo para auditoría o presentación.
- Estado del sistema para revisar Backend, MySQL, Node, Ollama, Poppler y Tesseract.

## Arquitectura

```text
frontend/              React + Vite + TailwindCSS
backend/               FastAPI + servicios de análisis
backend/src/rules      Reglas de riesgo explicables
backend/src/models     Modelo ML y anomalías
backend/src/ai_agent   Agente IA con Ollama
backend/src/services   Importación Excel/PDF, OCR, scoring y consultas
database/              Esquema SQL MySQL/MariaDB
docs/                  Documentación técnica, datos, reglas, IA y limitaciones
presentation/          Guion de pitch
```

## Tecnologías

- Frontend: React, Vite, TailwindCSS, Recharts, lucide-react.
- Backend: Python, FastAPI, pandas, numpy, scikit-learn.
- Base de datos: MySQL o MariaDB.
- IA local: Ollama con `checkia-gemma` o respaldo `gemma2:2b`.
- NLP: TF-IDF y similitud de coseno.
- OCR/PDF: Poppler, Tesseract, pdfplumber, pdf2image y pytesseract.

## Requisitos

- Python 3.11 o superior.
- Node.js 20 o superior.
- MySQL/MariaDB local o XAMPP.
- Ollama instalado.
- Poppler y Tesseract para OCR.

## Variables de entorno

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configuración típica local:

```env
APP_NAME=CheckIA
APP_ENV=local
API_HOST=127.0.0.1
API_PORT=8000
FRONTEND_ORIGIN=http://localhost:5173

DB_ENABLED=true
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=checkia

OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=checkia-gemma
OLLAMA_FALLBACK_MODEL=gemma2:2b
OLLAMA_TIMEOUT_SECONDS=25
```

## Base de datos

Crear la base `checkia`:

```bash
mysql -u root -p < database/checkia.sql
```

Con XAMPP normalmente basta con usar:

```env
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=checkia
```

La base almacena siniestros, pólizas, asegurados, proveedores, documentos, textos extraídos, facturas, partes policiales, declaraciones de accidente, alertas, análisis de riesgo e historial del chat.

## Instalación del backend

Desde la raíz del proyecto:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Ejecutar API:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API local:

```text
http://127.0.0.1:8000
```

Verificación:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/system/status
```

## Instalación del frontend

```bash
cd frontend
npm install
npm run dev
```

Aplicación local:

```text
http://localhost:5173
```

Compilar para producción:

```bash
npm run build
```

## Ollama

Instalar o verificar Ollama:

```bash
ollama --version
```

Descargar modelo base:

```bash
ollama pull gemma2:2b
```

Crear modelo especializado de CheckIA:

```bash
ollama create checkia-gemma -f Modelfile
```

Probar Ollama:

```bash
curl http://localhost:11434/api/generate -d "{\"model\":\"gemma2:2b\",\"prompt\":\"Hola, responde en español.\",\"stream\":false}"
```

Si `checkia-gemma` no existe, el backend usa `OLLAMA_FALLBACK_MODEL=gemma2:2b` para que el agente siga funcionando.

## OCR y PDFs

CheckIA primero intenta extraer texto directo del PDF. Si el texto es insuficiente, usa OCR.

En Windows:

```powershell
winget install UB-Mannheim.TesseractOCR
```

Poppler puede instalarse manualmente o mantenerse en `tools/poppler` como en este proyecto.

En Ubuntu/VPS:

```bash
apt update
apt install -y tesseract-ocr tesseract-ocr-spa poppler-utils
```

Verificar:

```bash
tesseract --version
pdftoppm -v
```

## Uso de la aplicación

1. Abre la página **Datos**.
2. Verifica que MySQL, Backend, Ollama y OCR estén activos.
3. Sube el Excel completo con las hojas del reto.
4. Sube el lote de PDFs: facturas, declaraciones de accidente y partes policiales.
5. Revisa el dashboard y los gráficos.
6. Entra a **Casos** para ordenar, filtrar y abrir el detalle de un siniestro.
7. Consulta al **Agente IA** con preguntas como:

- ¿Qué documentos tiene el siniestro SIN-0022?
- ¿Por qué se prioriza SIN-0022?
- ¿Hay inconsistencias entre Excel y PDFs?
- ¿Qué proveedores concentran más alertas?
- ¿Qué casos tienen documentos faltantes?
- Genera un resumen ejecutivo.

## Dataset esperado

El Excel debe contener estas hojas:

- `1_Siniestros`
- `2_Polizas`
- `3_Asegurados`
- `4_Proveedores`
- `5_Documentos`

La hoja `README` es aceptada si existe, pero no es obligatoria para el análisis.

Los documentos PDF pueden venir en carpetas o lotes:

- Declaraciones de accidente: archivos tipo `DA_SIN-0378_DOC-0952.pdf`.
- Facturas: archivos tipo `Muestras_Facturas_Siniestros-SIN-0005.pdf`.
- Partes policiales: archivos tipo `PP_SIN-0005_DOC-0012.pdf`.

El sistema relaciona automáticamente por ID de siniestro, ID de documento, nombre de archivo y texto interno extraído.

## Score de riesgo

El score se calcula de forma explicable combinando:

- Riesgo del asegurado.
- Riesgo del proveedor.
- Estado de póliza.
- Reclamos previos.
- Documentos incompletos o faltantes.
- Inconsistencias entre Excel y PDFs.
- Montos reclamados frente a suma asegurada o promedio del proveedor.
- Similitud narrativa.
- Evidencia de documento alterado.
- Reporte tardío o fechas inconsistentes.

Rangos:

- 0 a 30: Bajo.
- 31 a 60: Medio.
- 61 a 80: Alto.
- 81 a 100: Crítico.

Toda alerta requiere revisión humana.

## Agente IA

El agente usa un enfoque híbrido:

1. El backend interpreta la pregunta.
2. Consulta MySQL, alertas, documentos y textos extraídos.
3. Prepara contexto compacto y trazable.
4. Ollama redacta una respuesta amable, breve o detallada según la pregunta.

El agente puede responder sobre:

- siniestros
- pólizas
- asegurados
- proveedores
- documentos asociados
- facturas
- declaraciones de accidente
- partes policiales
- OCR
- alertas
- ranking de riesgo
- resumen ejecutivo

Las respuestas deben indicar fuentes como Excel, PDF, OCR, factura, parte policial o declaración de accidente cuando aplique.

## Ética y limitaciones

CheckIA es un prototipo de apoyo a la revisión. No emite acusaciones, no decide pagos, no rechaza siniestros y no genera conclusiones legales. Los datos usados deben ser sintéticos o públicos y no deben contener información personal real o confidencial.

Mensaje base:

```text
Esta alerta no constituye una acusación de fraude. El caso requiere revisión humana antes de cualquier decisión.
```

## Comandos útiles

Backend:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Build:

```bash
cd frontend
npm run build
```

Pruebas:

```bash
python -m pytest backend/tests
```

Estado:

```bash
curl http://127.0.0.1:8000/api/system/status
```

## Despliegue básico en VPS

Instalar dependencias del servidor:

```bash
apt update
apt install -y python3-venv python3-pip nodejs npm nginx mysql-server tesseract-ocr tesseract-ocr-spa poppler-utils
```

Instalar Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma2:2b
ollama create checkia-gemma -f Modelfile
```

Preparar backend:

```bash
cd /opt/CheckIA
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Preparar frontend:

```bash
cd /opt/CheckIA/frontend
npm install
npm run build
```

Ejecutar backend para prueba:

```bash
cd /opt/CheckIA
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

En producción se recomienda configurar `systemd` para FastAPI, Nginx como proxy y SSL con Certbot.

## Demo sugerida

1. Mostrar **Estado del sistema** con MySQL, Ollama y OCR activos.
2. Importar el Excel del reto.
3. Subir PDFs de facturas, declaraciones y partes policiales.
4. Abrir Dashboard y mostrar distribución de riesgo.
5. Filtrar gráficos por riesgo, ciudad o proveedor.
6. Abrir un caso crítico y revisar documentos, alertas y explicación.
7. Preguntar al agente: “¿Por qué se prioriza SIN-0022?”.
8. Generar el reporte ejecutivo.

## Archivos que no se deben subir

No subas archivos temporales, ambientes locales ni paquetes de despliegue:

- `.env`
- `.venv/`
- `node_modules/`
- `frontend/dist/`
- `*.tar.gz`
- logs locales

