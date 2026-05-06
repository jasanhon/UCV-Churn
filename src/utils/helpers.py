"""
utils/helpers.py
----------------
Funciones auxiliares reutilizables en todo el proyecto.
Incluye: resúmenes de datos, tests estadísticos, utilidades de visualización.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu, chi2_contingency


# ── Paleta de colores ─────────────────────────────────────────────────────────
PAL = {"No Churn": "#4C9BE8", "Churn": "#E85C4C"}


# ══════════════════════════════════════════════════════════════════════════════
# RESÚMENES Y CALIDAD
# ══════════════════════════════════════════════════════════════════════════════

def resumen_df(df: pd.DataFrame, nombre: str = "DataFrame") -> pd.DataFrame:
    """
    Imprime un resumen rápido del dataframe: shape, duplicados, nulos y tipos.
    Devuelve también el dataframe de info para poder usarlo en notebooks.
    """
    print(f"\n{'='*55}")
    print(f"  RESUMEN: {nombre}")
    print(f"{'='*55}")
    print(f"  Filas:         {df.shape[0]:,}")
    print(f"  Columnas:      {df.shape[1]}")
    print(f"  Duplicados:    {df.duplicated().sum():,}")

    info = pd.DataFrame({
        "dtype":     df.dtypes,
        "n_nulos":   df.isnull().sum(),
        "pct_nulos": (df.isnull().mean() * 100).round(2),
        "n_unicos":  df.nunique(),
    })
    print()
    print(info.to_string())
    return info


def check_quality(df: pd.DataFrame, checks: dict) -> pd.DataFrame:
    """
    Ejecuta una serie de checks de calidad sobre el dataframe.

    Parámetros
    ----------
    checks : dict  {nombre_check: expresión_booleana_serie}
    Ejemplo:
        checks = {
            'edad_negativa': (df['edad'] < 0).sum(),
            'nulos_importe': df['importe'].isnull().sum(),
        }
    """
    qdf = pd.DataFrame.from_dict(checks, orient="index", columns=["n_casos"])
    qdf["alerta"] = qdf["n_casos"].apply(lambda x: "⚠️" if x > 0 else "✅")
    return qdf


# ══════════════════════════════════════════════════════════════════════════════
# TESTS ESTADÍSTICOS
# ══════════════════════════════════════════════════════════════════════════════

def test_mannwhitney(df: pd.DataFrame, variable: str,
                     target: str = "ever_churn") -> dict:
    """
    Test de Mann-Whitney entre churners y no churners para una variable numérica.
    Devuelve dict con estadístico, p-valor y medianas de cada grupo.
    """
    a = df[df[target] == 0][variable].dropna()
    b = df[df[target] == 1][variable].dropna()
    u_stat, p_val = mannwhitneyu(a, b, alternative="two-sided")

    resultado = {
        "variable":        variable,
        "U":               round(u_stat, 0),
        "p_valor":         round(p_val, 4),
        "significativo":   p_val < 0.05,
        "mediana_no_churn": round(a.median(), 3),
        "mediana_churn":   round(b.median(), 3),
    }
    print(f"Mann-Whitney ({variable}): p={p_val:.4f} {'✅ significativo' if p_val < 0.05 else '❌ no significativo'}")
    print(f"  Mediana No Churn: {a.median():.3f} | Mediana Churn: {b.median():.3f}")
    return resultado


def cramers_v(x: pd.Series, y: pd.Series) -> tuple:
    """
    Calcula el estadístico Cramer's V para medir la asociación
    entre dos variables categóricas.
    Devuelve (V, p_valor).
    """
    tabla = pd.crosstab(x, y)
    chi2, p, _, _ = chi2_contingency(tabla)
    n = tabla.sum().sum()
    v = np.sqrt(chi2 / (n * (min(tabla.shape) - 1)))
    return round(v, 3), round(p, 4)


# ══════════════════════════════════════════════════════════════════════════════
# VISUALIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def boxplot_churn(df: pd.DataFrame, variable: str,
                  titulo: str = None, ax=None) -> None:
    """
    Boxplot de una variable numérica comparando churners vs no churners.
    Crea etiqueta legible para evitar problemas de palette con seaborn moderno.
    """
    df_plot = df.dropna(subset=[variable]).copy()
    df_plot["churn_label"] = df_plot["ever_churn"].map({0: "No Churn", 1: "Churn"})

    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 4))

    sns.boxplot(data=df_plot, x="churn_label", y=variable,
                order=["No Churn", "Churn"], palette=PAL, ax=ax)
    ax.set_title(titulo or f"{variable} vs Churn", fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel(variable)

    if ax is None:
        plt.tight_layout()
        plt.show()


def kde_churn(df: pd.DataFrame, variable: str,
              titulo: str = None, clip_q: float = None, ax=None) -> None:
    """
    KDE de una variable numérica comparando churners vs no churners.
    clip_q: si se pasa un cuantil (ej. 0.99), recorta los outliers antes de plotear.
    """
    df_plot = df.dropna(subset=[variable]).copy()
    if clip_q:
        cap = df_plot[variable].quantile(clip_q)
        df_plot[variable] = df_plot[variable].clip(upper=cap)

    df_plot["churn_label"] = df_plot["ever_churn"].map({0: "No Churn", 1: "Churn"})

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))

    for label, color in PAL.items():
        subset = df_plot[df_plot["churn_label"] == label][variable]
        sns.kdeplot(subset, ax=ax, color=color, fill=True, alpha=0.4, label=label)

    ax.set_title(titulo or f"Distribución de {variable} por grupo de churn",
                 fontweight="bold")
    ax.set_xlabel(variable)
    ax.legend()

    if ax is None:
        plt.tight_layout()
        plt.show()


def barras_churn_cat(df: pd.DataFrame, variable: str,
                     target: str = "ever_churn", titulo: str = None,
                     ax=None) -> pd.DataFrame:
    """
    Barras con la tasa de churn por categoría de una variable.
    Devuelve el dataframe con las tasas calculadas.
    """
    tasas = (df.groupby(variable)[target]
               .agg(["mean", "count"])
               .reset_index()
               .rename(columns={"mean": "tasa_churn", "count": "n"}))
    tasas = tasas.sort_values("tasa_churn", ascending=False)

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))

    bars = ax.bar(tasas[variable].astype(str), tasas["tasa_churn"] * 100,
                  color=sns.color_palette("RdYlGn_r", len(tasas)))
    ax.set_title(titulo or f"Tasa de churn por {variable}", fontweight="bold")
    ax.set_ylabel("% clientes con churn")
    ax.set_xlabel(variable)
    for bar, (_, row) in zip(bars, tasas.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{row['tasa_churn']*100:.1f}%\n(n={row['n']:,})",
                ha="center", va="bottom", fontsize=8)

    if ax is None:
        plt.tight_layout()
        plt.show()

    return tasas


def perfil_churner(df: pd.DataFrame, variables: list,
                   target: str = "ever_churn") -> pd.DataFrame:
    """
    Tabla comparativa de medias entre churners y no churners
    para una lista de variables numéricas.
    """
    vars_disp = [v for v in variables if v in df.columns]
    perfil = df.groupby(target)[vars_disp].mean().T
    perfil.columns = ["No Churn (0)", "Churn (1)"]
    perfil["Diferencia (%)"] = (
        (perfil["Churn (1)"] - perfil["No Churn (0)"]) /
        perfil["No Churn (0)"].abs() * 100
    ).round(1)
    return perfil.round(3)
