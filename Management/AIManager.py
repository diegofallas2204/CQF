import logging
import random
import time
from collections import deque
from datetime import datetime
from typing import Any, List, Optional, Tuple

logger = logging.getLogger("AIManager")


class AIManager:
    def __init__(self, difficulty: str = "easy", planner: Optional[Any] = None):
        """
        difficulty: "easy" | "medium" | "hard"
        planner: objeto con métodos path(a,b) y estimate_cost(a,b) (usado en hard)
        """
        self.difficulty = difficulty
        self.planner = planner
        self.agent = None  # se crea en reset()
        self.last_tick = time.time()

        # Parametrización por dificultad
        if difficulty == "easy":
            self.decision_interval = 1.2
            self.min_action_interval = 0.5
        elif difficulty == "medium":
            self.decision_interval = 0.7
            self.min_action_interval = 0.35
        elif difficulty == "hard":
            self.decision_interval = 0.35
            self.min_action_interval = 0.15
        else:
            self.decision_interval = 1.2
            self.min_action_interval = 0.5

        self.action_cooldown = 0.0
        self.last_decision_time = 0.0
        self.last_movement_time = 0.0  # Track when AI last moved for stamina recovery

        # Referencias al juego (setear con register_game_refs / attach_game)
        self._city = None
        self._order_mgr = None
        self._weather_mgr = None
        self._game = None
        self.game = None  # alias

        # Anti‑oscilación (Medium/Hard)
        self._recent_positions = deque(maxlen=10)

        # Memoria clima (Hard)
        self._last_weather_speed = None

        # Planificación secundaria (Hard)
        self._hard_next_planned = None

    # -----------------------
    # Creación del agente
    # -----------------------
    def _create_agent(self, diff: str):
        """Crea instancia de AIPlayer concreta según la dificultad."""
        if diff == "easy":
            from Entities.AIPlayer import RandomAI

            return RandomAI()
        if diff == "medium":
            from Entities.AIPlayer import HeuristicAI

            return HeuristicAI()
        if diff == "hard":
            from Entities.AIPlayer import GraphAI

            return GraphAI(planner=self.planner)
        from Entities.AIPlayer import RandomAI

        return RandomAI()

    # -----------------------
    # Integración con Game
    # -----------------------
    def register_game_refs(self, city: Any, order_manager: Any, weather_manager: Any):
        """Registra referencias para que la IA consulte el mundo."""
        self._city = city
        self._order_mgr = order_manager
        self._weather_mgr = weather_manager
        # mantener nombres legacy
        self.city = city
        self.order_manager = order_manager
        self.weather_manager = weather_manager

    def attach_game(self, game):
        """Adjunta la referencia a Game para invocar movimientos/aceptaciones."""
        self.game = game
        self._game = game

    # -----------------------
    # Tick principal
    # -----------------------
    def tick(self, delta_time: float):
        """Llamado cada frame; gestiona throttling y decide acción según dificultad."""
        if not self.agent or not self._city or not self._order_mgr:
            return

        if self.action_cooldown > 0:
            self.action_cooldown -= delta_time
            return

        now = time.time()
        if now - self.last_decision_time < self.decision_interval:
            return
        self.last_decision_time = now

        try:
            if self.difficulty == "easy":
                self._easy_behavior()
            elif self.difficulty == "medium":
                self._medium_behavior()
            elif self.difficulty == "hard":
                self._hard_behavior()
            else:
                self._easy_behavior()
        except Exception as e:
            print(f"[AIManager] Error en tick: {e}")
            import traceback

            traceback.print_exc()

    # -----------------------
    # Helpers básicos
    # -----------------------
    @staticmethod
    def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def _is_adjacent_or_same(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) <= 1

    def _get_weather_speed(self) -> float:
        try:
            return float(self._weather_mgr.get_speed_multiplier())
        except Exception:
            return 1.0

    # -----------------------
    # Helpers de navegación
    # -----------------------
    def _nearest_adjacent_walkable(
        self, target: Tuple[int, int]
    ) -> Optional[Tuple[int, int]]:
        """
        Si target es caminable devuelve target, sino devuelve la casilla caminable
        adyacente más cercana al agente (4-direcciones). Si no hay candidatas,
        devuelve None.
        """
        tx, ty = int(target[0]), int(target[1])
        if self._city.is_walkable(tx, ty):
            return (tx, ty)

        candidates: List[Tuple[int, int]] = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = tx + dx, ty + dy
            if self._city.is_walkable(nx, ny):
                candidates.append((nx, ny))

        if not candidates:
            return None

        pos = self.agent.position
        candidates.sort(key=lambda p: self._manhattan(pos, p))
        return candidates[0]

    def _local_bfs_next_step(
        self, target: Tuple[int, int], max_search: int = 64
    ) -> Optional[Tuple[int, int]]:
        """
        Búsqueda BFS local limitada que intenta hallar un primer paso hacia target.
        Retorna la primera casilla del path (siguiente paso) o None.
        """
        from collections import deque as _deque

        start = tuple(self.agent.position)
        goal = tuple(target)
        if start == goal:
            return None

        q = _deque([start])
        came_from = {start: None}
        nodes_explored = 0

        while q and nodes_explored < max_search:
            cur = q.popleft()
            nodes_explored += 1
            for nx, ny in (
                (cur[0] + 1, cur[1]),
                (cur[0] - 1, cur[1]),
                (cur[0], cur[1] + 1),
                (cur[0], cur[1] - 1),
            ):
                if not self._city.is_walkable(nx, ny):
                    continue
                neighbor = (nx, ny)
                if neighbor in came_from:
                    continue
                came_from[neighbor] = cur
                if neighbor == goal:
                    path = []
                    node = neighbor
                    while node is not None and node != start:
                        path.append(node)
                        node = came_from.get(node)
                    path.reverse()
                    return path[0] if path else None
                q.append(neighbor)

        # si no alcanzamos goal, intentar cualquier adyacente del goal que esté en came_from
        for adj in (
            (goal[0] + 1, goal[1]),
            (goal[0] - 1, goal[1]),
            (goal[0], goal[1] + 1),
            (goal[0], goal[1] - 1),
        ):
            if not self._city.is_walkable(adj[0], adj[1]):
                continue
            if adj in came_from:
                path = []
                node = adj
                while node is not None and node != start:
                    path.append(node)
                    node = came_from.get(node)
                path.reverse()
                return path[0] if path else None

        return None

    def _try_move(self, dx: int, dy: int) -> bool:
        """
        Intenta realizar un movimiento (dx,dy). Evita moverse a posiciones presentes
        en _recent_positions si existe al menos una alternativa válida no reciente.
        Retorna True si el movimiento se ejecutó.
        """
        if not self._city:
            return False

        cur_x, cur_y = self.agent.position
        nx, ny = cur_x + dx, cur_y + dy

        if not self._city.is_walkable(nx, ny):
            return False

        new_pos = (nx, ny)

        # Evitar oscilación sólo para Medium/Hard (Easy no usa este filtro)
        if self.difficulty in ("medium", "hard"):
            if new_pos in self._recent_positions:
                alt_exists = False
                for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    axp, ayp = cur_x + ax, cur_y + ay
                    if (axp, ayp) == new_pos:
                        continue
                    if (
                        self._city.is_walkable(axp, ayp)
                        and (axp, ayp) not in self._recent_positions
                    ):
                        alt_exists = True
                        break
                if alt_exists:
                    return False

        self._execute_action("move", dx, dy)
        return True

    # ---- Interacciones CPU (pickup/delivery) sin necesidad de moverse ----
    def _cpu_try_interaction(self) -> Optional[str]:
        """
        Si el agente está adyacente a su objetivo actual (pickup/dropoff) intenta
        explícitamente realizar la interacción con OrderManager (sin depender
        de un movimiento para que Game lo detecte).
        Retorna "picked", "delivered" o None.
        """
        try:
            from State.OrderState import OrderState
        except Exception:
            OrderState = None

        if not self.agent or not getattr(self.agent, "inventory_ids", None):
            return None

        oid = self.agent.inventory_ids[0]
        order = self._order_mgr.all_orders.get(oid)
        if not order:
            return None

        pos = self.agent.position

        # Pickup desde adyacencia
        if OrderState and order.state == OrderState.ACCEPTED:
            if self._is_adjacent_or_same(pos, tuple(order.pickup)):
                if self._order_mgr.pickup_order(order.id):
                    return "picked"

        # Delivery desde adyacencia
        if OrderState and order.state == OrderState.PICKED_UP:
            if self._is_adjacent_or_same(pos, tuple(order.dropoff)):
                delivered = self._order_mgr.deliver_order(order.id)
                if delivered:
                    try:
                        if order.id in self.agent.inventory_ids:
                            self.agent.inventory_ids.remove(order.id)
                        
                        # Calculate reputation change based on delivery timing
                        delivery_time = delivered.delivery_time
                        delay_seconds = delivered.calculate_delay(delivery_time)
                        early = delivered.is_early_delivery(delivery_time)
                        
                        # Apply reputation change to AI
                        if hasattr(self.agent, 'register_delivery_outcome'):
                            rep_delta = self.agent.register_delivery_outcome(
                                delay_seconds=delay_seconds,
                                early=early,
                            )
                        
                        # Add earnings to AI agent with reputation multiplier
                        if hasattr(self.agent, 'total_earnings'):
                            pay_mult = self.agent.get_pay_multiplier() if hasattr(self.agent, 'get_pay_multiplier') else 1.0
                            payout = int(round(delivered.payout * pay_mult))
                            self.agent.total_earnings += payout
                    except Exception:
                        pass
                    return "delivered"

        return None

    # ======================
    # Movimiento Fácil (random)
    # ======================
    def _random_step(self):
        """Paso completamente aleatorio a un vecino caminable (o no moverse si no hay)."""
        x, y = self.agent.position
        neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        walkables = [
            (nx, ny) for (nx, ny) in neighbors if self._city.is_walkable(nx, ny)
        ]
        if not walkables:
            return
        nx, ny = random.choice(walkables)
        self._execute_action("move", nx - x, ny - y)

    def _random_neighbor_step_towards(
        self, target: Optional[Tuple[int, int]], toward_prob: float = 0.3
    ):
        """
        Paso aleatorio con leve sesgo hacia target:
        - Con prob toward_prob, elige al azar entre vecinos que reduzcan la distancia a target.
        - Con prob (1 - toward_prob), elige un vecino completamente aleatorio.
        Si target es None, se comporta como _random_step.
        """
        x, y = self.agent.position
        neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        walkables = [
            (nx, ny) for (nx, ny) in neighbors if self._city.is_walkable(nx, ny)
        ]
        if not walkables:
            return
        if target is None or random.random() >= toward_prob:
            nx, ny = random.choice(walkables)
            self._execute_action("move", nx - x, ny - y)
            return
        # preferir vecinos que acerquen al objetivo
        tx, ty = target
        current_d = self._manhattan((x, y), (tx, ty))
        better = [
            (nx, ny)
            for (nx, ny) in walkables
            if self._manhattan((nx, ny), (tx, ty)) < current_d
        ]
        if better:
            nx, ny = random.choice(better)
        else:
            nx, ny = random.choice(walkables)
        self._execute_action("move", nx - x, ny - y)

    # ======================
    # Movimiento Medium/Hard (dirigido con evasión)
    # ======================
    def _move_towards_target(self, target: Tuple[int, int]) -> bool:
        """
        Mueve hacia target con avoidance (Medium/Hard). Retorna True si se movió.
        """
        if not self._city:
            return False

        cur_x, cur_y = self.agent.position
        adj = self._nearest_adjacent_walkable(target)
        if adj is None:
            return False
        tx, ty = adj

        dx_pref = 0 if tx == cur_x else (1 if tx > cur_x else -1)
        dy_pref = 0 if ty == cur_y else (1 if ty > cur_y else -1)

        if abs(tx - cur_x) >= abs(ty - cur_y):
            primary = (dx_pref, 0)
            secondary = (0, dy_pref)
        else:
            primary = (0, dy_pref)
            secondary = (dx_pref, 0)

        for step in (primary, secondary):
            dx, dy = step
            if dx == 0 and dy == 0:
                continue
            nx, ny = cur_x + dx, cur_y + dy
            if self._city.is_walkable(nx, ny):
                if self._try_move(dx, dy):
                    return True
            else:
                # Casilla preferida bloqueada: probar adyacentes ordenados por cercanía al objetivo
                candidates: List[Tuple[Tuple[int, int], int]] = []
                for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    cx, cy = nx + ax, ny + ay
                    if not self._city.is_walkable(cx, cy):
                        continue
                    d_goal = self._manhattan((cx, cy), (tx, ty))
                    candidates.append(((cx, cy), d_goal))
                candidates.sort(key=lambda t: t[1])
                for (cx, cy), _ in candidates:
                    mdx, mdy = (cx - cur_x, cy - cur_y)
                    if abs(mdx) <= 1 and abs(mdy) <= 1 and (mdx != 0 or mdy != 0):
                        if self._try_move(mdx, mdy):
                            return True

        bfs_step = self._local_bfs_next_step((tx, ty), max_search=64)
        if bfs_step:
            nx, ny = bfs_step
            dx = nx - cur_x
            dy = ny - cur_y
            if abs(dx) <= 1 and abs(dy) <= 1 and (dx != 0 or dy != 0):
                if self._try_move(dx, dy):
                    return True

        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if self._try_move(dx, dy):
                return True

        return False

    # -----------------------
    # Ejecutar acciones (move / accept)
    # -----------------------
    def _execute_action(self, action_type: str, *args):
        """
        Ejecuta la acción usando Game y actualiza cooldown y el buffer de posiciones.
        action_type: "move" -> args = (dx, dy)
                     "accept_order" -> args = (order,)
        """
        if not hasattr(self, "game") or not self.game:
            return

        try:
            if action_type == "move":
                dx, dy = args[0], args[1]
                if hasattr(self.game, "_attempt_cpu_move"):
                    self.game._attempt_cpu_move(dx, dy)
                self.action_cooldown = self.min_action_interval
                # Track movement time for stamina recovery
                self.last_movement_time = time.time()
                try:
                    if self.agent and hasattr(self.agent, "position"):
                        self._recent_positions.append(tuple(self.agent.position))
                except Exception:
                    pass

            elif action_type == "accept_order":
                order = args[0]
                if hasattr(self.game, "_cpu_accept_order"):
                    self.game._cpu_accept_order(order)
                self.action_cooldown = self.min_action_interval * 2
                if hasattr(self, "agent") and self.agent:
                    self.agent.route = []

        except Exception as e:
            print(f"[AIManager] Error ejecutando acción {action_type}: {e}")

    def _move_towards_center(self):
        if not self._city:
            return
        cx = self._city.width // 2
        cy = self._city.height // 2
        self._move_towards_target((cx, cy))

    # -----------------------
    # Behaviors: easy / medium / hard
    # -----------------------
    def _easy_behavior(self):
        """
        Fácil: Random Choice + Random Walk realmente aleatorio.
        - Elige un pedido al azar (sólo descarta los imposibles sin casilla adyacente).
        - Se mueve aleatoriamente (>=70% de las veces) y sólo con leve sesgo (<=30%)
          hacia el objetivo cuando existe.
        - Acepta si está a <= 1 del pickup real e intenta pickup explícito tras aceptar.
        - Si tiene pedido y está adyacente a pickup/dropoff, intenta interacción explícita.
        """
        from State.OrderState import OrderState

        # 1) Si no tiene pedido
        if not self.agent.inventory_ids:
            available = self._order_mgr.get_available_orders_by_priority()
            valid_orders = []
            for o in available:
                if o.state != OrderState.AVAILABLE:
                    continue
                if self._nearest_adjacent_walkable(o.pickup) is None:
                    continue
                if self._nearest_adjacent_walkable(o.dropoff) is None:
                    continue
                valid_orders.append(o)

            # Con prob alta, simplemente caminar aleatorio aunque haya pedidos
            if not valid_orders or random.random() < 0.5:
                # 70% paso completamente aleatorio, 30% leve sesgo hacia un pickup si existe
                if valid_orders and random.random() < 0.3:
                    candidate = random.choice(valid_orders)
                    target = self._nearest_adjacent_walkable(candidate.pickup) or tuple(
                        candidate.pickup
                    )
                    self._random_neighbor_step_towards(target, toward_prob=0.3)
                else:
                    self._random_step()
                return

            # Elegir pedido al azar y actuar mínimamente hacia él
            order = random.choice(valid_orders)

            # Aceptar si ya está adyacente y luego intentar pickup explícito
            if self._is_adjacent_or_same(self.agent.position, tuple(order.pickup)):
                self._execute_action("accept_order", order)
                self._cpu_try_interaction()
                return

            # 70% random puro, 30% leve drift hacia pickup
            target = self._nearest_adjacent_walkable(order.pickup) or tuple(
                order.pickup
            )
            self._random_neighbor_step_towards(target, toward_prob=0.3)
            return

        # 2) Si ya tiene pedido
        else:
            oid = self.agent.inventory_ids[0]
            order = self._order_mgr.all_orders.get(oid)
            if not order:
                # sin datos: moverse aleatorio
                self._random_step()
                return

            # Intento explícito de interacción si procede (evita quedarnos quietos)
            if self._cpu_try_interaction() is not None:
                return

            # Movemento aleatorio con leve sesgo hacia objetivo actual
            raw_target = None
            if getattr(order, "state", None).name == "ACCEPTED":
                raw_target = order.pickup
            elif getattr(order, "state", None).name == "PICKED_UP":
                raw_target = order.dropoff

            if raw_target is None:
                self._random_step()
                return

            target = self._nearest_adjacent_walkable(raw_target) or tuple(raw_target)
            # 75% random puro, 25% leve drift hacia el objetivo
            self._random_neighbor_step_towards(target, toward_prob=0.25)
            return

    def _medium_behavior(self):
        """
        Media: heurística con lookahead corto (2 pasos).
        - score(order) = payout - (dist_pick + dist_drop) - deadline_pen - climate_pen + priority*10
        - lookahead: añade 0.5 * (mejor score desde el dropoff)
        - Movimiento con avoidance + BFS local.
        - Interacción explícita (pickup/delivery) al estar adyacente para no quedarse quieto.
        """
        from State.OrderState import OrderState

        # Sin pedido: evaluar con heurística + lookahead
        if not self.agent.inventory_ids:
            avail = self._order_mgr.get_available_orders_by_priority()
            candidates = []
            for o in avail:
                if o.state != OrderState.AVAILABLE:
                    continue
                pick_adj = self._nearest_adjacent_walkable(o.pickup)
                drop_adj = self._nearest_adjacent_walkable(o.dropoff)
                if not pick_adj or not drop_adj:
                    continue

                base_score = self._medium_order_value(o, from_pos=self.agent.position)
                candidates.append((base_score, o, pick_adj, drop_adj))

            if not candidates:
                self._move_towards_center()
                return

            candidates.sort(key=lambda t: t[0], reverse=True)
            top = candidates[:3]

            best_total = -1e18
            best_choice = top[0]
            for base_score, o, pick_adj, drop_adj in top:
                future = self._medium_future_from(drop_adj, exclude_id=o.id)
                total = base_score + 0.5 * future
                if total > best_total:
                    best_total = total
                    best_choice = (base_score, o, pick_adj, drop_adj)

            _, best_order, best_pick_adj, _ = best_choice

            # Aceptar si adyacente y luego intentar pickup explícito
            if self._is_adjacent_or_same(self.agent.position, tuple(best_order.pickup)):
                self._execute_action("accept_order", best_order)
                self._cpu_try_interaction()
                return

            moved = self._move_towards_target(best_pick_adj)
            if not moved:
                self._move_towards_center()
            return

        # Con pedido: interacción si adyacente o moverse hacia objetivo adyacente alcanzable
        else:
            # Intento explícito de interacción primero
            if self._cpu_try_interaction() is not None:
                return

            oid = self.agent.inventory_ids[0]
            order = self._order_mgr.all_orders.get(oid)
            if not order:
                return

            raw_target = (
                order.pickup
                if getattr(order, "state", None).name == "ACCEPTED"
                else (
                    order.dropoff
                    if getattr(order, "state", None).name == "PICKED_UP"
                    else None
                )
            )
            if not raw_target:
                return

            target = self._nearest_adjacent_walkable(raw_target)
            if not target:
                if oid in self.agent.inventory_ids:
                    self.agent.inventory_ids.remove(oid)
                return

            moved = self._move_towards_target(target)
            if not moved:
                bfs_next = self._local_bfs_next_step(target, max_search=64)
                if bfs_next:
                    dx = bfs_next[0] - self.agent.position[0]
                    dy = bfs_next[1] - self.agent.position[1]
                    if abs(dx) <= 1 and abs(dy) <= 1 and (dx != 0 or dy != 0):
                        self._execute_action("move", dx, dy)
                        return
                self._move_towards_center()

    def _medium_order_value(self, order, from_pos: Tuple[int, int]) -> float:
        """
        Heurística de costo total: pick + drop desde from_pos.
        Incorpora penalización por clima y por deadline y competencia básica del jugador.
        """
        pick_adj = self._nearest_adjacent_walkable(order.pickup)
        drop_adj = self._nearest_adjacent_walkable(order.dropoff)
        if not pick_adj or not drop_adj:
            return -1e9

        dist_pick = self._manhattan(from_pos, pick_adj)
        dist_drop = self._manhattan(pick_adj, drop_adj)
        base_cost = dist_pick + dist_drop

        speed = self._get_weather_speed()
        climate_pen = (1.0 / max(1e-6, speed) - 1.0) * base_cost * 0.5

        deadline_pen = 0.0
        try:
            if isinstance(order.deadline, datetime):
                time_left = order.deadline.timestamp() - time.time()
                if time_left < 300:
                    deadline_pen = 50
                elif time_left < 600:
                    deadline_pen = 20
        except Exception:
            pass

        player_bonus_pen = 0.0
        try:
            if self.game and hasattr(self.game, "player"):
                player_pos = tuple(self.game.player.position)
                if self._manhattan(player_pos, pick_adj) + 1 < dist_pick:
                    player_bonus_pen = 15.0
        except Exception:
            pass

        score = (
            float(order.payout)
            - (base_cost * 1.2)
            - climate_pen
            - deadline_pen
            - player_bonus_pen
            + order.priority * 10.0
        )
        return score

    def _medium_future_from(
        self, from_pos: Tuple[int, int], exclude_id: Optional[str]
    ) -> float:
        """
        Evalúa el mejor pedido futuro desde 'from_pos' (una sola orden) para el lookahead.
        """
        from State.OrderState import OrderState

        best = -1e18
        avail = self._order_mgr.get_available_orders_by_priority()
        for o in avail:
            if o.id == exclude_id:
                continue
            if o.state != OrderState.AVAILABLE:
                continue
            pick_adj = self._nearest_adjacent_walkable(o.pickup)
            drop_adj = self._nearest_adjacent_walkable(o.dropoff)
            if not pick_adj or not drop_adj:
                continue
            val = self._medium_order_value(o, from_pos=from_pos)
            if val > best:
                best = val
        return best if best > -1e17 else 0.0

    def _hard_behavior(self):
        """
        Difícil: planificación A* con coste total (pick+drop) y replan por clima.
        - Usa planner.path ponderado (GraphBuilder) para estimar costes reales.
        - Valor = payout - cost_pick - cost_drop + priority*8
        - Replan al cambiar significativamente el multiplicador de clima.
        - Lookahead opcional de 2 pedidos (descuento 0.6).
        - Interacción explícita al estar adyacente para no quedarse quieto.
        """
        from State.OrderState import OrderState

        # Replan si cambió el clima significativamente
        cur_speed = self._get_weather_speed()
        if self._last_weather_speed is not None:
            if abs(cur_speed - self._last_weather_speed) >= 0.15:
                if hasattr(self.agent, "route"):
                    self.agent.route = []
                self._hard_next_planned = None
        self._last_weather_speed = cur_speed

        # Sin pedido: evaluar por coste total
        if not self.agent.inventory_ids:
            avail = self._order_mgr.get_available_orders_by_priority()
            valid = []
            for o in avail:
                if o.state != OrderState.AVAILABLE:
                    continue
                pick_adj = self._nearest_adjacent_walkable(o.pickup)
                drop_adj = self._nearest_adjacent_walkable(o.dropoff)
                if not pick_adj or not drop_adj:
                    continue
                value, cost_pick, cost_drop = self._hard_order_value(
                    o, from_pos=self.agent.position
                )
                valid.append((value, o, pick_adj, drop_adj, cost_pick, cost_drop))

            if not valid:
                self._move_towards_center()
                return

            valid.sort(key=lambda t: t[0], reverse=True)
            top = valid[:4]

            # Lookahead opcional: un segundo pedido tras dejar el primero
            best_total = -1e18
            best_choice = top[0]
            next_planned = None

            for i in range(len(top)):
                v1, o1, p1, d1, _, _ = top[i]
                total_val = v1
                next_choice = None
                for j in range(len(top)):
                    if j == i:
                        continue
                    _, o2, p2, d2, _, _ = top[j]
                    v2_from_after, _, _ = self._hard_order_value(o2, from_pos=d1)
                    two_val = v1 + 0.6 * v2_from_after
                    if two_val > total_val:
                        total_val = two_val
                        next_choice = (o2, p2, d2)
                if total_val > best_total:
                    best_total = total_val
                    best_choice = top[i]
                    next_planned = next_choice

            best_value, best_order, best_pick_adj, best_drop_adj, _, _ = best_choice
            self._hard_next_planned = next_planned

            # Aceptar si adyacente y luego intentar pickup explícito
            if self._is_adjacent_or_same(self.agent.position, tuple(best_order.pickup)):
                self._execute_action("accept_order", best_order)
                self._cpu_try_interaction()
                return

            self._follow_path_to_target(best_pick_adj)
            return

        # Con pedido: interacción explícita si adyacente; sino, seguir ruta
        else:
            if self._cpu_try_interaction() is not None:
                return

            oid = self.agent.inventory_ids[0]
            order = self._order_mgr.all_orders.get(oid)
            if not order:
                return

            raw_target = (
                order.pickup
                if getattr(order, "state", None).name == "ACCEPTED"
                else (
                    order.dropoff
                    if getattr(order, "state", None).name == "PICKED_UP"
                    else None
                )
            )
            if not raw_target:
                return

            adj_target = self._nearest_adjacent_walkable(raw_target)
            if not adj_target:
                if oid in self.agent.inventory_ids:
                    self.agent.inventory_ids.remove(oid)
                if hasattr(self.agent, "route"):
                    self.agent.route = []
                return

            self._follow_path_to_target(adj_target)
            return

    def _hard_order_value(
        self, order, from_pos: Tuple[int, int]
    ) -> Tuple[float, float, float]:
        """
        Calcula valor = payout - cost_pick - cost_drop + priority*8 usando planner.path.
        Devuelve (valor, cost_pick, cost_drop).
        """
        pick_adj = self._nearest_adjacent_walkable(order.pickup)
        drop_adj = self._nearest_adjacent_walkable(order.dropoff)
        if not pick_adj or not drop_adj:
            return (-1e9, float("inf"), float("inf"))

        cost_pick = self._path_cost(from_pos, pick_adj)
        cost_drop = self._path_cost(pick_adj, drop_adj)
        total_cost = cost_pick + cost_drop
        value = float(order.payout) - total_cost + order.priority * 8.0
        return (value, cost_pick, cost_drop)

    def _path_cost(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """
        Suma de pesos de la ruta a->b usando planner.path y planner.weight.
        Si no hay planner o path, fallback a Manhattan.
        """
        if not self.planner or not hasattr(self.planner, "path"):
            return float(self._manhattan(a, b))
        try:
            path = self.planner.path(a, b)
            if not path:
                return float(self._manhattan(a, b))
            cost = 0.0
            prev = a
            for node in path:
                if hasattr(self.planner, "weight"):
                    try:
                        cost += float(self.planner.weight(prev, node))
                    except Exception:
                        cost += 1.0
                else:
                    cost += 1.0
                prev = node
            return cost
        except Exception:
            return float(self._manhattan(a, b))

    # -----------------------
    # Path following (Hard)
    # -----------------------
    def _follow_path_to_target(self, target: Tuple[int, int]):
        """
        Planifica usando planner.path y sigue paso a paso. Re‑plans si detecta bloqueo.
        target debe ser una casilla caminable (o adyacente al objetivo real).
        """
        if not self.planner or not hasattr(self.planner, "path"):
            self._move_towards_target(target)
            return

        if not getattr(self.agent, "route", None):
            try:
                path = self.planner.path(self.agent.position, target)
                if path and len(path) > 0:
                    valid = all(self._city.is_walkable(p[0], p[1]) for p in path)
                    if valid:
                        self.agent.route = list(path)
                    else:
                        self._move_towards_target(target)
                        return
                else:
                    self._move_towards_target(target)
                    return
            except Exception as e:
                print(f"[Hard AI] Error planificando ruta: {e}")
                self._move_towards_target(target)
                return

        if self.agent.route:
            next_pos = self.agent.route[0]
            dx = next_pos[0] - self.agent.position[0]
            dy = next_pos[1] - self.agent.position[1]
            if abs(dx) <= 1 and abs(dy) <= 1 and (dx != 0 or dy != 0):
                if self._city.is_walkable(next_pos[0], next_pos[1]):
                    self._execute_action("move", dx, dy)
                    try:
                        self.agent.route.pop(0)
                    except Exception:
                        self.agent.route = []
                    return
                else:
                    self.agent.route = []
                    return
            else:
                self.agent.route = []
                return

    # -----------------------
    # Reset / inicialización
    # -----------------------
    def reset(self):
        """Reinicia el agente IA (se llama al iniciar/resetear partida)."""
        self.agent = self._create_agent(self.difficulty)
        self.last_tick = time.time()
        self.last_decision_time = 0.0
        self.action_cooldown = 0.0
        self.last_movement_time = 0.0  # Initialize movement tracking for stamina recovery
        self._recent_positions = deque(maxlen=10)
        if self.agent and hasattr(self.agent, "position"):
            try:
                self._recent_positions.append(tuple(self.agent.position))
            except Exception:
                pass

        # ajustar tiempos por dificultad (por si cambió)
        if self.difficulty == "easy":
            self.decision_interval = 1.2
            self.min_action_interval = 0.5
        elif self.difficulty == "medium":
            self.decision_interval = 0.7
            self.min_action_interval = 0.35
        elif self.difficulty == "hard":
            self.decision_interval = 0.35
            self.min_action_interval = 0.15
        else:
            self.decision_interval = 1.2
            self.min_action_interval = 0.5

        # inicializa memoria de clima (Hard)
        self._last_weather_speed = self._get_weather_speed()
        self._hard_next_planned = None
