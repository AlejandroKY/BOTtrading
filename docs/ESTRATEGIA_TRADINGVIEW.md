# Bot de señales para TradingView: ORB 5 minutos con puntaje (NQ y ES)

*Octubre de 2026. Herramienta de estudio, no asesoría financiera. Operar futuros puede hacerte perder más de lo que pones.*

**Archivos:**
- [`pine/orb5_puntaje.pine`](../pine/orb5_puntaje.pine) es el **indicador**. Te dice si hoy se opera, en qué mercado (NQ o ES), el **puntaje de calidad (0-100)** de la señal, la dirección, el stop, el parcial, los contratos y la hora de salida, y te avisa al celular.
- [`pine/orb5_puntaje_estrategia.pine`](../pine/orb5_puntaje_estrategia.pine) es la misma lógica en versión **estrategia**, para ver el backtest en el *Probador de estrategias* de TradingView.

Las reglas son exactamente las de las recetas `nq_orb5_puntaje` y `es_orb5_puntaje` de `futbot`. Lo verifiqué traduciendo el Pine línea a línea a Python y comparándolo con futbot. En 7 años de NQ real coinciden las 335 operaciones, tanto en gráfico de 1 minuto como de 5. En los datos de OANDA 2025-26 de NQ y ES coinciden también las operaciones, los motivos de salida y los contratos.

---

## 1. Lo que pediste y lo que dicen los datos

| Pediste | Resultado con datos reales |
|---|---|
| Trades con puntaje de 80 o más | **Existen y son los mejores**: 60 % de acierto y +0,93R por operación en NQ 2019-2026. Pero aparecen **~6 veces al año**. Por eso el umbral recomendado es **40**, que da ~1 trade por semana con 43 % de acierto. El umbral se cambia en la configuración |
| Buen acierto | **43-46 %**, contra 24 % del bot anterior. Lo logra la salida parcial: la mitad de los contratos sale en +2R y el resto queda protegido en la entrada |
| Lo más importante, ganancia | **+0,37R por operación neto de costos** en NQ 2019-2026: con $200 por operación, ~$260 por mes solo con NQ. Con ES de respaldo, ~$360 por mes en 2025-26 |
| Al menos 3 trades por semana | **No se puede sin perder calidad.** Con NQ y ES entre 9:30 y 11:30 salen ~1-1,3 trades por semana. Solo el 4-15 % de las semanas trae 3 o más. Todo lo que probé para sumar trades perdió plata (sección 10) |
| Aguantar solo 3-4 pérdidas seguidas | Con 43 % de acierto, una racha de 5-8 pérdidas es normal. La peor fue de **8** en 2019-2026 y de 5 en 2025-26. Con $200 por operación son ~$1.600, por debajo del límite de $2.000 de la cuenta |
| Lo mejor para una cuenta de fondeo de 50K | **LucidFlex 50K** con **riesgo por escalones** según el colchón que te queda: $300 / $200 / $100. Con NQ 2019-2026 aprueba 66 % y suspende 2 %, contra 56 % y 17 % con $200 fijo (secciones 4 y 9) |

---

## 2. Qué esperar

| | |
|---|---|
| Mercados | **NQ primero**; ES solo si NQ no califica. Se ejecuta en micro: MNQ ($2/punto) o MES ($5/punto) |
| Horario | La señal llega a las **9:35** de Nueva York (10:35 en Chile) y la operación termina como máximo a las **10:35** |
| Duración | Mediana de 12 minutos (los stops saltan en ~4); ninguna dura más de 60 |
| Frecuencia | ~1 a 1,3 por semana. Hay semanas sin trades: 28-36 % |
| Acierto | **~43-46 %** |
| Ganancia media | **+0,37R por operación** en NQ 2019-2026 y +0,31R en NQ+ES 2025-26, ya descontados comisión y deslizamiento |
| Peor racha | 8 pérdidas seguidas (2019-2026) |
| Meses positivos | 57 % en NQ 2019-2026 (peor mes −$885, mejor +$2.973 con $200 por operación) y 11 de 17 en 2025-26 |
| Caída máxima | −$1.911 (NQ 2019-2026) y −$1.259 (NQ+ES 2025-26), con $200 por operación |

---

## 3. Resultados

