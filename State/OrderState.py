from enum import Enum
class OrderState(Enum):
    """Estados posibles de un pedido"""

    AVAILABLE = "available"
    ACCEPTED = "accepted"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        return self.value
