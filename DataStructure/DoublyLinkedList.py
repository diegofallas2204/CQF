from typing import List

class DoublyLinkedNode:
    """Nodo para lista doblemente enlazada"""

    def __init__(self, data):
        self.data = data
        self.next = None
        self.prev = None

class DoublyLinkedList:
    """
    Lista doblemente enlazada para navegación bidireccional del inventario.
    Permite navegación eficiente adelante/atrás.

    Complejidad: O(1) inserción/eliminación en extremos, O(n) búsqueda
    """

    def __init__(self):
        self.head = None
        self.tail = None
        self.current = None  # Para navegación
        self._size = 0

    def append(self, data):
        """Agrega elemento al final"""
        new_node = DoublyLinkedNode(data)

        if not self.head:
            self.head = self.tail = self.current = new_node
        else:
            new_node.prev = self.tail
            self.tail.next = new_node
            self.tail = new_node

        self._size += 1

    def prepend(self, data):
        """Agrega elemento al inicio"""
        new_node = DoublyLinkedNode(data)

        if not self.head:
            self.head = self.tail = self.current = new_node
        else:
            new_node.next = self.head
            self.head.prev = new_node
            self.head = new_node

        self._size += 1

    def remove(self, data):
        """Remueve primera ocurrencia del elemento"""
        current = self.head

        while current:
            if current.data == data:
                # Actualizar current si estamos removiendo el nodo actual
                if current == self.current:
                    self.current = current.next or current.prev

                # Actualizar enlaces
                if current.prev:
                    current.prev.next = current.next
                else:
                    self.head = current.next

                if current.next:
                    current.next.prev = current.prev
                else:
                    self.tail = current.prev

                self._size -= 1
                return True

            current = current.next

        return False

    def navigate_next(self):
        """Navega al siguiente elemento"""
        if self.current and self.current.next:
            self.current = self.current.next
            return self.current.data
        return None

    def navigate_prev(self):
        """Navega al elemento anterior"""
        if self.current and self.current.prev:
            self.current = self.current.prev
            return self.current.data
        return None

    def get_current(self):
        """Obtiene elemento actual"""
        return self.current.data if self.current else None

    def reset_navigation(self):
        """Resetea navegación al primer elemento"""
        self.current = self.head

    def to_list(self) -> List:
        """Convierte a lista Python para fácil manipulación"""
        result = []
        current = self.head
        while current:
            result.append(current.data)
            current = current.next
        return result

    def size(self) -> int:
        """Retorna tamaño de la lista"""
        return self._size

    def is_empty(self) -> bool:
        """Verifica si la lista está vacía"""
        return self._size == 0
    
 