### NQ real (futuros MNQ de CME) 2019-2026, $200 por operación

| Año | Operaciones | Acierto | R medio | Resultado |
|---|---|---|---|---|
| 2019 (desde mayo) | 13 | 38 % | +0,19R | +$404 |
| 2020 | 44 | 41 % | +0,11R | +$1.010 |
| 2021 | 47 | 55 % | +0,91R | +$8.172 |
| 2022 | 48 | 29 % | +0,14R | +$785 |
| 2023 | 37 | 43 % | +0,29R | +$1.994 |
| **2024** | **58** | **38 %** | **+0,42R** | **+$4.099** |
| **2025** | **56** | **54 %** | **+0,59R** | **+$6.152** |
| **2026 (a sept.)** | **32** | **38 %** | **+0,01R** | **+$607** |
| **Total** | **335** | **43 %** | **+0,37R** | **+$23.224** |

Los 8 años son positivos, pero 2026 va casi en cero si se opera solo NQ. Con ES de respaldo, 2026 queda en +0,22R (OANDA).

### El puntaje funciona

| Puntaje | Operaciones (NQ 2019-26) | Acierto | R medio |
|---|---|---|---|
| 40-59 | 170 | 36 % | +0,10R |
| 60-79 | 118 | 45 % | +0,54R |
| **80+** | **47** | **60 %** | **+0,93R** |

Pasa lo mismo en los datos que no se usaron para diseñarlo:
- en 2023-2026, el grupo con 3-4 condiciones dio +0,4R a +1,5R;
- en el S&P 500 y el Nasdaq de 2005-2020 también sube el resultado con el puntaje;
- cambiar los pesos del puntaje no cambia el resultado.

### NQ + ES en 2025-2026 (tus datos de OANDA, velas de 5 minutos)

| | Operaciones | Por semana | Acierto | R medio | Resultado ($200) |
|---|---|---|---|---|---|
| NQ primero + ES respaldo | 93 (70 NQ + 23 ES) | 1,26 | 46 % | +0,31R | +$6.090 |
| Solo NQ | 70 | 0,95 | 46 % | +0,24R | +$3.794 |

### Historia larga (CFD de Oanda 2005-2020, NQ primero + ES respaldo)
723 operaciones (0,9 por semana), 41 % de acierto y +0,31R por operación, con costos llevados a precios de hoy.

### Comparado con el bot anterior (NQ real 2019-2026, $200 por operación)

| | Bot anterior (ORB rápido) | Bot nuevo (con puntaje) |
|---|---|---|
| Operaciones | 549 | 335 |
| Acierto | 24 % | **43 %** |
| Peor racha | 18 pérdidas | **8** |
| Ganancia total | $29.419 | $23.224 |
| LucidFlex 50K: aprueba / suspende | 45 % / **51 %** | **56 % / 17 %** |

El bot nuevo gana un poco menos en total, pero acierta casi el doble y quema la cuenta 3 veces menos. Para una cuenta de fondeo eso es lo que importa.

---

## 4. Cuenta de fondeo recomendada: LucidFlex 50K

En la simulación, Topstep, LucidFlex, Tradeify y MyFundedFutures dan casi la misma probabilidad. La simulación arranca una evaluación cada día del histórico y usa contratos enteros. Las cuatro tienen objetivo de $3.000 y límite de $2.000 al cierre diario.

**Con riesgo por escalones (recomendado):** $300 mientras te queden $1.400 o más sobre el límite, $200 entre $800 y $1.400, y $100 por debajo (sección 9).

| Datos | Aprueba | Suspende | No termina en 1 año | Tiempo típico |
|---|---|---|---|---|
| NQ real 2019-2026 | **66 %** | **2 %** | 32 % | ~5 meses (104 sesiones) |
| NQ+ES CFD 2005-2020 (precios de hoy) | 57 % | 7 % | 36 % | ~5,5 meses |
| NQ+ES OANDA 2025-26 | 100 % | 0 % | 0 % | ~3 meses (67 sesiones) |

**Con $200 fijo**, para comparar:

