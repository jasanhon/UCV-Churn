# SPEC 1: ESPECIFICACIÓN DE NEGOCIO
**Módulo:** Business Analytics y Estrategia Corporativa

Documento que define el problema desde la perspectiva del negocio: qué queremos conseguir, cómo mediremos el éxito y qué haremos con los resultados. Es el contrato entre el equipo de Data Science y la empresa.

---

### 1. Contexto y Antecedentes

En el último año, el mercado de las telecomunicaciones residencial ha sufrido una agresiva guerra de precios por la entrada de nuevos operadores Low Cost. Unión Central Voz (UCV) ha experimentado un incremento notable en la pérdida de clientes (Churn), especialmente en el segmento Prepago y en zonas rurales con peor calidad de red.

La captación de un nuevo cliente es hasta 5 veces más costosa que retener a uno actual. Cada cliente que abandona supone dejar de ingresar ~128 euros/mes durante el tiempo que habría permanecido activo. Con una tasa de Churn mensual del 0.62% y una tasa acumulada de 20% en 3 años, la dirección general ha priorizado estabilizar la cartera antes de que afecte críticamente a los ingresos recurrentes.

El análisis histórico identifica tres focos principales del problema:

- **Zona rural:** 33% de churn acumulado frente al 14.5% en zonas urbanas premium (diferencia de 2.3x)
- **Segmento Prepago:** 26.2% de churn frente al 16.1% de clientes Premium
- **Calidad de red:** en zonas con alto estrés de red (Q4), la tasa de churn alcanza el 47%

---

### 2. Objetivo de Negocio

El objetivo principal es desarrollar un sistema analítico que identifique proactivamente, cada mes, qué clientes tienen mayor probabilidad de abandonar la compañía en los próximos 30 días. Esto permitirá al equipo comercial actuar antes de que el cliente inicie el proceso de portabilidad, protegiendo los ingresos recurrentes y optimizando el presupuesto de retención.

Objetivos secundarios:

- Identificar los segmentos de mayor riesgo (Prepago, zonas rurales) para priorizar la inversión en retención e infraestructura de red
- Cuantificar el impacto económico esperado de las campañas de retención
- Sentar las bases para una aplicación comercial con alertas diarias para el equipo de ventas
- Proporcionar al equipo de red información sobre qué zonas generan más churn por calidad de servicio

---

### 3. KPIs y Métricas de Éxito

**Métricas de negocio:**

| KPI | Valor Actual | Objetivo |
|-----|-------------|----------|
| Tasa de Churn mensual | 0.62% | < 0.45% en 2 trimestres |
| Tasa de Churn acumulada (3 años) | 20.0% | < 15.0% |
| Tasa Churn zona rural | 33.0% | < 25.0% |
| Tasa Churn segmento Prepago | 26.2% | < 20.0% |

**Métricas financieras:**

- **ROI de campañas:** > 15% — evitar regalar descuentos a clientes que no se iban a ir
- **Ingreso protegido:** cada cliente retenido representa ~128 euros/mes × meses de vida adicional estimada
- **LTV (Customer Lifetime Value):** incrementar el LTV medio de la cartera en un 12% en 12 meses

**Métricas de eficiencia del modelo:**

- **AUC-ROC:** > 0.70 en modelo temporal sin leakage (umbral mínimo para producción)
- **Lift en top 10%:** > 3x respecto a selección aleatoria de clientes
- **Tasa real de churn en grupo Alto riesgo:** > 2.5% (vs 0.62% de media global)

---

### 4. Definición de Operaciones / Reglas de Negocio

**Definición exacta de Churn:**

Se considera Churn a cualquier cliente que:
- Solicite la baja voluntaria total de sus servicios
- Complete una portabilidad saliente hacia otra compañía
- No renueve su contrato al vencimiento (solo aplica a contratos con permanencia)

**Exclusiones — no se considerará Churn:**

- Bajas forzosas por impago prolongado (fraude o insolvencia declarada)
- Suspensiones temporales del servicio solicitadas por el cliente
- Cambios de titularidad dentro del mismo hogar
- Clientes corporativos o B2B

**Ventana de predicción:**

- **Horizonte temporal:** 30 días — predecir si el cliente abandona el mes siguiente
- **Frecuencia de scoring:** mensual, el primer día hábil de cada mes
- **Datos de entrada:** información disponible hasta el último día del mes anterior (lag 1 obligatorio para evitar leakage)
- **Unidad de predicción:** par cliente-mes

**Umbrales de acción definidos con el negocio:**

| Probabilidad predicha | Nivel | Acción |
|---|---|---|
| > 5% | Alto | Llamada telefónica prioritaria esta semana |
| 2% - 5% | Medio | Campaña email/SMS automatizada |
| < 2% | Bajo | Sin acción — monitoreo pasivo mensual |

---

