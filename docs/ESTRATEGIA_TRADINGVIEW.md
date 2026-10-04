# Bot de señales para TradingView: ORB 5 minutos con puntaje + Noise Area a las 10:00 (NQ y ES)

*Octubre de 2026. Herramienta de estudio, no asesoría financiera. Operar futuros puede hacerte perder más de lo que pones.*

**Archivos:**
- [`pine/orb5_puntaje.pine`](../pine/orb5_puntaje.pine) es el **indicador**. Te dice si hoy se opera, en qué mercado (NQ o ES), el **puntaje de calidad (0-100)** de la señal, la dirección, el stop, el parcial, los contratos y la hora de salida, y te avisa al celular.
- [`pine/orb5_puntaje_estrategia.pine`](../pine/orb5_puntaje_estrategia.pine) es la misma lógica en versión **estrategia**, para ver el backtest en el *Probador de estrategias* de TradingView.

El bot tiene **dos estrategias** (desde octubre de 2026):
- **Estrategia 1 (E1), ORB 5 min con puntaje:** la señal de las 9:35 en NQ o ES. Recetas `nq_orb5_puntaje` y `es_orb5_puntaje` de `futbot`.
- **Estrategia 2 (E2), Noise Area a las 10:00:** solo en NQ. A las 10:00 entra a favor del gap si el precio salió de su "zona de ruido". Sale a las 11:00 y arriesga la mitad que E1. Receta `nq_ruido10`.

Las reglas del Pine son las mismas que las de `futbot`. Para E1 lo verifiqué traduciendo el Pine línea a línea a Python: en 7 años de NQ real coinciden las 335 operaciones, en gráfico de 1 minuto y de 5. En los datos de OANDA 2025-26 de NQ y ES coinciden también los motivos de salida y los contratos. Para E2, futbot y el laboratorio coinciden en 330 de 331 operaciones de NQ real y en 70 de 71 de OANDA.

---

## 1. Lo que pediste y lo que dicen los datos

| Pediste | Resultado con datos reales |
|---|---|
| Trades con puntaje de 80 o más | **Existen y son los mejores**: 60 % de acierto y +0,93R por operación en NQ 2019-2026. Pero aparecen **~6 veces al año**. Por eso el umbral recomendado es **40**, que da ~1 trade por semana con 43 % de acierto. El umbral se cambia en la configuración |
| Buen acierto | **43-46 %**, contra 24 % del bot anterior. Lo logra la salida parcial: la mitad de los contratos sale en +2R y el resto queda protegido en la entrada |
| Lo más importante, ganancia | **+0,37R por operación neto de costos** en NQ 2019-2026: con $200 por operación, ~$260 por mes solo con NQ. Con ES de respaldo, ~$360 por mes en 2025-26 |
| Al menos 3 trades por semana | **Con las dos estrategias llegas a ~1,5-2 por semana.** E1 da ~0,9-1,3; E2 da ~0,9 señales, pero ~30 % no caben con $150 (stop de más de 75 puntos). Llegar a 3 sin perder calidad no fue posible: todo lo demás que probé perdió plata (sección 10) |
| Aguantar solo 3-4 pérdidas seguidas | Con 40-43 % de acierto, una racha de 5-8 pérdidas es normal. La peor de E1 fue de **8** en 2019-2026 y de 5 en 2025-26. Con $200 por operación son ~$1.600, por debajo del límite de $2.000 de la cuenta |
| Lo mejor para una cuenta de fondeo de 50K | **LucidFlex 50K** con **riesgo por escalones** según el colchón: $300 / $200 / $75 en E1, y E2 a la mitad ($150) solo con colchón de $1.400 o más. Con NQ 2019-2026 aprueba **76 %** y no suspende ninguna (antes: 66 % y 2 %). En 2005-2026, contando todo, aprueba 65 % y suspende 1 % (antes: 60 % y 8 %) (secciones 4 y 9) |

---

## 2. Qué esperar

