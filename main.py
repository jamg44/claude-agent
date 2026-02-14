import os
import re
from anthropic import Anthropic
from dotenv import load_dotenv
from tools import TOOL_DEFINITIONS, TOOL_EXECUTORS
from storage import ConversationStorage, DEFAULT_USER_ID

# Load environment variables from .env file
load_dotenv()

# Initialize client and storage
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
storage = ConversationStorage()
MODEL = "claude-sonnet-4-20250514"

MEMORY_TRIGGER_KEYWORDS = (
    "recuerda", "remember", "otra conversación", "conversación anterior",
    "como te dije", "como dije", "mi perfil", "mis preferencias",
    "sobre mí", "mi proyecto", "mi stack", "my preferences", "my profile"
)

MEMORY_CAPTURE_MARKERS = (
    "mi nombre es", "me llamo", "soy ", "trabajo en", "trabajo con",
    "prefiero", "me gusta", "uso ", "vivo en", "estoy aprendiendo",
    "i am ", "i work", "i prefer", "i like", "my name is"
)


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name using the registry"""
    executor = TOOL_EXECUTORS.get(tool_name)

    if executor:
        return executor(tool_input)

    return f"Tool not found: {tool_name}"


def should_load_cross_memory(user_message: str) -> bool:
    """Detect when cross-conversation memory is likely useful"""
    lowered = user_message.lower()
    return any(keyword in lowered for keyword in MEMORY_TRIGGER_KEYWORDS)


def memory_budget(user_message: str) -> tuple[int, int]:
    """Dynamic memory budget based on intent and input length"""
    if should_load_cross_memory(user_message):
        return 5, 1000

    if len(user_message) > 180:
        return 4, 800

    return 3, 550


def build_system_prompt_with_memory(
    system_prompt: str | None,
    memory_snippets: list[str]
) -> str | None:
    """Append compact memory context to system prompt when available"""
    if not memory_snippets and not system_prompt:
        return None

    base_prompt = system_prompt.strip() if system_prompt else ""
    if not memory_snippets:
        return base_prompt

    memory_block = "\n".join([f"- {snippet}" for snippet in memory_snippets])
    memory_section = (
        "Memoria útil de conversaciones anteriores (si aplica a esta petición):\n"
        f"{memory_block}\n"
        "Úsala solo cuando sea relevante; no inventes hechos faltantes."
    )

    if base_prompt:
        return f"{base_prompt}\n\n{memory_section}"
    return memory_section


def extract_memory_candidates(user_message: str) -> list[str]:
    """Extract stable user facts/preferences with lightweight heuristics"""
    normalized = " ".join(user_message.strip().split())
    lowered = normalized.lower()

    if len(normalized) < 18:
        return []

    if normalized.endswith("?") and "recuerda que" not in lowered:
        return []

    candidates = []

    explicit_match = re.search(r"recuerda que\s+(.+)$", normalized, flags=re.IGNORECASE)
    if explicit_match:
        explicit_memory = explicit_match.group(1).strip(" .")
        if len(explicit_memory) >= 8:
            candidates.append(explicit_memory)

    if any(marker in lowered for marker in MEMORY_CAPTURE_MARKERS):
        trimmed = normalized.strip(" .")
        if len(trimmed) <= 220:
            candidates.append(trimmed)
        else:
            candidates.append(trimmed[:220].rstrip() + "...")

    # Deduplicate preserving order
    unique = []
    for item in candidates:
        if item and item not in unique:
            unique.append(item)

    return unique


def run_agent(
    user_message: str,
    conversation_id: int = None,
    system_prompt: str = None,
    user_id: str = DEFAULT_USER_ID
) -> int:
    """Execute the agent with streaming and persistent memory

    Args:
        user_message: The user's question/request
        conversation_id: Optional conversation ID to continue. If None, creates new conversation
        system_prompt: Optional system prompt to control agent behavior

    Returns:
        The conversation_id (new or existing)
    """

    # Create new conversation or load existing
    if conversation_id is None:
        conversation_id = storage.create_conversation(user_id=user_id)
        messages = []
        print(f"\n🆕 New conversation (ID: {conversation_id}, user: {user_id})")
    else:
        # Load conversation history
        conv = storage.get_conversation(conversation_id)
        if conv is None or conv["user_id"] != user_id:
            conversation_id = storage.create_conversation(user_id=user_id)
            messages = []
            print(
                f"\n⚠️ Conversation not found for user '{user_id}'. "
                f"Started new one (ID: {conversation_id})"
            )
        else:
            messages = storage.get_messages(conversation_id)
            print(f"\n📖 Continuing: {conv['title']} (ID: {conversation_id})")
            print(f"   {len(messages)} previous messages loaded")

    # Add new user message
    print(f"\n🧑 User: {user_message}\n")
    messages.append({"role": "user", "content": user_message})
    storage.add_message(conversation_id, "user", user_message)

    # Save candidate long-term memories from user input
    for candidate in extract_memory_candidates(user_message):
        storage.save_memory(user_id=user_id, content=candidate, source_conversation_id=conversation_id)

    # Safety: max iterations to prevent infinite loops
    max_iterations = 10
    iteration = 0

    # Main loop
    while iteration < max_iterations:
        iteration += 1
        print(f"--- Iteration {iteration} ---")

        request_params = {
            "model": MODEL,
            "max_tokens": 1024,
            "tools": TOOL_DEFINITIONS,
            "messages": messages
        }

        max_items, max_chars = memory_budget(user_message)
        memory_snippets = storage.get_relevant_memories(
            user_id=user_id,
            query=user_message,
            max_items=max_items,
            max_chars=max_chars
        )
        merged_system_prompt = build_system_prompt_with_memory(system_prompt, memory_snippets)

        # Add system prompt if provided or memory is available
        if merged_system_prompt:
            request_params["system"] = merged_system_prompt

        # Stream only text content
        with client.messages.stream(**request_params) as stream:
            for event in stream:
                # Only stream text deltas
                if event.type == "content_block_delta":
                    if hasattr(event.delta, 'text'):
                        print(event.delta.text, end='', flush=True)

            # Get final message
            response = stream.get_final_message()

        print()  # New line after streaming
        print(f"Stop reason: {response.stop_reason}")

        # Process response
        if response.stop_reason == "end_turn":
            print(f"\n✅ Agent completed\n")

            # Save assistant response to storage
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            storage.add_message(conversation_id, "assistant", response.content)

            return conversation_id

        elif response.stop_reason == "tool_use":
            # LLM wants to use tools
            # Add LLM's response to history
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            # Save to storage
            storage.add_message(conversation_id, "assistant", response.content)

            # Execute all requested tools
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    print(f"\n🔧 Executing tool: {tool_name}")
                    print(f"   Input: {tool_input}")

                    # Execute the tool
                    result = execute_tool(tool_name, tool_input)
                    print(f"   Result: {result}\n")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Add results to history
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Save tool results to storage
            storage.add_message(conversation_id, "user", tool_results)

        else:
            print(f"⚠️  Unexpected stop_reason: {response.stop_reason}")
            return conversation_id

    print(f"⚠️  Max iterations ({max_iterations}) reached. Stopping.")
    return conversation_id


def list_conversations():
    """List all saved conversations"""
    convs = storage.list_conversations()

    if not convs:
        print("\nNo conversations found.")
        return

    print("\n" + "=" * 80)
    print("📚 Saved Conversations")
    print("=" * 80)
    for conv in convs:
        print(f"ID: {conv['id']} | user: {conv.get('user_id', DEFAULT_USER_ID)} | {conv['title']}")
        print(f"   Created: {conv['created_at']} | Updated: {conv['updated_at']}")
        print("-" * 80)


def show_memories(user_id: str):
    """Show stored cross-conversation memories for user"""
    memories = storage.list_memories(user_id=user_id)

    if not memories:
        print(f"\nNo memories found for user '{user_id}'.")
        return

    print("\n" + "=" * 80)
    print(f"🧠 Memories for user: {user_id}")
    print("=" * 80)
    for memory in memories:
        source = memory["source_conversation_id"]
        print(f"ID: {memory['id']} | source_conv: {source} | score: {memory['confidence']}")
        print(f"   {memory['content']}")
        print(f"   Updated: {memory['updated_at']}")
        print("-" * 80)


def clear_memories(user_id: str):
    """Clear all stored memories for user"""
    deleted = storage.clear_memories(user_id=user_id)
    print(f"\n🗑️ Deleted {deleted} memories for user '{user_id}'.")


if __name__ == "__main__":
    print("=" * 80)
    print("AGENT WITH MEMORY DEMO")
    print("=" * 80)

    system_prompt = (
        "Eres un buen asistente que habla en español, puede usar tools y responde rápido. "
        "Usa herramientas cuando sea necesario y proporciona respuestas claras."
    )

    # Demo 1: Start new conversation
    # conv_id = run_agent("Cuanto es 10 + 5?", system_prompt=system_prompt)

    # Demo 2: Continue same conversation - Claude should remember context
    # run_agent("Ahora multiplica ese resultado por 3", conversation_id=conv_id, system_prompt=system_prompt)

    # Demo 3: Test memory
    # run_agent("¿Cuál fue mi primera pregunta?", conversation_id=conv_id, system_prompt=system_prompt)

    # List all conversations
    # list_conversations()

    # Interactive mode
    conv_id = None
    user_id = DEFAULT_USER_ID

    print("\n" + "=" * 80)
    print("💬 Interactive mode - Commands: 'quit', 'list', 'mem', 'mem clear'")
    print("=" * 80)

    while True:
        user_input = input("\n🧑 You: ").strip()

        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'list':
            list_conversations()
            continue
        elif user_input.lower() == 'mem':
            show_memories(user_id)
            continue
        elif user_input.lower() == 'mem clear':
            clear_memories(user_id)
            continue
        elif user_input:
            conv_id = run_agent(
                user_input,
                conversation_id=conv_id,
                system_prompt=system_prompt,
                user_id=user_id
            )