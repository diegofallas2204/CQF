# WeatherManager.py
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

# Transición por defecto (tu TigerCity) para rellenar filas degeneradas
DEFAULT_TRANSITION = {
    "clear":  {"clear":0.2,"clouds":0.2,"wind":0.2,"heat":0.2,"cold":0.2},
    "clouds": {"clear":0.2,"clouds":0.2,"rain_light":0.2,"wind":0.2,"fog":0.2},
    "rain_light":{"clouds":0.333,"rain_light":0.333,"rain":0.333},
    "rain":   {"rain_light":0.25,"rain":0.25,"storm":0.25,"clouds":0.25},
    "storm":  {"rain":0.5,"clouds":0.5},
    "fog":    {"clouds":0.333,"fog":0.333,"clear":0.333},
    "wind":   {"wind":0.333,"clouds":0.333,"clear":0.333},
    "heat":   {"heat":0.333,"clear":0.333,"clouds":0.333},
    "cold":   {"cold":0.333,"clear":0.333,"clouds":0.333},
}


def _lower(s: str) -> str:
    return s.lower() if isinstance(s, str) else s

def _normalize_weather_cfg(data: dict) -> dict:
    """
    Devuelve una copia normalizada en minúsculas para condiciones y transiciones.
    """
    norm = {}
    initial = data.get("initial", {})
    norm["initial"] = {
        "condition": _lower(initial.get("condition", "clear")),
        "intensity": float(initial.get("intensity", 0.1))
    }
    # lista de condiciones → minúsculas
    conds = data.get("conditions", [])
    norm["conditions"] = [_lower(c) for c in conds]

    # transition → keys y subkeys en minúsculas
    trans = data.get("transition", {})
    norm_trans = {}
    for src, row in trans.items():
        src_l = _lower(src)
        norm_row = {}
        for dst, p in row.items():
            norm_row[_lower(dst)] = float(p)
        norm_trans[src_l] = norm_row
    norm["transition"] = norm_trans
    return norm

def _renorm(row: dict) -> dict:
    s = sum(row.values()) or 1.0
    return {k: (v / s) for k, v in row.items()}

# Multiplicadores base por clima (afectan velocidad)
SPEED_MULT: Dict[str, float] = {
    "clear": 1.00,
    "clouds": 0.98,
    "rain_light": 0.90,
    "rain": 0.85,
    "storm": 0.75,
    "fog": 0.88,
    "wind": 0.92,
    "heat": 0.90,
    "cold": 0.92,
}

# Penalización extra de stamina por celda según clima (se escala por intensidad)
# valores base; se multiplican por intensidad 0..1
STAMINA_PENALTY: Dict[str, float] = {
    "storm": 0.30,
    "heat": 0.20,
    "rain": 0.10,
    "wind": 0.10,
}

# Colores por clima (RGB)
_BG_COLOR: Dict[str, Tuple[int, int, int]] = {
    "clear": (135, 206, 235),
    "clouds": (180, 200, 210),
    "rain_light": (120, 140, 170),
    "rain": (100, 120, 150),
    "storm": (70, 80, 100),
    "fog": (200, 200, 200),
    "wind": (170, 200, 230),
    "heat": (255, 200, 120),
    "cold": (220, 240, 255),
}

def _lerp(a: float, b: float, t: float) -> float:
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t

def _lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )

def _tint(rgb: Tuple[int, int, int], intensity: float) -> Tuple[int, int, int]:
    # Atenúa un 0..25% según intensidad
    k = 1.0 - 0.25 * max(0.0, min(1.0, intensity))
    return (int(rgb[0] * k), int(rgb[1] * k), int(rgb[2] * k))

@dataclass
class WxState:
    condition: str
    intensity: float  # 0..1
    m_climate: float  # multiplicador resultante de clima

