# SPEC 2: LIMPIEZA Y CALIDAD DEL DATO
**Módulo:** Data Wrangling, Gobernanza y Calidad del Dato

Aquí se define la estrategia de "fontanería" de datos para asegurar que no metemos basura en el modelo (Garbage In, Garbage Out). Cada decisión de limpieza está justificada con una regla de negocio o un criterio estadístico — nunca se limpia por intuición.

---

### 1. Inventario de Fuentes de Datos

El proyecto integra 6 fuentes de datos procedentes de distintos sistemas corporativos:

| Archivo | Sistema Origen | Filas | Granularidad | Período |
|---------|---------------|-------|-------------|---------|
| clientes.csv | CRM Corporativo | 10.150 | 1 fila / cliente | Estático |
| churn_target.csv | Sistema de Bajas | 321.987 | 1 fila / cliente-mes | Ene 23 - Dic 25 |
| facturacion_mensual.csv | ERP Facturación | 326.816 | 1 fila / cliente-mes | Ene 23 - Dic 25 |
| interacciones_soporte.csv | CRM Soporte | 308.487 | 1 fila / interacción | Ene 23 - Dic 25 |
| calidad_senal_zona_mensual.csv | Sistema de Red | 1.096 | 1 fila / zona-mes | Ene 23 - Dic 25 |
| encuestas_texto.csv | Plataforma Encuestas | 1.015 | 1 fila / zona-mes | Ene 23 - Dic 25 |

**Nota sobre granularidad:** las 4 primeras fuentes operan a nivel de cliente, mientras que las 2 últimas operan a nivel de zona geográfica. La unión entre niveles se realiza a través de zona_id presente en clientes.csv.

---

### 2. Identificación de Claves Primarias y Relaciones

**Claves primarias por tabla:**

| Tabla | Clave Primaria | Unicidad esperada |
|-------|---------------|------------------|
| clientes.csv | cliente_id | 1:1 — un registro por cliente |
| churn_target.csv | (cliente_id, fecha) | 1:1 — un registro por cliente y mes |
| facturacion_mensual.csv | (cliente_id, fecha) | 1:1 — un registro por cliente y mes |
| interacciones_soporte.csv | interaccion_id | 1:1 — un registro por interacción |
| calidad_senal_zona_mensual.csv | (zona_id, fecha) | 1:1 — un registro por zona y mes |
| encuestas_texto.csv | encuesta_id | 1:1 |

**Diagrama de relaciones:**

```
clientes.csv  (cliente_id, zona_id)
    |
    |-- churn_target.csv            JOIN ON cliente_id + fecha (mes)
    |-- facturacion_mensual.csv     JOIN ON cliente_id + fecha (mes)
    |-- interacciones_soporte.csv   JOIN ON cliente_id + mes
    |
    +-- zona_id --> calidad_senal_zona_mensual.csv  JOIN ON zona_id + fecha
                    encuestas_texto.csv              JOIN ON zona_id + fecha
```

**Tipo de joins:** LEFT JOIN desde churn_target como tabla base para conservar todos los registros cliente-mes independientemente de si tienen datos en las otras fuentes.

**Integridad referencial verificada:**
- Los 10.000 clientes únicos aparecen en las 6 tablas sin huérfanos
- 27 clientes nunca tuvieron interacciones de soporte — es válido, no es un error
- Encuestas y calidad de red no tienen cliente_id directo, se unen via zona_id

---

### 3. Análisis de Valores Nulos y Estrategia

**clientes.csv:**

| Variable | Nulos | % | Estrategia |
|----------|-------|---|-----------|
| edad | 305 | 3.0% | Mantener como NaN — imputar con mediana en el pipeline de modelado, no en limpieza |
| ingreso_estimado | 304 | 3.0% | Igual |
| antiguedad_meses | 305 | 3.0% | Igual — además tiene negativos (ver punto 6) |
| estado_civil | 79 | 0.8% | Mantener NaN — el encoder lo tratará como categoría "desconocido" |
| sexo | 45 | 0.4% | Igual |

**facturacion_mensual.csv:**

| Variable | Nulos | % | Estrategia |
|----------|-------|---|-----------|
| importe_total | 9.799 | 3.0% | Mantener NaN — posibles errores del sistema de facturación. No imputar: inventar un importe distorsionaría el modelo |
| tipo_plan | 9.816 | 3.0% | Imputar con el plan más frecuente del cliente en otros meses |

