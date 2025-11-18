"""
tests/test_ui_screenshot.py

Test to generate screenshot of UI with AI stats
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from Game import Game
import pygame


def test_ui_with_ai():
    """Generate a screenshot of the UI with AI stats"""
    print('Creating game...')
    game = Game(screen_width=800, screen_height=600)
    
    print('Loading data...')
    success = game.load_data_phase3()
    assert success, "Failed to load game data"
    
    print('Starting game with medium difficulty (has AI)...')
    game.selected_difficulty = 'medium'
    game.start_game()
    
    # Verify AI is active
    assert game.ai_manager is not None, "AI manager should exist"
    assert game.ai_manager.agent is not None, "AI agent should exist"
    
    agent = game.ai_manager.agent
    print(f'\nAI Stats:')
    print(f'  Type: {type(agent).__name__}')
    print(f'  Stamina: {agent.stamina}')
    print(f'  Reputation: {agent.reputation}')
    print(f'  Total Earnings: {agent.total_earnings}')
    print(f'  Position: {agent.position}')
    
    # Simulate some earnings for visual demo
    agent.total_earnings = 250
    game.player.total_earnings = 400
    game.player.stamina = 75.0
    agent.stamina = 60.0
    
    print('\nSimulating game state with some progress...')
    print(f'  Player earnings: ${game.player.total_earnings}')
    print(f'  AI earnings: ${agent.total_earnings}')
    print(f'  Player stamina: {game.player.stamina}')
    print(f'  AI stamina: {agent.stamina}')
    
    # Render one frame
    print('\nRendering frame...')
    game.render()
    
    # Save screenshot
    screenshot_path = '/tmp/game_ui_with_ai.png'
    pygame.image.save(game.screen, screenshot_path)
    print(f'\n✓ Screenshot saved to {screenshot_path}')
    
    # Verify file exists
    assert os.path.exists(screenshot_path), f"Screenshot not saved to {screenshot_path}"
    file_size = os.path.getsize(screenshot_path)
    print(f'  File size: {file_size} bytes')
    assert file_size > 1000, "Screenshot file seems too small"
    
    print('\n✓ UI rendering test passed!')
    return screenshot_path


if __name__ == "__main__":
    screenshot_path = test_ui_with_ai()
    print(f'\nScreenshot available at: {screenshot_path}')
