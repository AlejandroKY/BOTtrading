# Bot de señales para TradingView: ORB de 5 minutos en el Nasdaq (NQ / MNQ)

*Octubre de 2026. Herramienta de estudio, no asesoría financiera. Operar futuros puede hacerte perder más de lo que pones.*

El indicador está en [`pine/orb5_nq_senales.pine`](../pine/orb5_nq_senales.pine). Te dice **cuándo comprar o vender, dónde va el stop, dónde va el take profit, cuántos contratos usar y cuándo salir**, y te avisa al celular. Las reglas son exactamente las de la receta `nq_orb5_gap` del kit `futbot`, probadas con 15 años de datos.

---

## 1. Qué esperar (léelo antes de usarlo)

| | |
|---|---|
| Mercado | Nasdaq-100: NQ (mini, $20/punto) o MNQ (micro, $2/punto) |
| Horario | Solo 9:30-11:30 de Nueva York. La señal llega a las **9:35** y la operación termina como máximo a las **11:30** |
| Señales | ~85 al año, **1 o 2 por semana**: solo en los días "en juego" (gap grande) |
| Acierto | **~31 %**: pierdes 2 de cada 3 operaciones |
| Cuando pierdes | Casi siempre exactamente lo que arriesgaste (−1R) |
| Cuando ganas | En promedio **2,7 veces** lo arriesgado; 1 de cada 10 operaciones gana 3R o más |
| Ganancia media | +0,25R bruto por operación; **~+0,12 a +0,22R neto** con los costos actuales |
| Rachas | La peor racha histórica fue de **20 pérdidas seguidas**; con este acierto, 3 de cada 4 años tienen alguna racha de 8 o más (simulación) |
| Meses positivos | 56 % |

Elegimos esta estrategia en vez de una de "80 % de aciertos" porque, con 15 años de datos, fue la **única** de la ventana 9:30-11:30 que mostró ventaja después de costos. Las variantes con target 1:1, y el filtro de probabilidad con 12 condiciones, quedaron en empate o perdieron (detalle en la sección 8). El precio de esa ventaja es aguantar muchas pérdidas chicas para cobrar pocas ganancias grandes.

**Probabilidad de aprobar Topstep 50K** (objetivo $3.000, límite $2.000 que sigue al cierre diario, regla de consistencia del 50 %), según 15 años de datos y costos de hoy:

| Riesgo por operación | Aprueba | Suspende | Tiempo típico hasta aprobar |
|---|---|---|---|
| **$150 (recomendado)** | **58 %** | 38 % | ~6 meses (119 sesiones) |
| $200 | 51 % | 46 % | ~5 meses |
| $250 | 47 % | 52 % | ~4,5 meses |
| $300 | 37 % | 62 % | ~4 meses |
| *Estrategia sin ventaja (azar)* | *23-26 %* | | |

*Simulación arrancando una evaluación cada día de 2005-2020, con tamaño por riesgo (como calcula el indicador) y un costo de ~0,03R por operación, que es lo que pesan hoy comisión y slippage con los rangos de apertura actuales. En [RESULTADOS_BACKTEST.md](RESULTADOS_BACKTEST.md) la misma estrategia con un número fijo de contratos y los costos de 2005-2020 aprueba un 35-39 %: en esos años los rangos medían pocos puntos y los costos pesaban 3 veces más por operación.*

Es una ventaja real pero **lenta**: con 1-2 señales por semana, llegar a $3.000 suele tomar meses, y la suscripción de la evaluación se paga cada mes. Arriesgar más no acelera las cosas: hace más probable que una racha te elimine.

---

## 2. Las reglas, con un ejemplo

1. **9:30-9:35 (Nueva York):** se forma la primera vela de 5 minutos. El indicador dibuja un rectángulo gris con su máximo y su mínimo.
2. **Filtro "día en juego":** solo se opera si la apertura de las 9:30 quedó lejos del cierre de ayer (16:00): el gap debe ser de al menos **0,30 veces el ATR diario**, que es el rango medio de los últimos 14 días. Los días con gap grande suelen tener noticias y tendencia. Los demás días el indicador escribe "Sin señal" y el motivo.
3. **Dirección:** si la vela cerró más arriba de donde abrió → **COMPRA**. Si cerró más abajo → **VENTA**. Si cerró igual → nada.
4. **Entrada:** a mercado a las 9:35, apenas llega la alerta.
5. **Stop loss:** el mínimo de esa vela si compras, o el máximo si vendes. La distancia entre la entrada y el stop es tu **riesgo (1R)**.
6. **Take profit:** 10R. Casi nunca se toca (2 % de las veces); está como tope por si hay un día excepcional.
7. **Salida por hora:** si a las **11:30** no tocó ni el stop ni el take profit, cierras a mercado.