| | |
|---|---|
| | **E1: ORB 5 min con puntaje** | **E2: Noise Area 10:00** |
|---|---|---|
| Mercados | **NQ primero**; ES solo si NQ no califica | Solo NQ |
| Contratos | Micro: MNQ ($2/punto) o MES ($5/punto) | MNQ |
| Horario | Señal a las **9:35** de Nueva York (10:35 en Chile); sale como máximo a las **10:35** | Señal a las **10:00** (11:00 en Chile); sale como máximo a las **11:00** |
| Duración | Mediana de 12 minutos; ninguna dura más de 60 | Hasta 60 minutos |
| Frecuencia | ~0,9 a 1,3 por semana | ~0,9 por semana |
| Acierto | **~43-46 %** | **~40 %** (2019-2025) |
| Ganancia media neta | **+0,37R** en NQ 2019-2026 y +0,31R en NQ+ES 2025-26 | **+0,45R** en NQ 2019-2026 y +0,36R en NQ 2005-2020, pero **−0,24R en 2026** |
| Peor racha | 8 pérdidas seguidas (2019-2026) | 12 (2025-26) |
| Riesgo | Escalones $300 / $200 / $75 | La mitad: $150, solo con colchón de $1.400 o más |

Las dos pueden darse el mismo día. Si E1 está abierta a las 10:00 en la misma dirección que E2, E2 suma contratos con su propio stop. Si está en la dirección contraria, E2 no se opera.

---

## 3. Resultados

### E1 en NQ real (futuros MNQ de CME) 2019-2026, $200 por operación

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

### E2: Noise Area a las 10:00 a favor del gap (NQ real 2019-2026)

| Año | Operaciones | Acierto | R medio |
|---|---|---|---|
| 2019 (desde mayo) | 23 | 35 % | −0,02R |
| 2020 | 34 | 44 % | +0,28R |
| 2021 | 44 | 57 % | +1,31R |
| 2022 | 58 | 41 % | +0,77R |
| 2023 | 39 | 36 % | +0,34R |
| 2024 | 49 | 37 % | +0,45R |
| 2025 | 48 | 40 % | +0,24R |
| **2026 (a sept.)** | **36** | **22 %** | **−0,24R** |
| **Total** | **331** | **40 %** | **+0,45R** |

- En NQ 2005-2020 (CFD, costos a precios de hoy): 655 operaciones, 39 % de acierto y +0,36R. Fue positiva en 12 de 16 años.
- Con tus datos de OANDA: +0,19R en 2025 y −0,23R en 2026.
- **2026 es el peor año de su historia.** Lo explico en la sección 8, junto con qué hacer.
- En ES no funciona igual: +0,14R en 2005-2020, pero −0,38R en 2025-26. Por eso E2 es solo para NQ.

### Las dos juntas en una cuenta de 50K

La pregunta era si fusionar las estrategias da algo mejor que cada una por separado. Lo medí con la simulación de cuentas LucidFlex 50K: una evaluación empezando cada día, plazo de 1 año y contratos enteros.

| Datos | Solo E1 | E1 + E2 (E2 a la mitad del riesgo y con colchón ≥ $1.400) |
|---|---|---|
| NQ real 2019-2026 | 69 % aprueba / 0 % suspende · 107 sesiones | **76 % / 0 %** · **87 sesiones** |
| NQ+ES CFD 2005-2020 | 53 % / 1,5 % · 110 sesiones | **60 % / 1,5 %** · 115 sesiones |
| NQ+ES OANDA 2025-26 | 100 % / 0 % · 67 sesiones | 100 % / 0 % · **57 sesiones** |
| Señales por semana | 0,9-1,3 | **1,7-2,2** (se operan ~1,5-2) |

Sí da algo mejor: aprueba más, suspende lo mismo, termina antes y opera el doble de seguido. Por eso las fusioné, pero solo de esa forma. Las otras formas de juntarlas suspendían más (sección 10).

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

**Recomendado: E1 + E2 con riesgo por escalones.**
- E1: $300 mientras te queden $1.400 o más sobre el límite, $200 entre $800 y $1.400, y $75 por debajo.
- E2: $150, solo con $1.400 o más (sección 9).

