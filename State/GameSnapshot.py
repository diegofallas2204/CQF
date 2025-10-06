from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class GameSnapshot:
    """
    Representa un snapshot del estado del juego para el sistema de deshacer.
    Usar dataclass facilita la serialización y comparación.
    """

    player_position: Tuple[int, int]
    player_stamina: float
    player_inventory_weight: float
    player_total_earnings: int
    current_time: float
    order_states: Dict[str, str]  # ID del pedido -> estado
    inventory_order_ids: List[str]  # IDs de pedidos en inventario
    timestamp: float