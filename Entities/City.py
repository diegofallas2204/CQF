from typing import Any, Dict, List, Optional, Tuple

class City:
    """Clase City de la Fase 1 (mismo código)"""

    def __init__(self):
        self.width = 0
        self.height = 0
        self.tiles: List[List[str]] = []
        self.legend: Dict[str, Dict] = {}
        self.goal = 0
        self.blocked_tiles = set()

    # Reemplaza tu método load_from_dict por este en City.py

    def load_from_dict(self, city_data: Dict[str, Any]) -> bool:
        try:
            # 1) Tomamos legend y lo normalizamos
            raw_legend = city_data.get("legend", {})
            if not isinstance(raw_legend, dict):
                raise TypeError("legend debe ser un dict")

            # Normalizar claves de legend a str por si vienen numéricas
            self.legend = {str(k): (v if isinstance(v, dict) else {}) for k, v in raw_legend.items()}

            # 2) Tomamos tiles y los normalizamos a List[List[str]]
            raw_tiles = city_data.get("tiles")
            if raw_tiles is None:
                raise KeyError("Falta 'tiles' en city_data")

            # Caso A: lista de strings -> convertir cada fila en lista de caracteres
            if all(isinstance(r, str) for r in raw_tiles):
                tiles = [list(r) for r in raw_tiles]

            # Caso B: lista de listas -> aseguramos que cada celda sea str
            elif all(isinstance(r, list) for r in raw_tiles):
                tiles = [[str(c) for c in r] for r in raw_tiles]

            else:
                raise TypeError("tiles debe ser lista de strings o lista de listas")

            # 3) Validar rectangularidad
            if len(tiles) == 0:
                raise ValueError("tiles está vacío")

            row_len = len(tiles[0])
            if any(len(r) != row_len for r in tiles):
                raise ValueError("Todas las filas de tiles deben tener el mismo largo")

            # 4) width/height: usar los provistos o inferirlos
            inferred_height = len(tiles)
            inferred_width = row_len
            self.width = int(city_data.get("width", inferred_width))
            self.height = int(city_data.get("height", inferred_height))

            if self.height != inferred_height or self.width != inferred_width:
                raise ValueError(
                    f"Dimensiones no coinciden: width/height ({self.width}x{self.height}) "
                    f"vs tiles ({inferred_width}x{inferred_height})"
                )

            self.tiles = tiles
            self.goal = int(city_data.get("goal", 3000))

            # 5) blocked_tiles: soporta 'blocked: true' o 'walkable: false'
            self.blocked_tiles = {
                t for t, info in self.legend.items()
                if bool(info.get("blocked", False)) or (info.get("walkable") is False)
            }

            # 6) Validar que todos los tile_types existan en legend (si tienes legend)
            if self.legend:
                # Busca el primero que no exista para dar un error claro
                for y, row in enumerate(self.tiles):
                    for x, t in enumerate(row):
                        if t not in self.legend:
                            raise ValueError(f"Tile '{t}' en ({x},{y}) no existe en legend")

            return True

        except (KeyError, ValueError, TypeError) as e:
            print(f"Error cargando mapa: {e}")
            # Opcional: pistas de depuración rápidas
            try:
                sample = {
                    "width": city_data.get("width"),
                    "height": city_data.get("height"),
                    "tiles_type": type(city_data.get("tiles")).__name__,
                    "row0_type": type(city_data.get("tiles", [None])[0]).__name__ if city_data.get("tiles") else None,
                    "legend_keys_sample": list(city_data.get("legend", {}).keys())[:5],
                }
                print(f"[DEBUG] Pistas: {sample}")
            except Exception:
                pass
            return False

    def is_valid_position(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        if not self.is_valid_position(x, y):
            return False
        tile_type = self.tiles[y][x]
        return tile_type not in self.blocked_tiles

    def get_surface_weight(self, x: int, y: int) -> float:
        if not self.is_valid_position(x, y):
            return 1.0
        tile_type = self.tiles[y][x]
        return self.legend.get(tile_type, {}).get("surface_weight", 1.0)

    def get_tile_type(self, x: int, y: int) -> Optional[str]:
        if not self.is_valid_position(x, y):
            return None
        return self.tiles[y][x]

    def get_tile_name(self, x: int, y: int) -> Optional[str]:
        tile_type = self.get_tile_type(x, y)
        if tile_type:
            return self.legend.get(tile_type, {}).get("name", tile_type)
        return None

    def get_adjacent_positions(self, x: int, y: int) -> List[Tuple[int, int]]:
        adjacent = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            if self.is_walkable(new_x, new_y):
                adjacent.append((new_x, new_y))

        return adjacent

    def calculate_manhattan_distance(
        self, pos1: Tuple[int, int], pos2: Tuple[int, int]
    ) -> int:
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def __repr__(self):
        return f"City({self.width}x{self.height}, goal={self.goal})"