| Datos | Aprueba | Suspende | No termina en 1 año | Tiempo típico |
|---|---|---|---|---|
| NQ real 2019-2026 | **76 %** | **0 %** | 24 % | ~4 meses (87 sesiones) |
| NQ+ES CFD 2005-2020 (precios de hoy) | 60 % | 1,5 % | 38 % | ~5,5 meses |
| NQ+ES OANDA 2025-26 | 100 % | 0 % | 0 % | ~2,7 meses (57 sesiones) |

**Solo E1 con los escalones anteriores** ($300 / $200 / $100), como estaba antes de esta ronda:

| Datos | Aprueba | Suspende | No termina en 1 año | Tiempo típico |
|---|---|---|---|---|
| NQ real 2019-2026 | 66 % | 2 % | 32 % | ~5 meses (104 sesiones) |
| NQ+ES CFD 2005-2020 (precios de hoy) | 57 % | 8 % | 35 % | ~5,5 meses |
| NQ+ES OANDA 2025-26 | 100 % | 0 % | 0 % | ~3 meses (67 sesiones) |

**Solo E1 con $200 fijo**, para comparar:

| Datos | Aprueba | Suspende | No termina en 1 año | Tiempo típico |
|---|---|---|---|---|
| NQ real 2019-2026 | 56 % | 17 % | 27 % | ~6 meses (120 sesiones) |
| NQ+ES CFD 2005-2020 | 57 % | 22 % | 21 % | ~7 meses |
| NQ+ES OANDA 2025-26 | 100 % | 0 % | 0 % | ~4,5 meses (96 sesiones) |

Los escalones aprueban igual o más y **suspenden mucho menos**: arriesgan más cuando hay espacio y menos cuando el límite está cerca. Bajar el último escalón de $100 a $75 bajó las cuentas suspendidas de 8 % a 1 % en 2005-2026, aprobando lo mismo. Las cuentas que no terminan en un año siguen vivas. En LucidFlex no hay plazo: mirando 2 años, con NQ 2019-2026 aprueba el 87 % y no suspende ninguna (solo E1).

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
6. **Tamaño:** riesgo por escalones según tu colchón sobre el límite de la cuenta: **$300** con $1.400 o más, **$200** desde $800 y **$75** por debajo. Contratos = riesgo ÷ (puntos hasta el stop × valor del punto), redondeando hacia abajo.
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

### Estrategia 2: Noise Area a las 10:00 (solo NQ)

Viene del paper *Beat the Market* (Zarattini, Aziz y Barbon, 2024). La idea es que cada mañana el precio se mueve dentro de una "zona de ruido" normal. Cuando sale de ella, suele seguir en esa dirección.

1. **El ruido.** Para cada uno de los últimos 14 días se mide cuánto se alejó el precio de las 10:00 de la apertura de las 9:30, en porcentaje. El promedio es el ruido (σ). En 2025-26 fue de 0,2 % a 0,5 %.
2. **La zona de ruido.**
   - Borde superior = el mayor entre la apertura de hoy y el cierre de ayer, × (1 + σ).
   - Borde inferior = el menor entre los dos, × (1 − σ).
3. **A las 10:00:**
   - **COMPRA** si hoy abrió con **gap alcista** (sobre el cierre de ayer) y el precio cerró **sobre el borde superior**.
   - **VENTA** si abrió con **gap bajista** y cerró **bajo el borde inferior**.
   - Contra el gap, o dentro de la zona, no se opera.
4. **Stop:**
   - En compras, el más alto entre el borde superior y el **VWAP** desde las 9:30. En ventas, el más bajo de los dos.
   - No se opera si el stop queda a menos de 6 puntos.
5. **Salida:** stop o **a las 11:00**. No tiene take profit ni parcial: en las pruebas, con objetivo o parcial ganaba menos.
6. **Tamaño:** la **mitad** del riesgo de E1 ($150) y **solo con colchón de $1.400 o más**. Con menos colchón, E2 no se opera.
7. **Junto con E1:**
   - Si E1 sigue abierta a las 10:00 en la misma dirección, E2 suma contratos con su propio stop.
   - Si E1 va en la dirección contraria, E2 no se opera.

