# Management/CacheManager.py
import json, os, time
from typing import Any, Optional

class CacheManager:
    """
    Cache por recurso (un archivo por key) que se SOBREESCRIBE siempre:
      api_cache/city.json
      api_cache/orders.json
      api_cache/weather.json
    Guarda también un timestamp dentro del archivo para poder aplicar TTL.
    """
    def __init__(self, base_dir: Optional[str] = None):
        base_dir = base_dir or os.path.dirname(__file__)
        self.cache_dir = os.path.normpath(os.path.join(base_dir, "..", "api_cache"))
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = "".join(c for c in key if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.cache_dir, f"{safe}.json")

    def save_cache(self, key: str, data: Any, timestamp: Optional[float] = None) -> None:
        """Escribe/actualiza SIEMPRE el mismo archivo por key (overwrite)."""
        payload = {
            "timestamp": float(timestamp) if timestamp is not None else time.time(),
            "Data": data
        }
        path = self._path(key)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)  # escritura atómica

    def load_cache(self, key: str, max_age_seconds: Optional[int] = None) -> Any:
        """
        Lee el archivo de la key. Si max_age_seconds está definido y el archivo
        es más viejo que eso, retorna None.
        """
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            ts = float(payload.get("timestamp", 0))
            if max_age_seconds is not None:
                if time.time() - ts > max_age_seconds:
                    return None
            return payload.get("Data", None)
        except Exception:
            return None

    def clear(self, key: str) -> None:
        """Borra el archivo de cache de la key (si existe)."""
        path = self._path(key)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
