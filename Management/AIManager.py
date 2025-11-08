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
        self.min_action_interval = 0.5  # mínimo 0.5s entre acciones (ajustable)
        self.last_decision_time = 0.0
        self.decision_interval = 1.0  # re-evaluar estrategia cada 1 segundo
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

    def _easy_behavior(self):
        """
        Estrategia Easy (RandomAI): Movimiento aleatorio y aceptación oportunista.
        - Si no tiene pedido → acepta el primero disponible
        - Si tiene pedido → se mueve hacia pickup/dropoff con algo de aleatoriedad
        - Movimiento aleatorio cuando está idle
        """
        import random
        from State.OrderState import OrderState
        
        # 1. Si no tiene pedido, intentar aceptar uno
        if not self.agent.inventory_ids:
            available = self._order_mgr.get_available_orders_by_priority()
            if available:
                order = available[0]
                
                # VALIDAR que realmente está disponible
                if order.state == OrderState.AVAILABLE:
                    self._execute_action("accept_order", order)
                    return  # No hacer más este tick
        
        # 2. Si tiene pedido, moverse hacia él
        if self.agent.inventory_ids:
            oid = self.agent.inventory_ids[0]
            order = self._order_mgr.all_orders.get(oid)
            
            if not order:
                return
            
            # Determinar target según estado del pedido
            if order.state == OrderState.ACCEPTED:
                target = order.pickup
            elif order.state == OrderState.PICKED_UP:
                target = order.dropoff
            else:
                return
            
            # Calcular dirección hacia el target
            dx = 0
            dy = 0
            
            if target[0] > self.agent.position[0]:
                dx = 1
            elif target[0] < self.agent.position[0]:
                dx = -1
            
            if target[1] > self.agent.position[1]:
                dy = 1
            elif target[1] < self.agent.position[1]:
                dy = -1
            
            # Aleatorizar un poco (25% chance de movimiento random)
            if random.random() < 0.25:
                dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            
            if dx != 0 or dy != 0:
                self._execute_action("move", dx, dy)
        
        # 3. Movimiento aleatorio si está idle
        else:
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
            if dx != 0 or dy != 0:
                self._execute_action("move", dx, dy)

    def _medium_behavior(self):
        """
        Estrategia Medium (HeuristicAI): Usa heurísticas para priorizar pedidos.
        - Calcula score basado en: distancia, pago, prioridad, deadline
        - Selecciona el mejor pedido según score
        - Movimiento directo hacia objetivos
        """
        from State.OrderState import OrderState
        import time
        
        # 1. Si no tiene pedido, evaluar y aceptar el mejor
        if not self.agent.inventory_ids:
            available = self._order_mgr.get_available_orders_by_priority()
            if not available:
                # Movimiento aleatorio hacia el centro del mapa
                self._move_towards_center()
                return
            
            # Calcular score para cada pedido
            best_order = None
            best_score = -float('inf')
            
            for order in available:
                if order.state != OrderState.AVAILABLE:
                    continue
                
                # Calcular distancia Manhattan al pickup
                dist = self._city.calculate_manhattan_distance(
                    self.agent.position, order.pickup
                )
                
                # Score = pago / (distancia + 1) + prioridad * 10 - urgencia_deadline
                current_time = time.time()
                deadline_urgency = 0
                if hasattr(order, 'deadline'):
                    try:
                        deadline_timestamp = order.deadline.timestamp() if hasattr(order.deadline, 'timestamp') else float(order.deadline)
                        time_left = deadline_timestamp - current_time
                        deadline_urgency = max(0, 100 - time_left / 10)  # Más urgente = mayor penalty
                    except:
                        pass
                
                score = (order.payout / (dist + 1)) + (order.priority * 10) - deadline_urgency
                
                if score > best_score:
                    best_score = score
                    best_order = order
            
            if best_order:
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
            dx = 0
            dy = 0
            
            if target[0] > self.agent.position[0]:
                dx = 1
            elif target[0] < self.agent.position[0]:
                dx = -1
            
            if target[1] > self.agent.position[1]:
                dy = 1
            elif target[1] < self.agent.position[1]:
                dy = -1
            
            if dx != 0 or dy != 0:
                self._execute_action("move", dx, dy)

    def _hard_behavior(self):
        """
        Estrategia Hard (GraphAI): Usa planificación con grafos (A*).
        - Construye grafo del mapa considerando clima
        - Planifica ruta óptima usando A*
        - Sigue el camino calculado
        """
        from State.OrderState import OrderState
        
        # 1. Si no tiene pedido, seleccionar el mejor usando planificación
        if not self.agent.inventory_ids:
            available = self._order_mgr.get_available_orders_by_priority()
            if not available:
                self._move_towards_center()
                return
            
            # Si tenemos planner, usarlo para encontrar el mejor pedido
            best_order = None
            best_cost = float('inf')
            
            for order in available:
                if order.state != OrderState.AVAILABLE:
                    continue
                
                # Calcular costo de ruta con A*
                if self.planner:
                    try:
                        path = self.planner.find_path(
                            self.agent.position,
                            order.pickup,
                            self._weather_mgr
                        )
                        
                        if path:
                            cost = len(path) - order.priority * 5 + order.payout / 10
                            if cost < best_cost:
                                best_cost = cost
                                best_order = order
                    except:
                        pass
            
            if best_order:
                self._execute_action("accept_order", best_order)
                return
        
        # 2. Si tiene pedido, usar A* para moverse
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
            
            # Usar A* para calcular siguiente paso
            if self.planner:
                try:
                    path = self.planner.find_path(
                        self.agent.position,
                        target,
                        self._weather_mgr
                    )
                    
                    if path and len(path) > 1:
                        next_pos = path[1]  # path[0] es la posición actual
                        dx = next_pos[0] - self.agent.position[0]
                        dy = next_pos[1] - self.agent.position[1]
                        
                        if dx != 0 or dy != 0:
                            self._execute_action("move", dx, dy)
                            return
                except Exception as e:
                    print(f"[Hard AI] Error en pathfinding: {e}")
            
            # Fallback: movimiento directo
            dx = 0
            dy = 0
            
            if target[0] > self.agent.position[0]:
                dx = 1
            elif target[0] < self.agent.position[0]:
                dx = -1
            
            if target[1] > self.agent.position[1]:
                dy = 1
            elif target[1] < self.agent.position[1]:
                dy = -1
            
            if dx != 0 or dy != 0:
                self._execute_action("move", dx, dy)

    def _move_towards_center(self):
        """Helper: mueve el agente hacia el centro del mapa"""
        if not self._city:
            return
        
        center_x = self._city.width // 2
        center_y = self._city.height // 2
        
        dx = 0
        dy = 0
        
        if self.agent.position[0] < center_x:
            dx = 1
        elif self.agent.position[0] > center_x:
            dx = -1
        
        if self.agent.position[1] < center_y:
            dy = 1
        elif self.agent.position[1] > center_y:
            dy = -1
        
        if dx != 0 or dy != 0:
            self._execute_action("move", dx, dy)

    def _execute_action(self, action_type: str, *args, **kwargs):
        """
        Wrapper para ejecutar acciones CON cooldown.
        """
        from State.OrderState import OrderState
        
        try:
            if action_type == "move":
                dx, dy = args[0], args[1]
                if self._game and hasattr(self._game, "_attempt_move_cpu"):
                    self._game._attempt_move_cpu(self.agent, dx, dy)
                    self.action_cooldown = self.min_action_interval
            
            elif action_type == "accept_order":
                order = args[0]
                if self._attempt_accept_order(order):
                    self.action_cooldown = self.min_action_interval * 2
            
            elif action_type == "pickup":
                order = args[0]
                # Implementar lógica de pickup si es necesario
                self.action_cooldown = self.min_action_interval * 1.5
            
            elif action_type == "deliver":
                order = args[0]
                # Implementar lógica de entrega si es necesario
                self.action_cooldown = self.min_action_interval * 2
        
        except Exception as e:
            print(f"[AIManager] Error ejecutando {action_type}: {e}")

    def _attempt_accept_order(self, order) -> bool:
        """
        Intenta aceptar un pedido validando que está disponible y el agente puede aceptarlo.
        Retorna True si se aceptó exitosamente, False en caso contrario.
        """
        from State.OrderState import OrderState
        
        # Validar que el pedido existe y está disponible
        if not order or order.state != OrderState.AVAILABLE:
            return False
        
        # Validar que el agente no tiene ya un pedido (límite de 1)
        if self.agent.inventory_ids:
            return False
        
        # Aceptar el pedido
        try:
            order.state = OrderState.ACCEPTED
            self.agent.inventory_ids.append(order.id)
            return True
        except Exception as e:
            print(f"[AIManager] Error aceptando pedido {order.id}: {e}")
            return False

    def attach_game(self, game):
        """Permite invocar métodos de game (ej. para mover CPU)"""
        self.game = game
        self._game = game

    def reset(self):
        """Reinicia el agente IA para una nueva partida"""
        self.agent = self._create_agent(self.difficulty)
        self.last_tick = time.time()
