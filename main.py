"""
main.py
-------
Punto de entrada del proyecto UCV-Churn.
Orquesta el pipeline completo en orden:

  1. Carga        → load.py
  2. Limpieza     → clean.py
  3. Features     → features.py

Ejecutar desde la raíz del proyecto:
    python main.py

Opciones:
    python main.py --only-load       Solo carga y muestra resúmenes
    python main.py --only-clean      Carga + limpieza
    python main.py --skip-panel      No construye el dataset panel (más rápido)
"""

import argparse
import time
from pathlib import Path
import sys

# Añadimos la raíz al path para que los imports funcionen
sys.path.append(str(Path(__file__).resolve().parent))

from src.load     import load_all
from src.clean    import clean_all
from src.features import build_dataset_final, build_dataset_panel


def parse_args():
    parser = argparse.ArgumentParser(description="Pipeline UCV-Churn")
    parser.add_argument("--only-load",   action="store_true",
                        help="Solo ejecuta la carga de datos")
    parser.add_argument("--only-clean",  action="store_true",
                        help="Ejecuta carga + limpieza")
    parser.add_argument("--skip-panel",  action="store_true",
                        help="No construye el dataset panel temporal")
    return parser.parse_args()


def main():
    args = parse_args()
    t0 = time.time()

    print("\n" + "█" * 55)
    print("  PIPELINE UCV-CHURN")
    print("█" * 55)

    # ── PASO 1: Carga ─────────────────────────────────────────────────────────
    data = load_all()

    if args.only_load:
        print(f"\nEjecutado en {time.time()-t0:.1f}s")
        return

    # ── PASO 2: Limpieza ──────────────────────────────────────────────────────
    clean = clean_all(data, save=True)

    if args.only_clean:
        print(f"\nEjecutado en {time.time()-t0:.1f}s")
        return

    # ── PASO 3: Feature engineering ───────────────────────────────────────────
    # Dataset binario (1 fila por cliente)
    df_final = build_dataset_final(
        clientes    = clean["clientes"],
        churn       = clean["churn"],
        factura     = clean["facturacion"],
        soporte     = clean["soporte"],
        calidad     = clean["calidad"],
        encuestas   = clean["encuestas"],
        save        = True,
    )

    # Dataset panel temporal (1 fila por cliente-mes)
    if not args.skip_panel:
        df_panel = build_dataset_panel(
            clientes = clean["clientes"],
            churn    = clean["churn"],
            factura  = clean["facturacion"],
            soporte  = clean["soporte"],
            calidad  = clean["calidad"],
            save     = True,
        )

    # ── Resumen final ─────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  PIPELINE COMPLETADO")
    print("=" * 55)
    print(f"  Dataset final:  {df_final.shape[0]:,} clientes x {df_final.shape[1]} cols")
    if not args.skip_panel:
        print(f"  Dataset panel:  {df_panel.shape[0]:,} filas x {df_panel.shape[1]} cols")
    print(f"  Tiempo total:   {time.time()-t0:.1f}s")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
