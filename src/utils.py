"""
src/utils.py
------------
Funciones auxiliares compartidas por todos los notebooks de análisis.

Centralizar aquí evita copiar el mismo código en cada EDA.
Importar con:
    from src.utils import missing_summary, iqr_outlier_mask, cramers_v
"""

import numpy as np
import pandas as pd
from scipy import stats


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resumen de valores nulos por columna.

    Para cada columna devuelve:
    - n_missing:   número de valores ausentes
    - pct_missing: porcentaje sobre el total de filas
    - dtype:       tipo de dato de la columna

    Ordenado de mayor a menor nulos para ver rápido los problemas.

    Uso:
        missing_summary(df)
    """
    summary = pd.DataFrame({
        'n_missing':   df.isna().sum(),
        'pct_missing': df.isna().mean() * 100,
        'dtype':       df.dtypes.astype(str),
    })
    return summary.sort_values(['n_missing', 'pct_missing'], ascending=False)


def iqr_outlier_mask(series: pd.Series) -> pd.Series:
    """
    Devuelve una máscara booleana con True donde hay outliers.

    Método IQR estándar:
    - Límite inferior: Q1 - 1.5 * IQR
    - Límite superior: Q3 + 1.5 * IQR

    Los valores no numéricos se tratan como NaN (no se marcan como outlier).

    Uso:
        mask = iqr_outlier_mask(df['edad'])
        df[mask]  # filas con outliers
    """
    s     = pd.to_numeric(series, errors='coerce').dropna()
    q1    = s.quantile(0.25)
    q3    = s.quantile(0.75)
    iqr   = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    num   = pd.to_numeric(series, errors='coerce')
    return (num < lower) | (num > upper)


def cramers_v(x: pd.Series, y: pd.Series) -> float:
    """
    Calcula la V de Cramér: medida de asociación entre dos variables categóricas.

    Rango: [0, 1]
    - 0 = sin asociación
    - 1 = asociación perfecta

    Complemento natural del test Chi-cuadrado: el p-valor dice si hay asociación,
    la V de Cramér dice cuánta.

    Uso:
        v = cramers_v(df['tipo_plan'], df['descuento_activo'])
        print(f'Asociación: {v:.3f}')
    """
    table = pd.crosstab(x, y)
    chi2  = stats.chi2_contingency(table)[0]
    n     = table.values.sum()
    r, k  = table.shape
    return np.sqrt((chi2 / n) / max(min(k - 1, r - 1), 1))


def resumen_categorica(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Frecuencia y porcentaje de cada categoría de una variable.

    Incluye NaN como categoría propia para no ocultarlos.

    Uso:
        resumen_categorica(df, 'tipo_plan')
    """
    return pd.DataFrame({
        'frecuencia': df[col].value_counts(dropna=False),
        'porcentaje': df[col].value_counts(normalize=True, dropna=False).mul(100).round(2),
    })


def summarize_rate(df: pd.DataFrame, col: str,
                   target: str = 'ever_churn') -> pd.DataFrame:
    """
    Calcula la tasa de churn por categoría de una variable.

    Para cada valor de 'col' devuelve:
    - n_total:     número de clientes en esa categoría
    - n_churn:     número de churners
    - churn_rate:  tasa de churn en porcentaje (%)

    Ordenado de mayor a menor tasa de churn.

    Uso:
        summarize_rate(df, 'tipo_plan')
        summarize_rate(df, 'tipo_zona', target='ever_churn')
    """
    return (
        df.groupby(col)[target]
        .agg(
            n_total = 'count',
            n_churn = 'sum',
        )
        .assign(churn_rate = lambda d: (d['n_churn'] / d['n_total'] * 100).round(2))
        .sort_values('churn_rate', ascending=False)
    )
