# Investigación: estrategias de futuros para el bot y su uso en cuentas de fondeo

*Octubre de 2026. Esto es investigación, no asesoría financiera. Operar futuros con apalancamiento puede hacerte perder más de lo que pones; las reglas de las prop firms cambian seguido, así que verifica todo en sus webs oficiales.*

---

## 0. Resumen en un minuto

**Qué busqué.** Estrategias **mecánicas** (automatizables al 100 %), **intradía** (las prop firms de futuros exigen cerrar todo antes del cierre de la sesión), con **evidencia pública** (papers o estadísticas reproducibles) y para **mercados de futuros distintos**. Encontré 7 familias que cubren 6 mercados: Nasdaq-100 (NQ), S&P 500 (ES), petróleo (CL), oro (GC), euro (6E) y bono a 10 años (ZN).

**Qué hice además.** Programé las 7 en un kit de backtesting (`futbot/`) y las probé con costos realistas sobre 15 años de datos de 1 minuto (2005-2020), además de simular miles de evaluaciones de prop firm (Topstep, Apex, Tradeify...). Los resultados completos están en [`RESULTADOS_BACKTEST.md`](RESULTADOS_BACKTEST.md).

**Lo que dicen los datos, sin maquillaje:**

1. Casi todas tienen **ventaja bruta positiva** (antes de costos), pero es pequeña. Con comisiones y slippage realistas **solo sobreviven las de momentum/ruptura en el Nasdaq** (Noise Area y ORB de 5 minutos), y con contratos **mini** (con micros, las comisiones se comen la ventaja).
2. Las que tienen **win rate alto** (cierre de gap, ~50 %) **no ganaron dinero**. Las que más ganaron (Nasdaq) tienen win rate **bajo** (17-35 %) y ganancias grandes cuando aciertan. El win rate solo no dice nada (ver sección 1).
3. **"Pasar fondeos fácilmente" no existe.** Una estrategia sin ventaja (Sharpe 0) aprueba un 23-26 % de las evaluaciones *por pura suerte*; para aprobar 65-75 % de las veces necesitas Sharpe ≥ 2 **y** un tamaño prudente. En la industria aprueba un 5-15 % de quienes compran evaluaciones y cobra alguna vez ~7 %.
4. Las mejores candidatas para tu nuevo bot: **(1) Noise Area en NQ** y **(2) ORB de 5 minutos en NQ**, seguidas de **CL primera media hora** y **ruptura del rango asiático en oro** como diversificadoras. Antes de arriesgar dinero hay que **re-validarlas con datos reales de CME 2019-2026** (ver sección 5): el kit ya está preparado para eso.

> **Actualización (octubre de 2026):** la estrategia del bot de TradingView es un trade rápido en NQ.
> Se opera el ORB de 5 minutos solo en días "en juego" (gap ≥ 0,30 ATR), con el stop en la mitad de la vela de
> 9:30-9:35 y salida como máximo a las 10:35. Se validó con datos reales de MNQ 2019-2026 (+0,30R por operación neto,
> 8 de 8 años positivos). La versión anterior, con salida a las 11:30, rindió solo +0,08R con esos datos.
> Reglas, números y guía en [ESTRATEGIA_TRADINGVIEW.md](ESTRATEGIA_TRADINGVIEW.md); el indicador está en
> [`pine/orb5_nq_rapido.pine`](../pine/orb5_nq_rapido.pine).

---

## 1. Cómo evaluar una estrategia (y por qué el win rate solo engaña)

| Métrica | Qué es | Por qué importa |
|---|---|---|
| **Win rate** | % de trades ganadores | Por sí sola no sirve: 20 % de aciertos con ganancias de 4R gana más que 60 % con ganancias de 0,5R |
| **Payoff** | ganancia media / pérdida media | Combinada con el win rate da la expectativa |
| **Profit factor (PF)** | ganancias brutas / pérdidas brutas | < 1 pierde; 1,1-1,3 es una ventaja modesta; > 1,5 sostenido en años es raro |
| **Expectativa** | ganancia media por trade, **después de costos** | Tiene que ser bastante mayor que comisión + slippage |
| **Sharpe (anual)** | rentabilidad media / volatilidad del P&L diario × √252 | La métrica clave para prop firms: decide la probabilidad de llegar al objetivo antes que al drawdown |
| **Max drawdown y peor día** | la peor racha y el peor día | En una cuenta de fondeo un solo día malo te elimina |

Regla útil: **win rate mínimo para no perder = 1 / (1 + payoff)**. Con payoff 2 necesitas más de 33 %; con payoff 0,5, más de 67 %. Por eso un "90 % de aciertos" casi siempre esconde pérdidas enormes cuando falla (martingalas, grids o stops lejanísimos).

