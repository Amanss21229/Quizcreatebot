import os
import asyncpg
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class DatabasePool:
    """Manages PostgreSQL connection pool using asyncpg."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize the connection pool."""
        try:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable not set")
            
            self.pool = await asyncpg.create_pool(
                database_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
                max_queries=50000,
                max_inactive_connection_lifetime=300
            )
            
            logger.info("✅ Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

db_pool = DatabasePool()

class QuizSessionRepository:
    """Repository for managing global quiz sessions in database with 1-hour retention."""
    
    def __init__(self, pool: DatabasePool):
        self.pool = pool
    
    async def get_next_quiz_id(self) -> str:
        """Get and increment the quiz ID counter."""
        try:
            query = """
                UPDATE quiz_id_counter 
                SET counter = counter + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                RETURNING counter
            """
            async with self.pool.pool.acquire() as conn:
                counter = await conn.fetchval(query)
            
            quiz_id = f"GQ{counter:04d}"
            logger.info(f"Generated new quiz ID: {quiz_id}")
            return quiz_id
            
        except Exception as e:
            logger.error(f"Error generating quiz ID: {e}", exc_info=True)
            raise
    
    async def save_quiz_session(
        self,
        quiz_id: str,
        question_count: int,
        time_per_question: int,
        quiz_data: Dict[str, Any],
        participants: List[Dict[str, Any]],
        groups: List[Dict[str, Any]]
    ) -> bool:
        """Save a completed quiz session to database with 1-hour expiry."""
        try:
            async with self.pool.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT INTO global_quiz_sessions 
                        (quiz_id, question_count, time_per_question, total_participants, quiz_data, completed_at, expires_at)
                        VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '1 hour')
                        ON CONFLICT (quiz_id) DO UPDATE SET
                            total_participants = EXCLUDED.total_participants,
                            quiz_data = EXCLUDED.quiz_data,
                            completed_at = CURRENT_TIMESTAMP,
                            expires_at = CURRENT_TIMESTAMP + INTERVAL '1 hour'
                        """,
                        quiz_id, question_count, time_per_question, len(participants), json.dumps(quiz_data)
                    )
                    
                    for participant in participants:
                        await conn.execute(
                            """
                            INSERT INTO quiz_participants 
                            (quiz_id, user_id, user_name, score, correct_answers, wrong_answers, unattempted)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            quiz_id,
                            participant['user_id'],
                            participant['user_name'],
                            participant['score'],
                            participant['correct'],
                            participant['wrong'],
                            participant['unattempted']
                        )
                    
                    for group in groups:
                        await conn.execute(
                            """
                            INSERT INTO quiz_group_results 
                            (quiz_id, group_id, group_name, participant_count)
                            VALUES ($1, $2, $3, $4)
                            """,
                            quiz_id,
                            group['group_id'],
                            group['group_name'],
                            group['participant_count']
                        )
            
            logger.info(f"✅ Saved quiz session {quiz_id} to database (expires in 1 hour)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving quiz session {quiz_id}: {e}", exc_info=True)
            return False
    
    async def get_quiz_session(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a quiz session by ID if it hasn't expired (within 1 hour)."""
        try:
            async with self.pool.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT quiz_id, question_count, time_per_question, total_participants, 
                           quiz_data, completed_at, expires_at
                    FROM global_quiz_sessions
                    WHERE quiz_id = $1 AND expires_at > CURRENT_TIMESTAMP
                    """,
                    quiz_id
                )
                
                if not row:
                    logger.warning(f"Quiz session {quiz_id} not found or expired")
                    return None
                
                participants = await conn.fetch(
                    """
                    SELECT user_id, user_name, score, correct_answers, wrong_answers, unattempted
                    FROM quiz_participants
                    WHERE quiz_id = $1
                    ORDER BY score DESC, correct_answers DESC
                    """,
                    quiz_id
                )
                
                groups = await conn.fetch(
                    """
                    SELECT group_id, group_name, participant_count
                    FROM quiz_group_results
                    WHERE quiz_id = $1
                    """,
                    quiz_id
                )
            
            return {
                'quiz_id': row['quiz_id'],
                'question_count': row['question_count'],
                'time_per_question': row['time_per_question'],
                'total_participants': row['total_participants'],
                'quiz_data': json.loads(row['quiz_data']),
                'completed_at': row['completed_at'],
                'expires_at': row['expires_at'],
                'participants': [
                    {
                        'user_id': p['user_id'],
                        'user_name': p['user_name'],
                        'score': p['score'],
                        'correct': p['correct_answers'],
                        'wrong': p['wrong_answers'],
                        'unattempted': p['unattempted']
                    }
                    for p in participants
                ],
                'groups': [
                    {
                        'group_id': g['group_id'],
                        'group_name': g['group_name'],
                        'participant_count': g['participant_count']
                    }
                    for g in groups
                ]
            }
            
        except Exception as e:
            logger.error(f"Error retrieving quiz session {quiz_id}: {e}", exc_info=True)
            return None
    
    async def cleanup_expired_sessions(self) -> int:
        """Delete quiz sessions older than 1 hour."""
        try:
            async with self.pool.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM global_quiz_sessions WHERE expires_at < CURRENT_TIMESTAMP"
                )
            
            deleted_count = int(result.split()[-1]) if result else 0
            
            if deleted_count > 0:
                logger.info(f"🗑️ Cleaned up {deleted_count} expired quiz sessions")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}", exc_info=True)
            return 0
    
    async def list_active_sessions(self) -> List[str]:
        """List all active (non-expired) quiz IDs."""
        try:
            async with self.pool.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT quiz_id, completed_at
                    FROM global_quiz_sessions
                    WHERE expires_at > CURRENT_TIMESTAMP
                    ORDER BY completed_at DESC
                    """
                )
            
            return [row['quiz_id'] for row in rows]
            
        except Exception as e:
            logger.error(f"Error listing active sessions: {e}", exc_info=True)
            return []

