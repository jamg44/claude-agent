"""Storage layer for conversation persistence using SQLite"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

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
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

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

    def create_conversation(self, title: str = None) -> int:
        """Create a new conversation and return its ID"""
        if not title:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO conversations (title) VALUES (?)",
                (title,)
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
                SELECT id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                """
            )

            rows = cursor.fetchall()

        conversations = []
        for row in rows:
            conversations.append({
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3]
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
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,)
            )

            row = cursor.fetchone()

        if row:
            return {
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3]
            }
        return None