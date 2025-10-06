from enum import Enum
class GameState(Enum):
    """Estados posibles del juego"""

    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    ORDER_SELECTION = "order_selection"  # Nuevo estado para seleccionar pedidos
