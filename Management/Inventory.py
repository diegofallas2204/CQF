from DataStructure.DoublyLinkedList import DoublyLinkedList
from DataStructure.SortingAlgorithms import SortingAlgorithms
from Entities.Order import Order, OrderState
from typing import Any, Deque, Dict, List, Optional, Tuple

class Inventory:
    """
    Gestión completa del inventario usando lista doblemente enlazada.
    Permite navegación eficiente y ordenamiento flexible.
    """

    def __init__(self, max_weight: float = 10.0):
        self.orders = DoublyLinkedList()
        self.max_weight = max_weight
        self.current_weight = 0.0
        self.orders_by_id: Dict[str, Order] = {}  # Hash table para búsqueda O(1)

    def can_add_order(self, order: Order) -> bool:
        """Verifica si se puede agregar el pedido"""
        can_add = self.current_weight + order.weight <= self.max_weight
        return can_add

    def add_order(self, order: Order) -> bool:
        """Agrega pedido al inventario"""
        if not self.can_add_order(order):
            print(f"Error: No se puede agregar {order.id} - excede capacidad")
            return False

        # Verificar si el pedido ya está en inventario
        if order.id in self.orders_by_id:
            print(f"Error: Pedido {order.id} ya está en inventario")
            return False

        self.orders.append(order)
        self.orders_by_id[order.id] = order
        self.current_weight += order.weight

        # Solo cambiar estado si no está ya aceptado
        if order.state != OrderState.ACCEPTED:
            order.state = OrderState.ACCEPTED

        print(
            f"✓ Pedido {order.id} agregado al inventario. Peso total: {self.current_weight:.1f}kg"
        )
        return True

    def remove_order(self, order_id: str) -> Optional[Order]:
        """Remueve pedido del inventario"""
        if order_id not in self.orders_by_id:
            return None

        order = self.orders_by_id[order_id]

        if self.orders.remove(order):
            del self.orders_by_id[order_id]
            self.current_weight -= order.weight
            print(
                f"Pedido {order_id} removido del inventario. Peso restante: {self.current_weight:.1f}kg"
            )
            return order

        return None

    def navigate_next(self) -> Optional[Order]:
        """Navega al siguiente pedido en inventario"""
        return self.orders.navigate_next()

    def navigate_prev(self) -> Optional[Order]:
        """Navega al pedido anterior en inventario"""
        return self.orders.navigate_prev()

    def get_current_order(self) -> Optional[Order]:
        """Obtiene pedido actual en navegación"""
        return self.orders.get_current()

    def reset_navigation(self):
        """Resetea navegación al primer pedido"""
        self.orders.reset_navigation()

    def get_orders_by_priority(self) -> List[Order]:
        """Retorna pedidos ordenados por prioridad (mayor primero)"""
        orders_list = self.orders.to_list()
        return SortingAlgorithms.quick_sort(
            orders_list, key_func=lambda order: order.priority, reverse=True
        )

    def get_orders_by_deadline(self) -> List[Order]:
        """Retorna pedidos ordenados por deadline (más urgente primero)"""
        orders_list = self.orders.to_list()
        return SortingAlgorithms.quick_sort(
            orders_list, key_func=lambda order: order.deadline, reverse=False
        )

    def get_orders_by_payout(self) -> List[Order]:
        """Retorna pedidos ordenados por pago (mayor primero)"""
        orders_list = self.orders.to_list()
        return SortingAlgorithms.quick_sort(
            orders_list, key_func=lambda order: order.payout, reverse=True
        )

    def is_empty(self) -> bool:
        """Verifica si el inventario está vacío"""
        return self.orders.is_empty()

    def get_count(self) -> int:
        """Retorna número de pedidos en inventario"""
        return self.orders.size()

    def get_available_weight(self) -> float:
        """Retorna peso disponible"""
        return self.max_weight - self.current_weight

    def __repr__(self):
        return f"Inventory({self.get_count()} orders, {self.current_weight:.1f}/{self.max_weight}kg)"