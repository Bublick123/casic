from typing import Dict, Set

class GameManager:
    """Менеджер для управления активными играми"""
    
    def __init__(self):
        self.active_games: Set[int] = set()
        self.game_players: Dict[int, Set[int]] = {}
    
    def add_game(self, game_id: int):
        """Добавляет игру в активные"""
        self.active_games.add(game_id)
        self.game_players[game_id] = set()
    
    def remove_game(self, game_id: int):
        """Удаляет игру из активных"""
        self.active_games.discard(game_id)
        self.game_players.pop(game_id, None)
    
    def add_player_to_game(self, game_id: int, user_id: int):
        """Добавляет игрока в игру"""
        if game_id in self.game_players:
            self.game_players[game_id].add(user_id)
    
    def remove_player_from_game(self, game_id: int, user_id: int):
        """Удаляет игрока из игры"""
        if game_id in self.game_players:
            self.game_players[game_id].discard(user_id)
    
    def get_game_players(self, game_id: int) -> Set[int]:
        """Возвращает игроков в игре"""
        return self.game_players.get(game_id, set())