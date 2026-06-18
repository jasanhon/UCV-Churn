# SPEC 3: EDA (ANÁLISIS EXPLORATORIO DE DATOS)
**Módulo:** Análisis Exploratorio de Datos y Técnicas Estadísticas

La hoja de ruta de los gráficos y análisis estadísticos realizados en los notebooks de EDA para exprimir los datos. Cada análisis parte de una hipótesis formulada antes de mirar los datos — no se buscan patrones a posteriori.

---

### 1. Análisis del Balanceo de la Variable Objetivo

**Nivel cliente — modelo binario (ever_churn):**

| Clase | N | % |
|-------|---|---|
| No Churn (0) | 8.000 | 80.0% |
| Churn (1) | 2.000 | 20.0% |

Desbalance moderado 4:1 — manejable con class_weight='balanced' en sklearn.

**Nivel cliente-mes — modelo temporal (churn mensual):**

| Clase | N | % |
|-------|---|---|
| No Churn (0) | 319.987 | 99.38% |
| Churn (1) | 2.000 | 0.62% |

Desbalance severo 1:160. Consecuencias directas para el diseño del modelo:

- Un clasificador que prediga siempre "no churn" alcanzaría accuracy del 99.38% — métrica completamente inútil para el negocio
- Se requiere class_weight='balanced' o scale_pos_weight=160 en XGBoost
- El umbral de decisión óptimo NO es 0.5 — requiere calibración según coste de negocio
- **Métrica correcta de evaluación: AUC-ROC** — independiente del umbral, mide la capacidad del modelo de ordenar clientes por riesgo

---

### 2. Estudio Distribucional Univariante (Variables Numéricas)

**Estadísticos descriptivos de las variables más relevantes:**

| Variable | Media | Mediana | Std | Rango real | Nulos |
|----------|-------|---------|-----|------------|-------|
| edad | 39.3 | 39.0 | 12.1 | 18-80 | 3.0% |
| ingreso_estimado | 3.479€ | 3.219€ | 1.247€ | 900-12.000€ | 3.0% |
| antiguedad_meses | 32.6 | 32.0 | 18.4 | 0-120 | 3.0% |
| importe_total | 127€ | 110€ | 68€ | 11-484€ | 3.0% |
| dias_retraso_pago | 4.1 | 0 | 28.3 | 0-1.100 | 0% |
| stress_calidad_lag | 0.40 | 0.43 | 0.14 | 0-0.80 | 0% |
| consumo_extra | 6.89€ | 0€ | 22.4€ | -50 a 380€ | 0% |

**Hallazgos univariantes clave:**

- **ingreso_estimado:** cola derecha pronunciada (media > mediana) — distribución no normal → usar tests no paramétricos
- **dias_retraso_pago:** el 89.7% de los registros vale 0 (pago puntual). Distribución muy asimétrica con cola extrema hasta 1.100 días
- **consumo_extra:** el 25.1% de los meses tiene valor 0 — señal de posible desenganche del servicio
- **stress_calidad_lag:** distribución bimodal con concentraciones en valores bajos (zonas urbanas) y altos (zonas rurales)

---

### 3. Análisis de Frecuencias (Variables Categóricas)

**tipo_plan:**

| Valor | N | % |
|-------|---|---|
| Premium | 5.062 | 50.6% |
| Prepago | 2.680 | 26.8% |
| Contrato | 2.258 | 22.6% |

**tipo_zona:**

| Valor | N | % | Nota |
|-------|---|---|------|
| urbana_premium | 4.485 | 44.8% | — |
| suburbana | 4.023 | 40.2% | — |
| rural | 1.492 | 14.9% | — |
| Valores erróneos | 16 | 0.2% | suburbanx, urbana??, rural-1 → corregidos en clean.py |

**canal (soporte):**

| Valor | N | % |
|-------|---|---|
| telefono | 137.187 | 44.5% |
| app_chat | 106.171 | 34.4% |
| tienda | 36.251 | 11.7% |
| email | 24.240 | 7.9% |
| Canales inválidos | 4.638 | 1.5% — carrier-pigeon, paloma, fax |

El motivo de soporte más frecuente es "Calidad de señal" (20.4%) — consistente con el hallazgo de que la red es el principal driver del churn.

---

### 4. Análisis Bivariante Numérico vs Target

