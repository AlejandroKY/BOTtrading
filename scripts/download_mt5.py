"""Descarga todo el histórico disponible de un terminal MetaTrader 5 abierto (p. ej. OANDA Global Demo).

Uso (Windows, con MT5 abierto y con sesión iniciada):
    pip install MetaTrader5
    python scripts/download_mt5.py            # M1 y M5 de los 6 mercados
Guarda data/oanda/<SIMBOLO>_<TF>.csv.gz con columnas time, open, high, low, close, volume, spread.
OJO: `time` es la hora del SERVIDOR de MT5 aunque aparezca como UTC. En OANDA es Nueva York + 7 h
(la apertura de las 9:30 NY aparece a las 16:30). Por eso se carga con --tz mt5:
    python -m futbot backtest ... --csv data/oanda/US100_M1.csv.gz --tz mt5
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

# símbolo MT5 de OANDA -> contrato de futbot
SYMBOLS = {
    "US500": "ES",
    "US100": "NQ",
    "US2000": "RTY",
    "XAUUSD.sml": "GC",
    "USOIL.sml": "CL",
    "EURUSD.sml": "6E",
}
TIMEFRAMES = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5}
CHUNK = 100_000  # máximo de velas por llamada
OUT = Path(__file__).resolve().parents[1] / "data" / "oanda"


def fetch_all(symbol: str, tf: int) -> pd.DataFrame:
    """Recorre el histórico hacia atrás en bloques hasta que el servidor no da más."""
    mt5.symbol_select(symbol, True)
    end, parts = datetime.now(timezone.utc), []
    while True:
        rates = mt5.copy_rates_from(symbol, tf, end, CHUNK)
        if rates is None or len(rates) < 2:
            break
        df = pd.DataFrame(rates)
        parts.append(df)
        first = datetime.fromtimestamp(int(df["time"].iloc[0]), timezone.utc)
        if first >= end:
            break
        end = first
        time.sleep(0.5)
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts).drop_duplicates("time").sort_values("time")
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df.rename(columns={"tick_volume": "volume"})[["time", "open", "high", "low", "close", "volume", "spread"]]


def main() -> None:
    if not mt5.initialize():
        raise SystemExit(f"No conecta con MT5: {mt5.last_error()}")
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        for symbol, contract in SYMBOLS.items():
            for tf_name, tf in TIMEFRAMES.items():
                df = fetch_all(symbol, tf)
                if df.empty:
                    print(f"{symbol} {tf_name}: sin datos")
                    continue
                path = OUT / f"{symbol.replace('.sml', '')}_{tf_name}.csv.gz"
                df.to_csv(path, index=False)
                print(f"{symbol} ({contract}) {tf_name}: {len(df):,} velas "
                      f"{df['time'].iloc[0]:%Y-%m-%d} -> {df['time'].iloc[-1]:%Y-%m-%d}  {path.name}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
