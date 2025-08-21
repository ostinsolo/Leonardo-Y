"""
Leonardo Memory Storage Backends
Implements SQLite and JSONL storage for the three-tier memory system
"""

import json
import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

from ..config import LeonardoConfig


class BaseMemoryStore:
    """Base class for memory storage backends."""
    
    def __init__(self, config: LeonardoConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize the storage backend."""
        raise NotImplementedError
    
    def get_recent_turns(self, user_id: str, n: int = 8) -> List[Dict]:
        """Get the last N conversation turns."""
        raise NotImplementedError
    
    def append_turn(self, user_id: str, turn: Dict) -> None:
        """Append a new turn to memory."""
        raise NotImplementedError
    
    def search_episodes(self, user_id: str, query: str, k: int = 5) -> List[Dict]:
        """Search episodic memory for relevant past interactions."""
        raise NotImplementedError
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile and preferences."""
        raise NotImplementedError
    
    def rollup_summaries(self, user_id: str) -> None:
        """Create summaries of old conversations."""
        raise NotImplementedError


class SQLiteMemoryStore(BaseMemoryStore):
    """SQLite-based memory store for production use."""
    
    def __init__(self, config: LeonardoConfig):
        super().__init__(config)
        self.db_path = Path("leonardo_memory.db")
        self.connection = None
        
    async def initialize(self):
        """Initialize SQLite database with proper schema."""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        
        # Create tables
        self.connection.executescript("""
            -- Recent turns (short-term memory)
            CREATE TABLE IF NOT EXISTS recent_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                turn_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                user_input TEXT,
                assistant_response TEXT,
                assistant_plan TEXT,
                validation_result TEXT,
                execution_result TEXT,
                verification_result TEXT,
                response_type TEXT,
                success BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Episodic memory (summarized past interactions)
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                episode_id TEXT NOT NULL UNIQUE,
                title TEXT,
                summary TEXT,
                start_time TEXT,
                end_time TEXT,
                turn_count INTEGER,
                topics TEXT, -- JSON array
                outcome TEXT,
                embedding_hash TEXT, -- For similarity search
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Long-term profile (user preferences, facts)
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                category TEXT,
                confidence REAL DEFAULT 1.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key)
            );
            
            -- Taught synonyms
            CREATE TABLE IF NOT EXISTS synonyms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                phrase TEXT NOT NULL,
                canonical TEXT NOT NULL,
                scope TEXT DEFAULT 'general',
                usage_count INTEGER DEFAULT 0,
                taught_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, phrase)
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_recent_turns_user_time ON recent_turns(user_id, timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_episodes_user ON episodes(user_id, start_time DESC);
            CREATE INDEX IF NOT EXISTS idx_profiles_user ON user_profiles(user_id, category);
            CREATE INDEX IF NOT EXISTS idx_synonyms_user ON synonyms(user_id, phrase);
        """)
        
        self.connection.commit()
        self.logger.info("✅ SQLite memory store initialized")
    
    async def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
    
    def get_recent_turns(self, user_id: str, n: int = 8) -> List[Dict]:
        """Get the last N conversation turns for a user."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM recent_turns 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, n))
            
            rows = cursor.fetchall()
            turns = []
            
            for row in reversed(rows):  # Return in chronological order
                turn = {
                    "turn_id": row["turn_id"],
                    "timestamp": row["timestamp"],
                    "user": row["user_input"],
                    "assistant": row["assistant_response"],
                    "assistant_plan": json.loads(row["assistant_plan"]) if row["assistant_plan"] else {},
                    "validation": json.loads(row["validation_result"]) if row["validation_result"] else {},
                    "execution": json.loads(row["execution_result"]) if row["execution_result"] else {},
                    "verification": json.loads(row["verification_result"]) if row["verification_result"] else {},
                    "response_type": row["response_type"],
                    "success": bool(row["success"])
                }
                turns.append(turn)
            
            return turns
            
        except Exception as e:
            self.logger.error(f"Failed to get recent turns for {user_id}: {e}")
            return []
    
    def append_turn(self, user_id: str, turn: Dict) -> None:
        """Append a new conversation turn."""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO recent_turns (
                    user_id, turn_id, timestamp, user_input, assistant_response,
                    assistant_plan, validation_result, execution_result, 
                    verification_result, response_type, success
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                turn.get("turn_id"),
                turn.get("timestamp"),
                turn.get("user"),
                turn.get("assistant"),
                json.dumps(turn.get("assistant_plan", {})),
                json.dumps(turn.get("validation", {})),
                json.dumps(turn.get("execution", {})),
                json.dumps(turn.get("verification", {})),
                turn.get("response_type"),
                turn.get("success", False)
            ))
            
            self.connection.commit()
            
            # Clean up old turns (keep only last 50 per user)
            cursor.execute("""
                DELETE FROM recent_turns 
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM recent_turns 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 50
                )
            """, (user_id, user_id))
            
            self.connection.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to append turn for {user_id}: {e}")
    
    def search_episodes(self, user_id: str, query: str, k: int = 5) -> List[Dict]:
        """Search episodic memory (simplified text matching for now)."""
        try:
            cursor = self.connection.cursor()
            
            # Simple text search - in production, use vector embeddings
            cursor.execute("""
                SELECT * FROM episodes 
                WHERE user_id = ? AND (
                    title LIKE ? OR summary LIKE ? OR topics LIKE ?
                )
                ORDER BY start_time DESC 
                LIMIT ?
            """, (user_id, f"%{query}%", f"%{query}%", f"%{query}%", k))
            
            rows = cursor.fetchall()
            episodes = []
            
            for row in rows:
                episode = {
                    "episode_id": row["episode_id"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "turn_count": row["turn_count"],
                    "topics": json.loads(row["topics"]) if row["topics"] else [],
                    "outcome": row["outcome"]
                }
                episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            self.logger.error(f"Failed to search episodes for {user_id}: {e}")
            return []
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile and preferences."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT key, value, category, confidence 
                FROM user_profiles 
                WHERE user_id = ?
                ORDER BY category, key
            """, (user_id,))
            
            rows = cursor.fetchall()
            profile = {}
            
            for row in rows:
                category = row["category"] or "general"
                if category not in profile:
                    profile[category] = {}
                
                profile[category][row["key"]] = {
                    "value": row["value"],
                    "confidence": row["confidence"]
                }
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to get user profile for {user_id}: {e}")
            return {}
    
    def update_profile_item(self, user_id: str, key: str, value: str, 
                          category: str = "general", confidence: float = 1.0) -> None:
        """Update a specific profile item."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_profiles 
                (user_id, key, value, category, confidence, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, key, value, category, confidence))
            
            self.connection.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update profile for {user_id}: {e}")
    
    def store_synonym(self, user_id: str, phrase: str, synonym_data: Dict) -> bool:
        """Store a taught synonym."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO synonyms 
                (user_id, phrase, canonical, scope, usage_count, taught_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                phrase,
                synonym_data["canonical"],
                synonym_data["scope"],
                synonym_data["usage_count"],
                synonym_data["taught_at"]
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store synonym for {user_id}: {e}")
            return False
    
    def get_synonym(self, user_id: str, phrase: str) -> Optional[str]:
        """Resolve a phrase to its canonical form."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT canonical FROM synonyms 
                WHERE user_id = ? AND phrase = ?
            """, (user_id, phrase))
            
            row = cursor.fetchone()
            if row:
                # Increment usage count
                cursor.execute("""
                    UPDATE synonyms 
                    SET usage_count = usage_count + 1 
                    WHERE user_id = ? AND phrase = ?
                """, (user_id, phrase))
                self.connection.commit()
                
                return row["canonical"]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get synonym for {user_id}: {e}")
            return None
    
    def rollup_summaries(self, user_id: str) -> None:
        """Create episode summaries from old turns."""
        try:
            cursor = self.connection.cursor()
            
            # Find turns older than 24 hours that aren't summarized yet
            cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
            
            cursor.execute("""
                SELECT * FROM recent_turns 
                WHERE user_id = ? AND timestamp < ? 
                ORDER BY timestamp
                LIMIT 20
            """, (user_id, cutoff_time))
            
            old_turns = cursor.fetchall()
            
            if len(old_turns) >= 5:  # Only summarize if we have enough turns
                # Create episode summary
                episode_id = f"{user_id}_episode_{int(datetime.now().timestamp())}"
                
                topics = set()
                successful_turns = 0
                
                for turn in old_turns:
                    if turn["response_type"]:
                        topics.add(turn["response_type"])
                    if turn["success"]:
                        successful_turns += 1
                
                title = f"Conversation with {len(old_turns)} exchanges"
                summary = f"User had {len(old_turns)} interactions. Topics: {', '.join(topics)}. Success rate: {successful_turns/len(old_turns)*100:.0f}%"
                
                # Store episode
                cursor.execute("""
                    INSERT OR REPLACE INTO episodes 
                    (user_id, episode_id, title, summary, start_time, end_time, 
                     turn_count, topics, outcome)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, episode_id, title, summary,
                    old_turns[0]["timestamp"], old_turns[-1]["timestamp"],
                    len(old_turns), json.dumps(list(topics)),
                    "completed" if successful_turns > len(old_turns) / 2 else "mixed"
                ))
                
                # Delete old turns that were summarized
                old_turn_ids = [turn["turn_id"] for turn in old_turns]
                placeholders = ",".join("?" * len(old_turn_ids))
                cursor.execute(f"""
                    DELETE FROM recent_turns 
                    WHERE turn_id IN ({placeholders})
                """, old_turn_ids)
                
                self.connection.commit()
                self.logger.info(f"Created episode summary for {user_id}: {len(old_turns)} turns")
                
        except Exception as e:
            self.logger.error(f"Failed to rollup summaries for {user_id}: {e}")
    
    def cleanup_old_data(self, user_id: str, cutoff_date: datetime) -> None:
        """Clean up data older than cutoff date."""
        try:
            cursor = self.connection.cursor()
            cutoff_str = cutoff_date.isoformat()
            
            # Delete old episodes
            cursor.execute("""
                DELETE FROM episodes 
                WHERE user_id = ? AND start_time < ?
            """, (user_id, cutoff_str))
            
            deleted_episodes = cursor.rowcount
            
            self.connection.commit()
            
            if deleted_episodes > 0:
                self.logger.info(f"Cleaned up {deleted_episodes} old episodes for {user_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data for {user_id}: {e}")
    
    def count_episodes(self, user_id: str) -> int:
        """Count stored episodes for a user."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM episodes WHERE user_id = ?", (user_id,))
            return cursor.fetchone()["count"]
        except:
            return 0
    
    def count_synonyms(self, user_id: str) -> int:
        """Count taught synonyms for a user."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM synonyms WHERE user_id = ?", (user_id,))
            return cursor.fetchone()["count"]
        except:
            return 0
    
    def get_memory_size(self, user_id: str) -> float:
        """Get approximate memory size in MB."""
        # This is a rough estimate - actual implementation would be more sophisticated
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM recent_turns WHERE user_id = ?) * 1.0 +
                    (SELECT COUNT(*) FROM episodes WHERE user_id = ?) * 0.5 +
                    (SELECT COUNT(*) FROM user_profiles WHERE user_id = ?) * 0.1 +
                    (SELECT COUNT(*) FROM synonyms WHERE user_id = ?) * 0.1
                as size_kb
            """, (user_id, user_id, user_id, user_id))
            
            return cursor.fetchone()["size_kb"] / 1024  # Convert to MB
        except:
            return 0.0
    
    def get_oldest_memory_date(self, user_id: str) -> Optional[str]:
        """Get the oldest memory timestamp for a user."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT MIN(timestamp) as oldest FROM (
                    SELECT timestamp FROM recent_turns WHERE user_id = ?
                    UNION ALL
                    SELECT start_time as timestamp FROM episodes WHERE user_id = ?
                )
            """, (user_id, user_id))
            
            result = cursor.fetchone()
            return result["oldest"] if result else None
        except:
            return None