| Datos | Aprueba | Suspende | No termina en 1 año | Tiempo típico |
|---|---|---|---|---|
| NQ real 2019-2026 | 56 % | 17 % | 27 % | ~6 meses (120 sesiones) |
| NQ+ES CFD 2005-2020 | 57 % | 22 % | 21 % | ~7 meses |
| NQ+ES OANDA 2025-26 | 100 % | 0 % | 0 % | ~4,5 meses (96 sesiones) |

Los escalones aprueban igual o más y **suspenden mucho menos**: arriesgan más cuando hay espacio y menos cuando el límite está cerca. Las cuentas que no terminan en un año siguen vivas. En LucidFlex no hay plazo: mirando 2 años, con NQ 2019-2026 aprueba el 87 % y no suspende ninguna.

Recomiendo **LucidFlex 50K** porque este bot es **lento**: tarda meses en llegar a $3.000. Por eso conviene una firma con **pago único y sin límite de tiempo**:
- **LucidFlex 50K:** pago único (~$146), sin límite de tiempo, límite de $2.000 que sigue al cierre diario y se fija $100 sobre el saldo inicial. Consistencia del 50 % en la evaluación y ninguna una vez financiada.
- **Topstep:** cobra ~$49 por mes, más ~$149 de activación. En 6 meses cuesta ~$440.
- **MyFundedFutures:** el plan Rapid exige consistencia del 30 % (mal para este bot: un día de 10R pesaría demasiado); el Pro cuesta ~$265.
- **Apex:** **no sirve** porque da solo 30 días. Con ~1 trade por semana casi nunca se llega.

Las reglas cambian seguido: **verifícalas en la web de la firma antes de comprar** (precios de octubre de 2026). Pregunta también si permite operar a las 10:00, cuando salen datos económicos.

---

## 5. Las reglas, con un ejemplo

1. **Día en juego:** la apertura de las 9:30 se aleja del cierre de ayer (16:00) al menos **0,15 veces el ATR diario**, que es el rango promedio de 14 días.
2. **Vela de 9:30 a 9:35:** si cierra más arriba de donde abrió → **COMPRA**; si cierra más abajo → **VENTA**.
3. **Stop:** en la **mitad de esa vela**, redondeada al tick alejándose de la entrada. No se opera si el stop queda a menos de 6 puntos en NQ o 4 en ES: las comisiones se comerían la ganancia.
4. **Puntaje (0-100):**
   - **30** si la vela cierra fuera del rango overnight a favor: sobre el máximo de 18:00-9:29 si compras, bajo el mínimo si vendes.
   - **Hasta 25** según la fuerza de la vela. Es el cuerpo dividido por el rango: 30 % o menos = 0 puntos, 80 % o más = 25.
   - **Hasta 20** según el tamaño del gap: 0,15 ATR = 0 puntos, 0,60 ATR o más = 20.
   - **15** si la apertura de las 9:30 ya quedó fuera del rango de ayer a favor.
   - **10** si es lunes (después del fin de semana hay más noticias acumuladas).
5. **Se opera con puntaje de 40 o más.** NQ va primero. Si NQ no califica y ES sí, se opera ES. Nunca los dos el mismo día.
6. **Tamaño:** riesgo por escalones según tu colchón sobre el límite de la cuenta: **$300** con $1.400 o más, **$200** desde $800 y **$100** por debajo. Contratos = riesgo ÷ (puntos hasta el stop × valor del punto), redondeando hacia abajo.
7. **Salidas:**
   - **TP1 en +2R:** cierras la **mitad** de los contratos y mueves el stop del resto **a la entrada** (breakeven).
   - El resto sale en **+10R** (casi nunca llega) o a las **10:35**.
   - Si solo tienes 1 contrato, no hay parcial: queda con el stop original hasta 10R o las 10:35.

**Ejemplo** (números inventados):
- **El gap.** Lunes. Ayer el NQ cerró en 24.000 y su rango de ayer fue 23.900-24.080. Durante la noche llegó como máximo a 24.170. Hoy abre a las 9:30 en 24.120 y el ATR es 400: gap = 120/400 = 0,30 ATR.
- **La vela.** La vela de 9:30-9:35 abre en 24.120, va de 24.110 a 24.200 y cierra en 24.190: **COMPRA**.
- **El puntaje:**
  - cierra sobre el máximo overnight (24.190 > 24.170): **30**;
  - cuerpo de 70/90 = 78 %: **24**;
  - gap de 0,30 ATR: **7**;
  - abrió sobre el máximo de ayer (24.120 > 24.080): **15**;
  - lunes: **10**.
  - Total: **86** → se opera, y es de las mejores.