**interacciones_soporte.csv:**

| Variable | Nulos | % | Estrategia |
|----------|-------|---|-----------|
| satisfaccion_post | 4.629 | 1.5% | Mantener NaN — el cliente no siempre valora la interacción. Es un dato válido |
| motivo | 4.640 | 1.5% | Asignar categoría "Desconocido" |

**Regla general:** en EDA, trabajar con los nulos sin imputar para descubrir patrones reales. En modelado, SimpleImputer(median) para numéricas y fill_value='desconocido' para categóricas. La imputación es responsabilidad del pipeline de modelado, no de clean.py.

---

### 4. Gestión de Duplicados

**Duplicados detectados y criterio de resolución:**

| Tabla | Tipo | Cantidad | Criterio |
|-------|------|----------|---------|
| clientes.csv | Exactos (todas las columnas iguales) | 150 | drop_duplicates() — conservar primera ocurrencia |
| churn_target.csv | Exactos | ~2.000 | drop_duplicates() |
| facturacion_mensual.csv | Exactos | 4.829 | drop_duplicates() |
| interacciones_soporte.csv | Exactos | 4.558 | drop_duplicates() |
| calidad_senal_zona_mensual.csv | Exactos | 16 | drop_duplicates() |
| encuestas_texto.csv | Exactos | 15 | drop_duplicates() |

**Regla general:** los duplicados exactos (todas las columnas idénticas) son siempre errores de exportación del sistema fuente y se eliminan sin excepción. Para duplicados por clave primaria con valores distintos en otras columnas, se conserva la primera ocurrencia (keep='first') y se registra en el log de limpieza.

**Resultado tras limpieza de clientes.csv:** 10.150 → 10.000 filas (150 duplicados exactos eliminados).

---

### 5. Formateo y Tipado de Datos

**Problema identificado en fechas:**
Las columnas de fecha contienen formatos mixtos en el mismo archivo (YYYY-MM-DD y DD/MM/YYYY simultáneamente). Se resuelve con:

```python
pd.to_datetime(df['fecha'], format='mixed', dayfirst=True)
```

**Conversiones numéricas:**

```python
# Variables que llegan como string por errores de exportación
df['antiguedad_meses'] = pd.to_numeric(df['antiguedad_meses'], errors='coerce')
df['ingreso_estimado'] = pd.to_numeric(df['ingreso_estimado'], errors='coerce')
```

**Normalización de strings en variables categóricas:**

```python
# Estandarización de planes (evitar duplicidad por capitalización)
df['tipo_plan'] = df['tipo_plan'].str.strip().str.title()
# Resultado: 'prepago', 'PREPAGO', 'Prepago' → todos quedan como 'Prepago'

# Corrección de errores tipográficos en tipo_zona
df['tipo_zona'] = df['tipo_zona'].replace({
    'suburbanx': 'suburbana',
    'urbana??':  'urbana_premium',
    'rural-1':   'rural'
})
```

**Principio de responsabilidades:**
- load.py: únicamente parsea fechas y tipos básicos. NO limpia datos de negocio.
- clean.py: aplica todas las reglas de negocio y correcciones de formato.

---

### 6. Tratamiento de Outliers / Valores Atípicos

**Metodología:** combinación de reglas de dominio (rangos físicamente posibles) y método IQR estándar (Q1 - 1.5×IQR, Q3 + 1.5×IQR) para variables sin límites naturales conocidos. Implementado en src/utils.py con la función iqr_outlier_mask().

**Outliers detectados y decisión:**

| Variable | Problema | Cantidad | Decisión | Justificación |
|----------|---------|---------|---------|--------------|
| antiguedad_meses | Valores negativos | 145 (mín = -110) | Normalizar a 0 | Imposible físicamente — error de migración de fechas de alta |
| edad | Fuera de rango [18, 100] | Pequeño | Marcar como NaN | Fuera del rango de clientes residenciales válidos |
| dias_retraso_pago | Máximos extremos > 1.000 días | Puntual | Mantener | Dato real aunque extremo — no eliminar señal legítima |
| consumo_extra | Negativos (abonos y correcciones) | 3.684 | Mantener | Son devoluciones legítimas del sistema de facturación |
| latencia_ms | > 200ms | 15 | Marcar como NaN | Imposible en una red operativa normal — error del sensor |
| velocidad_media_mbps | Negativos | 16 | Marcar como NaN | Imposible físicamente |
| cobertura_*_pct | Fuera de [0, 100] | Pequeño | Marcar como NaN | Fuera del rango válido de un porcentaje |
| puntuacion_general_1a5 | > 5 | 14 | Marcar como NaN | Fuera de la escala de la encuesta |
| nps_0a10 | > 10 | 9 | Marcar como NaN | Fuera de la escala NPS estándar |
| duracion_min (soporte) | > 300 minutos | Puntual | Marcar como NaN | Una llamada de más de 5 horas es un error de registro |

