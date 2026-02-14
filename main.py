import os
from anthropic import Anthropic
from dotenv import load_dotenv
from tools import TOOL_DEFINITIONS, TOOL_EXECUTORS
from storage import ConversationStorage

# Load environment variables from .env file
load_dotenv()

# Initialize client and storage
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
storage = ConversationStorage()
MODEL = "claude-sonnet-4-20250514"


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name using the registry"""
    executor = TOOL_EXECUTORS.get(tool_name)

    if executor:
        return executor(tool_input)

    return f"Tool not found: {tool_name}"


def run_agent(
    user_message: str,
    conversation_id: int = None,
    system_prompt: str = None
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
        conversation_id = storage.create_conversation()
        messages = []
        print(f"\n🆕 New conversation (ID: {conversation_id})")
    else:
        # Load conversation history
        conv = storage.get_conversation(conversation_id)
        if conv is None:
            conversation_id = storage.create_conversation()
            messages = []
            print(f"\n⚠️ Conversation not found. Started new one (ID: {conversation_id})")
        else:
            messages = storage.get_messages(conversation_id)
            print(f"\n📖 Continuing: {conv['title']} (ID: {conversation_id})")
            print(f"   {len(messages)} previous messages loaded")

    # Add new user message
    print(f"\n🧑 User: {user_message}\n")
    messages.append({"role": "user", "content": user_message})
    storage.add_message(conversation_id, "user", user_message)

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

        # Add system prompt if provided
        if system_prompt:
            request_params["system"] = system_prompt

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
        print(f"ID: {conv['id']} | {conv['title']}")
        print(f"   Created: {conv['created_at']} | Updated: {conv['updated_at']}")
        print("-" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("AGENT WITH MEMORY DEMO")
    print("=" * 80)

    system_prompt = (
        "Eres un buen asistente que habla en español, puede usar tools y responde rápido. "
        "Usa herramientas cuando sea necesario y proporciona respuestas claras."
    )

    # Demo 1: Start new conversation
    conv_id = run_agent("Cuanto es 10 + 5?", system_prompt=system_prompt)

    # Demo 2: Continue same conversation - Claude should remember context
    run_agent("Ahora multiplica ese resultado por 3", conversation_id=conv_id, system_prompt=system_prompt)

    # Demo 3: Test memory
    run_agent("¿Cuál fue mi primera pregunta?", conversation_id=conv_id, system_prompt=system_prompt)

    # List all conversations
    # list_conversations()

    # Interactive mode
    print("\n" + "=" * 80)
    print("💬 Interactive mode - Type 'quit' to exit, 'list' to see conversations")
    print("=" * 80)

    while True:
        user_input = input("\n🧑 You: ").strip()

        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'list':
            list_conversations()
            continue
        elif user_input:
            conv_id = run_agent(user_input, conversation_id=conv_id, system_prompt=system_prompt)