- **El stop y el tamaño.** El stop va en la mitad de la vela, 24.155, a 35 puntos. Con MNQ son 35 × $2 = $70 por contrato. Si es tu primer trade, el colchón es $2.000 y el riesgo $300, así que operas **4 MNQ** (riesgo de $280).
- **Las salidas.** El TP1 está en 24.190 + 70 = 24.260: ahí cierras 2 MNQ y mueves el stop de los otros 2 a 24.190. A las 10:35 cierras lo que quede.

---

## 6. Instalarlo en TradingView

1. Abre **dos gráficos de 5 minutos**: **NQ1!** (o MNQ1!) y **ES1!** (o MES1!). Funciona también en 1 minuto; otras temporalidades no.
2. En cada uno: **Pine Editor** → *Nuevo*. Pega [`pine/orb5_puntaje.pine`](../pine/orb5_puntaje.pine) → **Guardar** → **Añadir al gráfico**. Quita las versiones anteriores (*ORB5 rápido*, *ORB5 NQ*).
3. Configuración (engranaje):
   - **Riesgo por operación:** "Escalones según colchón (recomendado)".
   - **Colchón actual sobre el límite:** $2.000 al empezar la cuenta. **Actualízalo después de cada trade** con el saldo menos el nivel donde pierdes la cuenta; tu plataforma lo muestra como pérdida máxima restante. El indicador calcula solo el riesgo ($300, $200 o $100) y los contratos.
   - **Contratos:** Micro (MNQ / MES).
   - **Puntaje mínimo:** 40. Sube a 60 si prefieres menos trades y más acierto.
   - Lo demás déjalo igual.
4. Cada gráfico calcula el puntaje de **los dos** mercados y sabe cuál se opera hoy. El trade se dibuja solo en el gráfico del mercado elegido; el otro dice "se opera NQ" o "se opera ES".
5. **Versión estrategia (opcional):** pega [`pine/orb5_puntaje_estrategia.pine`](../pine/orb5_puntaje_estrategia.pine) en un gráfico de **MNQ1!** o **MES1!** y abre el *Probador de estrategias*. Muestra el acierto, el profit factor y la curva de capital con los datos que tiene cargados TradingView.
   - Usa los micro, porque el tamaño se calcula con el valor del punto del gráfico.
   - Calcula solo el colchón, simulando el límite de $2.000 que sigue al mejor saldo, y aplica los escalones.
   - Sus números pueden diferir un poco de los de futbot, porque TradingView decide el orden de stop y take profit dentro de cada vela.

### Qué vas a ver

| En el gráfico | Qué significa |
|---|---|
| Etiqueta **COMPRA 86** / **VENTA 64** a las 9:35 | La señal y su puntaje. Pasa el mouse para ver el plan completo y el detalle del puntaje |
| Rectángulo verde o rojo "vela 9:30" | La vela que dio la señal |
| Líneas azules **"máx overnight" / "mín overnight"** | El rango de la noche: si la vela cierra fuera, suma 30 puntos |
| Línea gris **"cierre ayer"** | La distancia hasta la apertura es el gap |
| Zona **roja** "STOP … −$… · N MNQ" | Tu riesgo: de la entrada al stop |
| Zona **verde** "TP1 … · cerrar N y stop a la entrada" | El objetivo del parcial. Al tocarlo cambia a "TP1 ✓" |
| Línea gruesa "entrada … · salir 10:35" | Entrada y hora límite |
| Etiqueta final **"+1,5R +$270"** | Resultado neto de costos. Pasa el mouse para ver el motivo de salida |
| Rectángulo **gris** con "sin trade: …" o "se opera ES" | Hoy no se opera en este mercado, y por qué |
| **Panel** | Qué se opera hoy, puntajes de NQ y ES, niveles, estado, estadísticas del gráfico y referencia del backtest |

---

## 7. Alertas y ejecución

**Crear la alerta** en los dos gráficos (ícono del reloj o `Alt + A`):
- **Condición:** `ORB5 puntaje` → **"Cualquier llamada a la función alert()"**.
- **Notificaciones:** *Notificar en la app*.

