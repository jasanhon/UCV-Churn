"""
src/features.py
---------------
Módulo de feature engineering.
Construye las variables derivadas a partir de los datos limpios y genera
dos datasets finales:
  - dataset_final.csv  → 1 fila por cliente (modelo binario ever_churn)
  - dataset_panel.csv  → 1 fila por cliente-mes (modelo temporal con lags)

Principio anti-leakage: todas las variables se calculan usando SOLO
información anterior al mes de referencia (lags correctamente aplicados).
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config.config import FILES_PROCESSED, LAG_MONTHS, ROLLING_WINDOW


# ══════════════════════════════════════════════════════════════════════════════
# FEATURES DE FACTURACIÓN (nivel cliente)
# ══════════════════════════════════════════════════════════════════════════════

def features_facturacion(factura: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega la facturación a nivel cliente.
    Genera métricas resumen y el plan dominante.
    """
    agg = factura.groupby("cliente_id").agg(
        importe_medio          = ("importe_total",        "mean"),
        cargo_base_medio       = ("cargo_base",           "mean"),
        consumo_extra_medio    = ("consumo_extra",        "mean"),
        descuento_medio        = ("descuento_aplicado",   "mean"),
        pct_meses_descuento    = ("descuento_aplicado",   lambda x: (x > 0).mean()),
        n_impagos              = ("impago_flag",          "sum"),
        pct_meses_impago       = ("impago_flag",          "mean"),
        dias_retraso_medio     = ("dias_retraso_pago",    "mean"),
        dias_retraso_max       = ("dias_retraso_pago",    "max"),
        stress_medio           = ("stress_calidad_lag",   "mean"),
        stress_max             = ("stress_calidad_lag",   "max"),
        n_incidencias_masivas  = ("incidencia_masiva_lag","sum"),
        variacion_consumo_media= ("variacion_consumo_pct","mean"),
        n_meses_facturados     = ("importe_total",        "count"),
    ).reset_index()

    # ⚠️  ADVERTENCIA — n_meses_facturados NO debe usarse como feature en el modelo binario.
    # Un cliente que abandonó en el mes 6 tiene 6 meses facturados; uno activo tiene 36.
    # El modelo aprendería que "pocos meses = churn" por ser consecuencia del target,
    # no una causa. En producción esta información no existe para clientes futuros.
    # Úsala solo para análisis descriptivo. Excluirla en el pipeline de modelado.

    # Plan dominante (el que aparece más meses)
    plan_dom = (
        factura.dropna(subset=["tipo_plan"])
        .groupby("cliente_id")["tipo_plan"]
        .agg(lambda x: x.value_counts().index[0])
        .reset_index()
        .rename(columns={"tipo_plan": "plan_dominante"})
    )
    agg = agg.merge(plan_dom, on="cliente_id", how="left")

    # Ratio consumo_extra / cargo_base (engagement relativo)
    agg["ratio_consumo_base"] = (
        agg["consumo_extra_medio"] / agg["cargo_base_medio"].replace(0, np.nan)
    ).round(4)

    # % meses sin consumo extra (indicador de desengagement)
    sin_consumo = (
        factura.assign(sin_consumo=(factura["consumo_extra"] <= 0).astype(int))
        .groupby("cliente_id")["sin_consumo"]
        .mean()
        .reset_index()
        .rename(columns={"sin_consumo": "pct_meses_sin_consumo"})
    )
    agg = agg.merge(sin_consumo, on="cliente_id", how="left")

    print(f"[features_facturacion] {len(agg):,} clientes, {agg.shape[1]} variables")
    return agg


# ══════════════════════════════════════════════════════════════════════════════
# FEATURES DE SOPORTE (nivel cliente)
# ══════════════════════════════════════════════════════════════════════════════