**Ejemplo** (números inventados):
- **El gap.** Ayer el NQ cerró en 24.000. Hoy abre a las 9:30 en 24.120: gap alcista.
- **La zona.** El ruido de los últimos 14 días es 0,40 %. Borde superior = 24.120 × 1,004 = 24.216,5.
- **La señal.** A las 10:00 el NQ cierra en 24.260, sobre el borde. El VWAP es 24.230: **COMPRA**.
- **El stop.** Va en el mayor entre 24.216,5 y 24.230, o sea 24.230: 30 puntos. Son 30 × $2 = $60 por MNQ, así que con $150 operas **2 MNQ** (riesgo de $120).
- **La salida.** Si no toca el stop, cierras a las 11:00.

---

## 6. Instalarlo en TradingView

1. Abre **dos gráficos de 5 minutos**: **NQ1!** (o MNQ1!) y **ES1!** (o MES1!). Funciona también en 1 minuto; otras temporalidades no.
2. En cada uno: **Pine Editor** → *Nuevo*. Pega [`pine/orb5_puntaje.pine`](../pine/orb5_puntaje.pine) → **Guardar** → **Añadir al gráfico**. Quita las versiones anteriores (*ORB5 rápido*, *ORB5 NQ*).
3. Configuración (engranaje):
   - **Riesgo por operación:** "Escalones según colchón (recomendado)".
   - **Colchón actual sobre el límite:** $2.000 al empezar la cuenta. **Actualízalo después de cada trade** con el saldo menos el nivel donde pierdes la cuenta; tu plataforma lo muestra como pérdida máxima restante. El indicador calcula solo el riesgo ($300, $200 o $100) y los contratos.
   - **Contratos:** Micro (MNQ / MES).
   - **Puntaje mínimo:** 40. Sube a 60 si prefieres menos trades y más acierto.
   - **Operar la estrategia 2:** activada. La E2 se dibuja solo en el gráfico de NQ/MNQ. Lee antes la sección 8 sobre su salud.
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
| Etiqueta **E2 COMPRA** / **E2 VENTA** a las 10:00 (gráfico de NQ) | Señal de la estrategia 2. Pasa el mouse para ver la zona de ruido, el VWAP y el stop |
| Zona roja "E2 STOP …" y línea punteada "E2 entrada … · salir 11:00" | Riesgo y hora límite de la E2 |
| Texto gris "E2: dentro de la zona de ruido" (u otro motivo) | Hoy no hay E2, y por qué |
| **Panel** | Qué se opera hoy, puntajes de NQ y ES, niveles, estado, estado de la E2, estadísticas del gráfico y referencia del backtest |

---

## 7. Alertas y ejecución

**Crear la alerta** en los dos gráficos (ícono del reloj o `Alt + A`):
- **Condición:** `ORB5 puntaje` → **"Cualquier llamada a la función alert()"**.
- **Notificaciones:** *Notificar en la app*.

**Mensajes que te llegarán:**
- **9:35:** `COMPRA NQ (puntaje 86): 4 MNQ a mercado ~24190 | STOP 24155 | TP1 24260 (cerrar 2) | TP 24540 | cerrar a las 10:35 NY`.
- **TP1:** `TP1 NQ: cierra 2 MNQ (~24260) y mueve el stop a la entrada 24190`.
- **Al salir:** `STOP NQ: …`, `Stop en la entrada (tras el parcial)` o `SALIDA 10:35 NQ: cierra la compra a mercado ahora`.
- **10:00 (E2):** `E2 COMPRA NQ (10:00): 2 MNQ a mercado ~24260 | STOP 24230 | sin TP | cerrar a las 11:00 NY`.
- **Salida de E2:** `E2 STOP NQ: …` o `E2 SALIDA 11:00 NQ: cierra la compra a mercado ahora`.

