import json
import os
import pickle
from typing import Optional

class FileManager:
    """Gestión de archivos locales para datos y partidas."""

    def __init__(self, data_dir="Data", saves_dir="saves"):
        self.data_dir = data_dir
        self.saves_dir = saves_dir
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(saves_dir, exist_ok=True)

    def save_game(self, game_state: dict, filename: str):
        path = os.path.join(self.saves_dir, filename)
        with open(path, "wb") as f:
            pickle.dump(game_state, f)

    def load_game(self, filename: str) -> Optional[dict]:
        path = os.path.join(self.saves_dir, filename)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return pickle.load(f)

    def save_json(self, data: dict, filename: str):
        path = os.path.join(self.data_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_json(self, filename: str) -> Optional[dict]:
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_scores(self, scores: list, filename: str = "puntajes.json"):
        path = os.path.join(self.data_dir, filename)
        scores_sorted = sorted(scores, key=lambda s: s["score"], reverse=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(scores_sorted, f, ensure_ascii=False, indent=2)

    def load_scores(self, filename: str = "puntajes.json") -> list:
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
