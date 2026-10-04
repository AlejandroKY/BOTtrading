# BOTtrading — estrategias de futuros + backtesting para cuentas de fondeo

Investigación y kit en Python para construir un bot de futuros (ES, NQ, GC, CL, ZN, 6E) pensado
para las reglas de las prop firms (Topstep, Apex, Tradeify, MyFundedFutures, Lucid...).

- 📈 **[pine/orb5_puntaje.pine](pine/orb5_puntaje.pine)**: el bot de señales para **TradingView** (NQ y ES,
  trade de 9:35 a 10:35 NY como máximo). Da a cada señal un **puntaje de calidad 0-100**, elige el mercado (NQ
  primero, ES de respaldo) y muestra compra/venta, stop, parcial en +2R con stop a la entrada, contratos para tu
  riesgo, panel y alertas al celular. También hay una versión para el Probador de estrategias:
  [pine/orb5_puntaje_estrategia.pine](pine/orb5_puntaje_estrategia.pine). Validado con datos reales de CME
  2019-2026 (43 % de acierto, +0,37R por operación, 8 de 8 años positivos). Suma una **segunda estrategia** en NQ
  (Noise Area a las 10:00 a favor del gap, salida a las 11:00, mitad del riesgo): juntas aprueban 76 % de las
  cuentas LucidFlex 50K simuladas en NQ 2019-2026, sin suspensos.
  Guía completa (resultados, cuenta de fondeo recomendada, instalación, alertas, ejecución):
  **[docs/ESTRATEGIA_TRADINGVIEW.md](docs/ESTRATEGIA_TRADINGVIEW.md)**.
- 📄 **[docs/INVESTIGACION_ESTRATEGIAS.md](docs/INVESTIGACION_ESTRATEGIAS.md)**: las 7 estrategias (reglas exactas,
  evidencia publicada y fuentes), reglas de prop firms 2026, si permiten bots, repositorios recomendados y hoja de ruta.
- 📊 **[docs/RESULTADOS_BACKTEST.md](docs/RESULTADOS_BACKTEST.md)**: backtest independiente de todas las estrategias
  (2005-2020, costos realistas) y probabilidad de aprobar evaluaciones de 50K.
- 🧰 **`futbot/`**: motor de backtesting intradía, estrategias, simulador de evaluaciones de prop firm y CLI.

> ⚠️ Esto es investigación, no asesoría financiera. Los resultados pasados (y más aún los simulados) no garantizan
> nada. Las reglas de las prop firms cambian: verifica en sus webs antes de comprar una evaluación.

## Instalación

Requiere Python 3.10+.

```bash
pip install -r requirements.txt
python -m pytest            # tests del motor, estrategias y simulador
python -m futbot list       # estrategias, recetas y presets de prop firms
```

## Datos

