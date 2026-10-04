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
python -m pytest                                          # 30 tests
python -m futbot list                                     # estrategias, recetas y prop firms
python -m futbot backtest --recipe nq_noise_area --symbol NQ   # verificación vs docs/RESULTADOS_BACKTEST.md
```
Los datos de 1 min se leen de `data/raw/financial-data` (sparse clone de FutureSharks/financial-data, ver README)
o de un CSV con `--csv ... --tz UTC`.

## Estructura
- `futbot/`: `engine.py` (motor), `strategies/` (estrategias; heredan de `futbot.strategies.base.Strategy`),
  `recipes.py` (estrategia + mercado), `propfirm.py` (reglas de evaluación), `data.py`, `metrics.py`,
  `report.py`, `contracts.py`, `cli.py`
- `tests/`: pytest
- `docs/`: `INVESTIGACION_ESTRATEGIAS.md`, `RESULTADOS_BACKTEST.md`

## No se suben a git
`data/raw/`, `data/cache/`, `results/` y `.venv/` (ya están en `.gitignore`).
