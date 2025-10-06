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
        # Punto 7: reputación inicia en 70
        self.reputation = 70  # 0-100

        # --- reputación/racha/tardanza ---
        self._on_time_streak = 0
        self._first_late_discount_used = False  # mitad de penalización si rep >=85

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
        stamina_extra_cost: float = 0.0,
    ) -> bool:
        if not self.can_move():
            return False

        weight_penalty = self.calculate_weight_penalty()
        base_cost = 0.5
        self.consume_stamina(
            base_consumption=base_cost,
            weight_penalty=weight_penalty,
            climate_penalty=stamina_extra_cost,
        )

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

    # ---------------- PUNTO 7: Reputación ----------------
    def apply_reputation_change(self, delta: int) -> int:
        """Aplica delta a reputación y clamp 0..100. Retorna el cambio efectivo."""
        prev = self.reputation
        self.reputation = int(max(0, min(100, self.reputation + delta)))
        return self.reputation - prev

    def get_pay_multiplier(self) -> float:
        """+5% si reputación ≥ 90 (PDF)."""
        return 1.05 if self.reputation >= 90 else 1.0

    def register_delivery_outcome(self, delay_seconds: float, early: bool) -> int:
        """
        Ajusta reputación según resultado:
        - Entrega temprana (≥20% antes): +5
        - A tiempo: +3
        - Tarde: ≤30s -2; 31–120s -5; >120s -10
        - Primera tardanza con rep≥85: mitad de penalización.
        Devuelve el delta aplicado.
        """
        delta = 0
        if early:
            delta = +5
            self._on_time_streak += 1
        elif delay_seconds <= 0:
            delta = +3
            self._on_time_streak += 1
        else:
            # Tarde → penalización según umbral
            if delay_seconds <= 30:
                penalty = -2
            elif delay_seconds <= 120:
                penalty = -5
            else:
                penalty = -10

            # 1ra tardanza con rep alta → mitad de penalización
            if self.reputation >= 85 and not self._first_late_discount_used:
                penalty = int(penalty / 2)  # redondea hacia 0
                self._first_late_discount_used = True

            delta = penalty
            self._on_time_streak = 0  # rompe racha

        # Bonus por racha de 3 sin penalización
        if self._on_time_streak and self._on_time_streak % 3 == 0:
            delta += self.apply_reputation_change(+2)  # aplica el +2 primero
            # ya sumó el +2, no duplicar: vamos a sumar el delta principal abajo
            # nota: el +2 ya fue aplicado, no necesitamos marcar racha aquí

        # Aplica delta principal
        self.apply_reputation_change(delta)
        return delta

    def __repr__(self):
        return f"Player(pos={self.position}, stamina={self.stamina:.1f}, weight={self.inventory_weight}, rep={self.reputation})"
