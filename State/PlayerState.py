from enum import Enum

class PlayerState(Enum):
    """Estados posibles del jugador basados en resistencia"""

    NORMAL = "normal"
    TIRED = "tired"
    EXHAUSTED = "exhausted"