**Mensajes que te llegarán:**
- **9:35:** `COMPRA NQ (puntaje 86): 4 MNQ a mercado ~24190 | STOP 24155 | TP1 24260 (cerrar 2) | TP 24540 | cerrar a las 10:35 NY`.
- **TP1:** `TP1 NQ: cierra 2 MNQ (~24260) y mueve el stop a la entrada 24190`.
- **Al salir:** `STOP NQ: …`, `Stop en la entrada (tras el parcial)` o `SALIDA 10:35 NQ: cierra la compra a mercado ahora`.

**Cómo ejecutar:**
1. **9:35:** orden **a mercado** con los contratos indicados, con **bracket**: el stop y el TP final. En TopstepX, Tradovate o NinjaTrader puedes armar una estrategia ATM o un bracket con dos objetivos: 50 % en TP1 y 50 % en TP final, con breakeven automático al tocar TP1.
2. **Si llegas tarde** y el precio ya avanzó más de 0,25R a tu favor, o ya tocó el stop, **salta la señal**.
3. **Al tocar TP1:** cierra la mitad y **mueve el stop a la entrada**. Si la plataforma lo hace sola, mejor.
4. **10:35:** cierra lo que quede (*Flatten*).
5. **Nunca** muevas el stop más lejos, ni cierres antes por miedo o por euforia.
6. **Una operación por día**, con el riesgo que indique el escalón.
7. **Después de cada trade**, actualiza el colchón en la configuración del indicador.

---

## 8. Plan de validación y repetir el backtest

**Demo desde mañana (4-8 semanas):**
- Toma **todas** las señales con puntaje ≥ 40, sin elegir.
- Anota fecha, mercado, puntaje, entrada esperada y real, salidas y errores.
- Serán ~5-10 operaciones: sirven para practicar la ejecución, no para medir la ventaja. Eso ya lo miden los 7 años de la sección 3.

**Repetir el backtest con tus datos:**

```powershell
# con tus archivos de OANDA (data/oanda, hora del servidor MT5):
python scripts/backtest_puntaje.py --nq data/oanda/US100_M5.csv.gz --es data/oanda/US500_M5.csv.gz --tz mt5
# con datos de CME de Databento (scripts/descargar_datos_databento.py, ver README):
python scripts/backtest_puntaje.py --nq "data/real/NQ_1m_*.parquet" --es "data/real/ES_1m_*.parquet"
# otro umbral u otro riesgo:
python scripts/backtest_puntaje.py --nq data/oanda/US100_M5.csv.gz --es data/oanda/US500_M5.csv.gz --tz mt5 --puntaje 60 --riesgo 250
```

El script muestra:
- los trades por semana, el acierto, el R medio y los resultados por año y por puntaje;
- la probabilidad de aprobar en LucidFlex, Topstep, Tradeify y MFFU, con riesgo fijo y por escalones;
- la **salud del sistema**: compara los últimos 30 trades con miles de grupos de 30 sacados al azar del historial.
  - Si rinden peor que el 95 % de ellos, da **ALERTA**: el mercado pudo cambiar y conviene parar y revisar.
  - Si están en el 20 % más bajo, da **atención**.
  - Hoy (octubre de 2026) está en **atención**: los últimos 30 trades dan +0,03R en NQ y +0,01R con tus datos de OANDA. Es una racha floja, normal en la historia (2020 y 2023 tuvieron otras), pero no una alarma. Es otra razón para empezar en demo.

> **Importante sobre tus archivos de OANDA:** MT5 guarda la **hora del servidor** (Nueva York + 7 horas), aunque el archivo diga UTC. Lo comprobé comparando US100 con el NQ real: coinciden con correlación 0,98-0,999 solo con ese desfase. Cárgalos siempre con `--tz mt5`. Con `--tz UTC`, todas las estrategias de la apertura se calculan 3 horas corridas.

**Criterios para comprar la evaluación:**
- [ ] Ejecutaste en demo todas las señales sin errores graves, incluido el parcial con breakeven.
- [ ] Aceptas ~1 trade por semana, semanas sin trades y rachas de 5-8 pérdidas.
- [ ] Entiendes que la probabilidad estimada de aprobar en un año es de ~55-65 % con escalones, y que la de suspender es baja (2-7 %) pero no cero.
- [ ] La salud del sistema no está en ALERTA cuando vayas a comprar.

