# Unión Central Voz — Predicción de Churn

Proyecto de ciencia de datos para la predicción del abandono de clientes (churn)
en una empresa ficticia del sector telecomunicaciones.

Desarrollado como caso práctico del Máster en Ciencia de Datos — UCV 2026.

---

## Contexto

Unión Central Voz (empresa ficticia) es una operadora de telecomunicaciones
residencial con 10.000 clientes activos. El proyecto analiza 36 meses de datos
(enero 2023 – diciembre 2025) para identificar los drivers del churn y construir
un modelo predictivo operativo.

**Resultado principal:** AUC = 0.7227 · Lift 3.49x en top 10% · 182 clientes
en riesgo alto identificados cada mes.

---

## Estructura del proyecto

```
UCV-Churn/
│
├── data/
│   ├── raw/                        # CSV originales (6 fuentes)
│   │   ├── clientes.csv
│   │   ├── churn_target.csv
│   │   ├── facturacion_mensual.csv
│   │   ├── interacciones_soporte.csv
│   │   ├── calidad_senal_zona_mensual.csv
│   │   └── encuestas_texto.csv
│   └── processed/                  # Datos limpios y panel final
│       ├── clientes_clean.csv
│       ├── facturacion_clean.csv
│       ├── soporte_clean.csv
│       ├── calidad_clean.csv
│       ├── encuestas_clean.csv
│       ├── churn_clean.csv
│       ├── dataset_final.csv
│       └── dataset_panel.csv       # Panel cliente-mes para modelado
│
├── notebooks/                      # Análisis exploratorio y modelos
│   │
│   ├── EDA_clientes_profesor.ipynb
│   ├── EDA_clientes_churn_profesor.ipynb
│   ├── EDA_Clientes_facturacion_churn.ipynb
│   ├── EDA_Cliente_Soporte_Churn.ipynb
│   ├── EDA_calidad_red.ipynb
│   ├── EDA_encuestas_nlp.ipynb
│   │
│   ├── modelo_churn_binario.ipynb   # Iteración 1 — baseline con leakage
│   ├── modelo_churn_temporal.ipynb  # Iteración 2 — modelo temporal sin leakage
│   ├── modelo_features.ipynb        # Iteración 3 — feature engineering
│   ├── modelo_features_v2.ipynb     # Iteración 4 — features V2
│   ├── modelo_mejoras.ipynb         # Iteración 5 — exploración de modelos
│   ├── modelo_mejoras_v2.ipynb      # Iteración 6 — código unificado
│   ├── Modelo_final.ipynb           # Análisis de negocio (modelo binario)
│   ├── Modelo_final_v2.ipynb        # Modelo segmentado por plan
│   └── modelo_final_v3.ipynb        # Modelo final: LightGBM, SHAP, Walk-Forward
│
├── src/                            # Pipeline modular
│   ├── load.py                     # Carga de CSVs y parseo de tipos
│   ├── clean.py                    # Limpieza y reglas de negocio
│   ├── features.py                 # Feature engineering y construcción del panel
│   └── utils.py                    # Funciones auxiliares compartidas
│
├── Docs/                           # Documentación del proyecto
│   ├── SPEC1_negocio.md            # Especificación de negocio (CRISP-DM fase 1)
│   ├── SPEC2_limpieza_calidad.md   # Especificación de calidad del dato
│   ├── SPEC3_eda.md                # Especificación de EDA
│   └── ...                         # Documentos del profesor
│
├── reports/
│   └── UCV_Churn_Dashboard.html    # Dashboard operativo interactivo
│
├── main.py                         # Orquestador del pipeline completo
├── requirements.txt                # Dependencias del proyecto
└── README.md                       # Este archivo
```

---

## Metodología

El proyecto sigue la metodología **CRISP-DM** de forma iterativa:

1. **Comprensión del negocio** — SPECs, hipótesis, KPIs
2. **Comprensión de los datos** — 6 EDAs independientes por fuente
3. **Preparación de datos** — pipeline modular load → clean → features
4. **Modelado** — 7 iteraciones de complejidad creciente
5. **Evaluación** — AUC-ROC, Walk-Forward Validation, curva de ganancia
6. **Despliegue** — Dashboard operativo + simulador de riesgo