**Ejemplo** (números inventados): ayer NQ cerró en 21.000. Hoy abre a las 9:30 en 21.120, un gap de 120 puntos, y el ATR diario es 300: 120/300 = 0,40 ≥ 0,30, así que es día en juego. La vela de 9:30-9:35 abre en 21.120 y cierra en 21.150: alcista → **COMPRA** a ~21.150. El mínimo de la vela es 21.110, así que el stop va en 21.110 y el riesgo es de 40 puntos. Con MNQ cada punto vale $2, así que 1 contrato arriesga $80; con un riesgo de $150 operas **1 MNQ**, porque 2 serían $160. El take profit (10R) queda en 21.550. Si a las 11:30 el precio está en 21.230, cierras con +80 puntos = **+2R**.

---

## 3. Instalarlo en TradingView

1. Abre el gráfico de **NQ1!** (o MNQ1!) en temporalidad de **5 minutos**. También funciona en 1 minuto, pero carga menos historia.
2. Abajo, abre **Pine Editor** → *Nuevo* → borra el contenido → pega todo el archivo [`pine/orb5_nq_senales.pine`](../pine/orb5_nq_senales.pine) → **Guardar** → **Añadir al gráfico**.
3. En la configuración del indicador (ícono de engranaje):
   - **Riesgo por operación:** $150 para Topstep 50K.
   - **Contrato que operas:** MNQ o NQ. Con $150 de riesgo casi siempre es MNQ.
   - **Comisión:** pon la real de tu cuenta, por contrato e ida y vuelta.
4. **Datos en tiempo real:** sin la suscripción de datos de CME, TradingView muestra los futuros con unos 10 minutos de retraso, y la señal te llegaría tarde. Para operar en vivo contrata los datos en tiempo real de CME, que son un complemento aparte del plan (revisa el precio actual en TradingView). Para estudiar señales pasadas no hacen falta.
5. La hora de Nueva York ya está dentro del script: no importa la zona horaria que tenga tu gráfico.

**Qué vas a ver:**
- un rectángulo gris (el rango de 9:30-9:35);
- una etiqueta verde ▲ COMPRA o roja ▼ VENTA con la entrada, el stop, el TP, los contratos y el riesgo en dólares;
- líneas de entrada (blanca), stop (roja) y take profit (verde punteada) hasta las 11:30;
- al cerrar, una etiqueta ✔ o ✖ con el resultado en R;
- el panel con el estado de hoy, las estadísticas del gráfico y la referencia histórica.

Las estadísticas del panel usan solo las pocas semanas que TradingView carga en el gráfico. Con tan pocas operaciones pueden variar mucho por suerte: la referencia confiable es la histórica (15 años).

---

## 4. Alertas al celular

1. Instala la app de TradingView en el celular e inicia sesión con la misma cuenta.
2. En el gráfico, crea una alerta (ícono del reloj o `Alt + A`):
   - **Condición:** `ORB5 NQ` → **"Cualquier llamada a la función alert()"** (*Any alert() function call*).
   - **Frecuencia:** una vez por cierre de barra.
   - **Vencimiento:** el más largo que permita tu plan.
   - **Notificaciones:** marca *Notificar en la app* (push al celular).
3. Te llegarán dos tipos de mensaje:
   - a las 9:35: `ORB5 NQ COMPRA a mercado | Entrada ≈ … | Stop … | TP … | 1 MNQ (riesgo $80) | Salir 11:30 NY`;
   - al cerrar: `ORB5 NQ: CERRAR posición (hora de salida) ≈ … | Resultado +2.00R`.

La alerta de cierre te sirve de recordatorio a las 11:30 si no tocó ni el stop ni el take profit.

---

