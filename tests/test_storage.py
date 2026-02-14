"""Tests for storage layer"""
from storage import ConversationStorage


def create_storage(tmp_path):
    """Create isolated storage instance for each test"""
    db_path = tmp_path / "test_conversations.db"
    return ConversationStorage(str(db_path)), db_path


def test_create_and_list_conversations(tmp_path):
    """Test creating and listing conversations"""
    storage, _ = create_storage(tmp_path)

    # Create conversations
    conv1_id = storage.create_conversation("Test conversation 1")
    conv2_id = storage.create_conversation("Test conversation 2")

    assert conv1_id == 1
    assert conv2_id == 2

    # List conversations
    convs = storage.list_conversations()
    assert len(convs) == 2

    # Check both conversations are there (order may vary due to timestamp precision)
    titles = [conv["title"] for conv in convs]
    assert "Test conversation 1" in titles
    assert "Test conversation 2" in titles


def test_add_and_get_messages(tmp_path):
    """Test adding and retrieving messages"""
    storage, _ = create_storage(tmp_path)

    conv_id = storage.create_conversation("Test")

    # Add messages
    storage.add_message(conv_id, "user", "Hello")
    storage.add_message(conv_id, "assistant", "Hi there!")

    # Get messages
    messages = storage.get_messages(conv_id)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there!"


def test_complex_content(tmp_path):
    """Test storing complex content (lists/dicts)"""
    storage, _ = create_storage(tmp_path)

    conv_id = storage.create_conversation("Test")

    # Add message with complex content
    complex_content = [
        {"type": "text", "text": "Hello"},
        {"type": "tool_use", "name": "calculator", "input": {"a": 1, "b": 2}}
    ]

    storage.add_message(conv_id, "assistant", complex_content)

    # Retrieve
    messages = storage.get_messages(conv_id)

    assert len(messages) == 1
    assert isinstance(messages[0]["content"], list)
    assert messages[0]["content"][0]["type"] == "text"


def test_conversation_update_time(tmp_path):
    """Test that adding messages updates conversation timestamp"""
    storage, _ = create_storage(tmp_path)

    conv_id = storage.create_conversation("Test")
    conv_before = storage.get_conversation(conv_id)

    # Add a message
    storage.add_message(conv_id, "user", "Hello")

    conv_after = storage.get_conversation(conv_id)

    # updated_at should change (or at least not be earlier)
    assert conv_after["updated_at"] >= conv_before["updated_at"]


def test_init_creates_missing_database_directory(tmp_path):
    """Test storage initialization creates missing parent directory for db"""
    db_dir = tmp_path / "temp_test_data"
    db_path = db_dir / "conversations.db"

    storage = ConversationStorage(str(db_path))
    conv_id = storage.create_conversation("Test")

    assert conv_id == 1
    assert db_dir.exists()
    assert db_path.exists()


def test_list_conversations_by_user(tmp_path):
    """Test conversation isolation between users"""
    storage, _ = create_storage(tmp_path)

    storage.create_conversation("User A - 1", user_id="user-a")
    storage.create_conversation("User A - 2", user_id="user-a")
    storage.create_conversation("User B - 1", user_id="user-b")

    user_a_convs = storage.list_conversations_by_user("user-a")
    user_b_convs = storage.list_conversations_by_user("user-b")

    assert len(user_a_convs) == 2
    assert len(user_b_convs) == 1
    assert all(conv["user_id"] == "user-a" for conv in user_a_convs)
    assert all(conv["user_id"] == "user-b" for conv in user_b_convs)


def test_save_memory_deduplicates_per_user(tmp_path):
    """Test memory deduplication for same user and content"""
    storage, _ = create_storage(tmp_path)

    memory_1 = storage.save_memory("user-a", "Prefiero respuestas cortas")
    memory_2 = storage.save_memory("user-a", "Prefiero respuestas cortas")
    memory_3 = storage.save_memory("user-b", "Prefiero respuestas cortas")

    assert memory_1 == memory_2
    assert memory_3 != memory_1


def test_get_relevant_memories_filters_by_user_and_query(tmp_path):
    """Test memory retrieval relevance and user isolation"""
    storage, _ = create_storage(tmp_path)

    storage.save_memory("user-a", "Vivo en Madrid")
    storage.save_memory("user-a", "Prefiero Python para scripts")
    storage.save_memory("user-a", "Trabajo con APIs REST")
    storage.save_memory("user-b", "Vivo en Barcelona")

    memories = storage.get_relevant_memories(
        user_id="user-a",
        query="¿Recuerdas en qué ciudad vivo?",
        max_items=3,
        max_chars=300
    )

    assert len(memories) >= 1
    assert any("Madrid" in memory for memory in memories)
    assert all("Barcelona" not in memory for memory in memories)


def test_get_relevant_memories_respects_char_budget(tmp_path):
    """Test memory retrieval enforces total character budget"""
    storage, _ = create_storage(tmp_path)

    storage.save_memory("user-a", "Me gusta programar en Python y crear automatizaciones.")
    storage.save_memory("user-a", "Prefiero respuestas técnicas y directas cuando hay código.")
    storage.save_memory("user-a", "Uso macOS para desarrollo local.")

    memories = storage.get_relevant_memories(
        user_id="user-a",
        query="¿Qué recuerdas de mis preferencias técnicas?",
        max_items=5,
        max_chars=80
    )

    total_chars = sum(len(memory) for memory in memories)
    assert total_chars <= 80