**Cómo ejecutar:**
1. **9:35:** orden **a mercado** con los contratos indicados, con **bracket**: el stop y el TP final. En TopstepX, Tradovate o NinjaTrader puedes armar una estrategia ATM o un bracket con dos objetivos: 50 % en TP1 y 50 % en TP final, con breakeven automático al tocar TP1.
2. **Si llegas tarde** y el precio ya avanzó más de 0,25R a tu favor, o ya tocó el stop, **salta la señal**.
3. **Al tocar TP1:** cierra la mitad y **mueve el stop a la entrada**. Si la plataforma lo hace sola, mejor.
4. **10:35:** cierra lo que quede (*Flatten*).
5. **Nunca** muevas el stop más lejos, ni cierres antes por miedo o por euforia.
6. **E2 a las 10:00:**
   - Orden a mercado con su stop, **sin take profit**. A las 11:00 cierra la E2.
   - Si E1 sigue abierta en la misma dirección, pon la E2 como una orden aparte, con su propio stop. No muevas el stop de E1.
7. **Máximo una E1 y una E2 por día**, con el riesgo que indique el escalón.
8. **Después de cada trade**, actualiza el colchón en la configuración del indicador. Con menos de $1.400, el indicador ya no da señales de E2.

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
- los resultados de E1, de E2 y de las dos juntas, y la probabilidad de aprobar con y sin E2 (`--sin-e2` la quita);
- la **salud** de cada estrategia: compara sus últimos 30 trades con miles de grupos de 30 sacados al azar de su historial.
  - Si rinden peor que el 95 % de ellos, da **ALERTA**: el mercado pudo cambiar y conviene parar y revisar.
  - Si están en el 20 % más bajo, da **atención**.

**Estado hoy (octubre de 2026):**
- **E1: atención.** Los últimos 30 trades dan +0,03R en NQ y +0,01R con tus datos de OANDA. Es una racha floja, normal en la historia (2020 y 2023 tuvieron otras), pero no una alarma.
- **E2: ALERTA.** Los últimos 30 trades dan −0,32R en NQ y −0,66R en OANDA: perdió 22 de 30 desde febrero. En 21 años nunca tuvo una racha así.

**Qué hacer con la E2:**
- **En demo, opérala.** No cuesta nada y sirve para practicar la segunda entrada.
- **Antes de pagar la evaluación,** baja datos nuevos con `scripts/download_mt5.py` y corre el script.
  - Si E2 sigue en ALERTA, **apágala** ("Operar la estrategia 2" en la configuración) y opera solo E1 hasta que salga de la alerta.
  - Si E2 sale de la alerta, opérala.
- **Por qué no la apago para siempre:** probé pausar cada estrategia después de 20-50 trades malos, y en la historia eso empeoró el resultado. Las operaciones que venían después de una mala racha fueron en promedio tan buenas como las demás. La pausa por ALERTA es una precaución por lo extrema que es esta racha, no una regla que mejore el backtest.

> **Importante sobre tus archivos de OANDA:** MT5 guarda la **hora del servidor** (Nueva York + 7 horas), aunque el archivo diga UTC. Lo comprobé comparando US100 con el NQ real: coinciden con correlación 0,98-0,999 solo con ese desfase. Cárgalos siempre con `--tz mt5`. Con `--tz UTC`, todas las estrategias de la apertura se calculan 3 horas corridas.

**Criterios para comprar la evaluación:**
- [ ] Ejecutaste en demo todas las señales sin errores graves, incluido el parcial con breakeven.
- [ ] Aceptas ~1 trade por semana, semanas sin trades y rachas de 5-8 pérdidas.
- [ ] Entiendes que la probabilidad estimada de aprobar en un año es de ~60-75 % con escalones y las dos estrategias, y que la de suspender es baja (0-2 %) pero no cero.
- [ ] La salud de E1 no está en ALERTA cuando vayas a comprar. Si la de E2 lo está, la apagas.

---

## 9. Gestión de riesgo

- **Riesgo por escalones según el colchón:** el colchón es el saldo menos el nivel donde pierdes la cuenta.

| Colchón | E1 | E2 |
|---|---|---|
| $1.400 o más (al empezar tienes $2.000) | **$300** | **$150** |
| $800 a $1.400 | **$200** | no se opera |
| menos de $800 | **$75** | no se opera |

  - Si vuelves a ganar, el colchón crece y el riesgo sube otra vez.
  - Así, una mala racha nunca te saca de golpe. Con $300 fijo, 7 pérdidas seguidas quemarían la cuenta; con escalones hacen falta muchas más.
  - Cerca del límite solo opera E1, y con poco riesgo.