**Opción A — datos gratis para investigar (CFDs de Oanda 2005-2020, ~1,5 GB).** Descarga solo los mercados
necesarios del repositorio público [FutureSharks/financial-data](https://github.com/FutureSharks/financial-data):

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/FutureSharks/financial-data data/raw/financial-data
cd data/raw/financial-data
git sparse-checkout set --no-cone $(for i in SPX500_USD NAS100_USD XAU_USD WTICO_USD USB10Y_USD EUR_USD US2000_USD; \
    do echo "pyfinancialdata/data/currencies/oanda/$i/"; done)
cd ../../..
```

El kit lo encuentra solo en `data/raw/financial-data` (o define `FUTURESHARKS_DIR`). La primera carga de cada
mercado tarda ~15 s; luego queda en caché en `data/cache/`.

**Opción B — tus propios datos de CME (recomendado antes de operar).** Cualquier CSV de 1 minuto con columnas
de tiempo y `open, high, low, close[, volume]` (Databento, TradingView, IBKR, FirstRate...). Por ejemplo con
[Databento](https://databento.com/futures) (trae $125 de crédito gratis):

```python
import databento as db  # pip install databento

client = db.Historical("TU_API_KEY")
data = client.timeseries.get_range(
    dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=["NQ.v.0"], stype_in="continuous",
    start="2019-01-01", end="2026-09-30",
)
data.to_df().to_csv("data/raw/NQ_1m.csv")  # timestamps en UTC (columna ts_event)
```

```bash
python -m futbot backtest --recipe nq_noise_area --symbol NQ --csv data/raw/NQ_1m.csv --tz UTC
```

Exportaciones de NinjaTrader (`yyyyMMdd HHmmss;open;high;low;close;volume`): `--fmt ninjatrader --tz <zona de la exportación>`.

## Uso

```bash
# Backtest de una receta (estrategia + mercado + parámetros de su paper)
python -m futbot backtest --recipe nq_noise_area                 # con micros (MNQ)
python -m futbot backtest --recipe nq_noise_area --symbol NQ     # con el mini
python -m futbot backtest --recipe nq_orb5 --start 2015-01-01 --save results/

# Cambiar parámetros o costos
python -m futbot backtest --recipe nq_noise_area --symbol NQ --param stop_pct=0.5 --dll 800
python -m futbot backtest --strategy range_breakout --symbol MCL \
    --param window_start=09:00 --param window_end=14:30 --param range_start=09:00 --param range_end=09:15

# ¿Con cuántos contratos y qué probabilidad tengo de aprobar una evaluación?
python -m futbot prop --recipe nq_orb5 --firm topstep_50k --firm tradeify_growth_50k --max-size 15

# Backtest del bot de TradingView (NQ primero + ES de respaldo) y probabilidad de aprobar cuentas de 50K
python scripts/backtest_puntaje.py --nq data/oanda/US100_M5.csv.gz --es data/oanda/US500_M5.csv.gz --tz mt5
python scripts/backtest_puntaje.py --nq "data/real/NQ_1m_*.parquet" --es "data/real/ES_1m_*.parquet"

# Acierto y R medio de una receta, netos y brutos, por dirección y por año
python -m futbot stats --recipe nq_orb5_puntaje --symbol MNQ --csv "data/real/NQ_1m_*.parquet"

# Regenerar docs/RESULTADOS_BACKTEST.md con todas las recetas (~7 min)
python -m futbot report
```

Recetas incluidas (`python -m futbot list`): `nq_orb5_puntaje`, `es_orb5_puntaje` y `nq_ruido10` (las del indicador de TradingView), `nq_orb5_rapida` y `nq_orb5_gap` (versiones anteriores), `nq_orb5`, `nq_orb5_atr`, `es_orb5`, `es_noise_area`, `nq_noise_area`,
`es_last30`, `nq_last30`, `zn_last30`, `gc_last30`, `cl_last30`, `6e_last30`, `cl_orb15`, `gc_london`, `6e_london`,
`es_orb30`, `nq_orb30`, `es_gap_fill`, `nq_gap_fill`, `gc_day_short`.

## Estructura

```
futbot/
├── contracts.py      # specs de ES/MES, NQ/MNQ, GC/MGC, CL/MCL, ZN, 6E/M6E... (tick, $/tick, comisión)
├── data.py           # carga de CSV (UTC → hora de Nueva York) y de FutureSharks, caché parquet
├── engine.py         # motor barra a barra: market/stop/limit, brackets OCO, slippage, límite diario, sin overnight
├── strategies/       # puntaje.py (ORB 5 min con puntaje: el bot de TradingView) · orb.py · opening.py
│                     # momentum.py (Noise Area, última media hora) · reversion.py (gap fill, sesgo horario)
├── recipes.py        # estrategia + mercado + parámetros de cada fuente
├── metrics.py        # win rate, profit factor, payoff, Sharpe, drawdown, peor día, tabla anual
├── propfirm.py       # simulador de evaluaciones (trailing EOD/intradía, DLL, consistencia, plazo) + presets 50K
├── portfolio.py      # un trade por día entre dos mercados (NQ primero, ES de respaldo)
├── report.py         # genera docs/RESULTADOS_BACKTEST.md
└── cli.py            # python -m futbot ...
tests/                # tests del motor, estrategias y simulador
pine/                 # indicador y estrategia de TradingView (mismas reglas que nq_orb5_puntaje / es_orb5_puntaje / nq_ruido10)
scripts/              # backtest del bot (backtest_puntaje.py) y descarga de datos (Databento, MetaTrader 5)
```

## Escribir una estrategia nueva

```python
from futbot.engine import sm, run_backtest
from futbot.strategies.base import Strategy


class MiEstrategia(Strategy):
    name = "mi_estrategia"
    default_params = dict(window_start="09:30", window_end="16:00", qty=1)

    def on_session_start(self, ctx):          # antes de la primera barra del día
        self.hecho = False

    def on_bar(self, ctx):                     # ctx.O/H/L/C/V[ctx.i], ctx.S[ctx.i] = minuto de sesión
        if not self.hecho and ctx.S[ctx.i] == sm("10:00") - 1:   # barra que cierra a las 10:00
            if ctx.C[ctx.i] > ctx.O[0]:
                ctx.buy(self.p["qty"], stop_offset=20, target_r=2)  # bracket: stop a 20 puntos, target 2R
            self.hecho = True
```

Las órdenes se ejecutan desde la barra siguiente; toda posición se cierra al final de `window_end`.
Supuestos de ejecución (conservadores) documentados en `futbot/engine.py`.

## Del backtest al bot en vivo

La lógica de cada estrategia sólo usa barras de 1 minuto y el `Context`, así que para operar en vivo basta con
alimentarla con barras en tiempo real y traducir `ctx.buy/sell/flatten` a la API de tu plataforma
(TopstepX/ProjectX con [`project-x-py`](https://github.com/TexasCoding/project-x-py), Tradovate o Rithmic con
[`async_rithmic`](https://github.com/rundef/async_rithmic)). La hoja de ruta completa está en la
[sección 5 de la investigación](docs/INVESTIGACION_ESTRATEGIAS.md#5-hoja-de-ruta-para-el-nuevo-bot).
