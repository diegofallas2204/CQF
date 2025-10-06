import json
from datetime import datetime, timedelta, timezone
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
        """Carga pedidos desde datos JSON (rebase de deadlines si vienen en el pasado)."""
        self.all_orders.clear()
        self.available_orders = PriorityQueue()
        self.expired_orders.clear()
        self.completed_orders.clear()

        now_aware = datetime.now(timezone.utc)

        # Para conservar el escalonado entre pedidos, usamos un offset inicial base
        # y sumamos 30s por índice (ajústalo si quieres que se separen más).
        base_offset = timedelta(minutes=10)
        step = timedelta(seconds=30)

        for i, od in enumerate(orders_data):
            order = Order(
                id=od["id"],
                pickup=tuple(od["pickup"]),
                dropoff=tuple(od["dropoff"]),
                payout=od["payout"],
                deadline=od["deadline"],
                weight=od["weight"],
                priority=od.get("priority", 0),
                release_time=od.get("release_time", 0),
            )

            # Si el deadline está en el pasado, rebasamos al futuro.
            # Esto solo afecta la instancia en memoria (no se escribe al archivo).
            if order.deadline <= now_aware:
                order.deadline = now_aware + base_offset + step * i

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
        if order_id in self.all_orders:
            o = self.all_orders[order_id]
            if o.state == OrderState.ACCEPTED:
                tz = o.deadline.tzinfo or timezone.utc
                o.state = OrderState.PICKED_UP
                o.pickup_time = datetime.now(tz)
                return True
        return False

    def deliver_order(self, order_id: str) -> Optional[Order]:
        if order_id in self.all_orders:
            o = self.all_orders[order_id]
            if o.state in [OrderState.PICKED_UP, OrderState.ACCEPTED]:
                tz = o.deadline.tzinfo or timezone.utc
                o.state = OrderState.DELIVERED
                o.delivery_time = datetime.now(tz)
                self.completed_orders.append(o)
                return o
        return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancela pedido aceptado"""
        if order_id in self.all_orders:
            order = self.all_orders[order_id]
            if order.state in [OrderState.ACCEPTED, OrderState.PICKED_UP]:
                order.state = OrderState.CANCELLED
                return True
        return False

    def update_expired_orders(self) -> list[Order]:
        just_expired = []
        for o in self.all_orders.values():
            tz = o.deadline.tzinfo or timezone.utc
            now_aware = datetime.now(tz)
            if o.is_expired(now_aware) and o.state not in [
                OrderState.DELIVERED,
                OrderState.CANCELLED,
                OrderState.EXPIRED,
            ]:
                o.state = OrderState.EXPIRED
                self.expired_orders.append(o)
                just_expired.append(o)
        return just_expired

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """Obtiene pedido por ID"""
        return self.all_orders.get(order_id)

    def get_statistics(self) -> dict:
        """
        Retorna estadísticas agregadas de pedidos.
        Las claves incluyen: total, available, completed, expired, cancelled,
        accepted, picked_up, delivered (además de las listas internas si quieres).
        """
        # Conteos por estado
        counts = {
            "available": 0,
            "accepted": 0,
            "picked_up": 0,
            "delivered": 0,
            "expired": 0,
            "cancelled": 0,
        }

        for o in self.all_orders.values():
            if o.state == OrderState.AVAILABLE:
                counts["available"] += 1
            elif o.state == OrderState.ACCEPTED:
                counts["accepted"] += 1
            elif o.state == OrderState.PICKED_UP:
                counts["picked_up"] += 1
            elif o.state == OrderState.DELIVERED:
                counts["delivered"] += 1
            elif o.state == OrderState.EXPIRED:
                counts["expired"] += 1
            elif o.state == OrderState.CANCELLED:
                counts["cancelled"] += 1

        stats = {
            "total": len(self.all_orders),
            "available": counts["available"],
            "completed": len(self.completed_orders),
            "expired": counts["expired"],
            "cancelled": counts["cancelled"],
            "accepted": counts["accepted"],
            "picked_up": counts["picked_up"],
            "delivered": counts["delivered"],
        }
        return stats
