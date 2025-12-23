"""
Redis Service for Session Management
Handles conversation storage, context management, and session lifecycle
"""

import redis
import json
import uuid
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RedisService:
    """Service for managing chat sessions and conversation context using Redis"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        password: str = None,
        session_ttl: int = None
    ):
        """
        Initialize Redis connection
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if required)
            session_ttl: Session time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port or int(os.getenv("REDIS_PORT", "6379"))
        self.db = db or int(os.getenv("REDIS_DB", "0"))
        self.password = password or os.getenv("REDIS_PASSWORD", None)
        self.session_ttl = session_ttl or int(os.getenv("SESSION_TTL", "3600"))
        
        logger.info(f"Initializing Redis connection: {self.host}:{self.port}")
        
        try:
            # Create Redis client
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password if self.password else None,
                decode_responses=True,  # Automatically decode bytes to strings
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.client.ping()
            logger.info("✅ Redis connection established")
            
        except redis.ConnectionError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Redis initialization error: {e}")
            raise
    
    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    def generate_session_id(self) -> str:
        """
        Generate a new unique session ID
        
        Returns:
            UUID string for the session
        """
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id}")
        return session_id
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists
        
        Args:
            session_id: Session ID to check
            
        Returns:
            True if session exists, False otherwise
        """
        key = f"session:{session_id}"
        exists = self.client.exists(key) > 0
        logger.debug(f"Session {session_id} exists: {exists}")
        return exists
    
    def create_session(self, session_id: str, metadata: Dict = None) -> bool:
        """
        Create a new session
        
        Args:
            session_id: Session ID
            metadata: Optional metadata for the session
            
        Returns:
            True if created successfully
        """
        try:
            key = f"session:{session_id}"
            
            session_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "message_count": 0,
                "metadata": metadata or {}
            }
            
            self.client.setex(
                key,
                self.session_ttl,
                json.dumps(session_data)
            )
            
            logger.info(f"Created session: {session_id} (TTL: {self.session_ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session data
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data dictionary or None if not found
        """
        try:
            key = f"session:{session_id}"
            data = self.client.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    def update_session_activity(self, session_id: str):
        """
        Update the last activity timestamp for a session
        
        Args:
            session_id: Session ID
        """
        try:
            session_data = self.get_session(session_id)
            if session_data:
                session_data["last_activity"] = datetime.now().isoformat()
                
                key = f"session:{session_id}"
                self.client.setex(
                    key,
                    self.session_ttl,
                    json.dumps(session_data)
                )
                logger.debug(f"Updated session activity: {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its messages
        
        Args:
            session_id: Session ID
            
        Returns:
            True if deleted successfully
        """
        try:
            # Delete session data
            session_key = f"session:{session_id}"
            messages_key = f"messages:{session_id}"
            
            self.client.delete(session_key)
            self.client.delete(messages_key)
            
            logger.info(f"Deleted session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    # ========================================================================
    # MESSAGE MANAGEMENT
    # ========================================================================
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> bool:
        """
        Add a message to the conversation history
        
        Args:
            session_id: Session ID
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata (sources, etc.)
            
        Returns:
            True if added successfully
        """
        try:
            key = f"messages:{session_id}"
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Add to list
            self.client.rpush(key, json.dumps(message))
            
            # Set TTL on messages list
            self.client.expire(key, self.session_ttl)
            
            # Update session message count
            session_data = self.get_session(session_id)
            if session_data:
                session_data["message_count"] = session_data.get("message_count", 0) + 1
                session_key = f"session:{session_id}"
                self.client.setex(
                    session_key,
                    self.session_ttl,
                    json.dumps(session_data)
                )
            
            logger.debug(f"Added {role} message to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            return False
    
    def get_messages(
        self,
        session_id: str,
        limit: int = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get conversation history
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to return (None = all)
            offset: Number of messages to skip from the start
            
        Returns:
            List of message dictionaries
        """
        try:
            key = f"messages:{session_id}"
            
            # Get messages from list
            if limit:
                end = offset + limit - 1
                messages_json = self.client.lrange(key, offset, end)
            else:
                messages_json = self.client.lrange(key, offset, -1)
            
            # Parse JSON
            messages = [json.loads(msg) for msg in messages_json]
            
            logger.debug(f"Retrieved {len(messages)} messages for session {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def get_recent_context(
        self,
        session_id: str,
        num_messages: int = 10
    ) -> str:
        """
        Get recent conversation context as a formatted string
        
        Args:
            session_id: Session ID
            num_messages: Number of recent messages to include
            
        Returns:
            Formatted conversation context
        """
        try:
            messages = self.get_messages(session_id)
            
            # Get last N messages
            recent_messages = messages[-num_messages:] if len(messages) > num_messages else messages
            
            # Format as context
            context_parts = []
            for msg in recent_messages:
                role = msg["role"].capitalize()
                content = msg["content"]
                context_parts.append(f"{role}: {content}")
            
            context = "\n".join(context_parts)
            logger.debug(f"Built context from {len(recent_messages)} messages")
            return context
            
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return ""
    
    def get_message_count(self, session_id: str) -> int:
        """
        Get the number of messages in a session
        
        Args:
            session_id: Session ID
            
        Returns:
            Number of messages
        """
        try:
            key = f"messages:{session_id}"
            count = self.client.llen(key)
            return count
        except Exception as e:
            logger.error(f"Failed to get message count: {e}")
            return 0
    
    def clear_messages(self, session_id: str) -> bool:
        """
        Clear all messages in a session (keep session alive)
        
        Args:
            session_id: Session ID
            
        Returns:
            True if cleared successfully
        """
        try:
            key = f"messages:{session_id}"
            self.client.delete(key)
            
            # Reset message count in session
            session_data = self.get_session(session_id)
            if session_data:
                session_data["message_count"] = 0
                session_key = f"session:{session_id}"
                self.client.setex(
                    session_key,
                    self.session_ttl,
                    json.dumps(session_data)
                )
            
            logger.info(f"Cleared messages for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear messages: {e}")
            return False
    
    # ========================================================================
    # STATISTICS & MANAGEMENT
    # ========================================================================
    
    def get_all_sessions(self) -> List[str]:
        """
        Get all active session IDs
        
        Returns:
            List of session IDs
        """
        try:
            # Scan for all session keys
            session_keys = []
            cursor = 0
            
            while True:
                cursor, keys = self.client.scan(
                    cursor=cursor,
                    match="session:*",
                    count=100
                )
                session_keys.extend(keys)
                
                if cursor == 0:
                    break
            
            # Extract session IDs
            session_ids = [key.split(":")[1] for key in session_keys]
            
            logger.info(f"Found {len(session_ids)} active sessions")
            return session_ids
            
        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """
        Get Redis statistics
        
        Returns:
            Dictionary with statistics
        """
        try:
            info = self.client.info()
            sessions = self.get_all_sessions()
            
            total_messages = 0
            for session_id in sessions:
                total_messages += self.get_message_count(session_id)
            
            stats = {
                "connected": True,
                "active_sessions": len(sessions),
                "total_messages": total_messages,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0)
            }
            
            logger.info(f"Redis stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"connected": False, "error": str(e)}
    
    def health_check(self) -> bool:
        """
        Check if Redis is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def close(self):
        """Close Redis connection"""
        try:
            self.client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Utility function
def get_redis_service() -> RedisService:
    """Factory function to get RedisService instance"""
    return RedisService()