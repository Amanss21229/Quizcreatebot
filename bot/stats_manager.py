import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

STATS_FILE = 'bot_stats.json'

class StatsManager:
    def __init__(self):
        self.users: Set[int] = set()
        self.groups: Set[int] = set()
        self.total_quizzes_generated = 0
        self.total_questions_sent = 0
        self.start_time = datetime.now().isoformat()
        self.load_stats()
    
    def load_stats(self):
        """Load statistics from JSON file."""
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r') as f:
                    data = json.load(f)
                    self.users = set(data.get('users', []))
                    self.groups = set(data.get('groups', []))
                    self.total_quizzes_generated = data.get('total_quizzes_generated', 0)
                    self.total_questions_sent = data.get('total_questions_sent', 0)
                    self.start_time = data.get('start_time', datetime.now().isoformat())
                logger.info(f"Loaded stats: {len(self.users)} users, {len(self.groups)} groups")
            except Exception as e:
                logger.error(f"Error loading stats: {e}")
                self._init_empty_stats()
        else:
            self._init_empty_stats()
    
    def _init_empty_stats(self):
        """Initialize empty statistics."""
        self.users = set()
        self.groups = set()
        self.total_quizzes_generated = 0
        self.total_questions_sent = 0
        self.start_time = datetime.now().isoformat()
    
    def save_stats(self):
        """Save statistics to JSON file."""
        try:
            data = {
                'users': list(self.users),
                'groups': list(self.groups),
                'total_quizzes_generated': self.total_quizzes_generated,
                'total_questions_sent': self.total_questions_sent,
                'start_time': self.start_time,
                'last_updated': datetime.now().isoformat()
            }
            with open(STATS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving stats: {e}")
    
    def add_user(self, user_id: int):
        """Add a user to statistics."""
        if user_id not in self.users:
            self.users.add(user_id)
            self.save_stats()
    
    def add_group(self, group_id: int):
        """Add a group to statistics."""
        if group_id not in self.groups:
            self.groups.add(group_id)
            self.save_stats()
    
    def record_quiz(self, num_questions: int):
        """Record a quiz generation."""
        self.total_quizzes_generated += 1
        self.total_questions_sent += num_questions
        self.save_stats()
    
    def get_stats(self) -> Dict:
        """Get all statistics."""
        return {
            'total_users': len(self.users),
            'total_groups': len(self.groups),
            'total_quizzes': self.total_quizzes_generated,
            'total_questions': self.total_questions_sent,
            'start_time': self.start_time,
            'users_list': list(self.users),
            'groups_list': list(self.groups)
        }

stats_manager = StatsManager()