---

## 9. Gestión de riesgo

- **Riesgo por escalones según el colchón:** el colchón es el saldo menos el nivel donde pierdes la cuenta.
  - **$300** si te quedan $1.400 o más (al empezar tienes $2.000).
  - **$200** entre $800 y $1.400.
  - **$100** por debajo de $800.
  - Si vuelves a ganar, el colchón crece y el riesgo sube otra vez.
  - Así, una mala racha nunca te saca de golpe. Con $300 fijo, 7 pérdidas seguidas quemarían la cuenta; con escalones hacen falta muchas más.
- **Contratos:** MNQ = riesgo ÷ (puntos hasta el stop × $2), redondeando hacia abajo; MES = riesgo ÷ (puntos × $5).
  - Si el stop está muy lejos para el riesgo de ese momento (más de 150, 100 o 50 puntos en NQ con $300, $200 o $100), no cabe ni 1 contrato y no se opera.
- Si prefieres un riesgo fijo, $200 es el más equilibrado. Con $250 aprueba más rápido, pero suspende más (17-28 %).
- **Consistencia del 50 % en la evaluación:** si un día ganas mucho, por ejemplo con un 10R, tendrás que ganar más en total para aprobar. Sigue operando normal.
- **Una vez financiado:** sigue con los escalones. Protegen igual la cuenta financiada.

---

## 10. Qué se probó y qué no funcionó

Para llegar a 3 trades por semana y a acierto alto probé, en NQ real 2019-2026, NQ/ES CFD 2005-2020 y tus datos de OANDA 2025-26:

| Idea | Resultado |
|---|---|
| Objetivo de 1R a 2R para toda señal (acierto 40-50 %) | Ganancia ~0 o negativa: la ventaja vive en las operaciones que corren |
| Tomar la mitad en +0,5R o +1R | Acierto 50-60 %, pero ganancia ~0 |
| Ir contra la ruptura del rango de 5, 15 o 30 minutos (acierto 55-66 %) | ~0 o negativo después de comisiones |
| Operar días sin gap (aunque tengan puntaje alto) | Negativo en 2023-2026 y en 2025-26 |
| Ruptura del rango overnight después de las 9:35 | Negativo en NQ 2023-2026 y en ES |
| Volumen relativo, tendencia de 20 días, solo compras | No mejoran de forma consistente |
| Riesgo según el puntaje ($300 en 60+, $150 en 40-59) | No mejora la probabilidad de aprobar |
| Elegir entre NQ y ES por el mejor puntaje | Peor que NQ primero: con el mismo puntaje, NQ rindió más (2005-2020) |
| *Segunda ronda de mejoras (octubre de 2026):* | |
| Dejar correr la mitad que queda hasta las 11:00 o las 11:30 | Mejora en algunos períodos y empeora en 2025-26: no es consistente |
| Candado de ganancia (en +3R o +4R, subir el stop a +1R o +2R) | Neutro o peor |
| Parcial de 1/3 en vez de 1/2 | Mejor en NQ 2019-26, peor en 2025-26 y con 2 puntos menos de acierto |
| Parcial en +1,5R o en +2,5R | Peor que en +2R |
| No operar con volatilidad alta (ATR sobre su media de 100 días) | Parecía mejorar, pero por quintiles no hay una relación consistente: ruido |
| No operar días de CPI o de empleo (8:30) | Mixto |
| No operar días de anuncio de la Fed | Esos trades pierden en promedio, pero son ~1 por año. En NQ 2019-26 quitarlos hasta empeoró la simulación de la cuenta (uno era un +3R). Queda como opción en futbot (`skip_fomc`), apagada |
| Exigir que NQ y ES abran en la misma dirección | Muy bueno en 2005-2018, al revés en 2025-26 |
| Russell (RTY) como tercer mercado de respaldo | Positivo en 2025-26 (+0,25R, sube a 1,6 trades por semana), pero negativo en 2005-2020 (−0,27R) |
| **Riesgo por escalones según el colchón** | **Adoptado**: igual o más probabilidad de aprobar y mucho menos de suspender en las tres fuentes de datos |