## 5. Cómo ejecutar la señal en tu cuenta (TopstepX u otra plataforma)

1. **9:35, llega la alerta:** abre una orden **a mercado** en la dirección indicada, con la cantidad de contratos que dice la etiqueta.
2. **En la misma orden, activa los brackets** (stop loss y take profit) con los precios de la alerta. Así, si te desconectas, el stop sigue puesto.
3. Si llegas tarde y el precio ya avanzó más de un cuarto del riesgo (0,25R) a favor, **no persigas la entrada**: salta esa señal.
4. **Nunca muevas el stop más lejos.** Puedes no tocarlo y dejar que trabaje.
5. **11:30:** si la posición sigue abierta, ciérrala a mercado (*Flatten*).
6. **Una sola operación por día.** Si perdiste, no busques "recuperar" con otra.
7. No subas el tamaño después de ganar ni de perder: siempre el mismo riesgo en dólares.

---

## 6. Plan de validación (tu meta: 4-8 semanas en demo)

**Lo que la demo SÍ puede validar:** que entiendes las señales, que ejecutas a tiempo y sin errores, y cuánto slippage real tienes.

**Lo que la demo NO puede validar:** si la estrategia gana. 8 semanas son ~13 señales, y con 31 % de acierto 13 operaciones pueden dar −5R o +10R por pura suerte. Para medir la ventaja hacen falta años de datos.

**Semana 1:** instala el indicador y revisa los días pasados del gráfico. Comprueba que entiendes por qué hubo o no hubo señal. Practica poner órdenes con brackets en la cuenta de simulación de tu plataforma.

**Semanas 2-8:** toma todas las señales en demo, sin elegir. Anota cada una en un diario: fecha, dirección, entrada esperada y real, stop, salida, resultado en R y errores. Al final compara tu R medio con el del panel: si es mucho peor, el problema está en la ejecución.

**En paralelo, valida la ventaja con datos reales de CME de 2019 a 2026** (el paso más importante, porque mis datos son CFDs de 2005-2020):

```bash
# con Databento (trae $125 de crédito gratis; ver README) descarga NQ 1 minuto 2019-2026 y luego:
python -m futbot stats   --recipe nq_orb5_gap --symbol NQ  --csv data/raw/NQ_1m.csv --tz UTC
python -m futbot prop    --recipe nq_orb5_gap --symbol MNQ --csv data/raw/NQ_1m.csv --tz UTC --firm topstep_50k --max-size 10
```

**Criterios para comprar la evaluación:**
- [ ] Con datos reales 2019-2026, la ganancia media neta es **mayor a +0,05R** y al menos 4 de los 7 años son positivos.
- [ ] En demo ejecutaste **todas** las señales sin errores graves, y tu slippage medio es de 1 tick o menos.
- [ ] Aceptas pasar meses en la evaluación y aguantar 10 o más pérdidas seguidas sin cambiar las reglas.
- [ ] Actualizaste en el indicador la "Referencia histórica" con los números de datos reales.

Si el primer criterio falla, **no compres la evaluación**: volvemos a investigar (sección 8).

**Comprobar que el indicador y futbot dan lo mismo:** en TradingView, *Exportar datos del gráfico* (menú del gráfico) guarda un CSV de NQ1!. Luego ejecuta `python -m futbot backtest --recipe nq_orb5_gap --symbol MNQ --csv export.csv --param risk_usd=150` y compara las operaciones con las etiquetas del gráfico. Yo verifiqué la paridad con una traducción línea a línea del Pine a Python: en 15 años coinciden las 1.308 operaciones en fecha y dirección, y el 99 % en el motivo de salida. Las diferencias restantes eran redondeos de precio de los CFD.

---

## 7. Gestión de riesgo para Topstep 50K

- **Riesgo por operación: $150.** Con $2.000 de límite aguantas 13 pérdidas seguidas. La peor racha de 15 años fue de 20 (más de $2.000 con $150), así que el riesgo de quemar la cuenta existe, aunque es bajo.
- **Contratos:** MNQ = $150 ÷ (riesgo en puntos × $2), redondeando hacia abajo. Si ni 1 MNQ cabe (stop de más de 75 puntos), **no se opera**: el indicador lo marca y no lo cuenta.
- **Regla de consistencia (50 %):** si un día ganas mucho (más de $1.500), la evaluación exigirá ganar más en total. No es un error: sigue operando normal.
- **Límite diario de la firma (opcional en Topstep):** la estrategia hace una sola operación al día, así que el límite diario casi nunca se activa.
- **Al aprobar (cuenta financiada):** las reglas de retiro y consistencia cambian. Mantén el mismo riesgo de $150 hasta tener un colchón sobre el límite.

