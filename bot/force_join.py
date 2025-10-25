import json
import os
import logging
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

FORCE_JOIN_FILE = 'force_join_data.json'
MAX_FORCE_JOIN_GROUPS = 5

class ForceJoinManager:
    def __init__(self):
        self.force_join_groups: List[Dict[str, str]] = []
        self.load_force_join_data()
    
    def load_force_join_data(self):
        """Load force join data from JSON file."""
        if os.path.exists(FORCE_JOIN_FILE):
            try:
                with open(FORCE_JOIN_FILE, 'r') as f:
                    data = json.load(f)
                    self.force_join_groups = data.get('groups', [])
                logger.info(f"Loaded {len(self.force_join_groups)} force join groups")
            except Exception as e:
                logger.error(f"Error loading force join data: {e}")
                self.force_join_groups = []
        else:
            self.force_join_groups = []
    
    def save_force_join_data(self):
        """Save force join data to JSON file."""
        try:
            with open(FORCE_JOIN_FILE, 'w') as f:
                json.dump({'groups': self.force_join_groups}, f, indent=2)
            logger.info(f"Saved {len(self.force_join_groups)} force join groups")
        except Exception as e:
            logger.error(f"Error saving force join data: {e}")
    
    def add_force_join(self, chat_id: str, invite_link: str, chat_title: str = None) -> bool:
        """Add a group/channel to force join list."""
        if len(self.force_join_groups) >= MAX_FORCE_JOIN_GROUPS:
            return False
        
        # Check if already exists
        for group in self.force_join_groups:
            if group['chat_id'] == chat_id:
                return False
        
        self.force_join_groups.append({
            'chat_id': chat_id,
            'invite_link': invite_link,
            'title': chat_title or f"Group/Channel {chat_id}"
        })
        self.save_force_join_data()
        return True
    
    def remove_force_join(self, identifier: str) -> bool:
        """Remove a group/channel from force join list by chat_id or invite_link."""
        original_length = len(self.force_join_groups)
        self.force_join_groups = [
            group for group in self.force_join_groups 
            if group['chat_id'] != identifier and group['invite_link'] != identifier
        ]
        
        if len(self.force_join_groups) < original_length:
            self.save_force_join_data()
            return True
        return False
    
    def get_force_join_groups(self) -> List[Dict[str, str]]:
        """Get all force join groups."""
        return self.force_join_groups
    
    async def check_user_membership(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> tuple[bool, List[Dict]]:
        """
        Check if user is a member of all force join groups.
        Returns (is_member_of_all, list_of_not_joined_groups)
        """
        if not self.force_join_groups:
            return True, []
        
        not_joined = []
        
        for group in self.force_join_groups:
            try:
                chat_id = group['chat_id']
                member = await context.bot.get_chat_member(chat_id, user_id)
                
                # Check if user is a member (not left, not kicked)
                if member.status in ['left', 'kicked']:
                    not_joined.append(group)
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if it's a permission error
                if 'bot is not a member' in error_msg or 'forbidden' in error_msg or 'not enough rights' in error_msg:
                    logger.critical(
                        f"Bot lacks permissions to check membership in {group['title']} (ID: {chat_id}). "
                        f"Please make the bot an admin in this group/channel. Error: {e}"
                    )
                    # Don't block users due to bot permission issues - log and skip
                    continue
                else:
                    logger.warning(f"Error checking membership for {group['title']} ({chat_id}): {e}")
                    # For other errors, assume user hasn't joined
                    not_joined.append(group)
        
        return len(not_joined) == 0, not_joined
    
    def create_join_buttons(self, not_joined_groups: List[Dict]) -> InlineKeyboardMarkup:
        """Create inline keyboard with join buttons for groups/channels."""
        keyboard = []
        
        for group in not_joined_groups:
            keyboard.append([
                InlineKeyboardButton(
                    f"📢 Join {group['title']}", 
                    url=group['invite_link']
                )
            ])
        
        # Add check membership button
        keyboard.append([
            InlineKeyboardButton(
                "✅ I Joined - Check Again", 
                callback_data="check_membership"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)

force_join_manager = ForceJoinManager()
