"""Configuraciones listas para usar: estrategia + mercado + parámetros por defecto.

Los parámetros salen de los papers / fuentes citadas, NO de una optimización sobre los datos
(así el backtest es una prueba honesta y no una curva ajustada a posteriori).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Recipe:
    id: str
    strategy: str
    symbol: str  # contrato con el que se backtestea (micro cuando existe, para dimensionar fino)
    title: str
    source: str
    params: dict = field(default_factory=dict)


IDX = dict(window_start="09:30", window_end="16:00")  # índices: sesión cash
GC = dict(window_start="08:20", window_end="13:30")  # oro: sesión COMEX
CL = dict(window_start="09:00", window_end="14:30")  # petróleo: sesión NYMEX
RATES_FX = dict(window_start="08:20", window_end="15:00")  # ZN y 6E
OVERNIGHT = dict(window_start="18:00", window_end="12:00")  # desde la apertura de Globex hasta el mediodía

RECIPES: dict[str, Recipe] = {
    r.id: r
    for r in [
        # --- 1. NQ: ORB de 5 minutos (Zarattini & Aziz 2023) ---------------------------------------
        Recipe("nq_orb5", "orb_zarattini", "MNQ", "NQ · ORB 5 min (10R o cierre)",
               "Zarattini & Aziz (2023), SSRN 4416622", dict(IDX, or_minutes=5, target_r=10.0)),
        Recipe("nq_orb5_atr", "orb_zarattini", "MNQ", "NQ · ORB 5 min, stop 10% ATR, salida al cierre",
               "Zarattini, Barbon & Aziz (2024), SSRN 4729284",
               dict(IDX, or_minutes=5, stop_atr=0.10, target_r=None)),
        Recipe("es_orb5", "orb_zarattini", "MES", "ES · ORB 5 min (10R o cierre)",
               "Zarattini & Aziz (2023), SSRN 4416622", dict(IDX, or_minutes=5, target_r=10.0)),
        # --- 2. ES/NQ: Noise Area (Zarattini, Aziz & Barbon 2024) ------------------------------------
        Recipe("es_noise_area", "noise_area", "MES", "ES · Noise Area (momentum intradía)",
               "Zarattini, Aziz & Barbon (2024), SSRN 4824172", dict(IDX)),
        Recipe("nq_noise_area", "noise_area", "MNQ", "NQ · Noise Area (momentum intradía)",
               "Zarattini, Aziz & Barbon (2024); réplica en ES/NQ de Quantitativo", dict(IDX)),
        # --- 3. Multi-mercado: momentum de la última media hora --------------------------------------
        Recipe("es_last30", "last_half_hour", "MES", "ES · Momentum última media hora",
               "Gao, Han, Li & Zhou (2018, JFE); Baltussen et al. (2021, JFE)", dict(IDX)),
        Recipe("nq_last30", "last_half_hour", "MNQ", "NQ · Momentum última media hora",
               "Gao et al. (2018); Baltussen et al. (2021)", dict(IDX)),
        Recipe("zn_last30", "last_half_hour", "ZN", "ZN · Momentum última media hora",
               "Baltussen et al. (2021): también en futuros de bonos", dict(RATES_FX)),
        Recipe("gc_last30", "last_half_hour", "MGC", "GC · Momentum última media hora",
               "Baltussen et al. (2021): también en materias primas", dict(GC)),
        Recipe("cl_last30", "last_half_hour", "MCL", "CL · 1ª media hora predice la última",
               "Wen, Gong, Ma & Xu (2021), Economic Modelling", dict(CL, predictor="first_half_hour")),
        Recipe("6e_last30", "last_half_hour", "M6E", "6E · Momentum última media hora",
               "Baltussen et al. (2021): también en divisas", dict(RATES_FX)),
        # --- 4. CL: ORB de la apertura de NYMEX ------------------------------------------------------
        Recipe("cl_orb15", "range_breakout", "MCL", "CL · ORB 09:00-09:15 (1,5R)",
               "Práctica habitual en CL (rango de la apertura de NYMEX)",
               dict(CL, range_start="09:00", range_end="09:15", trade_end="11:00", exit_time="14:30",
                    buffer_ticks=2, target_r=1.5)),
        # --- 5. Oro y euro: ruptura del rango asiático en la apertura de Londres ----------------------
        Recipe("gc_london", "range_breakout", "MGC", "GC · Ruptura rango asiático (Londres, 1,5R)",
               "London/Asian range breakout (práctica habitual)",
               dict(OVERNIGHT, range_start="19:00", range_end="03:00", trade_end="10:00", exit_time="11:30",
                    buffer_ticks=2, target_r=1.5)),
        Recipe("6e_london", "range_breakout", "M6E", "6E · London breakout (1,5R)",
               "London breakout en EUR/USD (práctica habitual)",
               dict(OVERNIGHT, range_start="19:00", range_end="03:00", trade_end="09:00", exit_time="11:00",
                    buffer_ticks=1, target_r=1.5)),
        # --- 6. Índices: ORB de 30 minutos manteniendo hasta el cierre --------------------------------
        Recipe("es_orb30", "range_breakout", "MES", "ES · ORB 30 min (stop opuesto, salida al cierre)",
               "Estadística ORB 30 min ES/NQ 2014-2026 (tradingstats.net)",
               dict(IDX, range_start="09:30", range_end="10:00", trade_end="12:00", exit_time="16:00",
                    target_r=None)),
        Recipe("nq_orb30", "range_breakout", "MNQ", "NQ · ORB 30 min (stop opuesto, salida al cierre)",
               "Estadística ORB 30 min ES/NQ 2014-2026 (tradingstats.net)",
               dict(IDX, range_start="09:30", range_end="10:00", trade_end="12:00", exit_time="16:00",
                    target_r=None)),
        # --- 7. Índices: cierre del gap (reversión, winrate alto) ------------------------------------
        Recipe("es_gap_fill", "gap_fill", "MES", "ES · Gap fill 0,10-0,60 % (salida 12:00)",
               "Estadística de cierre de gaps ES/NQ (edgeful, tradingstats.net)",
               dict(IDX, min_gap_pct=0.10, max_gap_pct=0.60)),
        Recipe("nq_gap_fill", "gap_fill", "MNQ", "NQ · Gap fill 0,15-0,80 % (salida 12:00)",
               "Estadística de cierre de gaps ES/NQ (edgeful, tradingstats.net)",
               dict(IDX, min_gap_pct=0.15, max_gap_pct=0.80)),
        # --- Experimento: oro "día vs noche" ---------------------------------------------------------
        Recipe("gc_day_short", "time_of_day", "MGC", "GC · Corto en sesión COMEX (anomalía día/noche)",
               "Overnight vs day returns in gold (J. Economics & Finance, 2018)",
               dict(GC, entry_time="08:20", side=-1)),
    ]
}
