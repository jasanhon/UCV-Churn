"""
src/clean.py
------------
Módulo de limpieza de datos.
Recibe los dataframes crudos del módulo load.py y devuelve versiones limpias.

Criterios generales:
  - Los CSV raw NUNCA se modifican
  - Los cambios se documentan con prints para trazabilidad
  - Se siguen reglas de negocio claras, no imputaciones arbitrarias
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config.config import FILES_PROCESSED


# =============================================================================
# FUNCIONES AUXILIARES DE INFRAESTRUCTURA
# =============================================================================

def _preparar_limpieza(df, entidad, id_col=None):
    """
    Realiza las operaciones de limpieza transversales a todos los datasets:
    1. Generación de copia profunda para integridad de memoria.
    2. Eliminación de duplicados exactos (registros idénticos).
    3. Eliminación de duplicados por identificador único si se requiere.
    """
    df_clean = df.copy()
    n_ini = len(df_clean)
    
    # Limpieza de duplicados exactos
    n_dup = df_clean.duplicated().sum()
    df_clean = df_clean.drop_duplicates()
    if n_dup > 0:
        print(f"[{entidad}] INFO: Eliminados {n_dup} registros duplicados exactos.")

    # Limpieza por identificador (ej. cliente_id) para asegurar unicidad
    if id_col and id_col in df_clean.columns:
        n_dup_id = df_clean.duplicated(subset=[id_col]).sum()
        df_clean = df_clean.drop_duplicates(subset=[id_col], keep="first")
        if n_dup_id > 0:
            print(f"[{entidad}] INFO: Eliminados {n_dup_id} registros duplicados por {id_col}.")
            
    return df_clean, n_ini


def normalizar_tipo_zona(df: pd.DataFrame, columna: str = "tipo_zona") -> pd.DataFrame:
    """
    Corrige valores erróneos de tipo_zona.
    """

    mapa_zona = {
        'suburbanx': 'suburbana',
        'urbana??':  'urbana_premium',
        'rural-1':   'rural',
    }

    n_corr = df[columna].isin(mapa_zona.keys()).sum()

    if n_corr > 0:
        print(
            f"[normalizar_tipo_zona] "
            f"{n_corr} valores corregidos: {list(mapa_zona.keys())}"
        )

        df[columna] = df[columna].replace(mapa_zona)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTES
# ══════════════════════════════════════════════════════════════════════════════

def clean_clientes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Procesa la tabla maestra de clientes aplicando reglas de integridad:
    - Normalización de rangos de edad (18-100 años).
    - Corrección de valores de antigüedad fuera de dominio (negativos).
    - Estandarización de categorías de planes comerciales.
    """
    # Ejecución de limpieza estructural
    df, n_ini = _preparar_limpieza(df, "Clientes", id_col="cliente_id")
    
    # Normalizar tipo_zona — corregir errores tipográficos del dataset
    df = normalizar_tipo_zona(df)

    # Tratamiento de Edad: Valores fuera de rango lógico se marcan como nulos
    # para su posterior imputación en el pipeline de modelado.
    mask_edad = (df["edad"] < 18) | (df["edad"] > 100)
    if mask_edad.sum() > 0:
        print(f"[Clientes] INFO: {mask_edad.sum()} edades fuera de rango ajustadas a NaN.")
        df.loc[mask_edad, "edad"] = np.nan

    # Tratamiento de Antigüedad: Corrección de errores en la fecha de alta
    # que generan meses negativos, normalizándolos a valor cero.
    df["antiguedad_meses"] = pd.to_numeric(df["antiguedad_meses"], errors="coerce")
    mask_ant = df["antiguedad_meses"] < 0
    if mask_ant.sum() > 0:
        print(f"[Clientes] INFO: {mask_ant.sum()} antigüedades negativas normalizadas a 0.")
        df.loc[mask_ant, "antiguedad_meses"] = 0

    # Normalización de Planes: Estandarización de strings para evitar 
    # duplicidad de categorías por errores de capitalización o espacios.
    df["tipo_plan"] = df["tipo_plan"].str.strip().str.title()

    print(f"[clean_clientes] Resultado: {n_ini:,} -> {len(df):,} filas | Nulos: {df.isnull().sum().sum()}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# CHURN
# ══════════════════════════════════════════════════════════════════════════════

def clean_churn(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza de churn_target.csv:
    - Elimina duplicados exactos y duplicados cliente-fecha
    - Valida que churn solo tome valores 0 o 1
    - Ordena por cliente_id y fecha
    """
    df, n_ini = _preparar_limpieza(df, "Facturacion")

    # Duplicados cliente-fecha
    n_dup_cf = df.duplicated(subset=["cliente_id", "fecha"]).sum()
    df = df.drop_duplicates(subset=["cliente_id", "fecha"], keep="first")
    if n_dup_cf > 0:
        print(f"[clean_churn] Eliminados {n_dup_cf} duplicados cliente-fecha")

    # Valores inválidos en churn
    mask_inv = ~df["churn"].isin([0, 1])
    if mask_inv.sum() > 0:
        print(f"[clean_churn] {mask_inv.sum()} valores inválidos en churn → eliminados")
        df = df[~mask_inv]

    df = df.sort_values(["cliente_id", "fecha"]).reset_index(drop=True)

    print(f"[clean_churn] Resultado: {n_ini:,} -> {len(df):,} filas | Nulos: {df.isnull().sum().sum()}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# FACTURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def clean_facturacion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza de facturacion_mensual.csv:
    - Elimina duplicados
    - Trata importe_total nulo (lo deja como NaN, documentado)
    - Trata consumo_extra negativo (abonos/correcciones, se deja como está pero se documenta)
    - Normaliza tipo_plan
    - Ordena por cliente_id y fecha
    """
    df, n_ini = _preparar_limpieza(df, "Facturacion")

    # importe_total nulo → documentamos, dejamos NaN
    n_nulos_imp = df["importe_total"].isnull().sum()
    if n_nulos_imp > 0:
        print(f"[clean_facturacion] {n_nulos_imp} registros con importe_total nulo "
              f"(se mantienen como NaN — posibles errores de sistema)")

    # consumo_extra negativo → documentamos (son abonos o correcciones)
    n_neg_cons = (df["consumo_extra"] < 0).sum()
    if n_neg_cons > 0:
        print(f"[clean_facturacion] {n_neg_cons} registros con consumo_extra negativo "
              f"(abonos/correcciones — se mantienen)")

    # tipo_plan: normalizar y dejar NaN donde no haya valor
    df["tipo_plan"] = df["tipo_plan"].str.strip().str.title()

    # Ordenar
    df = df.sort_values(["cliente_id", "fecha"]).reset_index(drop=True)

    print(f"[clean_facturacion] Resultado: {n_ini:,} -> {len(df):,} filas | Nulos: {df.isnull().sum().sum()}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# SOPORTE
# ══════════════════════════════════════════════════════════════════════════════

def clean_soporte(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza de interacciones_soporte.csv:
    - Elimina duplicados
    - Elimina duraciones negativas o extremas (> 300 min se considera error)
    - Valida que resuelto sea 0 o 1
    - Valida que satisfaccion_post esté entre 1 y 5
    """
    df, n_ini = _preparar_limpieza(df, "Soporte")

    # Duración negativa o extrema
    mask_dur = (df["duracion_min"] < 0) | (df["duracion_min"] > 300)
    if mask_dur.sum() > 0:
        print(f"[clean_soporte] {mask_dur.sum()} duraciones fuera de rango → NaN")
        df.loc[mask_dur, "duracion_min"] = np.nan

    # resuelto fuera de {0, 1}
    mask_res = ~df["resuelto"].isin([0, 1])
    if mask_res.sum() > 0:
        print(f"[clean_soporte] {mask_res.sum()} valores inválidos en 'resuelto' → NaN")
        df.loc[mask_res, "resuelto"] = np.nan

    # satisfaccion_post fuera de [1, 5]
    mask_sat = (df["satisfaccion_post"] < 1) | (df["satisfaccion_post"] > 5)
    if mask_sat.sum() > 0:
        print(f"[clean_soporte] {mask_sat.sum()} satisfacciones fuera de rango → NaN")
        df.loc[mask_sat, "satisfaccion_post"] = np.nan

    df = df.sort_values(["cliente_id", "fecha_evento"]).reset_index(drop=True)

    print(f"[clean_soporte] Resultado: {n_ini:,} -> {len(df):,} filas | Nulos: {df.isnull().sum().sum()}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# CALIDAD DE RED
# ══════════════════════════════════════════════════════════════════════════════

def clean_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza de calidad_senal_zona_mensual.csv:
    - Elimina duplicados
    - Valida rangos de cobertura (0-100%), latencia (> 0), velocidad (> 0)
    - Valida incidencia_masiva en {0, 1}
    """
    df, n_ini = _preparar_limpieza(df, "Calidad")

    # Normalizar tipo_zona — corregir errores tipográficos del dataset
    df = normalizar_tipo_zona(df)

    # Cobertura fuera de [0, 100]
    for col in ["cobertura_4g_pct", "cobertura_5g_pct", "tasa_cortes_pct"]:
        mask = (df[col] < 0) | (df[col] > 100)
        if mask.sum() > 0:
            print(f"[clean_calidad] {mask.sum()} valores de {col} fuera de [0,100] → NaN")
            df.loc[mask, col] = np.nan

    # Latencia y velocidad negativas
    for col in ["latencia_ms", "velocidad_media_mbps"]:
        mask = df[col] <= 0
        if mask.sum() > 0:
            print(f"[clean_calidad] {mask.sum()} valores de {col} <= 0 → NaN")
            df.loc[mask, col] = np.nan

    df = df.sort_values(["zona_id", "fecha"]).reset_index(drop=True)

    print(f"[clean_calidad] Resultado: {n_ini:,} -> {len(df):,} filas | Nulos: {df.isnull().sum().sum()}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# ENCUESTAS
# ══════════════════════════════════════════════════════════════════════════════

def clean_encuestas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza de encuestas_texto.csv:
    - Elimina duplicados
    - Valida rangos de puntuacion_general (1-5) y nps (0-10)
    - Elimina filas sin texto_libre (no aportan para NLP)
    """
    df, n_ini = _preparar_limpieza(df, "Encuestas")

    # Puntuación general fuera de [1, 5]
    mask_pun = (df["puntuacion_general_1a5"] < 1) | (df["puntuacion_general_1a5"] > 5)
    if mask_pun.sum() > 0:
        print(f"[clean_encuestas] {mask_pun.sum()} puntuaciones fuera de [1,5] → NaN")
        df.loc[mask_pun, "puntuacion_general_1a5"] = np.nan

    # NPS fuera de [0, 10]
    mask_nps = (df["nps_0a10"] < 0) | (df["nps_0a10"] > 10)
    if mask_nps.sum() > 0:
        print(f"[clean_encuestas] {mask_nps.sum()} NPS fuera de [0,10] → NaN")
        df.loc[mask_nps, "nps_0a10"] = np.nan

    # Sin texto libre → los mantenemos pero marcamos
    n_sin_texto = df["texto_libre"].isnull().sum()
    if n_sin_texto > 0:
        print(f"[clean_encuestas] {n_sin_texto} filas sin texto_libre")

    df = df.sort_values(["zona_id", "fecha"]).reset_index(drop=True)

    print(f"[clean_encuestas] Resultado: {n_ini:,} -> {len(df):,} filas | Nulos: {df.isnull().sum().sum()}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# LIMPIEZA COMPLETA
# ══════════════════════════════════════════════════════════════════════════════

def clean_all(data: dict, save: bool = True) -> dict:
    """
    Aplica la limpieza a todos los datasets y opcionalmente los guarda
    en data/processed/.

    Parámetros
    ----------
    data : dict   salida de load.load_all()
    save : bool   si True, guarda los CSVs limpios en data/processed/

    Devuelve un diccionario con los mismos keys pero dataframes limpios.
    """
    print("\n" + "=" * 50)
    print("  LIMPIANDO DATASETS")
    print("=" * 50 + "\n")

    clean = {
        "clientes":    clean_clientes(data["clientes"]),
        "churn":       clean_churn(data["churn"]),
        "facturacion": clean_facturacion(data["facturacion"]),
        "soporte":     clean_soporte(data["soporte"]),
        "calidad":     clean_calidad(data["calidad"]),
        "encuestas":   clean_encuestas(data["encuestas"]),
    }

    if save:
        print("\n--- Guardando en data/processed/ ---")
        mapping = {
            "clientes":    FILES_PROCESSED["clientes_clean"],
            "churn":       FILES_PROCESSED["churn_clean"],
            "facturacion": FILES_PROCESSED["facturacion_clean"],
            "soporte":     FILES_PROCESSED["soporte_clean"],
            "calidad":     FILES_PROCESSED["calidad_clean"],
            "encuestas":   FILES_PROCESSED["encuestas_clean"],
        }
        for key, path in mapping.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            clean[key].to_csv(path, index=False)
            print(f"  ✅ {path.name}")

    print("\n✅ Limpieza completada")
    return clean


if __name__ == "__main__":
    from src.load import load_all
    data = load_all()
    clean_all(data, save=True)
