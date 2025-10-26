import uuid
import time
import logging
from typing import Dict, Callable, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class AnonymousAdminVerifier:
    def __init__(self, timeout_seconds=300):  # 5 minutes timeout
        self.pending_commands: Dict[str, Dict[str, Any]] = {}
        self.timeout_seconds = timeout_seconds
    
    def _cleanup_expired(self):
        """Remove expired pending commands."""
        current_time = time.time()
        expired_tokens = [
            token for token, data in self.pending_commands.items()
            if current_time - data['timestamp'] > self.timeout_seconds
        ]
        for token in expired_tokens:
            del self.pending_commands[token]
            logger.info(f"Removed expired verification token: {token[:8]}...")
    
    def is_anonymous_admin(self, update: Update) -> bool:
        """Check if the message sender is an anonymous admin."""
        if not update.message:
            return False
        
        message = update.message
        
        # Anonymous admins have sender_chat set to the group chat
        # and the user might be the group itself
        if message.sender_chat and message.sender_chat.id == message.chat.id:
            # This is an anonymous admin
            return True
        
        return False
    
    async def require_verification(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command_name: str,
        command_handler: Callable,
        command_args: list = None
    ) -> bool:
        """
        Require verification for anonymous admin.
        Returns True if command was queued for verification, False otherwise.
        """
        self._cleanup_expired()
        
        chat = update.effective_chat
        message = update.message
        
        # Generate secure token
        token = str(uuid.uuid4())
        
        # Store pending command
        self.pending_commands[token] = {
            'chat_id': chat.id,
            'chat_title': chat.title,
            'command_name': command_name,
            'command_handler': command_handler,
            'command_args': command_args or [],
            'message_text': message.text,
            'timestamp': time.time(),
            'update': update,
            'context': context,
            'sender_chat_id': message.sender_chat.id if message.sender_chat else None
        }
        
        logger.info(f"Created verification token for anonymous admin in {chat.title}: {token[:8]}...")
        
        # Try to send private message with verification button
        # For anonymous admins, we need to handle this carefully
        # The bot can't directly message the anonymous admin
        # Instead, we'll prompt them in the group to verify
        
        keyboard = [[InlineKeyboardButton("✅ Verify & Execute", callback_data=f"verify:{token}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔐 **Anonymous Admin Verification Required**\n\n"
            f"Since you're posting as the group, I need to verify you're an admin.\n\n"
            f"**Command:** `{command_name}`\n"
            f"**Group:** {chat.title}\n\n"
            f"Click the button below to verify and execute this command:\n\n"
            f"⏰ This verification will expire in 5 minutes.",
            reply_markup=reply_markup
        )
        
        return True
    
    async def verify_and_execute(
        self,
        query,
        user_id: int,
        token: str,
        bot
    ) -> bool:
        """
        Verify the admin status and execute the pending command.
        Returns True if verification succeeded, False otherwise.
        """
        self._cleanup_expired()
        
        # Check if token exists
        if token not in self.pending_commands:
            await query.answer("❌ Verification expired or invalid!", show_alert=True)
            return False
        
        pending = self.pending_commands[token]
        chat_id = pending['chat_id']
        chat_title = pending['chat_title']
        command_name = pending['command_name']
        
        try:
            # Verify user is actually an admin in that group
            member = await bot.get_chat_member(chat_id, user_id)
            
            if member.status not in ['creator', 'administrator']:
                await query.answer("❌ You are not an admin in this group!", show_alert=True)
                del self.pending_commands[token]
                return False
            
            # Admin verified! Execute the command
            logger.info(f"Anonymous admin verified for {command_name} in {chat_title}")
            
            await query.answer("✅ Verified! Executing command...", show_alert=False)
            
            # Execute the stored command handler
            command_handler = pending['command_handler']
            update = pending['update']
            context = pending['context']
            
            # Update the effective user to the verified user (from callback query)
            # This is a workaround to make the command think it came from the verified user
            if update.message and query.from_user:
                update.message._unfreeze()
                update._effective_user = query.from_user
                update.message.from_user = query.from_user
                update.message._freeze()
            
            # Execute the command
            await command_handler(update, context)
            
            # Edit the verification message
            await query.edit_message_text(
                f"✅ **Verification Successful!**\n\n"
                f"Command `{command_name}` has been executed in **{chat_title}**.\n\n"
                f"【~@DrQuizRobot】"
            )
            
            # Remove from pending
            del self.pending_commands[token]
            return True
            
        except Exception as e:
            logger.error(f"Error during verification: {e}")
            await query.answer("❌ Verification failed!", show_alert=True)
            if token in self.pending_commands:
                del self.pending_commands[token]
            return False

# Global instance
anonymous_verifier = AnonymousAdminVerifier()
