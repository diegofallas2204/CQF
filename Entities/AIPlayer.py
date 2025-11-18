"""
Entities/AIPlayer.py

Clases base y esqueletos para agentes controlados por IA:
- AIPlayer: interfaz/base común
- RandomAI: comportamiento fácil (aleatorio)
- HeuristicAI: comportamiento medio (horizonte limitado / greedy)
- GraphAI: comportamiento difícil (A*, Dijkstra, planificación de rutas)

Estas clases deben integrarse con Game.py a través de:
 - update_world(city, orders, weather)
 - decide_accept_order() -> Optional[order_id]
 - decide_move() -> (dx, dy)  or next_position
 - on_tick(delta_time)
"""

from typing import Any, Dict, Optional, Tuple, List
import random
import math

class AIPlayer:
    def __init__(self, name: str = "CPU", difficulty: str = "easy"):
        self.name = name
        self.difficulty = difficulty
        self.position: Tuple[int, int] = (1, 1)
        self.stamina: float = 100.0
        self.reputation: int = 70
        self.inventory_ids: List[str] = []
        self.max_weight: float = 10.0
        self.current_target_order_id: Optional[str] = None
        self.route: List[Tuple[int,int]] = []  # planned path (seq of positions)
        self.total_earnings: int = 0  # Track AI earnings

    # ----- World / data input -----
    def update_world(self, city: Any, orders: Dict[str, Any], weather: Any):
        """
        Entregar al agente la vista actual del mundo.
        - city: instancia Entities.City
        - orders: dict de order_id -> Order
        - weather: WeatherManager u objeto con info de clima
        """
        self.city = city
        self.orders = orders
        self.weather = weather

    # ----- Decision API -----
    def decide_accept_order(self) -> Optional[str]:
        """Decide si aceptar un pedido disponible. Retorna el order_id o None."""
        raise NotImplementedError

    def decide_move(self) -> Tuple[int, int]:
        """
        Devuelve un movimiento relativo (dx,dy) o (0,0) para quedarse quieto.
        Implementación debe respetar is_walkable y stamina.
        """
        raise NotImplementedError

    def on_tick(self, delta_time: float):
        """Actualizaciones por tick (recuperación stamina, timers)."""
        # ejemplo: recuperar stamina lentamente
        pass

    # helpers de utilidad
    def distance_manhattan(self, a: Tuple[int,int], b: Tuple[int,int]) -> int:
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

# ---- Nivel fácil: RandomAI ----
class RandomAI(AIPlayer):
    def __init__(self, name: str = "CPU-Random"):
        super().__init__(name=name, difficulty="easy")
        self._rng = random.Random()

    def decide_accept_order(self) -> Optional[str]:
        # elige un pedido disponible al azar si cabe
        available = [
            o for o in self.orders.values()
            if getattr(o, "state", None) and str(getattr(o, "state")).
               lower().startswith("available")
        ]
        if not available:
            return None
        choice = self._rng.choice(available)
        return getattr(choice, "id", None)

    def decide_move(self) -> Tuple[int,int]:
        # mueve al azar entre vecinos caminables
        x,y = self.position
        neighbors = [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
        walkables = [n for n in neighbors if self.city.is_walkable(n[0], n[1])]
        if not walkables:
            return (0,0)
        nx,ny = self._rng.choice(walkables)
        return (nx - x, ny - y)

# ---- Nivel medio: HeuristicAI (horizonte limitado) ----
class HeuristicAI(AIPlayer):
    def __init__(self, name: str = "CPU-Heuristic", horizon: int = 2, alpha:float=1.0, beta:float=1.0, gamma:float=1.0):
        super().__init__(name=name, difficulty="medium")
        self.horizon = horizon
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def score_order(self, order) -> float:
        """
        Función heurística simplificada:
        score = alpha * payout - beta * distance_cost - gamma * weather_penalty
        """
        try:
            payout = float(order.payout)
            pickup = tuple(order.pickup)
            dist = self.distance_manhattan(self.position, pickup)
            weather_penalty = getattr(self.weather, "get_stamina_penalty_per_cell", lambda: 0.0)()
            return self.alpha * payout - self.beta * dist - self.gamma * weather_penalty
        except Exception:
            return -float("inf")

    def decide_accept_order(self) -> Optional[str]:
        # evalúa available orders por heurística y escoge la mejor si mejora la expectativa
        candidates = [o for o in self.orders.values() if getattr(o,"state",None) and str(getattr(o,"state")).lower().startswith("available")]
        if not candidates:
            return None
        scored = sorted(candidates, key=lambda o: self.score_order(o), reverse=True)
        best = scored[0]
        # umbral simple: aceptar si score positiva y cabe en capacidad
        if self.score_order(best) > 0:
            return getattr(best, "id", None)
        return None

    def decide_move(self) -> Tuple[int,int]:
        # simple: si hay target_order, moverse hacia pickup/dropoff según estado
        if self.current_target_order_id and self.current_target_order_id in self.orders:
            o = self.orders[self.current_target_order_id]
            # target position depende si pick-up o already picked
            target = getattr(o, "pickup", None)
            if getattr(o, "state", None) and str(getattr(o,"state")).lower().startswith("picked_up"):
                target = getattr(o, "dropoff", None)
            if target:
                tx,ty = int(target[0]), int(target[1])
                x,y = self.position
                dx = 0 if tx==x else (1 if tx>x else -1)
                dy = 0 if ty==y else (1 if ty>y else -1)
                # elegir mover en x o y primero (simple tie-break)
                if dx != 0 and self.city.is_walkable(x+dx, y):
                    return (dx,0)
                if dy != 0 and self.city.is_walkable(x, y+dy):
                    return (0,dy)
        # fallback: quedarse quieto
        return (0,0)

# ---- Nivel difícil: GraphAI (A* / Dijkstra / planificación) ----
class GraphAI(AIPlayer):
    def __init__(self, name:str="CPU-Graph", planner=None):
        super().__init__(name=name, difficulty="hard")
        self.planner = planner  # inyectar Graph/astar planner externo
        self.route: List[Tuple[int,int]] = []

    def decide_accept_order(self) -> Optional[str]:
        # evaluar relación payout/cost (placeholder)
        best_id = None
        best_value = -float("inf")
        for o in self.orders.values():
            if not str(getattr(o,"state")).lower().startswith("available"):
                continue
            # estimar coste con planner (si disponible)
            try:
                pickup = tuple(o.pickup)
                if self.planner:
                    cost = self.planner.estimate_cost(self.position, pickup)
                else:
                    cost = self.distance_manhattan(self.position, pickup)
                value = float(o.payout) - cost
                if value > best_value:
                    best_value = value
                    best_id = o.id
            except Exception:
                continue
        if best_value > 0:
            return best_id
        return None

    def plan_route_to(self, position: Tuple[int,int]):
        if self.planner:
            self.route = self.planner.path(self.position, position)
        else:
            self.route = []

    def decide_move(self) -> Tuple[int,int]:
        # si hay ruta planeada, seguirla
        if self.route:
            next_pos = self.route.pop(0)
            x,y = self.position
            nx,ny = next_pos
            return (nx-x, ny-y)
        # fallback: quedarse quieto
        return (0,0)