**Tests utilizados:** Mann-Whitney U (no asume normalidad, robusto ante outliers). Es la alternativa no paramétrica al t-test para comparar dos grupos independientes.

| Variable | Mediana No Churn | Mediana Churn | p-valor | Efecto |
|----------|-----------------|--------------|---------|--------|
| ingreso_estimado | 3.339€ | 2.844€ | ≈0 *** | -14.8% en churners |
| antiguedad_meses | 31.0 | 25.0 | ≈0 *** | -19.4% en churners |
| importe_medio | 128.6€ | 114.7€ | ≈0 *** | -10.8% en churners |
| pct_meses_impago | 10.0% | 14.8% | ≈0 *** | +48.0% en churners |
| dias_retraso_medio | 3.2 d | 5.1 d | ≈0 *** | +59.4% en churners |
| stress_medio | 0.387 | 0.458 | ≈0 *** | +18.3% en churners |
| n_interacciones | 33.7 | 19.4 | ≈0 *** | -42.5% en churners |
| num_lineas | 2.0 | 2.0 | 0.09 ns | Sin diferencia significativa |
| edad | 39.0 | 40.0 | 0.000 *** | Significativo pero efecto de 1 año — irrelevante |

**Hallazgo destacado — stress de red por cuartil:**

| Cuartil | Rango | Tasa Churn |
|---|---|---|
| Q1 (bajo) | 0.00 - 0.28 | 2.9% |
| Q2 | 0.28 - 0.43 | 27.1% |
| Q3 | 0.43 - 0.44 | 2.5% (anomalía: rango muy estrecho) |
| Q4 (alto) | 0.44 - 0.69 | **47.0%** |

El salto de Q1 (2.9%) a Q4 (47.0%) es el hallazgo más potente del proyecto.

---

### 5. Análisis Bivariante Categórico vs Target

**Tests utilizados:** Chi-cuadrado de independencia + V de Cramér (mide la fuerza de la asociación en rango 0 a 1).

| Variable | Chi2 | p-valor | V Cramér | Interpretación |
|----------|------|---------|---------|----------------|
| tipo_zona | 247.3 | ≈0 | **0.157** | Asociación alta — predictor categórico más potente |
| tipo_plan | 117.0 | ≈0 | **0.108** | Asociación media-alta |
| tipo_dispositivo | 70.4 | ≈0 | 0.084 | Asociación media (proxy de ingreso) |
| region | 28.4 | ≈0 | 0.053 | Asociación débil |
| descuento_activo | 10.9 | 0.001 | 0.033 | Asociación muy débil |
| estado_civil | 13.3 | 0.004 | 0.037 | Asociación muy débil |
| **sexo** | **0.9** | **0.831** | **0.009** | **SIN asociación — excluir del modelo** |

**Tasas de churn por segmento:**

Por tipo_zona: Rural **33.0%** / Suburbana **21.4%** / Urbana premium **14.5%**

Por tipo_plan: Prepago **26.2%** / Contrato **21.4%** / Premium **16.1%**

**Cruce zona × plan — hallazgo de dominancia geográfica:**

| Zona | Contrato | Premium | Prepago |
|---|---|---|---|
| Rural | 32.8% | 29.3% | 35.8% |
| Suburbana | 20.2% | 18.6% | 26.0% |
| Urbana Premium | 17.1% | 12.6% | 19.0% |

La zona domina sobre el plan: Premium en rural (29.3%) tiene más churn que Prepago en urbana (19.0%). El entorno geográfico supera al tipo de contrato como predictor del abandono.

---

### 6. Matriz de Correlación y Colinealidad

**Correlaciones relevantes entre variables numéricas:**

| Par de Variables | Correlación | Implicación para el modelo |
|-----------------|-------------|--------------------------|
| poblacion_zona ↔ ingreso_estimado | +0.356 | Colinealidad moderada — mantener ambas |
| poblacion_zona ↔ num_lineas | +0.340 | Colinealidad moderada |
| edad ↔ poblacion_zona | -0.219 | Colinealidad débil |
| stress_medio ↔ calidad_global | ≈ -0.780 | Colinealidad alta — usar ratio combinado |
| **n_meses_facturados ↔ ever_churn** | **-0.858** | **LEAKAGE CRÍTICO — excluir obligatoriamente** |
| antiguedad_meses ↔ cualquier variable | < 0.037 | Variable independiente, sin colinealidad |

