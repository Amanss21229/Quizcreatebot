import json
from pathlib import Path

class TagAllManager:
    def __init__(self, data_file='data/tagall_permissions.json'):
        self.data_file = data_file
        self.permissions = self._load_data()
    
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
                json.dump(self.permissions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving tagall permissions data: {e}")
    
    def set_permission(self, group_id, permission_type):
        """Set tagall permission for a group. permission_type: 'user' or 'admin'."""
        group_id = str(group_id)
        if permission_type in ['user', 'admin']:
            self.permissions[group_id] = permission_type
            self._save_data()
            return True
        return False
    
    def get_permission(self, group_id):
        """Get tagall permission for a group. Default is 'admin'."""
        return self.permissions.get(str(group_id), 'admin')
    
    def can_use_tagall(self, group_id, user_id, is_admin, is_group_admin):
        """Check if a user can use /tagall command."""
        permission = self.get_permission(group_id)
        
        # If permission is 'user', anyone can use it
        if permission == 'user':
            return True
        
        # If permission is 'admin', only bot admins or group admins can use it
        if permission == 'admin':
            return is_admin or is_group_admin
        
        return False

tagall_manager = TagAllManager()
