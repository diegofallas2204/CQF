import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from DataStructure.PriorityQueue import PriorityQueue
from DataStructure.SortingAlgorithms import SortingAlgorithms
from Entities.Order import Order
from State.OrderState import OrderState

class OrderManager:
    """
    Gestor avanzado de pedidos usando cola de prioridad.
    Maneja disponibilidad, expiración y estados.
    """

    def __init__(self):
        self.available_orders = PriorityQueue()
        self.all_orders: Dict[str, Order] = {}
        self.expired_orders: List[Order] = []
        self.completed_orders: List[Order] = []

    def load_orders(self, orders_data: List[Dict[str, Any]]):
        """Carga pedidos desde datos JSON"""
        self.all_orders.clear()
        self.available_orders = PriorityQueue()
        self.expired_orders.clear()
        self.completed_orders.clear()

        for order_data in orders_data:

            order = Order(
                id=order_data["id"],
                pickup=tuple(order_data["pickup"]),
                dropoff=tuple(order_data["dropoff"]),
                payout=order_data["payout"],
                deadline=order_data["deadline"],
                weight=order_data["weight"],
                priority=order_data.get("priority", 0),
                release_time=order_data.get("release_time", 0),
            )
            self.all_orders[order.id] = order

    def update_available_orders(self, current_game_time: float):
        """Actualiza pedidos disponibles basado en release_time"""
        # Obtener IDs ya en la cola para evitar duplicados
        available_ids = {order.id for order in self.available_orders.to_list()}

        for order in self.all_orders.values():
            if (
                order.is_available(current_game_time)
                and order.state == OrderState.AVAILABLE
                and order.id not in available_ids
            ):

                print(
                    f"Agregando pedido {order.id} a cola de prioridad (prioridad: {order.priority})"
                )
                self.available_orders.push(order, order.priority)

    def get_available_orders_by_priority(self) -> List[Order]:
        """Retorna pedidos disponibles ordenados por prioridad (filtrados por AVAILABLE)"""
        return [
            o
            for o in self.available_orders.to_list()
            if o.state == OrderState.AVAILABLE
        ]

    def get_available_orders_by_deadline(self) -> List[Order]:
        """Retorna pedidos disponibles ordenados por deadline"""
        available = [
            o
            for o in self.available_orders.to_list()
            if o.state == OrderState.AVAILABLE
        ]
        return SortingAlgorithms.merge_sort(
            available, key_func=lambda order: order.deadline, reverse=False
        )

    def get_available_orders_by_payout(self) -> List[Order]:
        """Retorna pedidos disponibles ordenados por pago"""
        available = [
            o
            for o in self.available_orders.to_list()
            if o.state == OrderState.AVAILABLE
        ]
        return SortingAlgorithms.merge_sort(
            available, key_func=lambda order: order.payout, reverse=True
        )

    def accept_order(self, order_id: str) -> Optional[Order]:
        """Marca pedido como aceptado y lo remueve de disponibles (si posible)"""
        if order_id not in self.all_orders:
            print(f"Error: Pedido {order_id} no encontrado en all_orders")
            return None

        # comprobar si ya existe un pedido aceptado o recogido en todo el sistema
        for o in self.all_orders.values():
            if o.state in [OrderState.ACCEPTED, OrderState.PICKED_UP]:
                print(
                    f"Error: Ya existe un pedido activo ({o.id}). No se permiten múltiples aceptados."
                )
                return None

        order = self.all_orders[order_id]
        if order.state == OrderState.AVAILABLE:
            # Marcar para aceptar (el inventario cambiará el estado definitivamente al agregarlo)
            # Remover de la cola de disponibles
            self.available_orders.remove_by_id(order_id)
            print(
                f"Pedido {order_id} removido de la cola de disponibles y listo para aceptar"
            )
            return order
        else:
            print(
                f"Error: Pedido {order_id} no está disponible (estado: {order.state})"
            )

        return None

    def pickup_order(self, order_id: str) -> bool:
        """Marca pedido como recogido"""
        if order_id in self.all_orders:
            order = self.all_orders[order_id]
            if order.state == OrderState.ACCEPTED:
                order.state = OrderState.PICKED_UP
                order.pickup_time = datetime.now()
                return True
        return False

    def deliver_order(self, order_id: str) -> Optional[Order]:
        """Marca pedido como entregado"""
        if order_id in self.all_orders:
            order = self.all_orders[order_id]
            if (
                order.state == OrderState.PICKED_UP
                or order.state == OrderState.ACCEPTED
            ):
                # Aceptamos entregarlo si está aceptado o recogido
                order.state = OrderState.DELIVERED
                order.delivery_time = datetime.now()
                self.completed_orders.append(order)
                return order
        return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancela pedido aceptado"""
        if order_id in self.all_orders:
            order = self.all_orders[order_id]
            if order.state in [OrderState.ACCEPTED, OrderState.PICKED_UP]:
                order.state = OrderState.CANCELLED
                return True
        return False

    def update_expired_orders(self):
        """Actualiza pedidos expirados - DESHABILITADO para testing"""
        # COMENTADO temporalmente para evitar que los pedidos se marquen como expirados
        # durante el desarrollo y testing
        pass

        # TODO: Implementar correctamente cuando se tengan fechas deadline realistas
        # current_time = datetime.now()
        #
        # for order in self.all_orders.values():
        #     if (order.is_expired(current_time) and
        #         order.state not in [OrderState.DELIVERED, OrderState.CANCELLED, OrderState.EXPIRED]):
        #
        #         order.state = OrderState.EXPIRED
        #         self.expired_orders.append(order)

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """Obtiene pedido por ID"""
        return self.all_orders.get(order_id)

    def get_statistics(self) -> Dict[str, int]:
        """Retorna estadísticas de pedidos"""
        stats = {
            "total": len(self.all_orders),
            "available": self.available_orders.size(),
            "completed": len(self.completed_orders),
            "expired": len(self.expired_orders),
        }

        # Contar por estado
        for state in OrderState:
            stats[state.value] = sum(
                1 for order in self.all_orders.values() if order.state == state
            )

        return stats