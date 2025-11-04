#!/usr/bin/env python3
"""
Migration script to transfer data from JSON files to PostgreSQL database.
Run this once to migrate existing data.
"""

import json
import os
import logging
from datetime import datetime
from bot.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_bot_stats():
    """Migrate bot statistics from JSON to database."""
    try:
        with open('bot_stats.json', 'r') as f:
            stats = json.load(f)
        
        # Migrate users
        users = stats.get('users', [])
        for user_id in users:
            db.add_user(user_id)
        logger.info(f"Migrated {len(users)} users")
        
        # Migrate groups
        groups = stats.get('groups', [])
        for group_id in groups:
            db.add_group(group_id)
        logger.info(f"Migrated {len(groups)} groups")
        
        # Update stats
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE bot_stats 
                    SET total_quizzes_generated = %s,
                        total_questions_sent = %s,
                        start_time = %s,
                        last_updated = %s
                    WHERE id = 1
                """, (
                    stats.get('total_quizzes_generated', 0),
                    stats.get('total_questions_sent', 0),
                    datetime.fromisoformat(stats.get('start_time', datetime.now().isoformat())),
                    datetime.fromisoformat(stats.get('last_updated', datetime.now().isoformat()))
                ))
        
        logger.info("Bot stats migrated successfully")
        return True
    except Exception as e:
        logger.error(f"Error migrating bot stats: {e}", exc_info=True)
        return False

def migrate_language_settings():
    """Migrate language settings from JSON to database."""
    try:
        file_path = 'data/language_settings.json'
        if not os.path.exists(file_path):
            logger.info("No language_settings.json file found")
            return True
        
        with open(file_path, 'r') as f:
            settings = json.load(f)
        
        count = 0
        for chat_id_str, language in settings.items():
            chat_id = int(chat_id_str)
            db.set_language(chat_id, language)
            count += 1
        
        logger.info(f"Migrated {count} language settings")
        return True
    except Exception as e:
        logger.error(f"Error migrating language settings: {e}", exc_info=True)
        return False

def migrate_welcome_groups():
    """Migrate welcome groups from JSON to database."""
    try:
        file_path = 'data/welcome_groups.json'
        if not os.path.exists(file_path):
            logger.info("No welcome_groups.json file found")
            return True
        
        with open(file_path, 'r') as f:
            groups = json.load(f)
        
        count = 0
        for group_id_str in groups:
            group_id = int(group_id_str)
            db.enable_welcome(group_id)
            count += 1
        
        logger.info(f"Migrated {count} welcome groups")
        return True
    except Exception as e:
        logger.error(f"Error migrating welcome groups: {e}", exc_info=True)
        return False

def migrate_tagall_permissions():
    """Migrate tagall permissions from JSON to database."""
    try:
        file_path = 'data/tagall_permissions.json'
        if not os.path.exists(file_path):
            logger.info("No tagall_permissions.json file found")
            return True
        
        with open(file_path, 'r') as f:
            permissions = json.load(f)
        
        count = 0
        for group_id_str, permission_level in permissions.items():
            group_id = int(group_id_str)
            db.set_tagall_permission(group_id, permission_level)
            count += 1
        
        logger.info(f"Migrated {count} tagall permission settings")
        return True
    except Exception as e:
        logger.error(f"Error migrating tagall permissions: {e}", exc_info=True)
        return False

def migrate_tracked_members():
    """Migrate tracked members from JSON to database."""
    try:
        file_path = 'data/tracked_members.json'
        if not os.path.exists(file_path):
            logger.info("No tracked_members.json file found")
            return True
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        count = 0
        for group_id_str, user_dict in data.items():
            group_id = int(group_id_str)
            # user_dict is a dictionary where keys are user IDs and values are member data
            for user_id_str, member in user_dict.items():
                db.track_member(
                    group_id=group_id,
                    user_id=member['user_id'],
                    first_name=member.get('first_name', 'Unknown'),
                    username=member.get('username'),
                    is_admin=member.get('is_admin', False)
                )
                count += 1
        
        logger.info(f"Migrated {count} tracked members")
        return True
    except Exception as e:
        logger.error(f"Error migrating tracked members: {e}", exc_info=True)
        return False

def migrate_force_join_groups():
    """Migrate force join groups from JSON to database."""
    try:
        file_path = 'force_join_data.json'
        if not os.path.exists(file_path):
            logger.info("No force_join_data.json file found")
            return True
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        groups = data.get('groups', [])
        count = 0
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                for group in groups:
                    cursor.execute("""
                        INSERT INTO force_join_groups (chat_id, invite_link, title, added_at, is_active)
                        VALUES (%s, %s, %s, NOW(), TRUE)
                        ON CONFLICT (chat_id) DO NOTHING
                    """, (
                        int(group['chat_id']),
                        group.get('invite_link'),
                        group.get('title')
                    ))
                    count += 1
        
        logger.info(f"Migrated {count} force join groups")
        return True
    except Exception as e:
        logger.error(f"Error migrating force join groups: {e}", exc_info=True)
        return False

def main():
    """Run all migrations."""
    logger.info("=" * 50)
    logger.info("Starting data migration from JSON to PostgreSQL")
    logger.info("=" * 50)
    
    migrations = [
        ("Bot Statistics", migrate_bot_stats),
        ("Language Settings", migrate_language_settings),
        ("Welcome Groups", migrate_welcome_groups),
        ("Tagall Permissions", migrate_tagall_permissions),
        ("Tracked Members", migrate_tracked_members),
        ("Force Join Groups", migrate_force_join_groups),
    ]
    
    results = {}
    for name, migration_func in migrations:
        logger.info(f"\nMigrating {name}...")
        results[name] = migration_func()
    
    logger.info("\n" + "=" * 50)
    logger.info("Migration Summary:")
    logger.info("=" * 50)
    for name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"{name}: {status}")
    
    all_success = all(results.values())
    if all_success:
        logger.info("\n🎉 All migrations completed successfully!")
        logger.info("\nYou can now safely delete the JSON files:")
        logger.info("  - bot_stats.json")
        logger.info("  - force_join_data.json")
        logger.info("  - data/language_settings.json")
        logger.info("  - data/welcome_groups.json")
        logger.info("  - data/tagall_permissions.json")
        logger.info("  - data/tracked_members.json")
    else:
        logger.error("\n⚠️ Some migrations failed. Please check the errors above.")
    
    return all_success

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
