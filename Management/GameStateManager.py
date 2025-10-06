from DataStructure.Stack import Stack
from DataStructure.DoublyLinkedList import DoublyLinkedList
from State.GameSnapshot import GameSnapshot
import time
from Entities.Order import OrderState

class GameStateManager:
    """
    Gestor de estados del juego para sistema de deshacer.
    Usa pila para almacenar snapshots del estado.
    """

    def __init__(self, max_history: int = 20):
        self.history = Stack(max_history)
        self.max_history = max_history

    def save_state(self, game_instance) -> bool:
        """
        Guarda snapshot del estado actual del juego.
        Retorna True si se guardó exitosamente.
        """
        try:
            # Obtener estados de pedidos
            order_states = {}
            inventory_order_ids = []

            if hasattr(game_instance, "order_manager"):
                order_states = {
                    order_id: order.state.value
                    for order_id, order in game_instance.order_manager.all_orders.items()
                }

            if hasattr(game_instance, "inventory"):
                inventory_order_ids = [
                    order.id for order in game_instance.inventory.orders.to_list()
                ]

            # Crear snapshot
            snapshot = GameSnapshot(
                player_position=game_instance.player.position,
                player_stamina=game_instance.player.stamina,
                player_inventory_weight=game_instance.player.inventory_weight,
                player_total_earnings=game_instance.player.total_earnings,
                current_time=game_instance.current_time,
                order_states=order_states,
                inventory_order_ids=inventory_order_ids,
                timestamp=time.time(),
            )

            self.history.push(snapshot)
            return True

        except Exception as e:
            print(f"Error guardando estado: {e}")
            return False

    def undo_last_action(self, game_instance) -> bool:
        """
        Restaura el último estado guardado.
        Retorna True si se restauró exitosamente.
        """
        if self.history.is_empty():
            return False

        try:
            snapshot = self.history.pop()

            # Restaurar estado del jugador
            game_instance.player.position = snapshot.player_position
            game_instance.player.stamina = snapshot.player_stamina
            game_instance.player.inventory_weight = snapshot.player_inventory_weight
            game_instance.player.total_earnings = snapshot.player_total_earnings
            game_instance.current_time = snapshot.current_time

            # Restaurar estados de pedidos
            if hasattr(game_instance, "order_manager"):
                for order_id, state_str in snapshot.order_states.items():
                    if order_id in game_instance.order_manager.all_orders:
                        order = game_instance.order_manager.all_orders[order_id]
                        order.state = OrderState(state_str)

            # Restaurar inventario
            if hasattr(game_instance, "inventory"):
                # Limpiar inventario actual
                game_instance.inventory.orders = DoublyLinkedList()
                game_instance.inventory.orders_by_id.clear()
                game_instance.inventory.current_weight = 0.0

                # Restaurar pedidos en inventario
                for order_id in snapshot.inventory_order_ids:
                    if (
                        hasattr(game_instance, "order_manager")
                        and order_id in game_instance.order_manager.all_orders
                    ):

                        order = game_instance.order_manager.all_orders[order_id]
                        game_instance.inventory.add_order(order)

            return True

        except Exception as e:
            print(f"Error restaurando estado: {e}")
            return False

    def can_undo(self) -> bool:
        """Verifica si se puede deshacer"""
        return not self.history.is_empty()

    def get_undo_count(self) -> int:
        """Retorna número de estados que se pueden deshacer"""
        return self.history.size()

    def clear_history(self):
        """Limpia historial de estados"""
        self.history.clear()
