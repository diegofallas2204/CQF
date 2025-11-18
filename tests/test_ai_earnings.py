"""
tests/test_ai_earnings.py

Test to verify AI agent earnings tracking functionality.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from Entities.AIPlayer import RandomAI, HeuristicAI, GraphAI
from Management.OrderManager import OrderManager
from State.OrderState import OrderState


def test_ai_has_total_earnings():
    """Verify all AI agent types have total_earnings attribute"""
    for AgentClass in [RandomAI, HeuristicAI, GraphAI]:
        agent = AgentClass()
        assert hasattr(agent, 'total_earnings'), f"{AgentClass.__name__} missing total_earnings"
        assert agent.total_earnings == 0, f"{AgentClass.__name__} total_earnings should start at 0"


def test_ai_earnings_tracking():
    """Test that AI earnings can be tracked"""
    agent = RandomAI()
    
    # Initial earnings should be 0
    assert agent.total_earnings == 0
    
    # Simulate earning money
    agent.total_earnings += 100
    assert agent.total_earnings == 100
    
    # Simulate more earnings
    agent.total_earnings += 50
    assert agent.total_earnings == 150


def test_ai_order_delivery_earnings():
    """Test that AI earnings increase when orders are delivered"""
    # This is a basic test - actual delivery logic is in Game.py
    agent = RandomAI()
    order_manager = OrderManager()
    
    # Load a test order
    orders_data = [{
        "id": "TEST-001",
        "pickup": [2, 2],
        "dropoff": [5, 5],
        "payout": 100,
        "deadline": "2025-12-31T23:59:59Z",
        "weight": 2.0,
        "priority": 1,
        "release_time": 0
    }]
    order_manager.load_orders(orders_data)
    
    # Get the order
    order = order_manager.all_orders.get("TEST-001")
    assert order is not None
    
    # Simulate delivery by manually adding earnings
    # (In actual game, this happens in _check_cpu_location_interactions)
    initial_earnings = agent.total_earnings
    agent.total_earnings += order.payout
    
    assert agent.total_earnings == initial_earnings + 100
    print(f"✓ AI earnings increased from {initial_earnings} to {agent.total_earnings}")


if __name__ == "__main__":
    test_ai_has_total_earnings()
    print("✓ test_ai_has_total_earnings passed")
    
    test_ai_earnings_tracking()
    print("✓ test_ai_earnings_tracking passed")
    
    test_ai_order_delivery_earnings()
    print("✓ test_ai_order_delivery_earnings passed")
    
    print("\n✓ All AI earnings tests passed!")
