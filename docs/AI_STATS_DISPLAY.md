# AI Opponent Stats Display - Implementation Guide

## Overview
This document describes the implementation of AI opponent stats display in the Courier Quest game UI. The feature adds a dedicated panel to show AI stats alongside the player's stats, enabling users to monitor both the player and AI progress simultaneously during gameplay.

## Requirements Implemented

### 1. AI Stamina Bar (Barra de Resistencia)
- **Location**: Top panel, left column
- **Display**: "Resistencia: XX" with visual bar
- **Color**: Cyan when healthy, Yellow when tired, Red when low
- **Updates**: Real-time during gameplay

### 2. AI Score (Puntuación)
- **Location**: Top panel, left column (below stamina)
- **Display**: "Puntos: $XXX"
- **Updates**: Increments when AI delivers orders
- **Tracking**: New `total_earnings` attribute in AIPlayer class

### 3. Additional Stats
- **Reputation**: Shows AI reputation value (0-100)
- **Inventory**: Number of active orders AI is carrying
- **Current Order**: Order ID and payout if AI has an active order
- **Position**: AI location on map (tracked internally)

### 4. Visual Distinction
- **AI Panel**: Purple background (#461964), cyan accents
- **Player Panel**: Blue background (#19466), yellow/green accents
- **Labels**: "IA (DIFFICULTY)" vs "JUGADOR"
- **Position**: AI panel on top, player panel on bottom

## Architecture

### Class Changes

#### AIPlayer (Entities/AIPlayer.py)
```python
class AIPlayer:
    def __init__(self, name: str = "CPU", difficulty: str = "easy"):
        # ... existing attributes ...
        self.total_earnings: int = 0  # NEW: Track AI earnings
```

#### AIManager (Management/AIManager.py)
```python
def _cpu_try_interaction(self) -> Optional[str]:
    # ... delivery logic ...
    if delivered:
        # NEW: Add earnings to AI agent
        if hasattr(self.agent, 'total_earnings'):
            self.agent.total_earnings += delivered.payout
```

#### Game (Game.py)
```python
def _render_extended_ui(self):
    """Modified to support dual-panel layout"""
    # Detect if AI is active
    has_ai = (hasattr(self, "ai_manager") and self.ai_manager 
              and hasattr(self.ai_manager, "agent") and self.ai_manager.agent)
    
    if has_ai:
        # Render AI panel first
        self._render_ai_stats_panel(...)
        # Then render player panel
        # ... player stats rendering ...

def _render_ai_stats_panel(self, panel_x, panel_y, panel_w, panel_h, 
                            panel_margin_x, panel_margin_y):
    """NEW: Dedicated method to render AI stats"""
    # Render stamina bar
    # Render earnings
    # Render reputation
    # Render inventory
    # Render current order
    # ... etc ...
```

## UI Layout

### Dual-Panel Mode (with AI)
```
+----------------------------------------------------------+
|                       GAME MAP                            |
|                                                          |
+----------------------------------------------------------+
| IA (DIFFICULTY)                                          |
| Resistencia: XX [====    ] Puntos: $XXX                 |
| Reputación: XX  Inventario: X  Pedido: XXX  Meta: $XXX  |
+----------------------------------------------------------+
| JUGADOR                                                  |
| Resistencia: XX [====    ] Puntos: $XXX                 |
| Reputación: XX  Inventario: X  Pedido: XXX  Tiempo: MM:SS|
+----------------------------------------------------------+
```

### Single-Panel Mode (without AI)
```
+----------------------------------------------------------+
|                       GAME MAP                            |
|                                                          |
+----------------------------------------------------------+
| JUGADOR                                                  |
| Resistencia: XX [========] Reputación: XX Pago x1.05    |
| Inventario: X  Peso: X.Xkg  Deshacer: X                |
| Actual: XXX  $XXX  Recuperando +2/s                     |
| Tiempo: MM:SS  $XXX/$GOAL  Clima: clear (0.10)         |
| Score (ahora): XXXX  base=XXX bonus=XXX -penalties      |
| Disponibles: X  Completados: X                          |
| [Controls info]                                          |
+----------------------------------------------------------+
```

## Testing

### Unit Tests
- `test_ai_earnings.py`: Verifies AI earnings tracking
- Tests that all AI agent types have `total_earnings` attribute
- Tests earnings increment on order delivery

### Integration Tests
- `test_ai_stats_integration.py`: Full integration testing
- Verifies all AI attributes exist
- Tests stat updates during gameplay
- Generates screenshot proof
- Compares player vs AI stats

### UI Tests
- `test_ui_screenshot.py`: Visual verification
- Generates screenshots with AI stats
- Verifies file creation and size

## Usage

### For Players
1. Start game and select difficulty (Easy/Medium/Hard)
2. AI stats automatically appear in top panel
3. Monitor AI progress during gameplay
4. Compare your performance against AI

### For Developers
```python
# Access AI stats
if game.ai_manager and game.ai_manager.agent:
    agent = game.ai_manager.agent
    print(f"AI Stamina: {agent.stamina}")
    print(f"AI Earnings: {agent.total_earnings}")
    print(f"AI Reputation: {agent.reputation}")
```

## Performance Considerations
- Minimal overhead: Only renders when AI is active
- Efficient layout: Compact 70px panels when both displayed
- No additional game logic: Stats update naturally during gameplay

## Future Enhancements
- [ ] Add AI speed/velocity indicator
- [ ] Show AI's planned route on map
- [ ] Display AI decision-making indicators
- [ ] Add historical stats comparison graph
- [ ] Implement AI performance metrics

## Troubleshooting

### Issue: AI stats not showing
**Solution**: Ensure game is started with difficulty other than "easy" (medium/hard have AI)

### Issue: AI earnings not updating
**Solution**: Verify AI is delivering orders successfully (check console logs)

### Issue: Stats overlap or misaligned
**Solution**: Check screen resolution is at least 800x600

## References
- Original issue: "Display AI stats like player stats"
- Screenshots: 
  - https://github.com/user-attachments/assets/f593fc3d-7214-4921-9fab-15837dfbad7c
  - https://github.com/user-attachments/assets/0a0b8197-6943-451c-9b3c-711b8528e687
- Test files: `tests/test_ai_*.py`