**Tratamiento de colinealidad:**

- stress_calidad_lag y calidad_global_mes tienen r ≈ -0.78. Se crea ratio_estres_lag1 = (dias_retraso + 1) / (calidad_global + 1) que combina ambas señales en una variable más informativa
- La regularización L1 (Lasso) en el modelo final actúa como selector automático, forzando a cero los coeficientes de variables redundantes

---

### 7. Segmentación y Análisis Multivariante

**Segmento de máximo riesgo identificado:**

La combinación de tipo_zona=rural + tipo_plan=Prepago + stress Q4 + antigüedad < 24 meses + % meses con impago > 20% produce tasas de churn estimadas superiores al 40%.

**Top 5 zonas más críticas (datos reales):**

| Zona | Región | Tipo | Tasa Churn | Stress Medio |
|------|--------|------|-----------|-------------|
| Z19 | Este | Rural | 39.4% | 0.661 |
| Z07 | Centro | Rural | 37.6% | 0.645 |
| Z03 | Sur | Rural | 36.2% | 0.658 |
| Z06 | Sur | Rural | 35.2% | 0.649 |
| Z01 | Centro | Rural | 34.9% | 0.647 |

Correlación stress_medio vs tasa_churn por zona: **r = +0.79** — muy alta.

**Validación de hipótesis de multicausalidad:**

La variable ratio_estres_lag1 = (dias_retraso + 1) / (calidad_global + 1) muestra mayor separación entre churners y no churners que cada componente por separado. Un cliente que paga tarde Y tiene mala red tiene probabilidad de churn mucho mayor que cualquiera de esos factores individualmente — la combinación es sinérgica, no aditiva.

**Hallazgo del churn silencioso:**

Los churners contactan a soporte un 42.5% MENOS que los no churners (mediana 17 vs 32 interacciones). El churn no se anuncia: los clientes que abandonan simplemente se van sin avisar. La señal útil no está en más llamadas sino en la ausencia de contacto combinada con señales económicas (impago) y técnicas (stress de red).

**Correlación NPS zonal vs tasa de churn:** r = -0.79. Las encuestas de satisfacción a nivel zonal predicen el churn con correlación muy alta — el sentimiento colectivo del entorno del cliente es una señal real, no ruido.

---

### 8. Conclusiones Preliminares y Selección de Variables

**Variables descartadas con justificación estadística:**

| Variable | Motivo | Evidencia |
|----------|--------|---------|
| sexo | Sin poder predictivo | V Cramér=0.009, p=0.831 |
| n_meses_facturados | Leakage crítico | r=-0.858 — consecuencia del churn, no causa |
| duracion_min (soporte) | Sin diferencia entre grupos | p=0.261 |
| canal (soporte) | Sin diferencia entre grupos | Todas las tasas ≈ 12.6% |
| flag_incongruente (encuestas) | Sin señal útil | r=-0.027 con churn zonal |
| estado_civil | Efecto demasiado pequeño | V=0.037 |

**Variables candidatas para el modelo — ordenadas por importancia validada:**

**Grupo 1 — Señales de red (muy alta importancia):**
stress_mes_lag1, stress_mes_roll3, calidad_global_lag1, tasa_cortes_lag1, ratio_estres_lag1

**Grupo 2 — Señales de pago (muy alta importancia):**
impago_mes_lag1, impago_mes_roll3, racha_impagos_lag1, dias_retraso_mes_lag1

**Grupo 3 — Perfil estático del cliente (alta importancia):**
antiguedad_meses, ingreso_estimado, importe_mes_lag1, tipo_plan_enc, tipo_zona, region

**Grupo 4 — Señales de soporte (importancia media):**
n_interacciones_mes_lag1, critica_pendiente_lag1, n_baja_mes_lag1

**Grupo 5 — Señales de percepción zonal (importancia moderada):**
sentimiento_zonal_lag1, cobertura_5g_lag1

**Variables excluidas del modelo temporal por exceso de nulos:**

satisfaccion_mes_lag1 y resolucion_mes_lag1 tienen más del 90% de nulos (solo meses con soporte activo). Si se incluyeran, el SimpleImputer estaría imputando la mediana en el 90% de los valores — la variable sería prácticamente artificial. Se excluyen del modelo temporal.

---
*SPEC 3 — UCV-Churn | Prácticas Aplicadas 2026*
