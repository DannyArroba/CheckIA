# Pitch CheckIA - 10 Minutos

## 1. Problema

Las aseguradoras reciben muchos siniestros y no todos pueden revisarse con la misma profundidad. El reto es priorizar los casos que muestran señales de posible riesgo sin afectar la experiencia del asegurado ni tomar decisiones injustas.

## 2. Solución CheckIA

CheckIA analiza siniestros sintéticos, calcula un score de 0 a 100 y clasifica los casos en verde, amarillo o rojo. La herramienta explica por qué un caso requiere revisión humana y evita lenguaje acusatorio.

## 3. Demo

- Mostrar dashboard con total de siniestros, montos, semáforo y gráficas.
- Abrir Casos y filtrar por riesgo alto.
- Entrar al detalle de un siniestro.
- Mostrar reglas activadas, factores y mensaje ético.
- Consultar al Agente IA: top 10 de mayor riesgo y proveedores con alertas.
- Mostrar Reporte Ejecutivo y exportación JSON.

## 4. Arquitectura e IA

Backend FastAPI con pandas y scikit-learn. Frontend React/Vite con Tailwind y Recharts. El score combina reglas explicables 70%, modelo IA/anomalías 20% y NLP 10%.

## 5. Impacto

CheckIA reduce tiempo de priorización, mejora trazabilidad, ayuda a concentrar esfuerzos de analistas y crea una base para gobierno de decisiones asistidas.

## 6. Ética

La app no acusa fraude, no rechaza reclamos y no toma decisiones legales. Toda alerta requiere revisión humana.

## 7. Próximos Pasos

- Validar reglas con expertos de siniestros.
- Integrar datos reales anonimizados.
- Medir sesgos y calibración.
- Crear auditoría de decisiones.
- Integrar flujos de gestión documental.
