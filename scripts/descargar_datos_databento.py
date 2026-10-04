"""Descarga velas de 1 minuto de futuros de CME desde Databento y las guarda por año en data/real/.

Databento da US$125 de crédito gratis al registrarse (https://databento.com); 2-3 años de velas de
1 minuto de un contrato cuestan muy poco de ese crédito. El script muestra el costo antes de bajar.

Uso (en tu PC):
    pip install databento pandas pyarrow
    # Windows PowerShell:   $env:DATABENTO_API_KEY = "db-xxxxxxxx"
    # macOS / Linux:        export DATABENTO_API_KEY=db-xxxxxxxx
    python scripts/descargar_datos_databento.py --symbol NQ --start 2024-01-01 --estimate   # sólo costo
    python scripts/descargar_datos_databento.py --symbol NQ --start 2024-01-01

Después:
    python -m futbot stats --recipe nq_orb5_gap --symbol NQ --csv "data/real/NQ_1m_*.parquet"

No pegues tu API key en el código ni en el chat: déjala sólo en la variable de entorno.
Los datos de CME tienen licencia: guárdalos en un repositorio PRIVADO (o no los subas).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="NQ", help="raíz del futuro: NQ, ES, GC, CL... (contrato continuo por volumen)")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=None, help="por defecto, hoy (UTC)")
    ap.add_argument("--out", default="data/real")
    ap.add_argument("--estimate", action="store_true", help="sólo muestra el costo estimado")
    ap.add_argument("--max-cost", type=float, default=20.0, help="no descarga si el costo supera este monto (USD)")
    args = ap.parse_args()

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("Falta la variable de entorno DATABENTO_API_KEY (ver instrucciones al inicio del archivo).")
    try:
        import databento as db
    except ImportError:
        sys.exit("Instala el cliente: pip install databento")

    end = args.end or pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    params = dict(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=[f"{args.symbol}.v.0"],
                  stype_in="continuous", start=args.start, end=end)
    client = db.Historical(key)
    cost = client.metadata.get_cost(**params)
    print(f"{args.symbol} 1 minuto {args.start} -> {end}: costo estimado US${cost:.2f} (se descuenta del crédito)")
    if args.estimate:
        return
    if cost > args.max_cost:
        sys.exit(f"El costo supera --max-cost {args.max_cost}. Sube ese límite si estás de acuerdo.")

    df = client.timeseries.get_range(**params).to_df()
    df = df.reset_index().rename(columns={"ts_event": "time"})
    df = df[["time", "open", "high", "low", "close", "volume"]].sort_values("time")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for year, g in df.groupby(df["time"].dt.year):
        path = out / f"{args.symbol}_1m_{year}.parquet"
        g.to_parquet(path, index=False)
        print(f"  {path}: {len(g):,} velas")
    print("Listo. Pruébalo con: python -m futbot stats --recipe nq_orb5_gap --symbol NQ "
          f'--csv "{out.as_posix()}/{args.symbol}_1m_*.parquet"')


if __name__ == "__main__":
    main()