---

### 7. Reglas de Consistencia Lógica

**Regla 1 — Antigüedad vs fecha de análisis:**
```
antiguedad_meses >= 0 siempre
Si fecha_alta > fecha_analisis → error de sistema → normalizar a 0
```

**Regla 2 — Churn vs número de observaciones:**
```
Si ever_churn = 1 → n_meses_observados < 36 (el cliente se fue antes del final)
Si ever_churn = 0 → n_meses_observados ≈ 36 (permanece todo el período)
Excepción válida: clientes dados de alta después de enero 2023
```

**Regla 3 — Variables de red dentro de rango:**
```
0 ≤ cobertura_4g_pct ≤ 100
0 ≤ cobertura_5g_pct ≤ 100
0 ≤ tasa_cortes_pct ≤ 100
latencia_ms > 0
velocidad_media_mbps > 0
```

**Regla 4 — Escalas de valoración:**
```
1 ≤ satisfaccion_post ≤ 5
1 ≤ puntuacion_general_1a5 ≤ 5
0 ≤ nps_0a10 ≤ 10
churn ∈ {0, 1} — cualquier otro valor se elimina
```

**Regla 5 — Canales de soporte válidos:**
```
canal ∈ {telefono, app_chat, email, tienda}
Valores detectados fuera de catálogo: carrier-pigeon, paloma, fax
Decisión: mantener con flag de calidad documentado — su tasa de resolución
es similar a los canales válidos y no distorsionan el análisis general
```

---

### 8. Transformación Inicial de Variables

**Variable objetivo — codificación binaria:**

```python
# Nivel mensual (modelo temporal — unidad: cliente-mes)
churn_target['churn'] = churn_target['churn'].astype(int)  # ya es 0/1

# Nivel cliente (modelo binario — unidad: cliente)
ever_churn = (churn_target
    .groupby('cliente_id')['churn']
    .max()
    .reset_index(name='ever_churn'))
# ever_churn = 1 si el cliente abandonó al menos una vez en los 36 meses
```

**Codificación de variables categóricas:**

```python
# Variables nominales (sin jerarquía natural) → OneHotEncoder con drop='first'
# tipo_zona:  [rural, suburbana, urbana_premium] → 2 columnas binarias
# region:     [Norte, Sur, Este, Oeste, Centro]  → 4 columnas binarias
# drop='first' evita multicolinealidad perfecta

# Variable ordinal (con jerarquía real) → codificación manual
panel['tipo_plan_enc'] = panel['tipo_plan'].map(
    {'Prepago': 1, 'Contrato': 2, 'Premium': 3}
).fillna(2)
# Prepago=1 < Contrato=2 < Premium=3 refleja la jerarquía real de valor
```

**Transformación anti-leakage — lags temporales:**

```python
# Para predecir churn en el mes T, solo se puede usar información del mes T-1
# Se aplica shift(1) por cliente ordenado cronológicamente
impago_mes_lag1 = factura.groupby('cliente_id')['impago_flag'].shift(1)
stress_mes_lag1 = factura.groupby('cliente_id')['stress_calidad_lag'].shift(1)
# El primer mes de cada cliente queda sin lag y se elimina del panel
panel = panel.dropna(subset=['impago_mes_lag1'])
```

**Variable excluida por leakage crítico:**

n_meses_facturados tiene correlación r = -0.858 con ever_churn. Un cliente que abandonó en el mes 6 tiene 6 meses facturados y uno activo tiene 36. El modelo aprendería una consecuencia del churn, no una causa. **EXCLUIDA del modelo. Documentada en features.py con advertencia explícita.**

---
*SPEC 2 — UCV-Churn | Prácticas Aplicadas 2026*
