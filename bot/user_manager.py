import json
import os
from typing import Dict, Optional


class UserManager:
    def __init__(self, data_file: str = 'users_data.json'):
        self.data_file = data_file
        self.users_data = self._load_data()

    def _load_data(self) -> Dict:
        """Загрузка данных пользователей"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_data(self):
        """Сохранение данных пользователей"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.users_data, f, ensure_ascii=False, indent=2)

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Получение данных пользователя"""
        return self.users_data.get(user_id)

    def save_user(self, user_id: str, user_data: Dict):
        """Сохранение данных пользователя"""
        # гарантируем, что есть все нужные поля
        user_data.setdefault('email', None)
        user_data.setdefault('timezone', 'Europe/Moscow')
        user_data.setdefault('reminder_minutes', 10)
        user_data.setdefault('calendar_id', None)  # персональный календарь
        self.users_data[user_id] = user_data
        self._save_data()

    def delete_user(self, user_id: str):
        """Удаление пользователя"""
        if user_id in self.users_data:
            del self.users_data[user_id]
            self._save_data()

    def ensure_calendar_id(self, user_id: str, calendar_id: str):
        """
        Сохраняет calendar_id пользователя, если он ещё не установлен.
        Используется после создания нового персонального календаря через сервисный аккаунт.
        """
        user_data = self.get_user(user_id)
        if not user_data:
            user_data = {}
        if not user_data.get('calendar_id'):
            user_data['calendar_id'] = calendar_id
            self.save_user(user_id, user_data)
