"""Carga de datos OHLCV de 1 minuto.

Todo se normaliza a un DataFrame con índice de timestamps en hora de Nueva York (ET) y columnas
open, high, low, close, volume. Cada timestamp marca el INICIO de la barra (la barra 09:30
cubre 09:30:00-09:30:59).

Fuentes soportadas:
- CSV genérico (Databento, TradingView, NinjaTrader exportado a CSV, FirstRate, IBKR, etc.).
- FutureSharks/financial-data (CFDs de Oanda 2005-2020, gratis en GitHub): sirve para investigar,
  pero NO es dato de futuros real. Antes de operar, valida con datos de CME (p.ej. Databento).
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import pandas as pd

ET = "America/New_York"
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.environ.get("FUTBOT_CACHE", REPO_ROOT / "data" / "cache"))

# Futuro -> instrumento equivalente en FutureSharks/financial-data (CFDs de Oanda, UTC)
FUTURESHARKS_MAP = {
    "ES": "SPX500_USD",
    "MES": "SPX500_USD",
    "NQ": "NAS100_USD",
    "MNQ": "NAS100_USD",
    "RTY": "US2000_USD",
    "M2K": "US2000_USD",
    "GC": "XAU_USD",
    "MGC": "XAU_USD",
    "CL": "WTICO_USD",
    "MCL": "WTICO_USD",
    "ZN": "USB10Y_USD",
    "6E": "EUR_USD",
    "M6E": "EUR_USD",
}

_TIME_COLS = ("time", "datetime", "timestamp", "ts_event", "date_time", "date")
_ALIASES = {
    "o": "open",
    "h": "high",
    "l": "low",
    "c": "close",
    "v": "volume",
    "vol": "volume",
    "last": "close",
}


def futuresharks_dir() -> Path:
    """Carpeta del clon de https://github.com/FutureSharks/financial-data."""
    candidates = [
        os.environ.get("FUTURESHARKS_DIR"),
        REPO_ROOT / "data" / "raw" / "financial-data",
        REPO_ROOT.parent / "futuresharks" / "financial-data",
        REPO_ROOT.parent / "financial-data",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    raise FileNotFoundError(
        "No encuentro FutureSharks/financial-data. Clónalo (ver README) y/o define FUTURESHARKS_DIR."
    )


def load_futuresharks(symbol: str, root: str | Path | None = None, use_cache: bool = True) -> pd.DataFrame:
    """Carga los CSV mensuales de Oanda (UTC) del instrumento equivalente a `symbol`."""
    inst = FUTURESHARKS_MAP.get(symbol.upper(), symbol)
    cache = CACHE_DIR / f"futuresharks_{inst}.parquet"
    if use_cache and cache.exists():
        return pd.read_parquet(cache)
    base = Path(root) if root else futuresharks_dir()
    files = sorted(glob.glob(str(base / "pyfinancialdata" / "data" / "currencies" / "oanda" / inst / "*" / "*.csv")))
    if not files:
        raise FileNotFoundError(f"No hay CSVs para {inst} en {base}")
    raw = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    df = _finalize(raw, time_col="time", tz="UTC")
    if use_cache:
        _write_cache(df, cache)
    return df


def load_csv(path: str | Path, tz: str = "UTC", fmt: str = "auto", use_cache: bool = False) -> pd.DataFrame:
    """Carga uno o varios CSV (acepta comodines: 'data/raw/ES_*.csv').

    tz:  zona horaria de los timestamps si vienen sin zona (Databento/IBKR suelen ser UTC;
         exportaciones de NinjaTrader/TradingView suelen estar en la hora local o del exchange).
    fmt: 'auto' (cabecera con time/open/high/low/close/volume) o 'ninjatrader'
         (formato 'yyyyMMdd HHmmss;open;high;low;close;volume' sin cabecera).
    """
    files = sorted(glob.glob(str(path))) or [str(path)]
    cache = CACHE_DIR / (Path(files[0]).stem + f"_{len(files)}.parquet")
    if use_cache and cache.exists():
        return pd.read_parquet(cache)
    frames = []
    for f in files:
        if fmt == "ninjatrader":
            raw = pd.read_csv(f, sep=";", header=None, names=["time", "open", "high", "low", "close", "volume"])
            raw["time"] = pd.to_datetime(raw["time"], format="%Y%m%d %H%M%S")
        else:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                head = fh.readline()
            raw = pd.read_csv(f, sep=";" if head.count(";") > head.count(",") else ",")
        frames.append(raw)
    df = _finalize(pd.concat(frames, ignore_index=True), time_col=None, tz=tz)
    if use_cache:
        _write_cache(df, cache)
    return df


def _finalize(raw: pd.DataFrame, time_col: str | None, tz: str) -> pd.DataFrame:
    df = raw.rename(columns={c: _ALIASES.get(str(c).strip().lower(), str(c).strip().lower()) for c in raw.columns})
    if time_col is None:
        if {"date", "time"} <= set(df.columns) and not pd.api.types.is_numeric_dtype(df["date"]):
            df["datetime"] = df["date"].astype(str) + " " + df["time"].astype(str)
            time_col = "datetime"
        else:
            time_col = next((c for c in _TIME_COLS if c in df.columns), None)
    if time_col is None:
        raise ValueError(f"No encuentro la columna de tiempo. Columnas: {list(df.columns)}")
    ts = df[time_col]
    if pd.api.types.is_numeric_dtype(ts):  # epoch en s / ms / ns
        unit = "s" if ts.max() < 1e11 else "ms" if ts.max() < 1e14 else "ns"
        idx = pd.to_datetime(ts, unit=unit, utc=True)
    else:
        try:
            idx = pd.to_datetime(ts)  # rápido: infiere el formato de la primera fila
        except (ValueError, TypeError):
            idx = pd.to_datetime(ts, format="mixed")
        if getattr(idx.dt, "tz", None) is None:
            idx = idx.dt.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
    missing = [c for c in ("open", "high", "low", "close") if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas {missing}. Columnas: {list(df.columns)}")
    out = pd.DataFrame(
        {
            "open": df["open"].astype(float).to_numpy(),
            "high": df["high"].astype(float).to_numpy(),
            "low": df["low"].astype(float).to_numpy(),
            "close": df["close"].astype(float).to_numpy(),
            "volume": (df["volume"].astype(float).to_numpy() if "volume" in df.columns else 1.0),
        },
        index=pd.DatetimeIndex(idx).tz_convert(ET),
    )
    out = out[out.index.notna()]
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out.index.name = "time"
    return out


def _write_cache(df: pd.DataFrame, path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)
    except (ImportError, ValueError, OSError):
        pass  # sin pyarrow no hay caché; no es grave


def resample(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Agrega barras de 1 minuto a barras de N minutos (etiqueta = inicio de la barra)."""
    rule = f"{minutes}min"
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return df.resample(rule, label="left", closed="left").agg(agg).dropna(subset=["open"])