def features_soporte(soporte: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega el soporte a nivel cliente.
    Genera métricas resumen y distribución de motivos y canales.
    """
    # ── Agregación de variables de soporte ───────────────────────────────────
    # NOTA sobre impago_mes y dias_retraso_mes:
    # Estas columnas vienen del CSV de soporte pero son datos de facturación
    # que se unieron al generar el dataset. Son redundantes con las que calcula
    # features_facturacion() y pueden introducir doble conteo en el modelo.
    # Se mantienen aquí porque en el dataset binario pueden aportar contexto
    # (el cliente llama a soporte en meses con impago), pero NO deben usarse
    # en el dataset panel — allí ya vienen de facturación con lag correcto.
    agg = soporte.groupby("cliente_id").agg(
        n_interacciones       = ("interaccion_id",       "count"),
        tasa_resolucion       = ("resuelto",             "mean"),
        satisfaccion_media    = ("satisfaccion_post",    "mean"),
        duracion_media_min    = ("duracion_min",         "mean"),
        n_impagos_sop         = ("impago_mes",           "sum"),   # ver nota arriba
        dias_retraso_sop      = ("dias_retraso_mes",     "sum"),   # ver nota arriba
        stress_sop_medio      = ("stress_calidad_lag",   "mean"),
        n_incid_masivas_sop   = ("incidencia_masiva_lag","sum"),
        n_canales_distintos   = ("canal",                "nunique"),
        n_motivos_distintos   = ("motivo",               "nunique"),
    ).reset_index()

    # Motivos como columnas (one-hot count)
    motivo_pivot = (
        soporte.groupby(["cliente_id", "motivo"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    motivo_pivot.columns = (
        ["cliente_id"] +
        [f"n_mot_{c.lower().replace(' ', '_').replace('/', '_')}"
         for c in motivo_pivot.columns[1:]]
    )
    agg = agg.merge(motivo_pivot, on="cliente_id", how="left")

    # Canal dominante
    canal_dom = (
        soporte.groupby("cliente_id")["canal"]
        .agg(lambda x: x.value_counts().index[0])
        .reset_index()
        .rename(columns={"canal": "canal_dominante"})
    )
    agg = agg.merge(canal_dom, on="cliente_id", how="left")

    print(f"[features_soporte] {len(agg):,} clientes, {agg.shape[1]} variables")
    return agg


# ══════════════════════════════════════════════════════════════════════════════
# FEATURES DE CALIDAD DE RED (nivel zona-mes → cliente)
# ══════════════════════════════════════════════════════════════════════════════

def features_calidad(calidad: pd.DataFrame,
                     clientes: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega la calidad de red a nivel cliente usando la zona del cliente.
    Calcula métricas medias de calidad de red para la zona de cada cliente.
    """
    # Métricas medias por zona (sobre todo el histórico)
    calidad_zona = calidad.groupby("zona_id").agg(
        calidad_global_media   = ("indice_calidad_global",  "mean"),
        calidad_global_min     = ("indice_calidad_global",  "min"),
        cobertura_4g_media     = ("cobertura_4g_pct",       "mean"),
        cobertura_5g_media     = ("cobertura_5g_pct",       "mean"),
        latencia_media         = ("latencia_ms",            "mean"),
        velocidad_media        = ("velocidad_media_mbps",   "mean"),
        tasa_cortes_media      = ("tasa_cortes_pct",        "mean"),
        n_incidencias_zona     = ("incidencia_masiva",      "sum"),
    ).reset_index()

    # Unimos con clientes usando zona_id
    df = clientes[["cliente_id", "zona_id"]].merge(calidad_zona,
                                                    on="zona_id", how="left")
    df = df.drop(columns=["zona_id"])

    print(f"[features_calidad] {len(df):,} clientes con métricas de calidad de red")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# FEATURES DE ENCUESTAS / NLP (nivel zona-mes → cliente)
# ══════════════════════════════════════════════════════════════════════════════

def features_encuestas(encuestas: pd.DataFrame,
                       clientes: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega las métricas de encuestas/NLP a nivel cliente usando la zona.
    Como las encuestas no se pueden unir a cliente individual, usamos
    la media por zona como proxy del sentimiento del entorno del cliente.
    """
    enc_zona = encuestas.groupby("zona_id").agg(
        nps_medio              = ("nps_0a10",              "mean"),
        puntuacion_media       = ("puntuacion_general_1a5","mean"),
        sentimiento_medio      = ("sent_text_latente",     "mean"),
        pct_incongruentes      = ("flag_incongruente",     "mean"),
        n_encuestas            = ("encuesta_id",           "count"),
    ).reset_index()

    df = clientes[["cliente_id", "zona_id"]].merge(enc_zona,
                                                    on="zona_id", how="left")
    df = df.drop(columns=["zona_id"])

    print(f"[features_encuestas] {len(df):,} clientes con métricas de encuestas/NLP")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# DATASET FINAL BINARIO (1 fila por cliente)
# ══════════════════════════════════════════════════════════════════════════════

def build_dataset_final(clientes: pd.DataFrame,
                        churn: pd.DataFrame,
                        factura: pd.DataFrame,
                        soporte: pd.DataFrame,
                        calidad: pd.DataFrame,
                        encuestas: pd.DataFrame,
                        save: bool = True) -> pd.DataFrame:
    """
    Construye el dataset analítico final con 1 fila por cliente.
    Integra todas las fuentes y añade la etiqueta ever_churn.

    Uso para el modelo binario (Opción A del profesor).
    """
    print("\n" + "=" * 50)
    print("  CONSTRUYENDO DATASET FINAL (binario)")
    print("=" * 50 + "\n")

    # Target: ever_churn
    churn_agg = churn.groupby("cliente_id").agg(
        ever_churn         = ("churn", "max"),
        n_meses_observados = ("churn", "count"),
        primer_mes         = ("fecha", "min"),
        ultimo_mes         = ("fecha", "max"),
    ).reset_index()

    # Features por fuente
    feat_factura   = features_facturacion(factura)
    feat_soporte   = features_soporte(soporte)
    feat_calidad   = features_calidad(calidad, clientes)
    feat_encuestas = features_encuestas(encuestas, clientes)

    # Integración
    df = clientes.merge(churn_agg,      on="cliente_id", how="inner")
    df = df.merge(feat_factura,         on="cliente_id", how="left")
    df = df.merge(feat_soporte,         on="cliente_id", how="left")
    df = df.merge(feat_calidad,         on="cliente_id", how="left")
    df = df.merge(feat_encuestas,       on="cliente_id", how="left")

    # Rellenar nulos en conteos (clientes sin soporte = 0 interacciones)
    cols_fill_zero = ["n_interacciones", "n_impagos_sop", "dias_retraso_sop",
                      "n_incid_masivas_sop", "n_canales_distintos", "n_motivos_distintos"]
    for col in cols_fill_zero:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    if save:
        path = FILES_PROCESSED["dataset_final"]
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        print(f"\n✅ Dataset final guardado: {path.name}")
        print(f"   {df.shape[0]:,} clientes x {df.shape[1]} columnas")
        print(f"   Tasa de ever_churn: {df['ever_churn'].mean()*100:.1f}%")

    return df


# ══════════════════════════════════════════════════════════════════════════════
# DATASET PANEL TEMPORAL (1 fila por cliente-mes)
# ══════════════════════════════════════════════════════════════════════════════

def build_dataset_panel(clientes: pd.DataFrame,
                        churn: pd.DataFrame,
                        factura: pd.DataFrame,
                        soporte: pd.DataFrame,
                        calidad: pd.DataFrame,
                        encuestas: pd.DataFrame = None,
                        save: bool = True) -> pd.DataFrame:
    """
    Construye el dataset panel con 1 fila por cliente-mes.
    Aplica lags correctamente para evitar leakage.

    Variables de facturación y soporte: se usan con lag de 1 mes.
    Variables de calidad de red: ya vienen con lag (stress_calidad_lag).
    Variables de encuestas: sentimiento medio zonal con lag de 1 mes.
      - encuestas es opcional (default None): si no se pasa, se omite.
      - Como las encuestas son anónimas por zona, se usan como proxy
        del sentimiento del entorno del cliente, igual que en build_dataset_final.

    Uso para el modelo temporal (Opción B del profesor).
    """
    print("\n" + "=" * 50)
    print("  CONSTRUYENDO DATASET PANEL (temporal)")
    print("=" * 50 + "\n")

    # Base: panel de churn (cliente x mes)
    panel = churn.copy()
    panel["mes"] = panel["fecha"].dt.to_period("M")

    # ── Facturación con lag 1 ─────────────────────────────────────────────────
    # Para cada mes t, usamos la facturación del mes t-1
    factura_lag = factura.copy()
    factura_lag["mes"] = factura_lag["fecha"].dt.to_period("M")
    factura_lag["mes_siguiente"] = factura_lag["mes"] + 1

    cols_factura = ["importe_total", "consumo_extra", "descuento_aplicado",
                    "impago_flag", "dias_retraso_pago", "variacion_consumo_pct",
                    "stress_calidad_lag"]

    factura_panel = factura_lag[["cliente_id", "mes_siguiente"] + cols_factura].copy()
    factura_panel = factura_panel.rename(columns={"mes_siguiente": "mes"})
    factura_panel = factura_panel.rename(columns={c: f"{c}_lag1" for c in cols_factura})

    panel = panel.merge(factura_panel, on=["cliente_id", "mes"], how="left")

    # ── Rolling window de facturación (últimos 3 meses) ──────────────────────
    factura_sorted = factura_lag.sort_values(["cliente_id", "mes"])
    for col in ["importe_total", "impago_flag", "stress_calidad_lag"]:
        roll = (
            factura_sorted.groupby("cliente_id")[col]
            .transform(lambda x: x.shift(1).rolling(ROLLING_WINDOW, min_periods=1).mean())
        )
        factura_sorted[f"{col}_roll{ROLLING_WINDOW}"] = roll

    roll_cols = [f"{c}_roll{ROLLING_WINDOW}" for c in
                 ["importe_total", "impago_flag", "stress_calidad_lag"]]
    factura_roll = factura_sorted[["cliente_id", "mes_siguiente"] + roll_cols].copy()
    factura_roll = factura_roll.rename(columns={"mes_siguiente": "mes"})
    panel = panel.merge(factura_roll, on=["cliente_id", "mes"], how="left")

    # ── Calidad de red por zona-mes (ya viene laggada) ───────────────────────
    calidad_panel = calidad.copy()
    calidad_panel["mes"] = calidad_panel["fecha"].dt.to_period("M")
    calidad_cols = ["indice_calidad_global", "tasa_cortes_pct",
                    "cobertura_4g_pct", "cobertura_5g_pct"]

    # Cruzamos zona del cliente
    zona_cliente = clientes[["cliente_id", "zona_id"]]
    panel = panel.merge(zona_cliente, on="cliente_id", how="left")
    calidad_mes = calidad_panel[["zona_id", "mes"] + calidad_cols]
    panel = panel.merge(calidad_mes, on=["zona_id", "mes"], how="left")

    # ── Encuestas: sentimiento zonal con lag 1 ──────────────────────────────
    # Las encuestas son anónimas por zona, no por cliente.
    # Usamos el sentimiento medio de la zona del mes anterior como proxy.
    # Mismo principio anti-leakage que facturación: mes T usa datos de T-1.
    if encuestas is not None:
        encuestas_panel = encuestas.copy()
        encuestas_panel["mes"] = encuestas_panel["fecha"].dt.to_period("M")
        enc_zona_mes = (
            encuestas_panel
            .groupby(["zona_id", "mes"])
            .agg(
                sentimiento_lag1   = ("sent_text_latente",      "mean"),
                nps_lag1           = ("nps_0a10",               "mean"),
                puntuacion_lag1    = ("puntuacion_general_1a5", "mean"),
            )
            .reset_index()
        )
        # Desplazar el mes +1 para que el sentimiento de T se use en T+1
        enc_zona_mes["mes"] = enc_zona_mes["mes"] + 1
        panel = panel.merge(enc_zona_mes, on=["zona_id", "mes"], how="left")
        print(f"[build_dataset_panel] Encuestas añadidas: {enc_zona_mes.shape[0]:,} zona-mes")

    # ── Perfil del cliente (estático) ────────────────────────────────────────
    cols_perfil = ["cliente_id", "edad", "sexo", "estado_civil", "num_lineas",
                   "tipo_plan", "ingreso_estimado", "antiguedad_meses",
                   "descuento_activo", "tipo_zona", "region"]
    cols_perfil_disp = [c for c in cols_perfil if c in clientes.columns]
    panel = panel.merge(clientes[cols_perfil_disp], on="cliente_id", how="left")

    # Limpieza final
    panel = panel.sort_values(["cliente_id", "fecha"]).reset_index(drop=True)

    if save:
        path = FILES_PROCESSED["dataset_panel"]
        path.parent.mkdir(parents=True, exist_ok=True)
        panel.to_csv(path, index=False)
        print(f"\n✅ Dataset panel guardado: {path.name}")
        print(f"   {panel.shape[0]:,} filas x {panel.shape[1]} columnas")
        print(f"   Tasa de churn en panel: {panel['churn'].mean()*100:.1f}%")

    return panel


if __name__ == "__main__":
    from src.load import load_all
    from src.clean import clean_all

    data = load_all()
    clean = clean_all(data, save=False)

    df_final = build_dataset_final(**clean, save=True)
    df_panel  = build_dataset_panel(
        clientes=clean["clientes"],  churn=clean["churn"],
        factura=clean["facturacion"], soporte=clean["soporte"],
        calidad=clean["calidad"],    encuestas=clean["encuestas"],
        save=True
    )
