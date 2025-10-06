# Entities/Player.py
from typing import Tuple
from State.PlayerState import PlayerState
from Entities.Order import Order

class Player:
    """Jugador con resistencia, peso, reputación y velocidad afectada por clima."""

    def __init__(
        self,
        start_position: Tuple[int, int] = (0, 0),
        max_inventory_weight: float = 10.0,
    ):
        self.position = start_position
        self.stamina = 100.0
        self.max_stamina = 100.0
        self.stamina_recovery_threshold = 30.0
        self.base_speed = 3.0
        self.current_speed = 3.0
        self.inventory_weight = 0.0
        self.max_inventory_weight = max_inventory_weight
        self.state = PlayerState.NORMAL
        self.total_earnings = 0
        self.reputation = 100  # 0-100

    def can_move(self) -> bool:
        return self.stamina > 0 or self.state != PlayerState.EXHAUSTED

    def can_accept_order(self, order: Order) -> bool:
        return (self.inventory_weight + order.weight) <= self.max_inventory_weight

    def consume_stamina(
        self,
        base_consumption: float = 0.5,
        weight_penalty: float = 0.0,
        climate_penalty: float = 0.0,
    ):
        total = base_consumption + weight_penalty + climate_penalty
        self.stamina = max(0, self.stamina - total)
        self._update_state()

    def recover_stamina(self, recovery_rate: float = 2.0, delta_time: float = 1.0):
        if self.stamina < self.max_stamina:
            self.stamina = min(
                self.max_stamina, self.stamina + (recovery_rate * delta_time)
            )
            self._update_state()

    def _update_state(self):
        if self.stamina <= 0:
            self.state = PlayerState.EXHAUSTED
        elif self.stamina <= 30:
            self.state = PlayerState.TIRED
        else:
            self.state = PlayerState.NORMAL

    def calculate_weight_penalty(self) -> float:
        if self.inventory_weight > 3:
            return 0.2 * (self.inventory_weight - 3)
        return 0.0

    def get_stamina_multiplier(self) -> float:
        if self.state == PlayerState.EXHAUSTED:
            return 0.0
        elif self.state == PlayerState.TIRED:
            return 0.8
        else:
            return 1.0

    def move_to(
        self,
        new_position: Tuple[int, int],
        climate_multiplier: float = 1.0,
        surface_weight: float = 1.0,
        reputation_multiplier: float = 1.0,
        stamina_extra_cost: float = 0.0,   # <— NUEVO: costo extra por clima
    ) -> bool:
        """
        - stamina_extra_cost: se suma al costo base por celda (fatiga extra por clima)
        - climate_multiplier: multiplica la velocidad final (no la stamina)
        """
        if not self.can_move():
            return False

        weight_penalty = self.calculate_weight_penalty()

        # Coste base por paso (ajústalo a gusto)
        base_cost = 0.5
        self.consume_stamina(
            base_consumption=base_cost,
            weight_penalty=weight_penalty,
            climate_penalty=stamina_extra_cost,
        )

        # Posición y velocidad
        self.position = new_position

        weight_multiplier = max(0.8, 1 - 0.03 * self.inventory_weight)
        stamina_multiplier = self.get_stamina_multiplier()

        self.current_speed = (
            self.base_speed
            * climate_multiplier
            * weight_multiplier
            * reputation_multiplier
            * stamina_multiplier
            * surface_weight
        )

        return True

    def add_earnings(self, amount: int):
        self.total_earnings += amount

    def __repr__(self):
        return f"Player(pos={self.position}, stamina={self.stamina:.1f}, weight={self.inventory_weight}, rep={self.reputation})"
