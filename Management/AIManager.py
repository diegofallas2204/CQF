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
        self.game = game

    def reset(self):
        """Reinicia el agente IA para una nueva partida"""
        self.agent = self._create_agent(self.difficulty)
        self.last_tick = time.time()
