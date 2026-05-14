"""
src/load.py
-----------
Módulo de carga de datos.
Lee los 6 CSV raw y devuelve los dataframes con los tipos básicos ya corregidos
(fechas, enteros...). NO hace limpieza de negocio — eso es responsabilidad de clean.py.
"""

import pandas as pd
from pathlib import Path

# Importamos la configuración de rutas
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config.config import FILES


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CARGA INDIVIDUALES
# ══════════════════════════════════════════════════════════════════════════════

def load_clientes(path=None) -> pd.DataFrame:
    """
    Carga clientes.csv.
    Columnas: cliente_id, zona_id, region, tipo_zona, poblacion_zona,
              edad, sexo, estado_civil, num_lineas, tipo_plan,
              tipo_dispositivo, ingreso_estimado, antiguedad_meses, descuento_activo
    """
    path = path or FILES["clientes"]
    df = pd.read_csv(path)
    print(f"[load] clientes:    {df.shape[0]:,} filas x {df.shape[1]} columnas")
    return df


def load_churn(path=None) -> pd.DataFrame:
    """
    Carga churn_target.csv.
    Columnas: cliente_id, fecha, churn (0/1)
    La columna fecha tiene formatos mixtos — se parsea con format='mixed'.
    """
    path = path or FILES["churn"]
    df = pd.read_csv(path)
    df["fecha"] = pd.to_datetime(df["fecha"], format="mixed", dayfirst=True)
    print(f"[load] churn:       {df.shape[0]:,} filas x {df.shape[1]} columnas")
    return df


def load_facturacion(path=None) -> pd.DataFrame:
    """
    Carga facturacion_mensual.csv.
    Columnas: cliente_id, fecha, zona_id, tipo_plan, num_lineas,
              cargo_base, consumo_extra, descuento_aplicado, importe_total,
              dias_retraso_pago, impago_flag, variacion_consumo_pct,
              stress_calidad_lag, incidencia_masiva_lag

    ⚠️ La columna fecha tiene formatos mixtos (YYYY-MM-DD y DD/MM/YYYY).
       Se usa format='mixed' con dayfirst=True para parsear correctamente.
    """
    path = path or FILES["facturacion"]
    df = pd.read_csv(path)
    df["fecha"] = pd.to_datetime(df["fecha"], format="mixed", dayfirst=True)
    print(f"[load] facturacion: {df.shape[0]:,} filas x {df.shape[1]} columnas")
    return df


def load_soporte(path=None) -> pd.DataFrame:
    path = path or FILES["soporte"]
    df = pd.read_csv(path)
    df["fecha_evento"] = pd.to_datetime(df["fecha_evento"], format="mixed", dayfirst=True)  # ← cambio aquí
    # 'mes' es una columna derivada que puede no estar en el CSV original
    if "mes" in df.columns:
        df["mes"] = pd.to_datetime(df["mes"], format="mixed", dayfirst=True)
    print(f"[load] soporte:     {df.shape[0]:,} filas x {df.shape[1]} columnas")
    return df


def load_calidad(path=None) -> pd.DataFrame:
    path = path or FILES["calidad"]
    df = pd.read_csv(path)
    df["fecha"] = pd.to_datetime(df["fecha"], format="mixed", dayfirst=True)
    print(f"[load] calidad:     {df.shape[0]:,} filas x {df.shape[1]} columnas")
    return df


def load_encuestas(path=None) -> pd.DataFrame:
    path = path or FILES["encuestas"]
    df = pd.read_csv(path)
    df["fecha"] = pd.to_datetime(df["fecha"], format="mixed", dayfirst=True)
    print(f"[load] encuestas:   {df.shape[0]:,} filas x {df.shape[1]} columnas")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# CARGA COMPLETA
# ══════════════════════════════════════════════════════════════════════════════

def load_all() -> dict:
    """
    Carga los 6 datasets de una vez y los devuelve en un diccionario.

    Uso:
        from src.load import load_all
        data = load_all()
        clientes = data['clientes']
        churn    = data['churn']
    """
    print("=" * 50)
    print("  CARGANDO DATASETS")
    print("=" * 50)

    datasets = {
        "clientes":    load_clientes(),
        "churn":       load_churn(),
        "facturacion": load_facturacion(),
        "soporte":     load_soporte(),
        "calidad":     load_calidad(),
        "encuestas":   load_encuestas(),
    }

    print("\n✅ Todos los datasets cargados correctamente")
    return datasets


if __name__ == "__main__":
    data = load_all()
