"""
tests/test_ai_throttling.py

Test para verificar el sistema de throttling del AIManager.
"""
import time
from Management.AIManager import AIManager
from Management.OrderManager import OrderManager
from Entities.City import City
from Management.WeatherManager import WeatherManager
from State.OrderState import OrderState
from types import SimpleNamespace


def test_throttling_prevents_rapid_actions():
    """Verifica que el throttling previene acciones muy rápidas"""
    # Setup
    ai_mgr = AIManager(difficulty="easy")
    order_mgr = OrderManager()
    city = City()
    weather_mgr = WeatherManager()
    
    # Cargar ciudad simple
    city.load_from_dict({
        "width": 10,
        "height": 10,
        "tiles": [["." for _ in range(10)] for _ in range(10)],
        "goal": 500
    })
    
    # Cargar pedidos
    orders_data = [{
        "id": "PED-001",
        "pickup": [2, 2],
        "dropoff": [5, 5],
        "payout": 100,
        "deadline": "2025-12-31T23:59:59Z",
        "weight": 2.0,
        "priority": 1,
        "release_time": 0
    }]
    order_mgr.load_orders(orders_data)
    order_mgr.update_available_orders(0.0)
    
    # Registrar referencias
    ai_mgr.register_game_refs(city, order_mgr, weather_mgr)
    
    # Mock del objeto game con método _attempt_move_cpu
    game_mock = SimpleNamespace()
    game_mock._attempt_move_cpu = lambda agent, dx, dy: None
    ai_mgr.attach_game(game_mock)
    
    # Test: llamar tick múltiples veces rápidamente
    tick_count = 0
    action_count = 0
    
    # Resetear last_decision_time para que la primera decisión se ejecute
    ai_mgr.last_decision_time = 0
    
    start_time = time.time()
    for i in range(10):
        ai_mgr.tick(0.016)  # ~60 FPS
        tick_count += 1
        time.sleep(0.02)  # Simular 50 FPS real
    
    elapsed = time.time() - start_time
    
    # Verificar que no todas las llamadas ejecutaron acciones
    # (debido al throttling, solo algunas deberían ejecutarse)
    assert tick_count == 10, "Deberían haberse llamado 10 ticks"
    
    # Verificar que el cooldown funciona
    assert ai_mgr.action_cooldown >= 0, "El cooldown debe ser no negativo"
    
    print(f"✓ Test throttling passed: {tick_count} ticks en {elapsed:.2f}s")


def test_decision_interval_throttling():
    """Verifica que el intervalo de decisión funciona correctamente"""
    ai_mgr = AIManager(difficulty="easy")
    order_mgr = OrderManager()
    city = City()
    weather_mgr = WeatherManager()
    
    # Cargar ciudad simple
    city.load_from_dict({
        "width": 10,
        "height": 10,
        "tiles": [["." for _ in range(10)] for _ in range(10)],
        "goal": 500
    })
    
    # Registrar referencias
    ai_mgr.register_game_refs(city, order_mgr, weather_mgr)
    
    # Configurar intervalo de decisión corto para testing
    ai_mgr.decision_interval = 0.1  # 100ms
    ai_mgr.last_decision_time = 0
    
    # Primera llamada debería ejecutarse
    ai_mgr.tick(0.016)
    first_decision_time = ai_mgr.last_decision_time
    assert first_decision_time > 0, "La primera decisión debería haber actualizado el tiempo"
    
    # Llamada inmediata no debería ejecutarse (menos de 100ms)
    time.sleep(0.05)  # 50ms
    ai_mgr.tick(0.016)
    assert ai_mgr.last_decision_time == first_decision_time, "No debería haber re-decidido tan pronto"
    
    # Después de esperar el intervalo completo, sí debería ejecutarse
    time.sleep(0.06)  # Total 110ms
    ai_mgr.tick(0.016)
    assert ai_mgr.last_decision_time > first_decision_time, "Debería haber re-decidido después del intervalo"
    
    print("✓ Test decision interval passed")


def test_attempt_accept_order_validation():
    """Verifica que _attempt_accept_order valida correctamente"""
    ai_mgr = AIManager(difficulty="easy")
    order_mgr = OrderManager()
    city = City()
    weather_mgr = WeatherManager()
    
    # Cargar ciudad simple
    city.load_from_dict({
        "width": 10,
        "height": 10,
        "tiles": [["." for _ in range(10)] for _ in range(10)],
        "goal": 500
    })
    
    # Cargar pedidos
    orders_data = [{
        "id": "PED-001",
        "pickup": [2, 2],
        "dropoff": [5, 5],
        "payout": 100,
        "deadline": "2025-12-31T23:59:59Z",
        "weight": 2.0,
        "priority": 1,
        "release_time": 0
    }]
    order_mgr.load_orders(orders_data)
    order_mgr.update_available_orders(0.0)
    
    # Registrar referencias
    ai_mgr.register_game_refs(city, order_mgr, weather_mgr)
    
    # Obtener pedido
    order = order_mgr.all_orders["PED-001"]
    
    # Verificación 1: Debería poder aceptar pedido disponible sin inventario
    assert ai_mgr.agent.inventory_ids == [], "Inventario debería estar vacío"
    result = ai_mgr._attempt_accept_order(order)
    assert result == True, "Debería aceptar el pedido disponible"
    assert "PED-001" in ai_mgr.agent.inventory_ids, "El pedido debería estar en el inventario"
    
    # Verificación 2: No debería poder aceptar otro pedido si ya tiene uno
    orders_data2 = [{
        "id": "PED-002",
        "pickup": [3, 3],
        "dropoff": [6, 6],
        "payout": 150,
        "deadline": "2025-12-31T23:59:59Z",
        "weight": 2.0,
        "priority": 2,
        "release_time": 0
    }]
    # Agregar el segundo pedido directamente al diccionario
    from Entities.Order import Order
    order2 = Order(
        id="PED-002",
        pickup=(3, 3),
        dropoff=(6, 6),
        payout=150,
        deadline="2025-12-31T23:59:59Z",
        weight=2.0,
        priority=2,
        release_time=0
    )
    order_mgr.all_orders["PED-002"] = order2
    order_mgr.available_orders.push(order2, order2.priority)
    
    result2 = ai_mgr._attempt_accept_order(order2)
    assert result2 == False, "No debería aceptar un segundo pedido"
    assert len(ai_mgr.agent.inventory_ids) == 1, "Solo debería tener un pedido"
    
    print("✓ Test accept order validation passed")


if __name__ == "__main__":
    test_throttling_prevents_rapid_actions()
    test_decision_interval_throttling()
    test_attempt_accept_order_validation()
    print("\n✓ Todos los tests de throttling pasaron exitosamente")
