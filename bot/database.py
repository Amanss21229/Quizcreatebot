import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    """PostgreSQL database connection manager for NEET Quiz Bot."""
    
    def __init__(self):
        self.connection_pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL environment variable is required")
            
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=database_url
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}", exc_info=True)
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def execute_query(self, query: str, params: tuple = None, fetch_one=False, fetch_all=False):
        """Execute a SQL query and optionally fetch results."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                if fetch_one:
                    result = cursor.fetchone()
                    return dict(result) if result else None
                elif fetch_all:
                    return [dict(row) for row in cursor.fetchall()]
                return cursor.rowcount
    
    # Language Settings
    def get_language(self, chat_id: int) -> str:
        """Get language preference for a chat."""
        query = "SELECT language FROM language_settings WHERE chat_id = %s"
        result = self.execute_query(query, (chat_id,), fetch_one=True)
        return result['language'] if result else 'english'
    
    def set_language(self, chat_id: int, language: str):
        """Set language preference for a chat."""
        query = """
            INSERT INTO language_settings (chat_id, language, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (chat_id) 
            DO UPDATE SET language = EXCLUDED.language, updated_at = NOW()
        """
        self.execute_query(query, (chat_id, language))
    
    # Welcome Groups
    def is_welcome_enabled(self, group_id: int) -> bool:
        """Check if welcome messages are enabled for a group."""
        query = "SELECT enabled FROM welcome_groups WHERE group_id = %s"
        result = self.execute_query(query, (group_id,), fetch_one=True)
        return result['enabled'] if result else False
    
    def enable_welcome(self, group_id: int, message: str = None) -> bool:
        """Enable welcome messages for a group."""
        query = """
            INSERT INTO welcome_groups (group_id, welcome_message, enabled, updated_at)
            VALUES (%s, %s, TRUE, NOW())
            ON CONFLICT (group_id)
            DO UPDATE SET enabled = TRUE, updated_at = NOW()
            RETURNING enabled
        """
        result = self.execute_query(query, (group_id, message), fetch_one=True)
        return result is not None
    
    def disable_welcome(self, group_id: int) -> bool:
        """Disable welcome messages for a group."""
        query = """
            UPDATE welcome_groups 
            SET enabled = FALSE, updated_at = NOW()
            WHERE group_id = %s
            RETURNING enabled
        """
        result = self.execute_query(query, (group_id,), fetch_one=True)
        return result is not None
    
    # Tagall Permissions
    def get_tagall_permission(self, group_id: int) -> str:
        """Get tagall permission level for a group."""
        query = "SELECT permission_level FROM tagall_permissions WHERE group_id = %s"
        result = self.execute_query(query, (group_id,), fetch_one=True)
        return result['permission_level'] if result else 'admin'
    
    def set_tagall_permission(self, group_id: int, permission_level: str):
        """Set tagall permission level for a group."""
        query = """
            INSERT INTO tagall_permissions (group_id, permission_level, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (group_id)
            DO UPDATE SET permission_level = EXCLUDED.permission_level, updated_at = NOW()
        """
        self.execute_query(query, (group_id, permission_level))
    
    # Tracked Members
    def track_member(self, group_id: int, user_id: int, first_name: str, username: str = None, is_admin: bool = False):
        """Track or update a member in a group."""
        query = """
            INSERT INTO tracked_members (group_id, user_id, first_name, username, is_admin, last_seen)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (group_id, user_id)
            DO UPDATE SET 
                first_name = EXCLUDED.first_name,
                username = EXCLUDED.username,
                is_admin = EXCLUDED.is_admin,
                last_seen = NOW()
        """
        self.execute_query(query, (group_id, user_id, first_name, username, is_admin))
    
    def get_group_members(self, group_id: int) -> List[Dict]:
        """Get all tracked members for a group."""
        query = "SELECT * FROM tracked_members WHERE group_id = %s ORDER BY last_seen DESC"
        return self.execute_query(query, (group_id,), fetch_all=True)
    
    # Bot Statistics
    def get_bot_stats(self) -> Dict:
        """Get bot statistics."""
        query = "SELECT * FROM bot_stats LIMIT 1"
        result = self.execute_query(query, fetch_one=True)
        return result if result else {}
    
    def increment_stat(self, stat_name: str, increment: int = 1):
        """Increment a bot statistic."""
        query = f"""
            UPDATE bot_stats 
            SET {stat_name} = {stat_name} + %s, last_updated = NOW()
            WHERE id = 1
        """
        self.execute_query(query, (increment,))
    
    def add_user(self, user_id: int, first_name: str = None, username: str = None):
        """Add or update a user."""
        # First check if user exists
        check_query = "SELECT user_id FROM bot_users WHERE user_id = %s"
        exists = self.execute_query(check_query, (user_id,), fetch_one=True)
        
        if not exists:
            # New user
            query = """
                INSERT INTO bot_users (user_id, first_name, username, first_seen, last_seen)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (user_id) DO NOTHING
            """
            rows_affected = self.execute_query(query, (user_id, first_name, username))
            if rows_affected > 0:
                self.increment_stat('total_users')
        else:
            # Update existing user
            query = """
                UPDATE bot_users
                SET first_name = %s, username = %s, last_seen = NOW()
                WHERE user_id = %s
            """
            self.execute_query(query, (first_name, username, user_id))
    
    def add_group(self, group_id: int, group_name: str = None):
        """Add or update a group."""
        # First check if group exists
        check_query = "SELECT group_id FROM bot_groups WHERE group_id = %s"
        exists = self.execute_query(check_query, (group_id,), fetch_one=True)
        
        if not exists:
            # New group
            query = """
                INSERT INTO bot_groups (group_id, group_name, first_added, last_active)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (group_id) DO NOTHING
            """
            rows_affected = self.execute_query(query, (group_id, group_name))
            if rows_affected > 0:
                self.increment_stat('total_groups')
        else:
            # Update existing group
            query = """
                UPDATE bot_groups
                SET group_name = %s, last_active = NOW()
                WHERE group_id = %s
            """
            self.execute_query(query, (group_name, group_id))
    
    def get_all_groups(self) -> List[int]:
        """Get all active group IDs."""
        query = "SELECT group_id FROM bot_groups WHERE is_active = TRUE"
        results = self.execute_query(query, fetch_all=True)
        return [row['group_id'] for row in results]
    
    def record_quiz(self, questions_count: int):
        """Record a quiz generation."""
        self.increment_stat('total_quizzes_generated')
        self.increment_stat('total_questions_sent', questions_count)
    
    def close(self):
        """Close all database connections."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed")


# Global database instance
db = Database()
