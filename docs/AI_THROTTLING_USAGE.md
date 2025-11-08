# AI Throttling System - Usage Guide

## Overview
The AI throttling system prevents the AI from executing actions too rapidly, which was causing:
- Movement too fast without delay between frames
- Repetitive attempts to accept orders every frame
- Command spam to OrderManager
- Cluttered logs with multiple attempts to accept the same order

## How It Works

### Throttling Mechanisms

1. **Action Cooldown**: After executing an action, the AI enters a cooldown period before it can execute another action.
   - Configurable via `min_action_interval` (default: 0.5 seconds)
   - Different actions have different cooldown multipliers:
     - Move: 1x (0.5s)
     - Accept order: 2x (1.0s)
     - Pickup: 1.5x (0.75s)
     - Deliver: 2x (1.0s)

2. **Decision Interval**: The AI only re-evaluates its strategy periodically, not every frame.
   - Configurable via `decision_interval` (default: 1.0 seconds)
   - Prevents constant re-computation of decisions

## Configuration

### Basic Setup

```python
from Management.AIManager import AIManager

# Create AI manager with difficulty level
ai_manager = AIManager(difficulty="easy")

# Register game references
ai_manager.register_game_refs(city, order_manager, weather_manager)
ai_manager.attach_game(game)

# In game loop
ai_manager.tick(delta_time)
```

### Adjusting Throttling Parameters

```python
# Make AI faster (for hard difficulty)
ai_manager.min_action_interval = 0.2  # 200ms between actions
ai_manager.decision_interval = 0.5    # Re-evaluate every 500ms

# Make AI slower (for easy difficulty)
ai_manager.min_action_interval = 0.5  # 500ms between actions
ai_manager.decision_interval = 1.0    # Re-evaluate every 1 second

# Make AI very slow (for debugging)
ai_manager.min_action_interval = 1.0  # 1s between actions
ai_manager.decision_interval = 2.0    # Re-evaluate every 2 seconds
```

## Recommended Values by Difficulty

| Parameter | Easy | Medium | Hard |
|-----------|------|--------|------|
| `min_action_interval` | 0.5s | 0.3s | 0.2s |
| `decision_interval` | 1.0s | 0.8s | 0.5s |

## Integration with Game.py

To integrate AIManager with Game.py, add the following:

```python
# In Game.__init__()
from Management.AIManager import AIManager

self.ai_manager = AIManager(difficulty="easy")

# After initializing city, order_manager, weather_manager
self.ai_manager.register_game_refs(self.city, self.order_manager, self.weather_manager)
self.ai_manager.attach_game(self)

# Adjust throttling parameters
self.ai_manager.min_action_interval = 0.3
self.ai_manager.decision_interval = 0.8

# In Game.update()
self.ai_manager.tick(delta_time)

# Add this method to Game class for AI movement
def _attempt_move_cpu(self, agent, dx, dy):
    """Permite al AI mover su agente"""
    current_x, current_y = agent.position
    new_x, new_y = current_x + dx, current_y + dy
    
    if self.city.is_walkable(new_x, new_y):
        agent.position = (new_x, new_y)
        return True
    return False
```

## Behavior Methods

The AI has three behavior methods corresponding to difficulty levels:

### Easy Behavior (`_easy_behavior`)
- Random movement with occasional direction to target
- Accepts first available order
- Simple validation to prevent multiple orders

### Medium Behavior (`_medium_behavior`)
- Heuristic-based decision making
- Evaluates orders based on payout, distance, and weather
- Moves toward targets using simple pathfinding

### Hard Behavior (`_hard_behavior`)
- Graph-based pathfinding (A* or Dijkstra)
- Advanced route planning
- Optimal order selection

## Validation

The `_attempt_accept_order()` method includes comprehensive validation:

1. ✅ Checks if agent already has an active order
2. ✅ Verifies order state is AVAILABLE
3. ✅ Ensures no other agent has accepted this order
4. ✅ Only accepts order if OrderManager allows it
5. ✅ Updates agent inventory and order state atomically

## Testing

Run the throttling tests:

```bash
cd /home/runner/work/CQF/CQF
PYTHONPATH=/home/runner/work/CQF/CQF python3 tests/test_ai_throttling.py
```

Expected output:
```
✓ Test throttling passed: 10 ticks en 0.20s
✓ Test decision interval passed
✓ Test accept order validation passed

✓ Todos los tests de throttling pasaron exitosamente
```

## Troubleshooting

### AI not moving
- Check that `_attempt_move_cpu()` is implemented in Game.py
- Verify `attach_game()` was called with correct game instance
- Ensure agent has valid position and city has walkable tiles

### AI accepting multiple orders
- Verify `_attempt_accept_order()` validation logic
- Check that order states are being updated correctly
- Ensure OrderManager is preventing multiple accepts

### Actions too slow/fast
- Adjust `min_action_interval` for action speed
- Adjust `decision_interval` for decision frequency
- Check that `delta_time` is being passed correctly to `tick()`

## Logging

The AI produces clean, throttled logs:

```
[CPU-CPU_Agent] ✓ Pedido PED-001 aceptado
[CPU-CPU_Agent] Pedido PED-001 recogido
[CPU-CPU_Agent] Pedido PED-001 entregado
```

No spam of:
```
Pedido PED-001 removido de la cola de disponibles y listo para aceptar (x100)
```

## Security Summary

✅ No security vulnerabilities detected by CodeQL
✅ All validation checks in place
✅ No race conditions in order acceptance
✅ Proper state management