class JSONLMemoryStore(BaseMemoryStore):
    """JSONL-based memory store for development/testing."""
    
    def __init__(self, config: LeonardoConfig):
        super().__init__(config)
        self.memory_dir = Path("leonardo_memory")
        self.memory_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize JSONL store."""
        self.logger.info("✅ JSONL memory store initialized")
    
    def _get_user_file(self, user_id: str, file_type: str) -> Path:
        """Get file path for a user's memory type."""
        return self.memory_dir / f"{user_id}_{file_type}.jsonl"
    
    def get_recent_turns(self, user_id: str, n: int = 8) -> List[Dict]:
        """Get recent turns from JSONL file."""
        file_path = self._get_user_file(user_id, "turns")
        
        if not file_path.exists():
            return []
        
        turns = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        turns.append(json.loads(line))
        except Exception as e:
            self.logger.error(f"Failed to read turns file: {e}")
            return []
        
        return turns[-n:] if turns else []  # Return last n turns
    
    def append_turn(self, user_id: str, turn: Dict) -> None:
        """Append turn to JSONL file."""
        file_path = self._get_user_file(user_id, "turns")
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(turn, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to append turn: {e}")
    
    def search_episodes(self, user_id: str, query: str, k: int = 5) -> List[Dict]:
        """Search episodes (simplified for JSONL)."""
        file_path = self._get_user_file(user_id, "episodes")
        
        if not file_path.exists():
            return []
        
        episodes = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        episode = json.loads(line)
                        # Simple text matching
                        if (query.lower() in episode.get("summary", "").lower() or 
                            query.lower() in episode.get("title", "").lower()):
                            episodes.append(episode)
        except Exception as e:
            self.logger.error(f"Failed to search episodes: {e}")
        
        return episodes[:k]  # Return top k matches
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile from JSONL."""
        file_path = self._get_user_file(user_id, "profile")
        
        if not file_path.exists():
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except Exception as e:
            self.logger.error(f"Failed to read profile: {e}")
            return {}
    
    def update_profile_item(self, user_id: str, key: str, value: str, 
                          category: str = "general", confidence: float = 1.0) -> None:
        """Update profile item in JSONL."""
        profile = self.get_user_profile(user_id)
        
        if category not in profile:
            profile[category] = {}
        
        profile[category][key] = {
            "value": value,
            "confidence": confidence,
            "updated_at": datetime.now().isoformat()
        }
        
        file_path = self._get_user_file(user_id, "profile")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(profile, ensure_ascii=False))
        except Exception as e:
            self.logger.error(f"Failed to update profile: {e}")
    
    def store_synonym(self, user_id: str, phrase: str, synonym_data: Dict) -> bool:
        """Store synonym in JSONL."""
        file_path = self._get_user_file(user_id, "synonyms")
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                record = {"phrase": phrase, **synonym_data}
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            self.logger.error(f"Failed to store synonym: {e}")
            return False
    
    def get_synonym(self, user_id: str, phrase: str) -> Optional[str]:
        """Get synonym from JSONL."""
        file_path = self._get_user_file(user_id, "synonyms")
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get("phrase") == phrase:
                            return record.get("canonical")
        except Exception as e:
            self.logger.error(f"Failed to get synonym: {e}")
        
        return None
    
    def rollup_summaries(self, user_id: str) -> None:
        """Simplified rollup for JSONL."""
        # In a real implementation, this would create episode summaries
        # For now, we just log that it was called
        self.logger.debug(f"Rollup summaries called for {user_id}")
    
    def cleanup_old_data(self, user_id: str, cutoff_date: datetime) -> None:
        """Simplified cleanup for JSONL."""
        self.logger.debug(f"Cleanup old data called for {user_id}")
    
    def count_episodes(self, user_id: str) -> int:
        """Count episodes in JSONL."""
        file_path = self._get_user_file(user_id, "episodes")
        
        if not file_path.exists():
            return 0
        
        count = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        count += 1
        except:
            pass
        
        return count
    
    def count_synonyms(self, user_id: str) -> int:
        """Count synonyms in JSONL."""
        file_path = self._get_user_file(user_id, "synonyms")
        
        if not file_path.exists():
            return 0
        
        count = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        count += 1
        except:
            pass
        
        return count
    
    def get_memory_size(self, user_id: str) -> float:
        """Get approximate memory size for JSONL."""
        total_size = 0
        
        for file_type in ["turns", "episodes", "profile", "synonyms"]:
            file_path = self._get_user_file(user_id, file_type)
            if file_path.exists():
                total_size += file_path.stat().st_size
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def get_oldest_memory_date(self, user_id: str) -> Optional[str]:
        """Get oldest memory date from JSONL."""
        oldest = None
        
        # Check turns file
        turns = self.get_recent_turns(user_id, 1000)  # Get a lot to find oldest
        if turns:
            oldest = turns[0].get("timestamp")
        
        return oldest
