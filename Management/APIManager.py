# Management/APIManager.py
from typing import Optional, List, Dict, Any
import Data.API as API_mod  # si usas paquete Data/

class APIManager:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or getattr(API_mod, "API_BASE", None)

    def get_city(self) -> Optional[Dict[str, Any]]:
        return API_mod.get_city_map()     # dict con tiles/legend/width/height/goal

    def get_orders(self) -> Optional[List[Dict[str, Any]]]:
        data = API_mod.get_city_jobs()
        # normalización defensiva si viniera envuelto
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            return data["data"]
        if isinstance(data, dict) and "orders" in data and isinstance(data["orders"], list):
            return data["orders"]
        return data

    def get_weather(self) -> Optional[Dict[str, Any]]:
        return API_mod.get_city_weather()

    # aliases opcionales
    def get_jobs(self): return self.get_orders()
    def get_city_map(self): return self.get_city()

    def __repr__(self) -> str:
        return f"<APIManager base_url={self.base_url!r} using {getattr(API_mod, '__file__', '?')}>"
