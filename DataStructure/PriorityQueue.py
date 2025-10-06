import heapq
from typing import List

class PriorityQueue:
    """
    Cola de prioridad implementada con heap binario.

    Para pedidos: mayor prioridad = menor valor en heap (se invierte)
    Complejidad: O(log n) inserción/extracción, O(1) peek
    """

    def __init__(self):
        self._heap = []
        self._index = 0  # Para romper empates y mantener orden FIFO

    def push(self, item, priority: int):
        """
        Agrega item con prioridad específica.
        Prioridad más alta = número más grande, pero heap usa min-heap
        así que invertimos la prioridad.
        """
        # Invertir prioridad para que mayor prioridad = menor heap value
        heap_priority = -priority
        heapq.heappush(self._heap, (heap_priority, self._index, item))
        self._index += 1

    def pop(self):
        """Extrae y retorna el item con mayor prioridad"""
        if self.is_empty():
            raise IndexError("pop from empty priority queue")
        return heapq.heappop(self._heap)[2]  # Retorna solo el item

    def peek(self):
        """Retorna el item con mayor prioridad sin extraerlo"""
        if self.is_empty():
            return None
        return self._heap[0][2]

    def is_empty(self) -> bool:
        """Verifica si la cola está vacía"""
        return len(self._heap) == 0

    def size(self) -> int:
        """Retorna el tamaño de la cola"""
        return len(self._heap)

    def to_list(self) -> List:
        """Retorna todos los items ordenados por prioridad (sin extraer)"""
        # Crear copia del heap y extraer todos los elementos
        temp_heap = self._heap.copy()
        result = []
        while temp_heap:
            result.append(heapq.heappop(temp_heap)[2])
        return result

    def remove_by_id(self, item_id: str):
        """Remueve elementos del heap por id (si existe)."""
        # Filtrar heap excluyendo el id
        new_heap = [
            entry for entry in self._heap if getattr(entry[2], "id", None) != item_id
        ]
        if len(new_heap) != len(self._heap):
            self._heap = new_heap
            heapq.heapify(self._heap)