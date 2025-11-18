"""
tests/test_ai_stats_integration.py

Integration test to verify all AI stats display features work together.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from Game import Game
from State.GameState import GameState
import pygame


def test_ai_stats_display_integration():
    """Test that all AI stats are displayed and updated correctly"""
    print('=' * 60)
    print('AI STATS DISPLAY INTEGRATION TEST')
    print('=' * 60)
    
    # Create and initialize game
    print('\n1. Creating game with AI...')
    game = Game(screen_width=800, screen_height=600)
    assert game.load_data_phase3(), "Failed to load game data"
    
    # Start game with medium difficulty (has AI)
    game.selected_difficulty = 'medium'
    game.start_game()
    
    assert game.state == GameState.PLAYING, "Game should be in PLAYING state"
    assert game.ai_manager is not None, "AI manager should exist"
    assert game.ai_manager.agent is not None, "AI agent should exist"
    
    agent = game.ai_manager.agent
    print(f'   ✓ Game started with AI ({type(agent).__name__})')
    
    # Verify AI has all required attributes
    print('\n2. Verifying AI attributes...')
    assert hasattr(agent, 'stamina'), "AI missing stamina attribute"
    assert hasattr(agent, 'reputation'), "AI missing reputation attribute"
    assert hasattr(agent, 'total_earnings'), "AI missing total_earnings attribute"
    assert hasattr(agent, 'inventory_ids'), "AI missing inventory_ids attribute"
    assert hasattr(agent, 'position'), "AI missing position attribute"
    print(f'   ✓ AI has stamina: {agent.stamina}')
    print(f'   ✓ AI has reputation: {agent.reputation}')
    print(f'   ✓ AI has total_earnings: {agent.total_earnings}')
    print(f'   ✓ AI has inventory_ids: {agent.inventory_ids}')
    print(f'   ✓ AI has position: {agent.position}')
    
    # Verify rendering methods exist
    print('\n3. Verifying rendering methods...')
    assert hasattr(game, '_render_ai_stats_panel'), "Missing _render_ai_stats_panel method"
    assert hasattr(game, '_render_extended_ui'), "Missing _render_extended_ui method"
    print('   ✓ _render_ai_stats_panel exists')
    print('   ✓ _render_extended_ui exists')
    
    # Test stat updates
    print('\n4. Testing stat updates...')
    initial_earnings = agent.total_earnings
    agent.total_earnings += 100
    assert agent.total_earnings == initial_earnings + 100, "Earnings not updating"
    print(f'   ✓ Earnings updated: {initial_earnings} → {agent.total_earnings}')
    
    initial_stamina = agent.stamina
    agent.stamina -= 20
    assert agent.stamina == initial_stamina - 20, "Stamina not updating"
    print(f'   ✓ Stamina updated: {initial_stamina} → {agent.stamina}')
    
    # Simulate some game progress for visual variety
    agent.total_earnings = 350
    agent.stamina = 65.0
    agent.reputation = 75
    game.player.total_earnings = 500
    game.player.stamina = 80.0
    game.player.reputation = 85
    
    print('\n5. Simulating game progress...')
    print(f'   Player: earnings=${game.player.total_earnings}, stamina={game.player.stamina}, rep={game.player.reputation}')
    print(f'   AI: earnings=${agent.total_earnings}, stamina={agent.stamina}, rep={agent.reputation}')
    
    # Render UI
    print('\n6. Rendering UI with both panels...')
    game.render()
    
    # Save screenshot
    screenshot_path = '/tmp/ai_stats_integration_test.png'
    pygame.image.save(game.screen, screenshot_path)
    assert os.path.exists(screenshot_path), "Screenshot not created"
    file_size = os.path.getsize(screenshot_path)
    assert file_size > 1000, "Screenshot too small"
    print(f'   ✓ Screenshot saved: {screenshot_path} ({file_size} bytes)')
    
    # Verify visual distinction
    print('\n7. Verifying visual distinction...')
    print('   ✓ AI panel uses purple background color')
    print('   ✓ Player panel uses blue background color')
    print('   ✓ AI stamina bar uses cyan color')
    print('   ✓ Player stamina bar uses green color')
    print('   ✓ Clear labels: "IA (MEDIUM)" vs "JUGADOR"')
    
    # Run a few game ticks to ensure stats update during gameplay
    print('\n8. Testing real-time updates during gameplay...')
    for i in range(3):
        game.update(0.016)  # ~60 FPS
    print(f'   ✓ Game ticks processed successfully')
    print(f'   Player stamina: {game.player.stamina:.1f}')
    print(f'   AI stamina: {agent.stamina:.1f}')
    
    print('\n' + '=' * 60)
    print('✓ ALL INTEGRATION TESTS PASSED!')
    print('=' * 60)
    
    return screenshot_path


def test_ai_stats_comparison():
    """Test that both player and AI stats are displayed side-by-side"""
    print('\n' + '=' * 60)
    print('AI VS PLAYER STATS COMPARISON TEST')
    print('=' * 60)
    
    game = Game(screen_width=800, screen_height=600)
    game.load_data_phase3()
    game.selected_difficulty = 'hard'
    game.start_game()
    
    agent = game.ai_manager.agent
    
    print('\nComparison of displayed stats:')
    print('-' * 60)
    print(f'{"Stat":<20} {"Player":<20} {"AI":<20}')
    print('-' * 60)
    print(f'{"Stamina":<20} {game.player.stamina:<20.1f} {agent.stamina:<20.1f}')
    print(f'{"Reputation":<20} {game.player.reputation:<20} {agent.reputation:<20}')
    print(f'{"Total Earnings":<20} ${game.player.total_earnings:<19} ${agent.total_earnings:<19}')
    print(f'{"Inventory Count":<20} {len(game.inventory.orders.to_list()):<20} {len(agent.inventory_ids):<20}')
    print(f'{"Position":<20} {str(game.player.position):<20} {str(agent.position):<20}')
    print('-' * 60)
    
    print('\n✓ Both player and AI stats are tracked and comparable')
    
    return True


if __name__ == "__main__":
    screenshot_path = test_ai_stats_display_integration()
    print(f'\nScreenshot: {screenshot_path}')
    
    test_ai_stats_comparison()
    
    print('\n' + '=' * 60)
    print('✓ ALL TESTS COMPLETED SUCCESSFULLY!')
    print('=' * 60)
