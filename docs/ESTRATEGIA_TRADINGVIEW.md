# Bot de señales para TradingView: ORB 5 minutos rápido en el Nasdaq (NQ / MNQ)

*Octubre de 2026. Herramienta de estudio, no asesoría financiera. Operar futuros puede hacerte perder más de lo que pones.*

El indicador está en [`pine/orb5_nq_rapido.pine`](../pine/orb5_nq_rapido.pine). Te dice **si hoy se opera, cuándo comprar o vender, dónde va el stop, cuántos contratos usar y a qué hora salir**, y te avisa al celular. Sus reglas son exactamente las de la receta `nq_orb5_rapida` del kit `futbot`. Lo verifiqué traduciendo el Pine línea a línea a Python: con 7 años de datos reales de CME coinciden las 543 operaciones, tanto en gráfico de 1 minuto como de 5 minutos.

**Qué cambió respecto de la versión anterior** (`orb5_nq_senales.pine`, que mantenía la operación hasta las 11:30):
- Al probarla con datos reales de CME 2019-2026, la versión anterior dio apenas **+0,08R por operación**, y en 2026 perdía (−0,15R). Por eso la reemplacé.
- La nueva versión es un **trade rápido**: la mitad de las operaciones termina en menos de 7 minutos y ninguna dura más de 60.
- Con los mismos datos rinde **+0,30R por operación**, y los 8 años son positivos.
- Las etiquetas ya no se superponen y el indicador no muestra señales contradictorias. Si una señal no se puede operar, sale en gris con el motivo.

---

## 1. Qué esperar (léelo antes de usarlo)

| | |
|---|---|
| Mercado | Nasdaq-100: MNQ (micro, $2/punto) o NQ (mini, $20/punto) |
| Horario | La señal llega a las **9:35** de Nueva York y la operación termina como máximo a las **10:35** |
| Duración | Mediana **7 minutos**. Los stops saltan en ~3 minutos y el 75 % de las operaciones dura menos de 40 minutos |
| Señales | ~76 al año, **1 o 2 por semana**. Solo hay señal en los días "en juego" (gap grande) |
| Acierto | **~24 %**: pierdes 3 de cada 4 operaciones |
| Cuando pierdes | En promedio −1,07R (casi siempre exactamente lo arriesgado) |
| Cuando ganas | En promedio **+4,5R**. Las pocas operaciones grandes pagan todas las pérdidas |
| Ganancia media | **+0,30R por operación**, ya descontados comisión y deslizamiento (1,2 puntos por operación) |
| Rachas | La peor racha de 2019-2026 fue de **18 pérdidas seguidas** |
| Meses | En 2024-2026, solo **16 de 32 meses** fueron positivos (peor mes −$1.078, mejor +$3.464, con $150 por operación) |

**No hay 80 % de acierto, y no lo voy a inventar.** Probé setups de acierto alto (objetivos de 1R, comprar retrocesos, ir contra la primera vela y un modelo de probabilidad): todos perdieron después de costos (sección 9). Esta estrategia gana porque aguanta muchas pérdidas chicas para cobrar pocas ganancias grandes. Si cierras las ganadoras temprano (por ejemplo en 3R), la ventaja desaparece.

---

## 2. Confirmación con datos reales de 2024, 2025 y 2026

