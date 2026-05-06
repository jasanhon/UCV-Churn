"""
config.py
---------
Parámetros globales del proyecto: rutas, constantes y configuración.
Si cambias la ubicación de los datos, solo hay que tocar este fichero.
"""

from pathlib import Path

# ── Rutas base ────────────────────────────────────────────────────────────────
ROOT_DIR       = Path(__file__).resolve().parents[1]
DATA_RAW       = ROOT_DIR / "data" / "raw"
DATA_PROCESSED = ROOT_DIR / "data" / "processed"
DATA_EXTERNAL  = ROOT_DIR / "data" / "external"
REPORTS_DIR    = ROOT_DIR / "reports"
MODELS_DIR     = ROOT_DIR / "models"
NOTEBOOKS_DIR  = ROOT_DIR / "notebooks"

# ── Nombres de ficheros raw ───────────────────────────────────────────────────
FILES = {
    "clientes":    DATA_RAW / "clientes.csv",
    "churn":       DATA_RAW / "churn_target.csv",
    "facturacion": DATA_RAW / "facturacion_mensual.csv",
    "soporte":     DATA_RAW / "interacciones_soporte.csv",
    "calidad":     DATA_RAW / "calidad_senal_zona_mensual.csv",
    "encuestas":   DATA_RAW / "encuestas_texto.csv",
}

# ── Nombres de ficheros procesados ────────────────────────────────────────────
FILES_PROCESSED = {
    "clientes_clean":    DATA_PROCESSED / "clientes_clean.csv",
    "churn_clean":       DATA_PROCESSED / "churn_clean.csv",
    "facturacion_clean": DATA_PROCESSED / "facturacion_clean.csv",
    "soporte_clean":     DATA_PROCESSED / "soporte_clean.csv",
    "calidad_clean":     DATA_PROCESSED / "calidad_clean.csv",
    "encuestas_clean":   DATA_PROCESSED / "encuestas_clean.csv",
    "dataset_final":     DATA_PROCESSED / "dataset_final.csv",
    "dataset_panel":     DATA_PROCESSED / "dataset_panel.csv",
}

# ── Parámetros del modelo ─────────────────────────────────────────────────────
TARGET_COL     = "ever_churn"       # para el modelo binario
TARGET_PANEL   = "churn"            # para el modelo panel
RANDOM_STATE   = 42
TEST_SIZE      = 0.2

# ── Parámetros de feature engineering ────────────────────────────────────────
LAG_MONTHS     = [1, 3, 6]          # lags a calcular
ROLLING_WINDOW = 3                  # ventana para medias móviles (meses)

# ── Columnas por fuente ───────────────────────────────────────────────────────
COLS_ID        = "cliente_id"
COLS_FECHA     = "fecha"
COLS_ZONA      = "zona_id"
