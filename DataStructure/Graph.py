"""
DataStructure/Graph.py

Grafo ligero para la cuadrícula con funciones de coste, Dijkstra y A*.
- adj: dict[node] -> dict[neighbor] = weight
- node: (x,y)
"""

from typing import Dict, Tuple, Iterable, List, Optional
import heapq
import math

Node = Tuple[int, int]


class Graph:
    def __init__(self):
        self.adj: Dict[Node, Dict[Node, float]] = {}

    def add_node(self, n: Node):
        self.adj.setdefault(n, {})

    def add_edge(self, a: Node, b: Node, w: float = 1.0):
        self.add_node(a)
        self.add_node(b)
        self.adj[a][b] = w

    def neighbors(self, n: Node) -> Iterable[Node]:
        return self.adj.get(n, {}).keys()

    def weight(self, a: Node, b: Node) -> float:
        return self.adj.get(a, {}).get(b, math.inf)

    def dijkstra(self, start: Node) -> Dict[Node, float]:
        dist = {start: 0.0}
        pq = [(0.0, start)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, math.inf):
                continue
            for v, w in self.adj.get(u, {}).items():
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))
        return dist

    def astar(self, start: Node, goal: Node, heuristic=None) -> Optional[List[Node]]:
        """
        Simple A* implementation; heuristic(node, goal) debe retornar coste estimado.
        Retorna lista de nodos desde start (excluido) a goal (incluido) o None si no hay path.
        """
        if heuristic is None:
            heuristic = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
        open_set = [(heuristic(start, goal), 0.0, start, None)]
        came_from = {}
        gscore = {start: 0.0}
        closed = set()
        while open_set:
            _, g, current, parent = heapq.heappop(open_set)
            if current in closed:
                continue
            came_from[current] = parent
            if current == goal:
                # reconstruir path (excluir start)
                path = []
                node = current
                while node is not None and node != start:
                    path.append(node)
                    node = came_from.get(node)
                path.reverse()
                return path
            closed.add(current)
            for nb, w in self.adj.get(current, {}).items():
                tentative_g = g + w
                if tentative_g < gscore.get(nb, math.inf):
                    gscore[nb] = tentative_g
                    f = tentative_g + heuristic(nb, goal)
                    heapq.heappush(open_set, (f, tentative_g, nb, current))
        return None

    # helper para estimación de coste entre dos nodos (puede usar dijkstra o heurística)
    def estimate_cost(self, a: Node, b: Node) -> float:
        # por defecto, usar Manhattan (rápido)
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # wrapper path method
    def path(self, a: Node, b: Node) -> List[Node]:
        p = self.astar(a, b)
        return p or []

    def validate_graph(self):
        """
        Método de debug para validar que el grafo está bien construido.
        Imprime información sobre nodos y aristas.

        Returns:
            True si el grafo es válido, False en caso contrario
        """
        print(f"[Graph] Validando grafo con {len(self.adj)} nodos")

        total_edges = 0
        for node, neighbors in self.adj.items():
            total_edges += len(neighbors)

        print(f"[Graph] Total de aristas: {total_edges}")

        # Verificar que hay al menos algunos nodos
        if len(self.adj) == 0:
            print("[Graph] ⚠️ ADVERTENCIA: Grafo vacío!")
            return False

        # Mostrar algunos nodos de ejemplo
        sample_nodes = list(self.adj.keys())[:5]
        print(f"[Graph] Nodos de ejemplo: {sample_nodes}")

        for node in sample_nodes:
            neighbors = list(self.adj[node].keys())
            print(f"  {node} -> {neighbors[:5]}")  # Solo primeros 5 vecinos

        return True
