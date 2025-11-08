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

    def attach_game(self, game):
        """Permite invocar métodos de game (ej. para mover CPU)"""
        self._game = game
        # Mantener referencia antigua para compatibilidad
        self.game = game

    def reset(self):
        """Reinicia el agente IA para una nueva partida"""
        self.agent = self._create_agent(self.difficulty)
        self.last_tick = time.time()
        # Reset throttling state
        self.action_cooldown = 0.0
        self.last_decision_time = 0.0
    
    def _execute_action(self, action_type: str, *args, **kwargs):
        """
        Wrapper para ejecutar acciones CON cooldown.
        """
        try:
            if action_type == "move":
                dx, dy = args[0], args[1]
                if self._game and hasattr(self._game, "_attempt_move_cpu"):
                    self._game._attempt_move_cpu(self.agent, dx, dy)
                    self.action_cooldown = self.min_action_interval  # reset cooldown
            
            elif action_type == "accept_order":
                order = args[0]
                if self._attempt_accept_order(order):
                    self.action_cooldown = self.min_action_interval * 2  # más cooldown al aceptar
            
            elif action_type == "pickup":
                order = args[0]
                if self._attempt_pickup(order):
                    self.action_cooldown = self.min_action_interval * 1.5
            
            elif action_type == "deliver":
                order = args[0]
                if self._attempt_deliver(order):
                    self.action_cooldown = self.min_action_interval * 2
        
        except Exception as e:
            print(f"[AIManager] Error ejecutando {action_type}: {e}")
    
    def _attempt_accept_order(self, order) -> bool:
        """
        Intenta aceptar un pedido con validación completa.
        Retorna True si se aceptó exitosamente.
        """
        try:
            from State.OrderState import OrderState
            
            # Validación 1: ¿Ya tiene un pedido activo?
            if self.agent.inventory_ids:
                return False
            
            # Validación 2: ¿El pedido está realmente disponible?
            if order.state != OrderState.AVAILABLE:
                return False
            
            # Validación 3: ¿Ya hay alguien más con este pedido?
            for o in self._order_mgr.all_orders.values():
                if o.state in [OrderState.ACCEPTED, OrderState.PICKED_UP]:
                    return False  # Ya hay un pedido activo en el sistema
            
            # Intentar aceptar desde OrderManager
            accepted_order = self._order_mgr.accept_order(order.id)
            
            if accepted_order:
                # OrderManager devuelve el pedido pero no cambia el estado automáticamente
                # El estado se cambia al agregarlo al inventario
                accepted_order.state = OrderState.ACCEPTED
                # Agregar al inventario del agente
                self.agent.inventory_ids.append(accepted_order.id)
                print(f"[CPU-{self.agent.name}] ✓ Pedido {accepted_order.id} aceptado")
                return True
            
            return False
            
        except Exception as e:
            print(f"[CPU] Error aceptando pedido: {e}")
            return False
    
    def _attempt_pickup(self, order) -> bool:
        """
        Intenta recoger un pedido.
        Retorna True si se recogió exitosamente.
        """
        try:
            from State.OrderState import OrderState
            
            if order.state == OrderState.ACCEPTED:
                # Verificar que el agente está en el punto de pickup
                if self.agent.position == order.pickup:
                    if self._order_mgr.pickup_order(order.id):
                        print(f"[CPU-{self.agent.name}] Pedido {order.id} recogido")
                        return True
            return False
        except Exception as e:
            print(f"[CPU] Error recogiendo pedido: {e}")
            return False
    
    def _attempt_deliver(self, order) -> bool:
        """
        Intenta entregar un pedido.
        Retorna True si se entregó exitosamente.
        """
        try:
            from State.OrderState import OrderState
            
            if order.state == OrderState.PICKED_UP:
                # Verificar que el agente está en el punto de entrega
                if self.agent.position == order.dropoff:
                    if self._order_mgr.deliver_order(order.id):
                        # Remover del inventario del agente
                        if order.id in self.agent.inventory_ids:
                            self.agent.inventory_ids.remove(order.id)
                        print(f"[CPU-{self.agent.name}] Pedido {order.id} entregado")
                        return True
            return False
        except Exception as e:
            print(f"[CPU] Error entregando pedido: {e}")
            return False
    
    def _easy_behavior(self):
        """
        RandomAI: Movimiento aleatorio y aceptación oportunista.
        CON THROTTLING.
        """
        import random
        from State.OrderState import OrderState
        
        # Si no tiene pedido, intentar aceptar UNO
        if not self.agent.inventory_ids:
            available = self._order_mgr.get_available_orders_by_priority()
            if available:
                # Tomar el primero disponible
                order = available[0]
                
                # VALIDAR que realmente está disponible
                if order.state == OrderState.AVAILABLE:
                    self._execute_action("accept_order", order)
                    return  # No hacer nada más este tick
        
        # Si tiene pedido, moverse hacia pickup o dropoff
        if self.agent.inventory_ids:
            oid = self.agent.inventory_ids[0]
            order = self._order_mgr.all_orders.get(oid)
            
            if not order:
                return
            
            target = order.pickup if order.state == OrderState.ACCEPTED else order.dropoff
            
            # Movimiento simple hacia el target
            dx = 1 if target[0] > self.agent.position[0] else (-1 if target[0] < self.agent.position[0] else 0)
            dy = 1 if target[1] > self.agent.position[1] else (-1 if target[1] < self.agent.position[1] else 0)
            
            if dx != 0 or dy != 0:
                # Aleatorizar un poco (25% chance)
                if random.random() < 0.25:
                    dx, dy = random.choice([(0,1), (0,-1), (1,0), (-1,0)])
                
                self._execute_action("move", dx, dy)
        
        else:
            # Movimiento aleatorio
            dx, dy = random.choice([(0,1), (0,-1), (1,0), (-1,0), (0,0)])
            if dx != 0 or dy != 0:
                self._execute_action("move", dx, dy)
    
    def _medium_behavior(self):
        """
        HeuristicAI: Comportamiento medio con evaluación heurística.
        """
        from State.OrderState import OrderState
        
        # Actualizar vista del mundo para el agente
        orders = self._order_mgr.all_orders if hasattr(self._order_mgr, "all_orders") else {}
        self.agent.update_world(self._city, orders, self._weather_mgr)
        
        # Si no tiene pedido, intentar aceptar uno
        if not self.agent.inventory_ids:
            choice = self.agent.decide_accept_order()
            if choice:
                order = self._order_mgr.all_orders.get(choice)
                if order and order.state == OrderState.AVAILABLE:
                    self._execute_action("accept_order", order)
                    return
        
        # Si tiene pedido, moverse hacia el objetivo
        if self.agent.inventory_ids:
            oid = self.agent.inventory_ids[0]
            self.agent.current_target_order_id = oid
            dx, dy = self.agent.decide_move()
            if (dx, dy) != (0, 0):
                self._execute_action("move", dx, dy)
    
    def _hard_behavior(self):
        """
        GraphAI: Comportamiento difícil con planificación de rutas.
        """
        from State.OrderState import OrderState
        
        # Actualizar vista del mundo para el agente
        orders = self._order_mgr.all_orders if hasattr(self._order_mgr, "all_orders") else {}
        self.agent.update_world(self._city, orders, self._weather_mgr)
        
        # Si no tiene pedido, intentar aceptar uno
        if not self.agent.inventory_ids:
            choice = self.agent.decide_accept_order()
            if choice:
                order = self._order_mgr.all_orders.get(choice)
                if order and order.state == OrderState.AVAILABLE:
                    self._execute_action("accept_order", order)
                    # Planear ruta al pickup
                    if hasattr(self.agent, 'plan_route_to'):
                        self.agent.plan_route_to(order.pickup)
                    return
        
        # Si tiene pedido, seguir la ruta planeada
        if self.agent.inventory_ids:
            oid = self.agent.inventory_ids[0]
            order = self._order_mgr.all_orders.get(oid)
            if order:
                # Si no hay ruta, planearla
                if not self.agent.route:
                    target = order.pickup if order.state == OrderState.ACCEPTED else order.dropoff
                    if hasattr(self.agent, 'plan_route_to'):
                        self.agent.plan_route_to(target)
                
                # Ejecutar siguiente paso de la ruta
                dx, dy = self.agent.decide_move()
                if (dx, dy) != (0, 0):
                    self._execute_action("move", dx, dy)