from Game import Game

def main():
    game = Game()
    if not game.load_data_phase3():
        print("No se pudo iniciar el juego por falta de datos.")
        return
    game.start_game()
    game.run()


if __name__ == "__main__":
    main()
