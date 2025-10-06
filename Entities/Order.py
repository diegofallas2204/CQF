from datetime import datetime, timedelta
from typing import Optional, Tuple
from State.OrderState import OrderState
class Order:
    """Clase Order extendida de la Fase 1 (mismo código)"""

    def __init__(
        self,
        id: str,
        pickup: Tuple[int, int],
        dropoff: Tuple[int, int],
        payout: int,
        deadline: str,
        weight: int,
        priority: int = 0,
        release_time: int = 0,
    ):
        self.id = id
        self.pickup = pickup
        self.dropoff = dropoff
        self.payout = payout
        self.deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        self.weight = weight
        self.priority = priority
        self.release_time = release_time
        self.state = OrderState.AVAILABLE
        self.pickup_time: Optional[datetime] = None
        self.delivery_time: Optional[datetime] = None

    def is_available(self, current_time: float) -> bool:
        return current_time >= self.release_time and self.state == OrderState.AVAILABLE

    def is_expired(self, current_time: datetime) -> bool:
        return current_time > self.deadline and self.state not in [
            OrderState.DELIVERED,
            OrderState.CANCELLED,
        ]

    def calculate_delay(self, delivery_time: datetime) -> float:
        return (delivery_time - self.deadline).total_seconds()

    def is_early_delivery(self, delivery_time: datetime) -> bool:
        time_diff = (self.deadline - delivery_time).total_seconds()
        total_time = 3600
        return time_diff >= (total_time * 0.2)

    def __repr__(self):
        return f"Order({self.id}, priority={self.priority}, weight={self.weight}, payout={self.payout})"