import json
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

ADMINS_FILE = 'bot_admins.json'

class AdminManager:
    def __init__(self, permanent_admins: List[int]):
        self.permanent_admins = set(permanent_admins)
        self.dynamic_admins: set = set()
        self.load_admins()
    
    def load_admins(self):
        """Load dynamic admins from JSON file."""
        if os.path.exists(ADMINS_FILE):
            try:
                with open(ADMINS_FILE, 'r') as f:
                    data = json.load(f)
                    self.dynamic_admins = set(data.get('admins', []))
                logger.info(f"Loaded {len(self.dynamic_admins)} dynamic admins")
            except Exception as e:
                logger.error(f"Error loading admins: {e}")
                self.dynamic_admins = set()
        else:
            self.dynamic_admins = set()
    
    def save_admins(self):
        """Save dynamic admins to JSON file."""
        try:
            with open(ADMINS_FILE, 'w') as f:
                json.dump({'admins': list(self.dynamic_admins)}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving admins: {e}")
    
    def add_admin(self, user_id: int) -> bool:
        """Add a user to admin list."""
        if user_id not in self.dynamic_admins:
            self.dynamic_admins.add(user_id)
            self.save_admins()
            return True
        return False
    
    def remove_admin(self, user_id: int) -> bool:
        """Remove a user from dynamic admin list (permanent admins cannot be removed)."""
        if user_id in self.permanent_admins:
            return False
        if user_id in self.dynamic_admins:
            self.dynamic_admins.remove(user_id)
            self.save_admins()
            return True
        return False
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin (permanent or dynamic)."""
        return user_id in self.permanent_admins or user_id in self.dynamic_admins
    
    def get_all_admins(self) -> List[int]:
        """Get all admins (permanent + dynamic)."""
        return list(self.permanent_admins.union(self.dynamic_admins))
    
    def is_permanent_admin(self, user_id: int) -> bool:
        """Check if user is a permanent admin."""
        return user_id in self.permanent_admins