**Costos.** Con el mismo movimiento de precio, un micro paga en comisión ~3 veces más por punto que un mini (MNQ: $1,40 ida y vuelta = 0,7 puntos de NQ; NQ: $4,50 = 0,22 puntos). Una estrategia que gana 1-2 puntos por trade puede ser rentable con NQ y perdedora con MNQ.

---

## 2. Las estrategias

### Tabla resumen

| # | Estrategia | Mercado | Tipo | Horario (hora de Nueva York) | Evidencia publicada | Win rate | Mi backtest 2005-2020 (1 mini, neto) | Veredicto |
|---|---|---|---|---|---|---|---|---|
| 1 | ORB de 5 minutos | **NQ** / MNQ | Ruptura | 09:30-16:00 | Paper SSRN 2023 + 2024 (QQQ/acciones) | ~17-21 % | PF 1,08-1,10 · Sharpe 0,30-0,36 (0,51-0,58 desde 2015) | **Candidata** |
| 2 | Noise Area (momentum intradía) | **NQ**, ES | Momentum | 10:00-16:00 | Paper SSRN 2024 + 2 réplicas en futuros | ~31-34 % | NQ: PF 1,13 · Sharpe 0,49 (1,04 desde 2015) · ES: ≈ 0 | **La mejor en NQ** |
| 3 | Momentum de la última media hora | ES, NQ, GC, CL, ZN, 6E | Momentum | últimos 30 min de la sesión | 2 papers en el *Journal of Financial Economics* | ~43-49 % | Ventaja bruta real, pero los costos la anulan (NQ ≈ 0) | Solo como filtro |
| 4 | Petróleo: 1ª media hora → última | **CL** / MCL | Momentum | 09:00-14:30 | Paper *Economic Modelling* 2021 | ~49 % | PF 1,06 · Sharpe 0,30 (≈ 0 desde 2015) | Diversificadora (débil) |
| 5 | Oro: ruptura del rango asiático (Londres) | **GC** / MGC | Ruptura | rango 19:00-03:00, operar 03:00-10:00 | Práctica muy usada (sin paper sólido) | ~46 % | PF 1,03 · Sharpe 0,20 (negativo desde 2015) | Diversificadora (débil) |
| 6 | London breakout | **6E** / M6E | Ruptura | rango 19:00-03:00, operar 03:00-09:00 | Backtests de foros/blogs | ~46 % | PF 0,94 · negativo | Descartada en su forma simple |
| 7 | Cierre del gap de apertura | **ES**, NQ | Reversión | 09:30-12:00 | Estadística: 60-70 % de gaps se cierran | ~49-51 % | ES: PF 0,81 · NQ: PF 0,99 | Descartada (pese al win rate) |

*Neto = con comisión de $4,50 por mini, slippage y redondeo al tick. Detalle completo, micros y resultados año por año en [`RESULTADOS_BACKTEST.md`](RESULTADOS_BACKTEST.md).*

---

### Estrategia 1 — ORB (Opening Range Breakout) de 5 minutos · Nasdaq-100 (NQ / MNQ)

**Idea.** La primera vela de 5 minutos tras la apertura de Wall Street (09:30) marca hacia dónde empuja el flujo institucional del día; se apuesta a que continúa.

**Reglas exactas** (Zarattini & Aziz, 2023):
1. Mira la vela 09:30-09:35. Si cierra **alcista** → **compra** a las 09:35; si cierra **bajista** → **vende**; si es doji → no operes.
2. **Stop**: el mínimo de esa vela (largos) o su máximo (cortos).
3. **Target**: 10 veces el riesgo (10R). Si no se toca ni el stop ni el target, **cierra a las 16:00**.
4. *Variante 2024* (Zarattini, Barbon & Aziz): stop a **10 % del ATR(14) diario** y sin target (salida al cierre).