**Lo que sí funcionó:** filtrar con un puntaje armado con condiciones que tienen lógica de mercado. Cada condición mejoró el resultado tanto en los datos usados para elegirla como en los guardados para comprobarla.

**Limitaciones honestas:**
- El puntaje y las salidas se eligieron mirando 2019-2026; la confirmación más limpia es la historia 2005-2020 y el hecho de que los 8 años den positivo.
- No conseguí futuros reales de ES de 2021 a 2024: para ES usé CFD de 2005-2020 y tus datos de OANDA 2025-26.
- 2026 viene flojo en NQ (+0,01R hasta septiembre). Una ventaja de +0,3R por operación puede desaparecer: repite `scripts/backtest_puntaje.py` cada 3-6 meses con datos nuevos.

---

## 11. Cómo seguir mejorándolo

Ordenado por lo que más ayuda:

1. **Datos reales de ES y datos nuevos de NQ.**
   - Con el crédito gratis de Databento ($125) puedes bajar NQ y ES de CME 2019-2026 con `scripts/descargar_datos_databento.py --symbol ES` (cuesta pocos dólares del crédito).
   - Es lo único que me faltó para validar ES fuera de los CFD.
   - Corre `scripts/backtest_puntaje.py` cada 1-3 meses y mira la **salud del sistema**.
2. **Tu diario de demo.**
   - Compara tu entrada real con la del indicador.
   - Si pierdes más de 1-2 ticks por operación o te saltas parciales, el problema está en la ejecución y se arregla antes que la estrategia.
3. **Automatizar la ejecución** (después de la demo).
   - Una alerta de TradingView enviada a un puente (TradersPost, PickMyTrade o CrossTrade) abre la orden con stop, parcial y breakeven sin demoras ni errores.
   - **Antes, confirma que tu firma lo permite.**
4. **Reglas para parar.**
   - Si la salud da ALERTA, o si en la cuenta real pierdes el 75 % del colchón, deja de operar y vuelve a correr el backtest con los datos nuevos.
5. **Ideas que todavía no probé:**
   - una segunda señal a las 10:00, después de los datos económicos;
   - el volumen de cada vela de 1 minuto;
   - aprender los pesos del puntaje de forma automática con validación por períodos.
   - Cada una se prueba igual: elegir con un período y comprobar con otro.

---

## 12. Glosario

| Término | Qué significa |
|---|---|
| **R** | Lo que arriesgas en una operación. "+2R" = ganaste el doble de lo arriesgado |
| **Puntaje** | Calidad de la señal de 0 a 100, según cuántas condiciones a favor cumple |
| **Parcial / TP1** | Cerrar una parte de los contratos en un primer objetivo (+2R) |
| **Breakeven** | Mover el stop al precio de entrada: lo que queda ya no puede perder (salvo comisiones) |
| **Rango overnight** | Máximo y mínimo entre las 18:00 de ayer y las 9:29 de hoy |
| **ORB** | *Opening Range Breakout*: operar en la dirección del primer rango de la apertura |
| **Gap** | Diferencia entre la apertura de hoy (9:30) y el cierre de ayer (16:00) |
| **ATR** | Cuánto se mueve el mercado en un día normal (promedio de 14 días) |
| **Roll** | Cambio al siguiente vencimiento del futuro (cada 3 meses); el indicador lo ajusta solo |
| **Bracket / ATM** | Stop y objetivos puestos junto con la entrada |
| **MLL / límite de pérdida** | Si el saldo toca ese nivel, pierdes la cuenta de fondeo |
| **Trailing al cierre (EOD)** | El límite sube con tu mejor saldo de cierre diario |
| **Dentro / fuera de muestra** | Datos usados para diseñar la regla / datos guardados para comprobarla |
| **NQ / MNQ, ES / MES** | Futuros del Nasdaq-100 y del S&P 500: mini ($20 y $50 por punto) y micro ($2 y $5) |

**Fuentes de datos:**
- NQ real: velas de 1 minuto de MNQ de Databento, publicadas en [vinentHuynh/QuantResearch](https://github.com/vinentHuynh/QuantResearch).
- CFD 2005-2020: [FutureSharks/financial-data](https://github.com/FutureSharks/financial-data).
- 2025-26: tus datos de OANDA MT5 (`data/oanda`).
