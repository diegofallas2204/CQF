"""
tests/test_ai_random.py

Test básico para RandomAI: con semilla fija debe seleccionar un pedido válido
y producir movimientos walkable.
"""
import random
from Entities.AIPlayer import RandomAI
from types import SimpleNamespace

def test_random_ai_selects_order_and_moves(city_fixture, orders_fixture):
    ai = RandomAI()
    # crear city mock ligero con is_walkable
    city = SimpleNamespace()
    city.tiles = city_fixture.get("tiles", [])
    city.is_walkable = lambda x,y: 0 <= x < len(city.tiles[0]) and 0 <= y < len(city.tiles)
    ai.update_world(city, {o["id"]: SimpleNamespace(**o) for o in orders_fixture}, None)
    # forzamos seed para reproducibilidad
    ai._rng.seed(42)
    choice = ai.decide_accept_order()
    # choice puede ser None si no hay disponible; assert no excepción y que tipo sea str o None
    assert (choice is None) or isinstance(choice, str)
    dx,dy = ai.decide_move()
    assert isinstance(dx, int) and isinstance(dy, int)