- **Contratos:** MNQ = riesgo ÷ (puntos hasta el stop × $2), redondeando hacia abajo; MES = riesgo ÷ (puntos × $5).
  - Si el stop está muy lejos para el riesgo de ese momento, no cabe ni 1 contrato y no se opera. En NQ el límite es 150, 100 o 37 puntos con $300, $200 o $75, y 75 puntos para E2 con $150.
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

**Tercera ronda (octubre de 2026): una segunda estrategia y la fusión.** Busqué en internet estrategias con evidencia publicada que encajaran en 9:30-11:30, con trades de máximo 1 hora en NQ/ES. Elegí dos candidatas y las probé con el mismo protocolo: diseño con 2005-2014 y comprobación con 2015-2020, NQ real 2019-2026 y OANDA 2025-26.

| Idea | Resultado |
|---|---|
| **Candidata A: ruptura del rango de la primera hora** (9:30-10:30, operada de 10:30 a 11:30) | **Descartada.** NQ rompe ese rango para un solo lado el 72-84 % de los días, pero después de la ruptura no hay ventaja. Entre −0,02R y −0,23R por operación en casi todos los datos, con 5 tipos de stop y objetivo |
| **Candidata B: Noise Area tal como el paper** (controles a las 10:00, 10:30 y 11:00, a favor o en contra del gap) | **Elegida**, aunque débil así: +0,04R de media, positiva en NQ y negativa en ES |
| Mejora 1: solo el control de las 10:00 | El de las 10:00 fue el mejor en los 4 grupos (hasta +0,30R). Los de 10:30 y 11:00 dieron casi siempre negativo (−0,45R a +0,09R) |
| **Mejora 2: solo a favor del gap** | **La gran mejora.** En NQ, a favor del gap: +0,18R a +0,26R; en contra: −0,13R. En ES, a favor: −0,05R a +0,07R; en contra: −0,18R a −0,33R. En los 4 grupos de datos, a favor del gap rindió más |
| Resultado: Noise Area 10:00 a favor del gap, solo NQ | +0,42R (2005-12), +0,31R (2013-20), +0,69R (2019-22), +0,23R (2023-26). En OANDA 2025-26: −0,04R |
| E2 en ES | +0,14R en 2005-2020, pero −0,38R en 2025-26: descartado |
| E2 con take profit en 2R o 3R, parcial en 1,5R o 2R, stop por ATR, banda ×0,8 o ×1,2, 10 o 20 días de ruido | Todas peores o iguales: se queda como el paper |
| E2 con el trailing del paper (salir si a las 10:30 vuelve a la zona) | Igual que sin trailing: lo quité para que sea más simple |
| E2 con filtros extra (rango overnight, rango de ayer, tendencia, volumen, día de la semana) | Ninguno mejora de forma consistente |
| *Mejoras para la E1:* | |
| Entrada con orden límite en un retroceso (20-50 % hacia el stop) | Peor: se pierden las mejores operaciones, las que no retroceden |
| Breakeven en +1R o +1,5R (antes del parcial) | Peor |
| Salir si a las 10:00 o 10:30 el precio vuelve a la zona de ruido | Peor o igual |
| Operar NQ y ES a la vez cuando los dos califican | Más suspensos en la simulación de la cuenta |
| Exigir que la vela vaya a favor del gap, o que el primer movimiento sea grande comparado con otros días | Mixto: no se sostiene en todos los datos |
| **Último escalón de $75 en vez de $100** | **Adoptado**: en 2005-2026 suspende 1 % de las cuentas en vez de 8 % y aprueba lo mismo |
| *Fusión de E1 y E2 (simulación de LucidFlex 50K, con el mismo nivel de suspensos):* | |
| E2 solo los días sin E1 | Aprueba algo más que E1 sola, pero suspende más que la opción elegida |
| E2 siempre, con el mismo riesgo que E1 | Suspende mucho más: 43 % en 2005-2012 y 15 % en NQ 2019-26 (E1 sola: 16 % y 6 %) |
| E2 solo como refuerzo de E1 (mismo día, misma dirección) | Bueno (+3-5 puntos de aprobación), pero suma pocas operaciones |
| **E2 siempre, a la mitad del riesgo y solo con colchón ≥ $1.400** | **Adoptado**: aprueba 65 % y suspende 1 % en 2005-2026, contra 60 % y 8 % de E1 sola con los escalones anteriores. Termina antes y opera el doble |
| Pausar una estrategia después de 20-50 trades malos (curva de capital) | No ayuda: las operaciones después de una mala racha fueron, en promedio, tan buenas como las demás |