class WeatherManager:
    """
    Gestiona ráfagas de clima a partir de un JSON de configuración:
    {
      "version": "...",
      "data": {
        "initial": {"condition": "clear", "intensity": 0.1},
        "conditions": [...],
        "transition": { "<cond>": { "<next>": prob, ...}, ... }
      }
    }
    """
    def __init__(self):
        self.conditions: set[str] = set(SPEED_MULT.keys())
        self.transition: Dict[str, Dict[str, float]] = {}
        self.current: Optional[WxState] = None
        self.target: Optional[WxState] = None

        # Timers
        self._t: float = 0.0            # tiempo dentro de la ráfaga actual
        self._burst_dur: float = 0.0    # duración de ráfaga (60..90 s)
        self._trans_dur: float = 0.0    # duración transición (3..5 s)
        self._trans_t: float = 0.0      # tiempo dentro de la transición

        # Colores cache
        self._bg_current: Tuple[int, int, int] = (150, 180, 200)
        self._bg_target: Tuple[int, int, int] = self._bg_current

    # ---------- Inicialización desde JSON ----------
    def init_from_api_config(self, cfg: dict, *, seed: Optional[int] = 7) -> None:
        if seed is not None:
            random.seed(seed)

        raw = cfg.get("data", {})
        data = _normalize_weather_cfg(raw)  # ↓ todo en minúsculas

        init_cond = data["initial"]["condition"]
        init_int = float(data["initial"]["intensity"])

        # conditions y transition del payload
        self.conditions = set(data.get("conditions") or list(SPEED_MULT.keys()))
        self.transition = data.get("transition", {})

        # --- RELLENO: para cada condición, si la fila está vacía o solo tiene self-loop, usa DEFAULT_TRANSITION
        for cond in (self.conditions or SPEED_MULT.keys()):
            cond = _lower(cond)
            row = self.transition.get(cond, {})
            # consideramos degenerado si no hay fila o si (len==1 y es self-loop)
            if not row or (len(row) == 1 and cond in row):
                fallback = DEFAULT_TRANSITION.get(cond)
                if fallback:
                    # solo incluir destinos válidos que existan en SPEED_MULT (por seguridad)
                    clean = {dst: float(prob) for dst, prob in fallback.items() if dst in SPEED_MULT}
                    self.transition[cond] = _renorm(clean)
                else:
                    # último recurso: quedarse igual
                    self.transition[cond] = {cond: 1.0}
            else:
                # renormaliza la fila existente por si no suma 1.0
                self.transition[cond] = _renorm({ _lower(dst): float(p) for dst, p in row.items() })

        # Asegura que el inicial tenga fila utilizable
        if init_cond not in self.transition:
            self.transition[init_cond] = _renorm(DEFAULT_TRANSITION.get(init_cond, {init_cond: 1.0}))

        self.current = WxState(
            condition=init_cond,
            intensity=init_int,
            m_climate=self._mul_from(init_cond, init_int),
        )
        self.target = None
        self._bg_current = _BG_COLOR.get(init_cond, (150, 180, 200))
        self._bg_target = self._bg_current

        self._t = 0.0
        self._burst_dur = self._rand_burst()
        self._trans_dur = 0.0
        self._trans_t = 0.0

        # Debug útil: ver qué destinos reales tiene 'init_cond'
        print(f"[Weather] init='{init_cond}' int={init_int}  row={list(self.transition.get(init_cond, {}).keys())}")

    # ---------- Bucle principal ----------
    def update(self, dt: float) -> None:
        """Llamar cada frame con dt (segundos). Maneja ráfagas y transición suave."""
        if not self.current:
            return

        # Si estamos en transición, blend
        if self.target and self._trans_t < self._trans_dur:
            self._trans_t += dt
            if self._trans_t >= self._trans_dur:
                # Cerrar transición -> target pasa a ser current
                self.current = self.target
                self.target = None
                self._bg_current = self._bg_target
                self._t = 0.0
                self._burst_dur = self._rand_burst()
            return

        # Ráfaga estable
        self._t += dt
        if self._t >= self._burst_dur:
            # Elegir siguiente clima con la matriz de transición
            nxt_cond = self._pick_next(self.current.condition)
            nxt_int = self._sample_intensity(nxt_cond)
            # dentro de update(), justo donde calculas nxt_cond/nxt_int
            print(f"[Weather] {self.current.condition} -> {nxt_cond} (int={nxt_int})")
            self.target = WxState(
                condition=nxt_cond,
                intensity=nxt_int,
                m_climate=self._mul_from(nxt_cond, nxt_int),
            )
            self._bg_target = _BG_COLOR.get(nxt_cond, self._bg_current)
            self._trans_dur = self._rand_transition()
            self._trans_t = 0.0

    # ---------- Lecturas para Game/Player/UI ----------
    def get_speed_multiplier(self) -> float:
        """Multiplicador de velocidad actual (interpolado si está en transición)."""
        if not self.current:
            return 1.0
        if not self.target or self._trans_dur <= 0.0 or self._trans_t >= self._trans_dur:
            return self.current.m_climate
        alpha = self._trans_t / self._trans_dur
        return _lerp(self.current.m_climate, self.target.m_climate, alpha)

    def get_stamina_penalty_per_cell(self) -> float:
        """Costo extra de stamina por celda en función del clima (0 si no aplica)."""
        cond, inten = self._effective_condition_and_intensity()
        base = STAMINA_PENALTY.get(cond, 0.0)
        return base * max(0.0, min(1.0, inten))

    def get_background_color(self) -> Tuple[int, int, int]:
        """Color de fondo actual (mezcla en transición + tinte por intensidad)."""
        if not self.current:
            return (0, 0, 0)
        if not self.target or self._trans_dur <= 0.0 or self._trans_t >= self._trans_dur:
            return _tint(self._bg_current, self.current.intensity)
        alpha = self._trans_t / self._trans_dur
        blend = _lerp_color(self._bg_current, self._bg_target, alpha)
        cur_tinted = _tint(self._bg_current, self.current.intensity)
        tgt_tinted = _tint(self._bg_target, self.target.intensity)
        return _lerp_color(cur_tinted, tgt_tinted, alpha)

    def get_ui_tuple(self) -> Tuple[str, float, bool]:
        """(condition, intensity, in_transition) para mostrar en HUD."""
        if not self.current:
            return ("unknown", 0.0, False)
        in_trans = bool(self.target and self._trans_t < self._trans_dur)
        cond, inten = self._effective_condition_and_intensity()
        return (cond, float(inten), in_trans)

    # ---------- Utilidades internas ----------
    def _pick_next(self, current: str) -> str:
        row = self.transition.get(current, {})
        if not row:
            return current
        items = list(row.items())
        total = sum(p for _, p in items) or 1.0
        r = random.random()
        acc = 0.0
        for state, p in items:
            acc += p / total
            if r <= acc:
                return state
        return items[-1][0]

    def _mul_from(self, condition: str, intensity: float) -> float:
        base = SPEED_MULT.get(condition, 1.0)
        # Intensidad 0 → 1.0 (sin efecto), Intensidad 1 → base completo
        return _lerp(1.0, base, max(0.0, min(1.0, intensity)))

    def _sample_intensity(self, state: str) -> float:
        if state in ("clear", "clouds"):
            lo, hi = 0.1, 0.6
        elif state in ("rain_light", "rain", "storm"):
            lo, hi = 0.3, 0.95
        elif state in ("heat", "cold"):
            lo, hi = 0.2, 0.8
        else:  # fog, wind
            lo, hi = 0.2, 0.7
        return round(random.uniform(lo, hi), 2)

    def _rand_burst(self) -> float:
        return float(random.randint(60, 90))  # segundos

    def _rand_transition(self) -> float:
        return float(random.randint(3, 5))    # segundos

    def _effective_condition_and_intensity(self) -> Tuple[str, float]:
        if not self.current:
            return ("clear", 0.0)
        if not self.target or self._trans_dur <= 0.0 or self._trans_t >= self._trans_dur:
            return (self.current.condition, self.current.intensity)
        alpha = self._trans_t / self._trans_dur
        cond = self.target.condition if alpha > 0.5 else self.current.condition
        inten = _lerp(self.current.intensity, self.target.intensity, alpha)
        return (cond, inten)
