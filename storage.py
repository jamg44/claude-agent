"""Storage layer for conversation persistence using SQLite"""
import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

DEFAULT_USER_ID = "default"

def serialize_content(content) -> str:
    """Convert Anthropic content blocks to JSON-serializable format

    Args:
        content: Can be string, list of blocks, dict, or Anthropic objects

    Returns:
        JSON string
    """
    if isinstance(content, str):
        return content

    if isinstance(content, (list, tuple)):
        # Convert list of blocks to dicts
        serializable = []
        for item in content:
            if hasattr(item, 'model_dump'):
                # Anthropic SDK objects have model_dump()
                serializable.append(item.model_dump())
            elif isinstance(item, dict):
                serializable.append(item)
            else:
                serializable.append(str(item))
        return json.dumps(serializable)

    if isinstance(content, dict):
        return json.dumps(content)

    if hasattr(content, 'model_dump'):
        # Single Anthropic object
        return json.dumps(content.model_dump())

    # Fallback to string
    return str(content)


class ConversationStorage:
    """Manages conversation persistence in SQLite"""

    def __init__(self, db_path: str = "./data/conversations.db"):
        """Initialize storage with database path"""
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Create SQLite connection with consistent settings"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Create tables if they don't exist"""
        # Ensure target directory exists when using nested db paths
        db_parent = Path(self.db_path).parent
        db_parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            cursor = conn.cursor()

            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Backward compatibility: add user_id to older databases
            cursor.execute("PRAGMA table_info(conversations)")
            columns = {row[1] for row in cursor.fetchall()}
            if "user_id" not in columns:
                cursor.execute(
                    "ALTER TABLE conversations ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'"
                )

            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    role TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)

            # Cross-conversation memory snippets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_conversation_id INTEGER,
                    confidence REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_conversation_id) REFERENCES conversations(id)
                )
            """)

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_user_id_updated ON memories(user_id, updated_at DESC)"
            )

    def create_conversation(self, title: str = None, user_id: str = DEFAULT_USER_ID) -> int:
        """Create a new conversation and return its ID"""
        if not title:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
                (user_id, title)
            )

            conversation_id = cursor.lastrowid

        return conversation_id

    def add_message(self, conversation_id: int, role: str, content: str | list | dict):
        """Add a message to a conversation

        Args:
            conversation_id: The conversation ID
            role: 'user' or 'assistant'
            content: Message content (string, list, dict, or Anthropic objects)
        """
        # Serialize content to JSON
        content_str = serialize_content(content)

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content_str)
            )

            # Update conversation's updated_at
            cursor.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,)
            )

    def get_messages(self, conversation_id: int) -> List[Dict]:
        """Get all messages for a conversation

        Returns:
            List of message dicts with 'role' and 'content' keys in Anthropic format
        """
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT role, content FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,)
            )

            rows = cursor.fetchall()

        messages = []
        for row in rows:
            role, content = row

            # Try to parse JSON content
            try:
                parsed_content = json.loads(content)

                # Clean Anthropic objects - remove extra fields
                if isinstance(parsed_content, list):
                    cleaned_content = []
                    for item in parsed_content:
                        if isinstance(item, dict):
                            # Keep only essential fields based on type
                            if item.get('type') == 'text':
                                cleaned_content.append({
                                    'type': 'text',
                                    'text': item.get('text', '')
                                })
                            elif item.get('type') == 'tool_use':
                                cleaned_content.append({
                                    'type': 'tool_use',
                                    'id': item.get('id', ''),
                                    'name': item.get('name', ''),
                                    'input': item.get('input', {})
                                })
                            elif item.get('type') == 'tool_result':
                                cleaned_content.append({
                                    'type': 'tool_result',
                                    'tool_use_id': item.get('tool_use_id', ''),
                                    'content': item.get('content', '')
                                })
                            else:
                                # Keep other types as-is
                                cleaned_content.append(item)
                        else:
                            cleaned_content.append(item)

                    content = cleaned_content
                else:
                    content = parsed_content

            except (json.JSONDecodeError, TypeError):
                # Keep as string if not valid JSON
                pass

            messages.append({
                "role": role,
                "content": content
            })

        return messages

    def list_conversations(self) -> List[Dict]:
        """List all conversations

        Returns:
            List of conversation dicts with id, title, created_at, updated_at
        """
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                """
            )

            rows = cursor.fetchall()

        conversations = []
        for row in rows:
            conversations.append({
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            })
        return conversations

    def list_conversations_by_user(self, user_id: str) -> List[Dict]:
        """List all conversations for a user"""
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,)
            )

            rows = cursor.fetchall()

        conversations = []
        for row in rows:
            conversations.append({
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            })
        return conversations

    def get_conversation(self, conversation_id: int) -> Optional[Dict]:
        """Get conversation details

        Returns:
            Dict with id, title, created_at, updated_at or None if not found
        """
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,)
            )

            row = cursor.fetchone()

        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            }
        return None

    def save_memory(
        self,
        user_id: str,
        content: str,
        source_conversation_id: int | None = None,
        confidence: float = 1.0
    ) -> int:
        """Store a cross-conversation memory snippet for a user"""
        content = (content or "").strip()
        if not content:
            raise ValueError("Memory content cannot be empty")

        with self._connect() as conn:
            cursor = conn.cursor()

            # Deduplicate exact same memory for same user
            cursor.execute(
                """
                SELECT id FROM memories
                WHERE user_id = ? AND content = ?
                LIMIT 1
                """,
                (user_id, content)
            )
            existing = cursor.fetchone()

            if existing:
                memory_id = existing[0]
                cursor.execute(
                    """
                    UPDATE memories
                    SET updated_at = CURRENT_TIMESTAMP,
                        confidence = CASE WHEN confidence < ? THEN ? ELSE confidence END
                    WHERE id = ?
                    """,
                    (confidence, confidence, memory_id)
                )
                return memory_id

            cursor.execute(
                """
                INSERT INTO memories (user_id, content, source_conversation_id, confidence)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, content, source_conversation_id, confidence)
            )
            return cursor.lastrowid

    def get_relevant_memories(
        self,
        user_id: str,
        query: str,
        max_items: int = 5,
        max_chars: int = 700
    ) -> List[str]:
        """Retrieve compact, relevant memories for a user without bloating context"""
        words = [
            word for word in re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", query.lower())
            if len(word) >= 4
        ]

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, content, confidence, updated_at
                FROM memories
                WHERE user_id = ?
                ORDER BY updated_at DESC, confidence DESC
                LIMIT 100
                """,
                (user_id,)
            )
            candidates = cursor.fetchall()

        if not candidates:
            return []

        scored = []
        for memory_id, content, confidence, updated_at in candidates:
            lowered = content.lower()
            keyword_hits = sum(1 for w in words if w in lowered)
            score = (keyword_hits * 10) + confidence
            scored.append((score, updated_at, memory_id, content))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

        selected = []
        used_chars = 0
        for score, _updated_at, memory_id, content in scored:
            if score <= 0 and words:
                continue

            memory_text = content.strip()
            if not memory_text:
                continue

            projected = used_chars + len(memory_text)
            if projected > max_chars:
                continue

            selected.append((memory_id, memory_text))
            used_chars = projected
            if len(selected) >= max_items:
                break

        return [content for _, content in selected]

    def list_memories(self, user_id: str, limit: int = 20) -> List[Dict]:
        """List latest stored memories for a user"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, content, confidence, source_conversation_id, created_at, updated_at
                FROM memories
                WHERE user_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit)
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "content": row[1],
                "confidence": row[2],
                "source_conversation_id": row[3],
                "created_at": row[4],
                "updated_at": row[5],
            }
            for row in rows
        ]

    def clear_memories(self, user_id: str) -> int:
        """Delete all memories for a user and return deleted count"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,))
            total = cursor.fetchone()[0]
            cursor.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            return total