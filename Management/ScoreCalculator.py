from typing import Dict
class ScoreCalculator:
    """
    Calculadora de puntajes del juego.
    Implementa la fórmula especificada en el documento.
    """

    @staticmethod
    def calculate_base_score(
        total_earnings: int, reputation_multiplier: float = 1.0
    ) -> float:
        """Calcula puntaje base"""
        return total_earnings * reputation_multiplier

    @staticmethod
    def calculate_time_bonus(
        completion_time: float, total_game_time: float, early_threshold: float = 0.2
    ) -> float:
        """
        Calcula bonus por terminar temprano.
        early_threshold: porcentaje del tiempo restante para considerar 'temprano'
        """
        time_remaining = total_game_time - completion_time
        early_time = total_game_time * early_threshold

        if time_remaining >= early_time:
            # Bonus proporcional al tiempo restante
            bonus_factor = time_remaining / total_game_time
            return bonus_factor * 500  # Bonus base de 500 puntos

        return 0.0

    @staticmethod
    def calculate_penalties(
        cancelled_orders: int, expired_orders: int, late_deliveries: int
    ) -> float:
        """Calcula penalizaciones"""
        penalty = 0.0
        penalty += cancelled_orders * 50  # -50 por cancelación
        penalty += expired_orders * 100  # -100 por expiración
        penalty += late_deliveries * 25  # -25 por entrega tardía

        return penalty

    @staticmethod
    def calculate_final_score(
        total_earnings: int,
        reputation_multiplier: float,
        completion_time: float,
        total_game_time: float,
        cancelled_orders: int = 0,
        expired_orders: int = 0,
        late_deliveries: int = 0,
    ) -> Dict[str, float]:
        """
        Calcula puntaje final completo.
        Retorna diccionario con desglose de puntuación.
        """
        base_score = ScoreCalculator.calculate_base_score(
            total_earnings, reputation_multiplier
        )
        time_bonus = ScoreCalculator.calculate_time_bonus(
            completion_time, total_game_time
        )
        penalties = ScoreCalculator.calculate_penalties(
            cancelled_orders, expired_orders, late_deliveries
        )

        final_score = max(0, base_score + time_bonus - penalties)

        return {
            "base_score": base_score,
            "time_bonus": time_bonus,
            "penalties": penalties,
            "final_score": final_score,
            "breakdown": {
                "earnings": total_earnings,
                "reputation_multiplier": reputation_multiplier,
                "completion_time": completion_time,
                "cancelled_orders": cancelled_orders,
                "expired_orders": expired_orders,
                "late_deliveries": late_deliveries,
            },
        }