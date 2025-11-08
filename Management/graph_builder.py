"""
Management/graph_builder.py

Convierte una instancia City y WeatherManager en un Graph ponderado.
- Usa city.tiles y city.get_surface_weight(x,y)
- Ajusta peso por multiplicador de clima
- Cachea el graph para no reconstruir cada frame
"""
from DataStructure.Graph import Graph
from typing import Any, Tuple

class GraphBuilder:
    def __init__(self):
        self._cached_city_id = None
        self._cached_graph = None

    def build(self, city: Any, weather: Any) -> Graph:
        # Si el mapa no ha cambiado, retornar cache
        city_id = getattr(city, "id", id(city))
        if self._cached_city_id == city_id and self._cached_graph is not None:
            return self._cached_graph
        g = Graph()
        for y, row in enumerate(getattr(city, "tiles", [])):
            for x, tile in enumerate(row):
                if tile in getattr(city, "blocked_tiles", []):
                    continue
                node = (x,y)
                g.add_node(node)
                # vecinos 4-direcciones
                for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                    if 0 <= ny < city.height and 0 <= nx < city.width:
                        if city.is_walkable(nx, ny):
                            w = city.get_surface_weight(nx, ny)
                            # aplicar factor clima si procede
                            if weather and hasattr(weather, "get_speed_multiplier"):
                                # invertir multiplicador para convertir velocidad->cost (simple heuristic)
                                mul = weather.get_speed_multiplier()
                                w = w * (1.0 + max(0.0, 1.0 - mul))
                            g.add_edge(node, (nx,ny), w)
        self._cached_city_id = city_id
        self._cached_graph = g
        return g