**Datos:** velas de 1 minuto del micro Nasdaq MNQ de CME, de mayo de 2019 al 3 de septiembre de 2026, publicadas por Databento en el repositorio público [vinentHuynh/QuantResearch](https://github.com/vinentHuynh/QuantResearch). Les quité el salto de cada cambio de contrato (roll). Los datos no están en este repo porque tienen licencia de CME: puedes bajar los tuyos con el script de Databento (sección 7).

**Resultado año por año.** Es lo que habría mostrado el indicador con $150 de riesgo por operación en MNQ, a los precios de cada año y neto de costos:

| Año | Operaciones | Acierto | R medio | Resultado | Peor caída del año |
|---|---|---|---|---|---|
| 2019 (desde mayo) | 23 | 30 % | +0,01R | −$76 | −$948 |
| 2020 | 78 | 21 % | +0,03R | +$453 | −$2.750 |
| 2021 | 73 | 25 % | +0,63R | +$6.546 | −$1.211 |
| 2022 | 74 | 26 % | +0,44R | +$4.563 | −$2.000 |
| 2023 | 65 | 22 % | +0,11R | +$1.048 | −$2.333 |
| **2024** | **79** | **25 %** | **+0,27R** | **+$1.863** | **−$3.145** |
| **2025** | **86** | **29 %** | **+0,56R** | **+$6.399** | **−$1.256** |
| **2026 (a sept.)** | **65** | **22 %** | **+0,11R** | **+$1.772** | **−$1.448** |
| **Total** | **543** | **24 %** | **+0,30R** | **+$22.567** | |

**Otras pruebas:**
- **Otra fuente para 2026.** Con NQ de abril a septiembre de 2026 (getdata-finance), las señales coinciden 100 % en dirección con las de MNQ. El resultado fue +0,12R por operación en 36 operaciones.
- **Antes de 2019.** Con el CFD del Nasdaq de Oanda dio +0,24R en 2005-2014 (629 operaciones) y +0,30R en 2015-2020 (418 operaciones), con los costos llevados a los precios de hoy. No son futuros reales, pero en 2019-2020, donde se solapan con MNQ, las señales coinciden en dirección el 100 % de las veces.
- **Ambas direcciones ganan:** compras +0,18R y ventas +0,43R por operación.

**Cómo se eligió, sin hacer trampa:**
- Probé 144 variantes de trade rápido en MNQ real. Las ordené mirando **solo 2019-2022** y llevé las 3 mejores a **2023-2026**, con un criterio estricto fijado antes: R medio > 0 con t > 1,5.
- **Ninguna pasó ese criterio.** La 1ª falló. La 2ª, que es esta, fue positiva en los dos períodos (+0,22R y +0,18R) y en 7 de 8 años, pero con t = 1,2. Es la mejor candidata, aunque la elegí después de ver 2023-2026.
- Después agregué una regla de sentido común: **no operar si el stop queda a menos de 6 puntos**. Ahí las comisiones se comen entre el 25 % y el 150 % del riesgo.
- Con esa regla quedó en +0,33R y +0,27R, con 8 de 8 años positivos.
- Esa regla se decidió *después* de ver los datos. Además, la estadística por período es moderada (t de 1,7-1,8 en cada mitad y 2,4 en total). Hay ventaja, pero **no hay certeza**: puede tener rachas largas sin ganar, como 2019-2020, 2023 o la primera mitad de 2026.

---

## 3. Probabilidad de aprobar Topstep 50K

Reglas simuladas: objetivo $3.000, límite de $2.000 que sigue al cierre diario y regla de consistencia del 50 %. La simulación arranca una evaluación cada día de 2019-2026 con datos reales de MNQ llevados al precio de hoy. Usa contratos enteros de MNQ, calculados como lo hace el indicador.

| Riesgo por operación | Aprueba | Suspende | No termina en 1 año | Tiempo típico hasta aprobar |
|---|---|---|---|---|
| $100 | 15 % | 10 % | 75 % | ~9-10 meses |
| **$150 (recomendado)** | **47 %** | **38 %** | 16 % | ~6 meses (120 sesiones) |
| $200 | 49 % | 48 % | 3 % | ~4,5 meses |
| $300 | 39 % | 60 % | <1 % | ~4 meses |

Es una ventaja real pero **lenta**, y es casi una moneda al aire si cuentas que la evaluación se paga cada mes. Arriesgar más acelera el camino, pero también hace más probable que una racha te elimine: en 2024 la caída máxima fue de $3.145 con $150 por operación, más que el límite de $2.000. **No es "fácil"**: nadie honesto puede prometer eso.

---

## 4. Las reglas, con un ejemplo

1. **Día en juego:** solo se opera si la apertura de las 9:30 quedó lejos del cierre de ayer (16:00). El gap tiene que ser de al menos **0,30 veces el ATR diario**, que es cuánto se mueve el NQ en un día normal (promedio de 14 días). Sin este filtro, la estrategia pierde.
2. **9:30-9:35:** se forma la primera vela de 5 minutos. Si cerró **más arriba** de donde abrió → **COMPRA**. Si cerró **más abajo** → **VENTA**. Si cerró igual → nada.
3. **Entrada:** a mercado a las 9:35.
4. **Stop loss:** en la **mitad de esa vela**, redondeada al tick alejándose de la entrada. La distancia entre la entrada y el stop es tu riesgo (1R). Si el stop queda a menos de **6 puntos**, no se opera.
5. **Take profit:** 10R. Está lejos a propósito y solo se toca un 3-4 % de las veces.
6. **Salida por tiempo:** si a las **10:35** no tocó ni el stop ni el take profit, cierras a mercado.
7. **Tamaño:** contratos = riesgo en USD ÷ (puntos hasta el stop × valor del punto), redondeando hacia abajo. Si no cabe ni 1 contrato, no se opera.

**Ejemplo** (números inventados):
- **El gap.** Ayer el NQ cerró en 24.000. Hoy abre a las 9:30 en 24.180 y el ATR diario es 450. El gap es de 180 puntos, y 180 / 450 = 0,40, que es al menos 0,30: es día en juego.
- **La señal.** La vela de 9:30-9:35 va de un mínimo de 24.150 a un máximo de 24.250 y cierra en 24.230, más arriba de donde abrió (24.180): **COMPRA** a ~24.230.
- **El stop.** La mitad de la vela es (24.250 + 24.150) / 2 = 24.200. Ese es el stop, a 30 puntos de la entrada.
- **El tamaño.** Con MNQ, 30 puntos × $2 = $60 por contrato. Con $150 de riesgo operas **2 MNQ** (riesgo de $120).
- **La salida.** El take profit queda en 24.530. Si a las 10:35 el precio está en 24.290, cierras con +60 puntos = **+2R** = +$240 menos comisiones.

---

## 5. Instalarlo en TradingView

1. Abre el gráfico de **NQ1!** o **MNQ1!** en **5 minutos**. También funciona en 1 minuto; otras temporalidades no.
2. Abajo, abre **Pine Editor** → *Nuevo*. Borra el contenido, pega todo el archivo [`pine/orb5_nq_rapido.pine`](../pine/orb5_nq_rapido.pine) y luego **Guardar** → **Añadir al gráfico**. Si tenías la versión anterior (*ORB 5m NQ · Señales*), quítala del gráfico.
3. En la configuración del indicador (ícono de engranaje):
   - **Riesgo por operación:** $150 para Topstep 50K.
   - **Contrato que operas:** MNQ. Con $150 casi siempre son 1-3 MNQ.
   - **Costo por operación:** 1,2 puntos (comisión + deslizamiento). Súbelo si tu comisión es mayor.
   - **Stop mínimo:** 6 puntos.
4. **Datos en tiempo real:** sin la suscripción de datos de CME, TradingView muestra los futuros con ~10 minutos de retraso y la señal te llegaría tarde. Para operar en vivo contrata los datos de CME, que se pagan aparte del plan. Para estudiar señales pasadas no hacen falta.
5. **No configures nada más:**
   - La hora de Nueva York ya está dentro del script.
   - El gap y el ATR se calculan con datos **ajustados por cambio de contrato**, para evitar gaps falsos los días de roll (4 veces al año).
   - Usa la sesión completa de Globex aunque tu gráfico muestre solo el horario regular.

### Qué vas a ver

| En el gráfico | Qué significa |
|---|---|
| Rectángulo **gris** sobre la vela de 9:30 + texto "sin trade: …" | Hoy no se opera, y el motivo: gap chico, vela sin dirección, stop muy cerca o riesgo mayor a tu límite |
| Rectángulo **verde o rojo** sobre la vela de 9:30 ("vela 9:30") | Esa vela dio la señal |
| Línea punteada gris **"cierre ayer"** | Cierre de ayer a las 16:00. La distancia hasta la apertura de las 9:30 es el gap |
| Etiqueta **COMPRA** (verde) o **VENTA** (roja) a las 9:35 | La señal. Pasa el mouse encima para ver el plan completo |
| Línea gruesa + texto "entrada … · salir 10:35" | Precio de entrada y hora de salida |
| Zona **roja** con "STOP … −$… · N MNQ" | Tu riesgo: de la entrada al stop, con contratos y dólares |
| Zona **verde** con "máx +1,6R" | Hasta dónde llegó el precio a tu favor |
| Etiqueta final **"+2,1R +$310"** o **"−1,0R −$150"** | El resultado neto de costos. Pasa el mouse para ver si salió por stop, por tiempo o por take profit |
| **Panel** (arriba a la derecha) | Estado de hoy, señal, niveles, take profit, estado de la operación, estadísticas del gráfico y referencia del backtest |

La fila "En este gráfico" del panel cuenta solo las operaciones del historial que TradingView tiene cargado, que suelen ser pocas semanas. Con tan pocas operaciones puede salir cualquier cosa por suerte. La referencia confiable es la de la sección 2.

---

## 6. Alertas al celular y cómo ejecutar

**Crear la alerta:**
1. Instala la app de TradingView en el celular con la misma cuenta.
2. En el gráfico, crea una alerta (ícono del reloj o `Alt + A`):
   - **Condición:** `ORB5 rápido` → **"Cualquier llamada a la función alert()"**.
   - **Notificaciones:** *Notificar en la app*.
   - **Vencimiento:** el más largo que permita tu plan.

**Mensajes que te llegarán:**
- **9:35:** `COMPRA 2 MNQ a mercado ~24230 | STOP 24200 | TP 24530 | cerrar a las 10:35 NY`.
- **Si toca el stop:** `STOP tocado: compra cerrada en ~24200 (−1.0R)`.
- **10:35:** `SALIDA 10:35: cierra la compra a mercado ahora (~24290, +2.0R)`.

**Cómo ejecutar** (TopstepX u otra plataforma):
1. **9:35:** abre una orden **a mercado** con los contratos indicados, **con bracket**: el stop y el take profit del mensaje. Así, si te desconectas, el stop sigue puesto.
2. **Si llegas tarde** y el precio ya avanzó a tu favor más de un cuarto del riesgo (0,25R), o ya tocó el stop, **salta la señal**.
3. **No cierres antes por miedo ni por euforia.** Las salidas son solo tres: stop, take profit o 10:35. Las ganancias grandes, que pagan todo, ocurren justamente cuando uno tiene ganas de cerrar.
4. **10:35:** si la posición sigue abierta, ciérrala a mercado (*Flatten*).
5. **Nunca muevas el stop más lejos.**
6. **Una sola operación por día.**
7. **Mismo riesgo siempre:** no subas después de ganar ni de perder.

---

## 7. Plan de validación (tu meta: 4-8 semanas en demo)

**Lo que la demo SÍ valida:** que entiendes las señales, que ejecutas a tiempo y cuánto deslizamiento real tienes.

**Lo que la demo NO valida:** si la estrategia gana. 8 semanas son ~12 señales, y con 24 % de acierto 12 operaciones pueden dar −10R o +15R por pura suerte. Para eso están los 7 años de la sección 2.

1. **Semana 1:**
   - Instala el indicador y revisa los días pasados del gráfico. Comprueba que entiendes por qué hubo o no hubo señal.
   - Practica órdenes con bracket en la cuenta de simulación.
2. **Semanas 2-8:**
   - Toma **todas** las señales en demo, sin elegir.
   - Anota cada una: fecha, dirección, entrada esperada y real, stop, salida, resultado en R y errores.
   - Al final compara tu R medio con el del panel. Si es mucho peor, el problema está en la ejecución (llegar tarde, cerrar antes).

**Repetir la prueba con tus propios datos** (opcional, para no depender de mí):

```bash
pip install databento pandas pyarrow
# PowerShell: $env:DATABENTO_API_KEY = "db-..."   (tu clave queda solo en tu PC, no la pegues en el chat)
python scripts/descargar_datos_databento.py --symbol NQ --start 2019-06-01 --estimate   # cuánto cuesta (crédito gratis $125)
python scripts/descargar_datos_databento.py --symbol NQ --start 2019-06-01
python -m futbot stats --recipe nq_orb5_rapida --symbol NQ --csv "data/real/NQ_1m_*.parquet"
python -m futbot prop  --recipe nq_orb5_rapida --symbol MNQ --csv "data/real/NQ_1m_*.parquet" --firm topstep_50k --param risk_usd=150 --max-size 2
```

`futbot` ajusta solo los cambios de contrato, con la columna `instrument_id` que guarda el script. En `prop`, el tamaño 1 equivale a $150 por operación y el 2 a $300, a los precios de cada año. Mis tablas de la sección 3 usan el precio de hoy, así que tus números van a variar un poco. No subas esos datos a un repositorio público, porque tienen licencia de CME.

**Criterios para comprar la evaluación:**
- [ ] En demo ejecutaste **todas** las señales sin errores graves, y tu deslizamiento medio es de 1-2 ticks.
- [ ] Aceptas pasar meses en la evaluación, aguantar 15 o más pérdidas seguidas y varios meses en negativo sin cambiar las reglas.
- [ ] Entiendes que la probabilidad estimada de aprobar es de ~50 %, no 100 %.

---

## 8. Gestión de riesgo para Topstep 50K

- **Riesgo por operación: $150.** Con $2.000 de límite aguantas ~13 pérdidas seguidas. La peor racha de 2019-2026 fue de 18, así que el riesgo de quemar la cuenta existe (38 % en la simulación).
- **Contratos:** MNQ = $150 ÷ (puntos hasta el stop × $2), redondeando hacia abajo.
  - Si el stop está a más de 75 puntos, no cabe ni 1 MNQ: **no se opera**. En 2026 pasó en ~8 % de las señales.
  - Si está a menos de 6 puntos, tampoco se opera: las comisiones se comerían la ganancia.
- **Regla de consistencia (50 %):** si un día ganas mucho (más de $1.500, por ejemplo con un take profit de 10R), la evaluación exigirá ganar más en total. No es un error: sigue operando normal.
- **Límite diario:** con una sola operación por día y $150 de riesgo, el límite diario no se activa.
- **Al aprobar:** las reglas de retiro y consistencia cambian. Mantén $150 por operación hasta tener un colchón sobre el límite.

---

## 9. Qué se probó y qué no funcionó

| Idea | Resultado |
|---|---|
| Versión anterior: ORB 5 min + gap, stop en el extremo de la vela, hasta las 11:30 | +0,08R/operación en MNQ real 2019-2026; −0,15R en 2026. **Reemplazada** |
| Solo compras + stop en la mitad + salida 10:05 (elegida con CFD y una muestra chica de 2026) | **Falló** en 2021-2025: −0,07R/operación, 1 de 5 años positivo |
| Objetivos de 1R a 3R (más acierto) | Pierden o quedan en cero: la ventaja vive en las pocas operaciones que corren mucho |
| Ir contra la primera vela (fade), comprar el retroceso al 50 %, esperar el cierre fuera del rango de 15-30 min | Pierden después de costos |
| Sin el filtro de gap | Pierde en todos los períodos y con cualquier hora de salida |
| Modelo de "probabilidad de ganar" con 12 condiciones (CFD 2005-2020) | Fuera de muestra no separó nada (AUC 0,53; 0,50 = azar) |

**Lo que dice la investigación publicada:**
- Dos estudios de 2026 encuentran que las señales intradía de los futuros de índices **no sobreviven a los costos** en promedio: Fetna (225 pruebas pre-registradas en 9 futuros) y Mesfin (MNQ 2021-2025).
- El registro de investigación del repositorio de donde salieron los datos llega a lo mismo con SPY/QQQ.
- Nuestra ventaja es modesta y concentrada (días en juego, 1 hora, stop ajustado). **Puede desaparecer.** Por eso:
  - el panel muestra los resultados reales en tu gráfico;
  - conviene repetir la prueba cada 6 meses con datos nuevos (`futbot stats`). Si 12 meses seguidos salen negativos, para y revisa.

**Ideas que quedan en fila** (cada una se prueba igual: elegir con un período, comprobar con otro):
1. Ajustar el tamaño según el ATR del día.
2. Una segunda estrategia que no dependa de la apertura, para diversificar.
3. Revisar el umbral del gap (0,2 a 0,5 funcionó) sin sobreajustar.

---

## 10. Glosario

| Término | Qué significa |
|---|---|
| **R** | Lo que arriesgas en una operación (puntos hasta el stop × valor por punto × contratos). "+2R" = ganaste el doble de lo arriesgado |
| **Stop loss** | Orden que cierra la operación con pérdida si el precio llega a cierto nivel |
| **Take profit (TP)** | Orden que cierra con ganancia en un nivel fijado |
| **Bracket / OCO** | Stop y take profit puestos juntos: cuando se ejecuta uno, se cancela el otro |
| **ORB** | *Opening Range Breakout*: operar en la dirección del primer rango de la apertura |
| **Gap** | Diferencia entre la apertura de hoy (9:30) y el cierre de ayer (16:00) |
| **ATR** | *Average True Range*: cuánto se mueve el mercado en un día normal (promedio de 14 días) |
| **Roll / cambio de contrato** | Cada 3 meses el futuro "vigente" pasa al siguiente vencimiento, que cotiza a otro precio; sin ajustar, eso crea un gap falso |
| **Slippage / deslizamiento** | Diferencia entre el precio que querías y el que te dieron |
| **Acierto (win rate)** | % de operaciones ganadoras |
| **Expectativa** | Ganancia media por operación (en R o en $) |
| **Drawdown / caída** | Pérdida desde el máximo de la cuenta |
| **MLL** | *Maximum Loss Limit* de Topstep: si el saldo toca ese nivel, pierdes la cuenta |
| **Trailing al cierre (EOD)** | El límite sube con tu mejor saldo de cierre diario (hasta el saldo inicial) |
| **Dentro / fuera de muestra** | Datos usados para elegir la regla / datos guardados para comprobarla sin trampas |
| **t (estadístico t)** | Qué tan lejos de cero está la ganancia media comparada con el ruido; más de 2 es evidencia razonable |
| **NQ / MNQ** | Futuro del Nasdaq-100 mini ($20 por punto) / micro ($2 por punto) |