**Evidencia publicada.**
- Paper 2023 ([SSRN 4416622](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622)): en QQQ 2016-2023, la versión con TQQQ ganó **1.484 %** frente al 169 % de comprar y mantener QQQ, con un alfa anual de ~33 % según los autores. Resúmenes del paper hablan de ~24 % de aciertos ([danfin.net](https://danfin.net/opening-range-breakout-research)).
- Paper 2024 ([SSRN 4729284](https://www.wealth-lab.com/api/discussion/download/pdf/8007-ssrn-4729284-1-pdf)): aplicado a las 20 "Stocks in Play" (acciones con volumen anormal), **+1.600 % neto, Sharpe 2,81** (2016-2023). Ojo: es en acciones, no en futuros.

**Mi backtest** (NQ, 2005-2020): win rate 20,7 %, payoff 4,1, PF 1,08, **+$2.287/año por contrato**, Sharpe 0,30 (**0,58 desde 2015**), pero drawdown máximo de $22.000 con 1 NQ. La variante con stop ATR da PF 1,10 y Sharpe 0,36 con menos drawdown ($16.600). En ES pierde. **Con micros (MNQ) queda en cero** por las comisiones. Coincide con el paper en que funciona mejor desde 2016.

**Para cuentas de fondeo.** Win rate bajo = rachas de hasta 37 pérdidas seguidas, psicológicamente duras pero inofensivas si el riesgo por trade es pequeño. El riesgo de cada trade (el rango de la vela de 5 min) tuvo una mediana de ~10 puntos de NQ en 2015-2020 ($200 por NQ, $20 por MNQ) y de ~25 puntos en los días más volátiles; con el NQ a precios actuales, más alto, esos rangos en puntos son mayores. En una cuenta 50K encaja **1 NQ o 3-5 MNQ**.

**Riesgos.** El target de 10R casi nunca se toca: la ganancia viene de los días de tendencia que cierras a las 16:00. Si el mercado entra en rango durante meses (2005-2007, 2010-2012), pierdes de a poco.

---

### Estrategia 2 — "Noise Area" (momentum intradía) · NQ y ES

**Idea.** Durante el día el precio se mueve dentro de un "ruido" normal. Cuando se sale de lo normal para esa hora, suele haber un desequilibrio de órdenes que continúa (fondos que rebalancean, coberturas de opciones gamma).

**Reglas exactas** (Zarattini, Aziz & Barbon, 2024):
1. Para cada minuto del día calcula `σ(t)` = promedio, en los **últimos 14 días**, de `|precio(t) / apertura − 1|` a esa misma hora.
2. Bandas: `superior = max(apertura, cierre de ayer) × (1 + σ(t))` e `inferior = min(apertura, cierre de ayer) × (1 − σ(t))`.
3. Solo en los checkpoints de cada media hora (10:00, 10:30 … 15:30): si el precio está **sobre la banda superior → largo**; **bajo la inferior → corto**; dentro → nada.
4. **Salida**: trailing stop en `max(banda superior, VWAP)` para largos (`min(banda inferior, VWAP)` para cortos), revisado en los mismos checkpoints; cierre obligatorio a las 16:00.
5. El paper ajusta el tamaño para tener volatilidad diaria constante (2 %, máximo 4x apalancamiento).

**Evidencia publicada.**
- Paper ([SSRN 4824172](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172)): SPY 2007-2024, **+1.985 % neto, 19,6 % anual, Sharpe 1,33**.
- Réplica en futuros de [Quantitativo](https://www.quantitativo.com/p/intraday-momentum-for-es-and-nq): win rate ~39 %, payoff ~2; **ES: 8,1 % anual, Sharpe 0,91, drawdown 24 %; NQ: hasta 24,3 % anual, Sharpe 1,67**.
- Réplica independiente con protocolo anti-sobreajuste ([codecat-ops/zarattini-2024-momentum-spy](https://github.com/codecat-ops/zarattini-2024-momentum-spy)): SPY 2020-2026 Sharpe 1,11; en ES (2024-2026) 41 % de aciertos y payoff 1,69, **pero Sharpe ≈ 0 desde 2025**: la ventaja se ha comprimido últimamente. Hay que vigilarlo.

**Mi backtest** (2005-2020, 1 contrato, sin el ajuste por volatilidad): **NQ: win rate 34 %, payoff 2,2, PF 1,13, +$3.278/año, Sharpe 0,49 y 1,04 desde 2015**, drawdown $13.100. En ES queda en cero tras costos (Sharpe bruto 0,75). Es la estrategia más sólida que probé.

**Para cuentas de fondeo.** Su peor día con 1 NQ fue **−$5.958** (19-mar-2020, en pleno crash del COVID), porque entre checkpoints no hay stop. Con un stop duro del 0,5 % el peor día bajó a −$4.030 (3-mar-2020: recorte de emergencia de la Fed a las 10:00, el precio saltó por encima del stop). Con un trailing de $2.000 cualquiera de los dos quema la cuenta. Imprescindible: **stop duro** (`stop_pct`), **límite de pérdida diaria en el bot**, **no operar días de FOMC/CPI** y tamaño de 3-6 MNQ o 1 NQ como máximo.

---

### Estrategia 3 — Momentum de la última media hora · multi-mercado (ES, NQ, GC, CL, ZN, 6E)

**Idea.** Lo que el mercado hizo durante el día tiende a continuar en la última media hora, porque los market makers de opciones y los ETFs apalancados tienen que cubrirse en la dirección del movimiento antes del cierre.

**Reglas exactas.**
1. 30 minutos antes del cierre de la sesión (15:30 en ES/NQ, 13:00 en oro, 14:00 en petróleo, 14:30 en ZN y 6E) calcula el retorno desde el cierre de ayer.
2. Si es positivo → **compra**; si es negativo → **vende**. Sal en el cierre.

**Evidencia publicada.**
- Gao, Han, Li & Zhou (2018, *Journal of Financial Economics*, [SSRN 2440866](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)): SPY 1993-2013, la primera media hora predice la última; estrategia con **6,67 % anual y Sharpe 1,08** (vs 0,29 de comprar y mantener); **20 % anual en días de FOMC**.
- Baltussen, Da, Lammers & Martens (2021, *JFE*, [SSRN 3760365](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365)): el efecto existe en **más de 60 futuros** de acciones, bonos, materias primas y divisas (1974-2020) y se explica por coberturas gamma.

**Mi backtest.** La ventaja **bruta** existe en ES, NQ, CL y oro (Sharpe bruto 0,37-0,84), pero es de ~1 punto de ES por trade: con costos queda en cero o negativa (NQ: +$318/año, 0,45 desde 2015). En ZN y 6E los costos superan con creces el movimiento de 30 minutos.

**Uso recomendado.** No como estrategia sola, sino como **filtro** del bot: no abrir posiciones *contra* la dirección del día en la última media hora, o dejar correr las posiciones a favor hasta el cierre.

---

### Estrategia 4 — Petróleo (CL / MCL): la primera media hora predice la última

**Reglas.** Igual que la estrategia 3, pero el predictor es el retorno desde el cierre de ayer (14:30) hasta las **09:30** (primera media hora de NYMEX, incluye la noche). Entrada a las 14:00, salida a las 14:30.

**Evidencia.** Wen, Gong, Ma & Xu (2021, *Economic Modelling*, [SSRN 3553682](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3553682_code2537556.pdf?abstractid=3553682&mirid=1)): R² fuera de muestra de 0,659 % (alto para un predictor de un solo día); el efecto es más fuerte con **alta volatilidad, alto volumen y saltos nocturnos**.

**Mi backtest** (1 CL): win rate 49 %, PF 1,06, +$2.022/año, Sharpe 0,30 — pero ≈ 0 desde 2015. El **ORB de las 09:00-09:15** (otra estrategia popular en CL) perdió dinero (PF 0,93).

**Veredicto.** Útil como diversificadora, idealmente filtrando por los días de alta volatilidad nocturna que señala el paper (siguiente experimento a hacer con el kit).

---

### Estrategia 5 — Oro (GC / MGC): ruptura del rango asiático en la apertura de Londres

**Reglas.**
1. Marca el máximo y el mínimo de **19:00 a 03:00** (sesión asiática).
2. A partir de las 03:00 (Londres) coloca **compra stop** 2 ticks sobre el máximo y **venta stop** 2 ticks bajo el mínimo (OCO: si se activa una, se cancela la otra).
3. **Stop** en el lado opuesto del rango; **target 1,5R**; órdenes pendientes canceladas a las 10:00; cierre a las 11:30.

**Evidencia.** Es de las más usadas por traders de oro y de prop firms, pero no encontré estudios rigurosos; los backtests públicos son de TradingView y blogs. Hay un paper sobre una **anomalía día/noche** en el oro ([Journal of Economics and Finance, 2018](https://link.springer.com/article/10.1007/s12197-017-9403-0)): retornos positivos de noche y negativos durante la sesión de COMEX.

**Mi backtest** (1 GC): win rate 46 %, PF 1,03, +$2.326/año, Sharpe 0,20; **negativa desde 2015**. La anomalía día/noche (vender oro a las 08:20 y cerrar a las 13:30) también perdió (PF 0,94).

**Veredicto.** Marginal. Puede aportar diversificación (no se correlaciona con el Nasdaq), pero no la pondría sola.

---

### Estrategia 6 — Euro (6E / M6E): London breakout

**Reglas.** Las mismas de la estrategia 5 con el euro: rango 19:00-03:00, ruptura entre 03:00 y 09:00, stop en el lado opuesto, target 1,5R, cierre a las 11:00.

**Evidencia.** Backtests de foros y blogs: win rate 41-55 % y profit factor de 1,35-1,5 solo con target de 1,5R; las variantes populares dan resultados "débiles o mixtos" ([medium/@phitzi](https://medium.com/@phitzi/backtest-results-revealed-is-the-london-breakout-strategy-worth-it-0e9df65dd63b), [ForexFactory](https://www.forexfactory.com/thread/230640-a-simple-london-breakout)).

**Mi backtest** (1 6E): PF 0,94, −$3.033/año. **Descartada** en su forma simple.

---

### Estrategia 7 — Cierre del gap de apertura · ES y NQ (la de "win rate alto")

**Reglas.**
1. Gap = apertura de las 09:30 − cierre de las 16:00 de ayer.
2. Si el gap está entre **0,10 % y 0,60 %** (ES; 0,15-0,80 % en NQ), opera **en contra** del gap a la apertura.
3. **Target** = cierre de ayer (gap cerrado); **stop** = el mismo tamaño del gap en contra; salida a las 12:00.

**Evidencia.** Estadísticas públicas: ES cierra el gap en la misma sesión ~60-70 % de las veces, más cuanto más pequeño ([edgeful](https://www.edgeful.com/blog/posts/es-futures-trading-strategies), [tradingstats.net](https://tradingstats.net/gap-fill-strategy/)).

**Mi backtest.** Win rate 49 % (ES) y 51 % (NQ), pero **PF 0,81 y 0,99**: pierde. Lección importante: *"el 70 % de los gaps se cierran"* no es lo mismo que *"la estrategia gana"*: el gap suele crecer antes de cerrarse (y salta el stop), y cuando no se cierra la pérdida es mayor que la ganancia típica.

---

### Otras que probé o revisé y no recomiendo tal cual

- **ORB de 30 minutos manteniendo hasta el cierre (ES/NQ)**: la estadística de "continuación" del 65-67 % ([tradingstats.net](https://tradingstats.net/orb-breakout-strategy-guide/)) no se convierte en ganancias con stop en el lado opuesto del rango: PF 0,83-0,89.
- **ICT Silver Bullet**: muy popular en prop firms, se anuncian 70-80 % de aciertos, pero un backtest mecánico público en NQ da **25,9 % de aciertos y PF 0,51** (27 trades, muestra chica) ([repo](https://github.com/cjosh4toyotas-stack/silver-bullet-backtest)). Depende de filtros discrecionales difíciles de automatizar.
- **Scripts de "90 % de aciertos"** (TradingView/GitHub): casi siempre son grids, martingalas o indicadores que repintan. Desconfía de cualquier win rate sin profit factor, drawdown y costos.

---

## 3. Cuentas de fondeo (prop firms de futuros) en 2026

### 3.1 Reglas de una cuenta de 50K (resumen a octubre de 2026)

| Firma (plan) | Objetivo | Drawdown | Tipo | Límite diario | Consistencia en evaluación | Plazo | ¿Bots? |
|---|---|---|---|---|---|---|---|
| **Topstep** (Trading Combine 50K) | $3.000 | $2.000 | Trailing al cierre del día (se fija en $50.000) | Opcional | Mejor día ≤ 50 % del beneficio | Sin límite (pago mensual) | **Sí**, vía API de TopstepX (ProjectX), desde tu propio equipo, **sin VPS/VPN**, sin HFT. API: $29/mes ($14,50 con descuento) |
| **Apex** (4.0, 50K EOD) | $3.000 | $2.000 | Trailing al cierre | $1.000 (pausa el día) | No (50 % para cobrar en la cuenta PA) | **30 días naturales** | En evaluación sí; en cuentas PA/live **prohíbe el bot totalmente desatendido**: tiene que estar supervisado |
| **Tradeify** (Growth 50K) | $3.000 | $2.000 | Trailing al cierre | $1.250 (pausa) | No | Se puede aprobar en 1 día | Permite automatización y copy trading (sin HFT/arbitraje) |
| **MyFundedFutures** (Pro 50K) | $3.000 | $2.000 | Trailing al cierre | No tiene | 50 % | — | Permite algo trading desde julio de 2025 |
| **Lucid Trading** (LucidFlex 50K) | $3.000 | $2.000 | Al cierre | — | 50 % (sin consistencia en funded) | Mín. 2 días | Aparece entre las que permiten bots |

Fuentes: [Topstep (proptradingvibes)](https://proptradingvibes.com/blog/topstep-trading-combine-rules), [Topstep API](https://help.topstep.com/en/articles/11187768-topstepx-api-access), [Apex 4.0](https://proptradingvibes.com/blog/apex-evaluation-account-rules), [automatización en Apex](https://blog.pickmytrade.trade/apex-funded-automation-rules-2026/), [Tradeify](https://help.tradeify.co/en/articles/10495915-growth-evaluation-accounts), [MyFundedFutures](https://proptradingvibes.com/blog/myfundedfutures-rules-overview), [Lucid](https://proptradingvibes.com/blog/lucid-trading-50k-account-rules), [firmas que permiten bots](https://damnpropfirms.com/best-prop-firms-for-algo-trading/). Las mismas reglas están como presets en [`futbot/propfirm.py`](../futbot/propfirm.py).

**Trailing "al cierre" vs "intradía".** Con trailing al cierre (EOD), el umbral solo sube con el saldo de cierre del día. Con trailing intradía sube con la **ganancia no realizada máxima**: si un trade llega a +$1.500 y termina en 0, ya "gastaste" $1.500 de drawdown. Las estrategias de momentum (que dejan correr y devuelven parte) sufren mucho con trailing intradía: **elige cuentas EOD**.

### 3.2 La matemática de aprobar

Estadísticas de la industria: aprueba un **5-15 %** de las evaluaciones compradas y solo ~7 % de los compradores llega a cobrar ([QuantVPS](https://www.quantvps.com/blog/prop-firm-statistics)). Topstep reportó para 2025 que el 16,8 % de los Trading Combines avanzó y que el 33 % de quienes llegaron a cuenta financiada cobró al menos una vez ([traderssecondbrain](https://traderssecondbrain.com/guides/prop-firm-pass-rate)).

Simulé estrategias "ideales" con reglas de Topstep 50K (detalle en [`RESULTADOS_BACKTEST.md`](RESULTADOS_BACKTEST.md#referencia-qué-sharpe-hace-falta-para-aprobar)):

| Sharpe anual de la estrategia | Aprueba con volatilidad diaria de $500 | Aprueba con volatilidad diaria de $250 (tarda ~3x más) |
|---|---|---|
| 0 (sin ventaja) | 26 % | 23 % |
| 1 | 40 % | 46 % |
| 2 | 54 % | 73 % |
| 3 | 65 % | 86 % |

Conclusiones:
- **Aprobar no prueba nada**: sin ventaja se aprueba 1 de cada 4 veces. Las firmas ganan con las tarifas de los otros 3.
- Para aprobar con alta probabilidad necesitas **Sharpe ≥ 2** y una **volatilidad diaria de ~1/8 del drawdown** ($250 en una cuenta con $2.000).
- Las estrategias que probé tienen Sharpe 0,3-0,5 en el período completo (0,5-1 desde 2015): **todavía no alcanzan** para que aprobar sea "fácil". Por eso el plan pasa por combinarlas en cartera y validarlas con datos recientes.

### 3.3 Reglas prácticas para dimensionar el bot en una evaluación 50K

1. **Riesgo por trade ≤ 5-10 % del drawdown** ($100-200): 3-6 MNQ o 1 NQ según el stop.
2. **Límite de pérdida diaria del bot ≤ 25-40 % del drawdown** ($500-800) y **kill switch** al tocarlo.
3. **No operar** los minutos alrededor de FOMC, CPI y NFP, y reducir tamaño en regímenes de volatilidad extrema (los peores días del Noise Area fueron en el crash de marzo de 2020, incluido el recorte de emergencia de la Fed del 3 de marzo).
4. **Consistencia**: con reglas del 50 %, si un día ganas más de ~$1.200, deja de operar ese día (un día enorme te obliga a ganar más para aprobar).
5. **Minis antes que micros** cuando el riesgo lo permite: las comisiones de los micros se comen las ventajas pequeñas.
6. **Cuentas con trailing al cierre** y sin plazo (Topstep, Tradeify, MFFU). El plazo de 30 días de Apex obliga a usar más tamaño: en mis simulaciones el "mejor" tamaño en Apex es casi siempre el más grande, o sea, convierte la evaluación en una lotería.
7. Revisa si la firma permite bots **en la fase financiada**, no solo en la evaluación (Apex no permite bots desatendidos en PA; Topstep exige ejecutar desde tu propio PC).

---

## 4. Repositorios recomendados

### Para backtesting e investigación

| Repositorio | Qué es | Cuándo usarlo |
|---|---|---|
| [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | Motor profesional (núcleo en Rust, API en Python), ~29.600 ★, LGPL-3.0. El mismo código corre en backtest y en vivo; adaptadores para Databento (datos CME) e Interactive Brokers | Cuando quieras pasar a un sistema "de producción" con datos de calidad. Curva de aprendizaje media/alta |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | Motor de QuantConnect (C#/Python), ~21.900 ★, Apache-2.0; soporta futuros, backtest local y en la nube | Si prefieres un ecosistema completo con datos en la nube |
| [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | Backtesting simple en Python, ~9.000 ★, AGPL-3.0 | Prototipos rápidos de un solo instrumento (no maneja multiplicadores de futuros por sí solo) |
| [robcarver17/pysystemtrade](https://github.com/robcarver17/pysystemtrade) | Trading sistemático de futuros (tendencia y carry) con IB, ~3.500 ★ | Para una cuenta propia a largo plazo; **no** sirve para prop firms (posiciones de días/semanas) |
| [codecat-ops/zarattini-2024-momentum-spy](https://github.com/codecat-ops/zarattini-2024-momentum-spy) | Réplica independiente del Noise Area en SPY y ES con protocolo anti-sobreajuste | Para contrastar tu implementación de la estrategia 2 |

### Para ejecutar el bot con prop firms

| Repositorio | Plataforma | Notas |
|---|---|---|
| [TexasCoding/project-x-py](https://github.com/TexasCoding/project-x-py) | **TopstepX / ProjectX** | SDK asíncrono en Python (MIT): órdenes bracket, datos en tiempo real por WebSocket, 60+ indicadores. La opción más directa para un bot en Topstep |
| [rundef/projectx-api](https://github.com/rundef/projectx-api) | TopstepX / ProjectX | Alternativa más ligera |
| [rundef/async_rithmic](https://github.com/rundef/async_rithmic) | **Rithmic** (Apex, Bulenox, Tradeify, etc.) | API asíncrona en Python (MIT, ~120 ★): órdenes, ticks, libro L2, barras históricas |
| [tradovate/example-api-js](https://github.com/tradovate/example-api-js) | **Tradovate** (Apex, Tradeify, MFFU...) | Ejemplos oficiales de la API REST/WebSocket |
| [ib-api-reloaded/ib_async](https://github.com/ib-api-reloaded/ib_async) | Interactive Brokers | Para operar tu propia cuenta en IBKR |

**Repos de bots completos para prop firms** (pocos usuarios: úsalos como referencia, revisa el código antes de confiar en él):
- [Cobez02/trade](https://github.com/Cobez02/trade): bot para MES/MNQ con **Noise Area + ORB**, backtester de 1 minuto con costos, Monte Carlo de probabilidad de aprobar y conectores a Tradovate y ProjectX. Es lo más parecido a lo que buscas.
- [dkiernan159/Trading-Bot](https://github.com/dkiernan159/Trading-Bot): ORB 09:30-09:45 con retest en MNQ sobre TopstepX, con límites diarios y kill switch.
- [bryce-sneed/projectx-trader](https://github.com/bryce-sneed/projectx-trader): framework (alfa) para TopstepX con backtester y bot en vivo, sin estrategia incluida.

**Sin programar**: TradingView (Pine Script) → webhook → [TradersPost](https://traderspost.io) o [PickMyTrade](https://pickmytrade.io) → Tradovate/Rithmic/TopstepX (desde ~$29-49/mes, requiere plan de pago de TradingView). Y **NinjaTrader 8** (NinjaScript, C#), compatible con la mayoría de las firmas vía Rithmic/Tradovate.

### Datos

| Fuente | Qué ofrece | Costo |
|---|---|---|
| [Databento](https://databento.com/futures) | Datos oficiales de CME (ES, NQ, GC, CL, ZN, 6E…) en barras de 1 minuto, ticks y libro de órdenes, con API para Python | **$125 de crédito gratis**; luego pago por uso |
| [FutureSharks/financial-data](https://github.com/FutureSharks/financial-data) | CFDs de Oanda de 1 minuto 2005-2020 (los que usé) | Gratis |
| Exportar desde NinjaTrader, TradingView o tu broker | Históricos de 1 minuto de los contratos reales | Incluido con la plataforma |
| [FirstRate Data](https://firstratedata.com/i/futures/ES) | 15+ años de futuros intradía | De pago |

---

## 5. Hoja de ruta para el nuevo bot

1. **Elige firma y plataforma primero**, porque definen la API: TopstepX (Python, `project-x-py`), Tradovate o Rithmic (Apex/Tradeify/MFFU) o NinjaTrader.
2. **Datos reales de CME**: descarga NQ, ES, CL y GC de 1 minuto de 2019 a 2026 (Databento con el crédito gratis alcanza para barras de 1 minuto). El kit los carga con `--csv` (ver [README](../README.md)).
3. **Re-valida** las estrategias 1, 2, 4 y 5 con esos datos: `python -m futbot backtest --recipe nq_noise_area --symbol NQ --csv data/raw/NQ_1m.csv`. Mira sobre todo 2024-2026 (la réplica independiente avisa que el Noise Area se debilitó en 2025).
4. **Robustez**, no optimización: mueve cada parámetro ±20-30 % y comprueba que el resultado no se derrumba; separa los datos en dentro/fuera de muestra (walk-forward). Si solo funciona con un valor exacto, es sobreajuste.
5. **Cartera**: combina 2-4 estrategias poco correlacionadas (p.ej. Noise Area NQ + ORB NQ + CL + oro) y simula la cartera con `futbot.propfirm` para elegir el tamaño. Diversificar es la forma más barata de subir el Sharpe.
6. **Gestión de riesgo dentro del bot**: límite de pérdida diaria, máximo de trades, filtro de noticias, guardia de consistencia (parar tras +$1.200 en el día), kill switch y logs de cada orden.
7. **Paper trading 4-8 semanas** en la cuenta de simulación de la plataforma, comparando cada ejecución real con lo que habría hecho el backtest (slippage, fills).
8. **Evaluación** con el tamaño que sugiera el simulador (normalmente 3-6 micros o 1 mini) y **funded** con todavía más prudencia: ahí está el dinero de verdad (los retiros).

**Arquitectura sugerida del bot en vivo** (la misma separación que usa el kit, para que el código de la estrategia sea idéntico en backtest y en vivo):

```
feed de datos (WebSocket) → constructor de barras de 1 min → estrategia (futbot.strategies)
      → gestor de riesgo (DLL, tamaño, consistencia, noticias) → adaptador de ejecución
        (ProjectX / Tradovate / Rithmic) → registro de órdenes + alertas (Telegram/Discord)
```

---

## 6. Fuentes

**Papers y réplicas**
- Zarattini & Aziz (2023), *Can Day Trading Really Be Profitable?* — [SSRN 4416622](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622)
- Zarattini, Barbon & Aziz (2024), *A Profitable Day Trading Strategy For The U.S. Equity Market* — [SSRN 4729284](https://www.wealth-lab.com/api/discussion/download/pdf/8007-ssrn-4729284-1-pdf) · [QuantConnect](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)
- Zarattini, Aziz & Barbon (2024), *Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)* — [SSRN 4824172](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172)
- Quantitativo, *Intraday Momentum for ES and NQ* — [quantitativo.com](https://www.quantitativo.com/p/intraday-momentum-for-es-and-nq)
- Réplica independiente del Noise Area — [github.com/codecat-ops/zarattini-2024-momentum-spy](https://github.com/codecat-ops/zarattini-2024-momentum-spy)
- Gao, Han, Li & Zhou (2018), *Market Intraday Momentum*, JFE — [SSRN 2440866](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2440866)
- Baltussen, Da, Lammers & Martens (2021), *Hedging Demand and Market Intraday Momentum*, JFE — [SSRN 3760365](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365)
- Wen, Gong, Ma & Xu (2021), *Intraday momentum and return predictability: Evidence from the crude oil market*, Economic Modelling — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0264999319310417)
- *Overnight versus day returns in gold and gold related assets* (2018), Journal of Economics and Finance — [Springer](https://link.springer.com/article/10.1007/s12197-017-9403-0)

**Estadísticas de mercado**
- ORB en ES/NQ 2014-2026 — [tradingstats.net](https://tradingstats.net/orb-breakout-strategy-guide/)
- Cierre de gaps — [tradingstats.net](https://tradingstats.net/gap-fill-strategy/) · [edgeful](https://www.edgeful.com/blog/posts/es-futures-trading-strategies)
- ICT Silver Bullet, backtest mecánico — [github.com/cjosh4toyotas-stack/silver-bullet-backtest](https://github.com/cjosh4toyotas-stack/silver-bullet-backtest)

**Prop firms**
- Estadísticas de aprobación — [QuantVPS](https://www.quantvps.com/blog/prop-firm-statistics) · [traderssecondbrain](https://traderssecondbrain.com/guides/prop-firm-pass-rate)
- Firmas que permiten bots — [damnpropfirms](https://damnpropfirms.com/best-prop-firms-for-algo-trading/) · [PickMyTrade FAQ](https://pickmytrade.io/faq/prop-firm-automation/)
- TopstepX API — [ayuda de Topstep](https://help.topstep.com/en/articles/11187768-topstepx-api-access) · [reglas de automatización](https://blog.pickmytrade.io/topstepx-rules-payouts-drawdown-automation/)
- Apex 4.0 — [reglas de evaluación](https://proptradingvibes.com/blog/apex-evaluation-account-rules) · [automatización](https://blog.pickmytrade.trade/apex-funded-automation-rules-2026/)
- Tradeify — [Growth](https://help.tradeify.co/en/articles/10495915-growth-evaluation-accounts) · MyFundedFutures — [reglas](https://proptradingvibes.com/blog/myfundedfutures-rules-overview) · Lucid — [50K](https://proptradingvibes.com/blog/lucid-trading-50k-account-rules)

**Datos**
- Databento (CME) — [databento.com/futures](https://databento.com/futures)
- FutureSharks/financial-data — [github.com/FutureSharks/financial-data](https://github.com/FutureSharks/financial-data)
