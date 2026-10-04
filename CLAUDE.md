# CLAUDE.md

**BOTtrading / futbot**: investigación de estrategias intradía de futuros (ES, NQ, GC, CL, ZN, 6E, RTY) y kit de
backtesting en Python con simulador de evaluaciones de prop firms (Topstep, Apex, Tradeify, MFFU, Lucid) y CLI.

## Entorno (Windows / PowerShell)
```powershell
python -m venv .venv                 # solo la primera vez (Python >= 3.10)
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Comandos
```powershell
python -m pytest                                          # tests (motor, estrategias, prop firms, datos)
python -m futbot list                                     # estrategias, recetas y prop firms
python -m futbot backtest --recipe nq_noise_area --symbol NQ   # verificación vs docs/RESULTADOS_BACKTEST.md
```
Los datos de 1 min se leen de `data/raw/financial-data` (sparse clone de FutureSharks/financial-data, ver README)
o de un CSV con `--csv ... --tz UTC`.

`data/oanda/` (sí versionado): histórico reciente de OANDA MT5 (M1 desde jun-2026, M5 desde may-2025) de
US500, US100, US2000, XAUUSD, USOIL y EURUSD, bajado con `scripts/download_mt5.py` (requiere MT5 abierto).
La columna `time` es la hora del servidor MT5 (Nueva York + 7 h), no UTC: cargar siempre con `--tz mt5`.
Ej.: `python -m futbot backtest --recipe nq_noise_area --symbol NQ --csv data/oanda/US100_M1.csv.gz --tz mt5`

## Estructura
- `futbot/`: `engine.py` (motor), `strategies/` (estrategias; heredan de `futbot.strategies.base.Strategy`),
  `recipes.py` (estrategia + mercado), `propfirm.py` (reglas de evaluación), `data.py`, `metrics.py`,
  `report.py`, `contracts.py`, `cli.py`
- `tests/`: pytest
- `docs/`: `INVESTIGACION_ESTRATEGIAS.md`, `RESULTADOS_BACKTEST.md`, `ESTRATEGIA_TRADINGVIEW.md` (el bot de TradingView)
- `pine/orb5_puntaje.pine` (indicador) y `pine/orb5_puntaje_estrategia.pine` (strategy): mismas reglas que
  `futbot/strategies/puntaje.py` (recetas `nq_orb5_puntaje` y `es_orb5_puntaje`). Si cambias una regla, cámbiala
  en los dos lados. Backtest del bot: `python scripts/backtest_puntaje.py --nq ... --es ... [--tz mt5]`

## No se suben a git
`data/raw/`, `data/cache/`, `results/` y `.venv/` (ya están en `.gitignore`).