---

## 8. Por qué no hay "80 % de probabilidad" y cómo vamos a mejorar

**Lo que se probó (NQ 2005-2020, entrenando con 2005-2014 y comprobando con 2015-2020):**
- **9 variantes con target 1:1 o parecido** en la ventana 9:30-11:30 (ORB 5, 15 y 30 minutos, rupturas con distintos stops, Noise Area): todas perdieron después de costos, con acierto de 46-55 %.
- **Un modelo de probabilidad con 12 condiciones de la mañana:** fuera de muestra apenas separó las señales buenas de las malas (AUC 0,53, donde 0,50 es azar).
- **Tomar la mitad de la ganancia rápido (+0,5R) y mover el stop a breakeven:** sube el acierto a ~62 %, pero la ventaja desaparece.
- **La única mejora consistente fue el filtro de gap grande.** Mejoró los dos períodos en el Nasdaq y también 2005-2014 en el S&P 500 y el Russell, mercados que no se usaron para encontrarlo. En esos dos índices, la estrategia completa no gana desde 2015.

**El ciclo de mejora** (cada idea se prueba igual: entrenar con un período, confirmar con otro y con otros mercados):
1. Con datos reales 2019-2026, recalcular las estadísticas (`futbot stats`) y actualizar la referencia del indicador.
2. Ideas en la fila, por orden de evidencia:
   - **Solo compras:** los largos rindieron más en 2015-2020, y otros estudios encuentran el mismo sesgo alcista en ORB de ES/NQ.
   - **Umbral del gap:** cualquier valor entre 0,2 y 0,4 funcionó; revisarlo con datos reales sin sobreajustar.
   - **Salida más tarde** (12:00 o hasta el cierre con brackets) si cambia tu horario: hasta el cierre rindió más.
   - **Segunda estrategia que diversifique:** por ejemplo, el momentum de la última media hora con contratos mini, si algún día puedes estar a esa hora.
3. Tu diario de demo: si tu ejecución difiere del backtest, corregir primero eso.

---

## 9. Glosario

| Término | Qué significa |
|---|---|
| **R** | Lo que arriesgas en una operación (distancia al stop × valor por punto × contratos). "+2R" = ganaste el doble de lo que arriesgaste |
| **Stop loss** | Orden que cierra la operación con pérdida si el precio llega a cierto nivel |
| **Take profit (TP)** | Orden que cierra con ganancia en un nivel fijado |
| **Bracket / OCO** | Stop y take profit puestos juntos: cuando se ejecuta uno, se cancela el otro |
| **ORB** | *Opening Range Breakout*: operar en la dirección del primer rango de la apertura |
| **Gap** | Diferencia entre la apertura de hoy (9:30) y el cierre de ayer (16:00) |
| **ATR** | *Average True Range*: cuánto se mueve el mercado en un día normal (promedio de 14 días) |
| **Slippage** | Diferencia entre el precio que querías y el que te dieron |
| **Win rate / acierto** | % de operaciones ganadoras |
| **Profit factor** | Ganancias totales ÷ pérdidas totales (más de 1 = gana) |
| **Expectativa** | Ganancia media por operación (en R o en $) |
| **Drawdown** | Caída desde el máximo de la cuenta |
| **MLL** | *Maximum Loss Limit* de Topstep: si el saldo toca ese nivel, pierdes la cuenta |
| **Trailing al cierre (EOD)** | El límite sube con tu mejor saldo de cierre diario (hasta el saldo inicial) |
| **Backtest** | Probar las reglas con datos históricos |
| **Dentro / fuera de muestra** | Datos usados para diseñar la regla / datos guardados para comprobarla sin trampas |
| **NQ / MNQ** | Futuro del Nasdaq-100 mini ($20 por punto) / micro ($2 por punto) |