---

## Especificaciones técnicas (SPECs)

Documentos de especificación formal en `Docs/`:

| Documento | Módulo | Contenido |
|-----------|--------|-----------|
| `SPEC1_negocio.md` | Business Analytics | Objetivos, KPIs, hipótesis, stakeholders |
| `SPEC2_limpieza_calidad.md` | Data Wrangling | Inventario de fuentes, nulos, duplicados, reglas |
| `SPEC3_eda.md` | EDA y Estadística | Balanceo, distribuciones, correlaciones, selección de variables |

---

## Evolución del modelo

| Iteración | AUC | Leakage | Descripción |
|-----------|-----|---------|-------------|
| Binario LR/RF | 0.991 | ✅ Sí | Baseline — detectado y documentado |
| Temporal LR base | 0.685 | ❌ No | Primer modelo honesto con LAG-1 |
| LR GridSearch | 0.690 | ❌ No | Tuning de hiperparámetros |
| LR + Features tendencia | 0.701 | ❌ No | racha_impagos, sin_consumo_2m |
| LR Features V2 | 0.703 | ❌ No | ratio_estres, critica_pendiente |
| LR Mejoras / V2 | 0.689-0.690 | ❌ No | Exploración exhaustiva de modelos |
| **Modelo Final V3** | **0.7227** | ❌ No | LightGBM + SHAP + Walk-Forward |

---

## Hallazgos principales

1. **La calidad de red es el driver más potente** — zonas con estrés Q4 tienen
   47% de churn vs 2.9% en Q1 (ratio 16x).

2. **La zona geográfica domina sobre el tipo de plan** — rural 33% de churn vs
   urbana premium 14.5%. Un cliente Premium en zona rural tiene más churn que
   un Prepago en zona urbana.

3. **El churn silencioso** — los churners contactan un 42.5% MENOS a soporte
   antes de irse. No se puede detectar con señales reactivas.

---

## Instalación y uso

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar el pipeline completo
python main.py

# 4. Explorar los notebooks en orden
# Empezar por los EDAs, luego los modelos en orden numérico
```

---

## Orden recomendado de lectura

**EDAs** (entender los datos):
1. `EDA_clientes_profesor.ipynb`
2. `EDA_clientes_churn_profesor.ipynb`
3. `EDA_Clientes_facturacion_churn.ipynb`
4. `EDA_Cliente_Soporte_Churn.ipynb`
5. `EDA_calidad_red.ipynb`
6. `EDA_encuestas_nlp.ipynb`

**Modelos** (evolución iterativa):
7. `modelo_churn_binario.ipynb` — baseline + detección de leakage
8. `modelo_churn_temporal.ipynb` — primer modelo honesto
9. `modelo_features.ipynb` — feature engineering
10. `modelo_features_v2.ipynb` — features V2
11. `modelo_mejoras.ipynb` — exploración de modelos
12. `modelo_mejoras_v2.ipynb` — código unificado
13. `Modelo_final.ipynb` — análisis de negocio
14. `Modelo_final_v2.ipynb` — modelo segmentado
15. `modelo_final_v3.ipynb` — **modelo definitivo**

---

## Dependencias principales

```
pandas · numpy · scikit-learn · xgboost · lightgbm · shap · lifelines
matplotlib · seaborn · jupyter
```

---

## Notas importantes

- **Leakage:** `n_meses_facturados` (r=−0.858 con target) excluida del modelo.
  Documentada en `src/features.py` con advertencia explícita.
- **Split temporal:** por cliente entero, nunca por fila.
- **Desbalance:** class_weight='balanced' obligatorio (ratio 1:160).
- **Umbral:** 5% (no 0.5) — calibrado según coste de negocio.

---

*Prácticas Aplicadas en Análisis de Datos 2026 · Máster en Ciencia de Datos · UCV*