**Lo que sí funcionó:** filtrar con un puntaje armado con condiciones que tienen lógica de mercado. Cada condición mejoró el resultado tanto en los datos usados para elegirla como en los guardados para comprobarla.

**Limitaciones honestas:**
- El puntaje y las salidas se eligieron mirando 2019-2026; la confirmación más limpia es la historia 2005-2020 y el hecho de que los 8 años den positivo.
- No conseguí futuros reales de ES de 2021 a 2024: para ES usé CFD de 2005-2020 y tus datos de OANDA 2025-26.
- 2026 viene flojo en NQ para E1 (+0,01R hasta septiembre) y malo para E2 (−0,24R). Una ventaja de +0,3-0,4R por operación puede desaparecer: repite `scripts/backtest_puntaje.py` cada 1-3 meses con datos nuevos.
- Las reglas de E2 que más ayudan (solo a las 10:00 y solo a favor del gap) las elegí mirando todos los datos. Las condiciones tienen lógica y se cumplen en los 4 grupos de datos por separado, pero no son una prueba tan limpia como un período que nunca miré.

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
   - el volumen de cada vela de 1 minuto;
   - aprender los pesos del puntaje de forma automática con validación por períodos;
   - un puntaje para la E2, como el de E1, cuando haya más datos de 2026-2027 para comprobarlo.
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
| **Noise Area / zona de ruido** | El rango en que el precio se mueve normalmente a esa hora, medido con los últimos 14 días. Fuera de él, el movimiento suele seguir |
| **VWAP** | Precio promedio ponderado por volumen desde las 9:30 |
| **Gap** | Diferencia entre la apertura de hoy (9:30) y el cierre de ayer (16:00) |
| **ATR** | Cuánto se mueve el mercado en un día normal (promedio de 14 días) |
| **Roll** | Cambio al siguiente vencimiento del futuro (cada 3 meses); el indicador lo ajusta solo |
| **Bracket / ATM** | Stop y objetivos puestos junto con la entrada |
| **MLL / límite de pérdida** | Si el saldo toca ese nivel, pierdes la cuenta de fondeo |
| **Trailing al cierre (EOD)** | El límite sube con tu mejor saldo de cierre diario |
| **Dentro / fuera de muestra** | Datos usados para diseñar la regla / datos guardados para comprobarla |
| **NQ / MNQ, ES / MES** | Futuros del Nasdaq-100 y del S&P 500: mini ($20 y $50 por punto) y micro ($2 y $5) |

**Fuentes de las estrategias:**
- E1: Zarattini y Aziz (2023), [*Can Day Trading Really Be Profitable?*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622).
- E2: Zarattini, Aziz y Barbon (2024), [*Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)*](https://www.semanticscholar.org/paper/Beat-the-Market:-An-Effective-Intraday-Momentum-for-Zarattini-Aziz/e498fd2da1bd1422a2b1612253e4d2fbbaf232bf).
- Candidata descartada, estadísticas del rango de la primera hora: [tradingstats.net](https://tradingstats.net/initial-balance-breakout-statistics/) y [edgeful](https://www.edgeful.com/blog/posts/top-3-day-trading-strategies-for-beginners).

**Fuentes de datos:**
- NQ real: velas de 1 minuto de MNQ de Databento, publicadas en [vinentHuynh/QuantResearch](https://github.com/vinentHuynh/QuantResearch).
- CFD 2005-2020: [FutureSharks/financial-data](https://github.com/FutureSharks/financial-data).
- 2025-26: tus datos de OANDA MT5 (`data/oanda`).
