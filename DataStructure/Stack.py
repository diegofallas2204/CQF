
class Stack:
    """
    Pila (LIFO) para el sistema de deshacer movimientos.
    Implementación simple pero eficiente.

    Complejidad: O(1) push/pop, O(1) peek
    """

    def __init__(self, max_size: int = 50):
        self._items = []
        self.max_size = max_size

    def push(self, item):
        """Agrega item al tope de la pila"""
        self._items.append(item)

        # Limitar tamaño para evitar uso excesivo de memoria
        if len(self._items) > self.max_size:
            self._items.pop(0)  # Remover el más antiguo

    def pop(self):
        """Extrae y retorna el item del tope"""
        if self.is_empty():
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self):
        """Retorna el item del tope sin extraerlo"""
        if self.is_empty():
            return None
        return self._items[-1]

    def is_empty(self) -> bool:
        """Verifica si la pila está vacía"""
        return len(self._items) == 0

    def size(self) -> int:
        """Retorna el tamaño de la pila"""
        return len(self._items)

    def clear(self):
        """Limpia la pila"""
        self._items.clear()