# Data/API.py  (o API.py si está en raíz)
import requests

API_BASE = "https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"

def fetch_json(endpoint: str):
    url = f"{API_BASE}{endpoint}"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.json()

def get_healthz():
    try:
        return fetch_json("/healthz")
    except Exception as e:
        print(f"[API] healthz error: {e}")
        return None

def get_city_map():
    """Devuelve el **payload de ciudad** listo (sin wrappers)."""
    try:
        raw = fetch_json("/city/map")
        # desanidar si viene {"version": "...", "data": {...}}
        if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
            raw = raw["data"]
        return raw
    except Exception as e:
        print(f"[API] city error: {e}")
        return None

def get_city_jobs():
    """Devuelve lista de pedidos (puede venir envuelto)."""
    try:
        raw = fetch_json("/city/jobs")
        if isinstance(raw, dict) and isinstance(raw.get("data"), list):
            return raw["data"]
        return raw
    except Exception as e:
        print(f"[API] jobs error: {e}")
        return None

def get_city_weather():
    """Devuelve dict de clima (puede venir envuelto)."""
    try:
        raw = fetch_json("/city/weather")
        if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
            raw = raw["data"]
        return raw
    except Exception as e:
        print(f"[API] weather error: {e}")
        return None
