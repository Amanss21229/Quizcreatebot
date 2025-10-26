import json
from pathlib import Path
from datetime import datetime
import time

class TagAllManager:
    def __init__(self, 
                 permissions_file='data/tagall_permissions.json',
                 members_file='data/tracked_members.json'):
        self.permissions_file = permissions_file
        self.members_file = members_file
        self.permissions = self._load_permissions()
        self.tracked_members = self._load_members()
        self._pending_save = False
        self._last_save_time = 0
        self._save_interval = 10
    
    def _load_permissions(self):
        try:
            Path('data').mkdir(exist_ok=True)
            if Path(self.permissions_file).exists():
                with open(self.permissions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_permissions(self):
        try:
            Path('data').mkdir(exist_ok=True)
            with open(self.permissions_file, 'w', encoding='utf-8') as f:
                json.dump(self.permissions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving tagall permissions data: {e}")
    
    def _load_members(self):
        try:
            Path('data').mkdir(exist_ok=True)
            if Path(self.members_file).exists():
                with open(self.members_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_members(self):
        try:
            Path('data').mkdir(exist_ok=True)
            with open(self.members_file, 'w', encoding='utf-8') as f:
                json.dump(self.tracked_members, f, ensure_ascii=False, indent=2)
            self._last_save_time = time.time()
            self._pending_save = False
        except Exception as e:
            print(f"Error saving tracked members data: {e}")
    
    def _save_members_throttled(self):
        """Save members data with throttling to avoid blocking on every message."""
        self._pending_save = True
        current_time = time.time()
        
        # Only save if enough time has passed since last save
        if current_time - self._last_save_time >= self._save_interval:
            self._save_members()
    
    def flush_pending_saves(self):
        """Force save if there are pending changes. Call this on shutdown."""
        if self._pending_save:
            self._save_members()
    
    def set_permission(self, group_id, permission_type):
        """Set tagall permission for a group. permission_type: 'user' or 'admin'."""
        group_id = str(group_id)
        if permission_type in ['user', 'admin']:
            self.permissions[group_id] = permission_type
            self._save_permissions()
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
    
    def track_member(self, chat_id, user_id, first_name, username=None, is_bot=False):
        """Track a member who sends a message in the group. Admin status updated separately."""
        chat_id = str(chat_id)
        user_id = str(user_id)
        
        # Skip bots
        if is_bot:
            return
        
        # Initialize chat if not exists
        if chat_id not in self.tracked_members:
            self.tracked_members[chat_id] = {}
        
        # Get existing admin status or default to False
        existing_is_admin = False
        if user_id in self.tracked_members[chat_id]:
            existing_is_admin = self.tracked_members[chat_id][user_id].get('is_admin', False)
        
        # Store/update user info
        self.tracked_members[chat_id][user_id] = {
            'user_id': int(user_id),
            'first_name': first_name,
            'username': username,
            'is_admin': existing_is_admin,
            'last_seen': datetime.now().isoformat()
        }
        
        # Use throttled save instead of immediate save
        self._save_members_throttled()
    
    def update_admin_status(self, chat_id, admin_ids):
        """Batch update admin status for all tracked members in a chat."""
        chat_id = str(chat_id)
        
        if chat_id not in self.tracked_members:
            return
        
        # Update admin status for all tracked members
        for user_id in self.tracked_members[chat_id]:
            self.tracked_members[chat_id][user_id]['is_admin'] = int(user_id) in admin_ids
        
        # Use throttled save
        self._save_members_throttled()
    
    def get_members_for_tagging(self, chat_id, exclude_admins=True):
        """Get list of tracked members for a chat, optionally excluding admins."""
        chat_id = str(chat_id)
        
        if chat_id not in self.tracked_members:
            return []
        
        members = []
        for user_id, user_data in self.tracked_members[chat_id].items():
            # Skip admins if requested
            if exclude_admins and user_data.get('is_admin', False):
                continue
            
            members.append(user_data)
        
        return members
    
    def get_member_count(self, chat_id):
        """Get count of tracked members in a chat."""
        chat_id = str(chat_id)
        if chat_id not in self.tracked_members:
            return 0
        return len(self.tracked_members[chat_id])

tagall_manager = TagAllManager()
