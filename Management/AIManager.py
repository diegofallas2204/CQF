"""
Management/AIManager.py

Coordinador para agentes IA. Se encarga de:
 - Instanciar el agente según configuración
 - Proveer referencias (city, order_manager, weather_manager)
 - Ejecutar tick del agente en el loop del juego
 - Registrar logs/decisiones para análisis (playtests)
"""
from typing import Optional, Dict, Any
from Entities.AIPlayer import RandomAI, HeuristicAI, GraphAI
import time
import logging

logger = logging.getLogger("AIManager")

class AIManager:
    def __init__(self, difficulty: str = "easy", planner: Optional[Any] = None):
        self.difficulty = difficulty
        self.planner = planner
        self.agent = self._create_agent(difficulty)
        self.last_tick = time.time()
        
        # ===== Sistema de throttling (Fase 2) =====
        self.action_cooldown = 0.0  # tiempo restante de cooldown
        self.min_action_interval = 0.8  # mínimo 0.8s entre acciones (reducir CPU)
        self.last_decision_time = 0.0
        self.decision_interval = 1.5  # re-evaluar estrategia cada 1.5 segundos (reducir CPU)
        # ==========================================
        
        # Referencias al juego (se setean con register_game_refs y attach_game)
        self._city = None
        self._order_mgr = None
        self._weather_mgr = None
        self._game = None

    def _create_agent(self, diff: str):
        if diff == "easy":
            return RandomAI()
        if diff == "medium":
            return HeuristicAI()
        if diff == "hard":
            return GraphAI(planner=self.planner)
        return RandomAI()

    def register_game_refs(self, city: Any, order_manager: Any, weather_manager: Any):
        self._city = city
        self._order_mgr = order_manager
        self._weather_mgr = weather_manager
        # Mantener referencias antiguas para compatibilidad
        self.city = city
        self.order_manager = order_manager
        self.weather_manager = weather_manager

    def tick(self, delta_time: float):
        """
        Actualización principal con throttling.
        """
        if not self.agent or not self._city or not self._order_mgr:
            return
        
        # ===== Cooldown de acciones =====
        if self.action_cooldown > 0:
            self.action_cooldown -= delta_time
            return  # Skip este frame si estamos en cooldown
        
        # ===== Re-decisión periódica (no cada frame) =====
        current_time = time.time()
        if current_time - self.last_decision_time < self.decision_interval:
            return  # No re-decidir tan seguido
        
        self.last_decision_time = current_time
        
        # ===== Ejecutar lógica de IA =====
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

    def attach_game(self, game):
        """Permite invocar métodos de game (ej. para mover CPU)"""
        self.game = game

    def reset(self):
        """Reinicia el agente IA para una nueva partida"""
        self.agent = self._create_agent(self.difficulty)
        self.last_tick = time.time()
        self.last_decision_time = 0.0
        self.action_cooldown = 0.0

    def _execute_action(self, action_type: str, *args):
        """
        Ejecuta una acción del agente IA (mover, aceptar pedido, etc.)
        """
        if not hasattr(self, 'game') or not self.game:
            return
        
        try:
            if action_type == "move":
                dx, dy = args[0], args[1]
                # Usar el método interno de Game para mover el CPU
                if hasattr(self.game, '_attempt_cpu_move'):
                    self.game._attempt_cpu_move(dx, dy)
                # Aplicar cooldown después de moverse
                self.action_cooldown = self.min_action_interval
            
            elif action_type == "accept_order":
                order = args[0]
                # Llamar al método de game para aceptar el pedido
                if hasattr(self.game, '_cpu_accept_order'):
                    self.game._cpu_accept_order(order)
                # Aplicar cooldown después de aceptar
                self.action_cooldown = self.min_action_interval
        
        except Exception as e:
            print(f"[AIManager] Error ejecutando acción {action_type}: {e}")

    def _move_towards_center(self):
        """
        Mueve el agente hacia el centro del mapa.
        """
        if not self._city:
            return
        
        center_x = self._city.width // 2
        center_y = self._city.height // 2
        
        current_x, current_y = self.agent.position
        
        dx = 0
        dy = 0
        
        if center_x > current_x:
            dx = 1
        elif center_x < current_x:
            dx = -1
        
        if center_y > current_y:
            dy = 1
        elif center_y < current_y:
            dy = -1
        
        if dx != 0 or dy != 0:
            self._execute_action("move", dx, dy)

    def _easy_behavior(self):
        """
        Estrategia Easy (RandomAI): Movimiento aleatorio y selección aleatoria de pedidos.
        """
        from State.OrderState import OrderState
        
        # 1. Si no tiene pedido, intentar aceptar uno aleatorio
        if not self.agent.inventory_ids:
            available = self._order_mgr.get_available_orders_by_priority()
            if available:
                # Elegir uno al azar
                import random
                order = random.choice(available)
                if order.state == OrderState.AVAILABLE:
                    print(f"[Easy AI] Aceptando pedido aleatorio {order.id}")
                    self._execute_action("accept_order", order)
                    return
        
        # 2. Movimiento aleatorio
        import random
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        
        if dx != 0 or dy != 0:
            self._execute_action("move", dx, dy)

    def _medium_behavior(self):
        """
        Estrategia Medium (HeuristicAI): Usa heurísticas para priorizar pedidos.
        """
        from State.OrderState import OrderState
        import time
        from datetime import datetime
        
        # 1. Si no tiene pedido, evaluar y aceptar el mejor
        if not self.agent.inventory_ids:
            available = self._order_mgr.get_available_orders_by_priority()
            if not available:
                self._move_towards_center()
                return
            
            # Calcular score para cada pedido
            best_order = None
            best_score = -float('inf')
            
            current_time = time.time()
            
            for order in available:
                if order.state != OrderState.AVAILABLE:
                    continue
                
                try:
                    # Calcular distancia Manhattan al pickup
                    dist = self._city.calculate_manhattan_distance(
                        self.agent.position, order.pickup
                    )
                    
                    # Score base: pago / (distancia + 1) + prioridad * 10
                    score = (order.payout / (dist + 1)) + (order.priority * 10)
                    
                    # Considerar deadline (si existe)
                    if hasattr(order, 'deadline') and order.deadline:
                        try:
                            # Convertir deadline a timestamp
                            if isinstance(order.deadline, datetime):
                                deadline_ts = order.deadline.timestamp()
                            elif isinstance(order.deadline, (int, float)):
                                deadline_ts = float(order.deadline)
                            else:
                                deadline_ts = None
                            
                            if deadline_ts:
                                time_left = deadline_ts - current_time
                                # Penalizar pedidos con poco tiempo (urgentes)
                                if time_left < 300:  # Menos de 5 min
                                    score -= 50
                                elif time_left < 600:  # Menos de 10 min
                                    score -= 20
                        
                        except Exception as e:
                            print(f"[Medium AI] Error procesando deadline: {e}")
                            pass
                    
                    if score > best_score:
                        best_score = score
                        best_order = order
                
                except Exception as e:
                    print(f"[Medium AI] Error evaluando pedido {order.id}: {e}")
                    continue
            
            if best_order:
                print(f"[Medium AI] Seleccionado pedido {best_order.id} con score {best_score:.1f}")
                self._execute_action("accept_order", best_order)
                return
        
        # 2. Si tiene pedido, moverse directamente hacia él
        if self.agent.inventory_ids:
            oid = self.agent.inventory_ids[0]
            order = self._order_mgr.all_orders.get(oid)
            
            if not order:
                return
            
            # Determinar target
            if order.state == OrderState.ACCEPTED:
                target = order.pickup
            elif order.state == OrderState.PICKED_UP:
                target = order.dropoff
            else:
                return
            
            # Movimiento directo (sin aleatoriedad)
            # Priorizar movimiento en X, luego Y (no diagonal)
            dx = 0
            dy = 0
            
            if target[0] > self.agent.position[0]:
                dx = 1
            elif target[0] < self.agent.position[0]:
                dx = -1
            elif target[1] > self.agent.position[1]:
                # Solo mover en Y si ya estamos alineados en X
                dy = 1
            elif target[1] < self.agent.position[1]:
                dy = -1
            
            if dx != 0 or dy != 0:
                self._execute_action("move", dx, dy)
        
        # 3. Si está idle (no debería pasar), moverse al centro
        else:
            self._move_towards_center()

    def _hard_behavior(self):
        """
        Estrategia Hard (GraphAI): Usa A* pathfinding para planificación óptima.
        """
        from State.OrderState import OrderState
        
        # 1. Si no tiene pedido, evaluar y aceptar el mejor usando el planner
        if not self.agent.inventory_ids:
            available = self._order_mgr.get_available_orders_by_priority()
            if not available:
                self._move_towards_center()
                return
            
            best_order = None
            best_value = -float('inf')
            
            for order in available:
                if order.state != OrderState.AVAILABLE:
                    continue
                
                try:
                    # Usar el planner para estimar el costo real
                    if self.planner:
                        cost = self.planner.estimate_cost(self.agent.position, order.pickup)
                    else:
                        # Fallback a distancia Manhattan
                        cost = self._city.calculate_manhattan_distance(
                            self.agent.position, order.pickup
                        )
                    
                    value = order.payout - cost
                    
                    if value > best_value:
                        best_value = value
                        best_order = order
                
                except Exception as e:
                    print(f"[Hard AI] Error evaluando pedido {order.id}: {e}")
                    continue
            
            if best_order and best_value > 0:
                print(f"[Hard AI] Seleccionado pedido {best_order.id} con valor {best_value:.1f}")
                self._execute_action("accept_order", best_order)
                return
        
        # 2. Si tiene pedido, usar pathfinding para moverse
        if self.agent.inventory_ids:
            oid = self.agent.inventory_ids[0]
            order = self._order_mgr.all_orders.get(oid)
            
            if not order:
                return
            
            # Determinar target
            if order.state == OrderState.ACCEPTED:
                target = order.pickup
            elif order.state == OrderState.PICKED_UP:
                target = order.dropoff
            else:
                return
            
            # Intentar usar el pathfinding
            if self.planner and hasattr(self.agent, 'route'):
                # Si no hay ruta o la ruta está vacía, planificar una nueva
                if not self.agent.route:
                    try:
                        path = self.planner.path(self.agent.position, target)
                        if path:
                            self.agent.route = path
                    except Exception as e:
                        print(f"[Hard AI] Error planificando ruta: {e}")
                
                # Seguir la ruta
                if self.agent.route:
                    next_pos = self.agent.route[0]
                    dx = next_pos[0] - self.agent.position[0]
                    dy = next_pos[1] - self.agent.position[1]
                    
                    if dx != 0 or dy != 0:
                        self._execute_action("move", dx, dy)
                        # Remover el punto de la ruta después de moverse
                        self.agent.route.pop(0)
                    return
            
            # Fallback: movimiento directo (como medium)
            # Priorizar movimiento en X, luego Y (no diagonal)
            dx = 0
            dy = 0
            
            if target[0] > self.agent.position[0]:
                dx = 1
            elif target[0] < self.agent.position[0]:
                dx = -1
            elif target[1] > self.agent.position[1]:
                # Solo mover en Y si ya estamos alineados en X
                dy = 1
            elif target[1] < self.agent.position[1]:
                dy = -1
            
            if dx != 0 or dy != 0:
                self._execute_action("move", dx, dy)
        
        # 3. Si está idle, moverse al centro
        else:
            self._move_towards_center()
