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

    def _create_agent(self, diff: str):
        if diff == "easy":
            return RandomAI()
        if diff == "medium":
            return HeuristicAI()
        if diff == "hard":
            return GraphAI(planner=self.planner)
        return RandomAI()

    def register_game_refs(self, city: Any, order_manager: Any, weather_manager: Any):
        self.city = city
        self.order_manager = order_manager
        self.weather_manager = weather_manager

    def tick(self, delta_time: float):
        # actualizar vista del mundo y dejar que el agente decida
        try:
            orders = self.order_manager.all_orders if hasattr(self.order_manager, "all_orders") else {}
            self.agent.update_world(self.city, orders, self.weather_manager)
            # Decide accept
            choice = self.agent.decide_accept_order()
            if choice:
                try:
                    self.order_manager.accept_order(choice)
                    logger.debug(f"AI accepted order {choice}")
                except Exception as e:
                    logger.debug(f"AI failed to accept {choice}: {e}")
            # Move
            dx,dy = self.agent.decide_move()
            if (dx,dy) != (0,0):
                # aplicar movimiento usando la misma API que Player (Game debe exponer attempt_move_cpu)
                if hasattr(self, "game") and hasattr(self.game, "_attempt_move_cpu"):
                    self.game._attempt_move_cpu(self.agent, dx, dy)
            self.agent.on_tick(delta_time)
        except Exception as e:
            logger.exception("AIManager.tick error: %s", e)

    def attach_game(self, game):
        """Permite invocar métodos de game (ej. para mover CPU)"""
        self.game = game

    def reset(self):
        """Reinicia el agente IA para una nueva partida"""
        self.agent = self._create_agent(self.difficulty)
        self.last_tick = time.time()