### 5. Hipótesis de Negocio

**H1 — Los clientes sin permanencia contractual (Prepago) presentan mayor tasa de abandono**

Hipótesis: la ausencia de compromiso contractual reduce las barreras de salida y hace al cliente más sensible a ofertas de la competencia. Esperamos que Prepago tenga el doble de churn que Premium.

Resultado validado: Prepago 26.2% vs Premium 16.1% vs Contrato 21.4%. Test Chi-cuadrado significativo (p ≈ 0, V de Cramér = 0.108). **CONFIRMADA.**

**H2 — La mala calidad de la red es el principal driver del churn, especialmente en zonas rurales**

Hipótesis: los clientes rurales abandonan principalmente porque la infraestructura de red es inferior. Si esto es cierto, la inversión en mejora de red reducirá el churn más que los descuentos.

Resultado validado: stress_calidad_lag es la variable más potente del modelo. Q4 alto stress → 47% de churn vs Q1 bajo stress → 2.9%. Correlación NPS zonal vs tasa de churn: r = -0.79. **CONFIRMADA.**

**H3 — Los clientes con historial de impago frecuente tienen mayor riesgo inminente de abandono**

Hipótesis: el impago no es solo un problema financiero, sino una señal de desenganche progresivo. Un cliente que lleva 3 meses consecutivos sin pagar está preparando su salida.

Resultado validado: racha_impagos_lag1 es la 3ª variable más importante del modelo temporal. Clientes en Q4 de % meses con impago tienen 41.9% de churn vs 15.5% en Q1. **CONFIRMADA.**

---

### 6. Alcance y Limitaciones

**Dentro del alcance:**

- Clientes particulares (B2C) activos en territorio nacional
- Clientes con al menos 1 mes de antigüedad
- Contratos de fibra, ADSL o líneas móviles de prepago/pospago
- Datos históricos: enero 2023 — diciembre 2025 (36 meses)
- 10.000 clientes únicos en la cartera residencial analizada

**Fuera del alcance:**

- Clientes corporativos o empresas (B2B): sus contratos llevan negociaciones personalizadas que distorsionan el comportamiento del churn residencial
- Bajas involuntarias por impago o fraude
- Predicción de churn a más de 30 días vista
- Clientes con menos de 1 mes de antigüedad (sin historial para aplicar lags)

**Limitaciones conocidas:**

- El churn tiene una componente aleatoria (ofertas puntuales de la competencia, cambios personales) que ningún modelo puede capturar. AUC teórico máximo estimado entre 0.78 y 0.80
- Las encuestas de satisfacción son anónimas por zona, no por cliente individual
- La calidad de red se mide por zona geográfica, no por domicilio exacto del cliente
- El modelo no distingue entre churn definitivo y portabilidad temporal

---

### 7. Acciones y Decisiones Derivadas

El output del modelo (probabilidad de churn de 0 a 1) se integra en el CRM de la compañía para disparar acciones diferenciadas según el nivel de riesgo y el valor del cliente:

**Riesgo Alto + Cliente Premium (prob > 5%, ingreso > 3.500 euros):**
Alerta prioritaria para el Call Center de Retención. Oferta: renovación de terminal gratuita o descuento del 30% en factura con permanencia de 12 meses.

**Riesgo Alto + Cliente Estándar (prob > 5%, ingreso ≤ 3.500 euros):**
Envío automatizado de campaña email/SMS. Oferta: mejora de servicios sin coste adicional (más GB de datos o subida de velocidad de fibra).

**Riesgo Medio (2-5% prob):**
Inclusión en campaña mensual de fidelización pasiva. Newsletter con ventajas exclusivas de permanencia.

**Aplicación comercial diaria — el primer día hábil de cada mes el modelo genera:**

1. Lista priorizada de clientes a contactar, ordenada por probabilidad × ingreso estimado
2. Perfil de riesgo con los 3 factores que más contribuyen al score de cada cliente
3. Acción recomendada y guión de retención sugerido al agente
4. Formulario de registro: fecha de contacto, resultado, observaciones, oferta aceptada o rechazada

---

### 8. Stakeholders y Usuarios Finales

| Rol | Área | Interés principal |
|-----|------|------------------|
| Sponsor del proyecto | Dirección de Marketing y Clientes | ROI de retención, cuota de mercado |
| Product Owner | Jefe de Fidelización | Lista diaria de clientes a contactar |
| Usuarios finales | Agentes del Call Center de Retención | Score y guión de cada cliente |
| Seguimiento | Equipo de Business Intelligence (BI) | Dashboard de KPIs mensual |
| Equipo técnico | Data Science (nosotros) | Mantenimiento y reentrenamiento del modelo |
| Infraestructura | Equipo TI / CRM | Integración del modelo en producción |

---
*SPEC 1 — UCV-Churn | Prácticas Aplicadas 2026*
