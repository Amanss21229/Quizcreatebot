import json
from pathlib import Path

class LanguageManager:
    def __init__(self, data_file='data/language_settings.json'):
        self.data_file = data_file
        self.language_settings = self._load_data()
    
    def _load_data(self):
        try:
            Path('data').mkdir(exist_ok=True)
            if Path(self.data_file).exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_data(self):
        try:
            Path('data').mkdir(exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.language_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving language data: {e}")
    
    def set_language(self, chat_id, language):
        """Set language for a chat (group or user)."""
        chat_id = str(chat_id)
        if language in ['hindi', 'english']:
            self.language_settings[chat_id] = language
            self._save_data()
            return True
        return False
    
    def get_language(self, chat_id):
        """Get language for a chat. Default is English."""
        return self.language_settings.get(str(chat_id), 'english')

language_manager = LanguageManager()