class StatsRepository:
    """Repository for managing bot statistics."""
    
    def __init__(self, pool: DatabasePool):
        self.pool = pool
    
    async def increment_stat(self, stat_name: str, increment: int = 1):
        """Increment a bot statistic."""
        try:
            query = f"""
                UPDATE bot_stats 
                SET {stat_name} = {stat_name} + $1, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """
            async with self.pool.pool.acquire() as conn:
                await conn.execute(query, increment)
        except Exception as e:
            logger.error(f"Error incrementing stat {stat_name}: {e}", exc_info=True)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get global bot statistics."""
        try:
            async with self.pool.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM bot_stats WHERE id = 1")
            
            if row:
                return dict(row)
            return {}
        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {}
    
    async def track_user(self, user_id: int, username: str = None):
        """Track user activity."""
        try:
            async with self.pool.pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT user_id FROM user_stats WHERE user_id = $1",
                    user_id
                )
                
                if not result:
                    await conn.execute(
                        """
                        INSERT INTO user_stats (user_id, username, quiz_count)
                        VALUES ($1, $2, 0)
                        """,
                        user_id, username
                    )
                    await self.increment_stat('total_users')
                else:
                    await conn.execute(
                        """
                        UPDATE user_stats
                        SET username = $2, last_seen = CURRENT_TIMESTAMP
                        WHERE user_id = $1
                        """,
                        user_id, username
                    )
        except Exception as e:
            logger.error(f"Error tracking user {user_id}: {e}", exc_info=True)
    
    async def track_group(self, group_id: int, group_name: str = None):
        """Track group activity."""
        try:
            async with self.pool.pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT group_id FROM group_stats WHERE group_id = $1",
                    group_id
                )
                
                if not result:
                    await conn.execute(
                        """
                        INSERT INTO group_stats (group_id, group_name, quiz_count)
                        VALUES ($1, $2, 0)
                        """,
                        group_id, group_name
                    )
                    await self.increment_stat('total_groups')
                else:
                    await conn.execute(
                        """
                        UPDATE group_stats
                        SET group_name = $2, last_seen = CURRENT_TIMESTAMP
                        WHERE group_id = $1
                        """,
                        group_id, group_name
                    )
        except Exception as e:
            logger.error(f"Error tracking group {group_id}: {e}", exc_info=True)
    
    async def increment_user_quiz_count(self, user_id: int):
        """Increment quiz count for a user."""
        try:
            async with self.pool.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE user_stats
                    SET quiz_count = quiz_count + 1
                    WHERE user_id = $1
                    """,
                    user_id
                )
        except Exception as e:
            logger.error(f"Error incrementing user quiz count: {e}", exc_info=True)
    
    async def increment_group_quiz_count(self, group_id: int):
        """Increment quiz count for a group."""
        try:
            async with self.pool.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE group_stats
                    SET quiz_count = quiz_count + 1
                    WHERE group_id = $1
                    """,
                    group_id
                )
        except Exception as e:
            logger.error(f"Error incrementing group quiz count: {e}", exc_info=True)

quiz_session_repo = QuizSessionRepository(db_pool)
stats_repo = StatsRepository(db_pool)
